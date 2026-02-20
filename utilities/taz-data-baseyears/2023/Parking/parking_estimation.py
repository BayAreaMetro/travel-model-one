"""
Parking Cost Estimation Module

This module provides statistical modeling for estimating parking costs in TAZ zones
without observed data. It implements a hybrid approach:

Architecture:
- **Hourly parking (OPRKCST)**: Machine learning classification with model comparison
  - Supports multiple models: Logistic Regression, Random Forest, Gradient Boosting, SVM
  - Trains on San Francisco, Oakland, San Jose, Berkeley observed meter data (paid vs free)
  - Uses stratified 5-fold cross-validation for robust model selection
  - Ensures balanced paid/free parking distribution in each fold
  - Predicts paid/free for other cities with parking capacity
  - Assigns flat $2.00/hr rate to predicted paid parking TAZs
  
- **Long-term parking (PRKCST)**: County-level density thresholds
  - Uses commercial employment density percentiles within each county
  - Percentile is configurable (default: 95th percentile)
  - Combines daily and monthly parking into single long-term cost
  - Assigns discounted rates for non-core cities (65% of SF/Oak/SJ observed median)

Key Constraints:
- Hourly predictions (OPRKCST) only where on_all > 0 (on-street capacity)
- Long-term predictions (PRKCST) only where off_nres > 0 (off-street capacity)
- All predictions only in cities (place_name not null)
- Predictions exclude SF/Oakland/SJ/Berkeley (those use observed data only)
- Minimum commercial_emp_den threshold for paid parking consideration

Workflow:
1. add_density_features(): Calculate employment densities + AREATYPE one-hot encoding
2. report_county_density_distributions(): Diagnostic percentile report by county
3. stratified_kfold_validation(): 5-fold CV with balanced paid/free samples (default)
4. estimate_and_validate_hourly_parking_models(): Model selection orchestration
5. apply_hourly_parking_model(): Apply selected model for hourly parking (OPRKCST)
6. estimate_parking_by_county_threshold(): Threshold-based long-term parking (PRKCST)

Model-Specific Features:
- Linear models (Logistic Regression, SVM): 4 density features
- Tree-based models (Random Forest, Gradient Boosting): 4 density + 3 AREATYPE features

Entry Point:
- main(): Standalone script execution
- merge_hourly_cost(): Function called from land_use_pipeline.py orchestration
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import sys
import argparse
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import StratifiedKFold

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import INTERIM_CACHE_DIR, ANALYSIS_CRS
from parking_capacity import get_parking_capacity


# ============================================================================
# Feature Configuration for Parking Cost Estimation Models
# ============================================================================

# Base employment density and population features (used by all models)
BASE_FEATURES = [
    'commercial_emp_den',
    'downtown_emp_den',
    'pop_den',
    'edhealthrec_emp_den'
]

# AREATYPE one-hot encoded features (spatial hierarchy)
# Captures urban form: CBD, Urban Business, Urban (Regional Core is baseline)
# Only used by tree-based models to avoid overfitting in linear models
AREATYPE_FEATURES = [
    'areatype_cbd',             # AREATYPE = 1 (Central Business District)
    'areatype_urban_business',  # AREATYPE = 2 (Urban Business)
    'areatype_urban'            # AREATYPE = 3 (Urban)
    # AREATYPE = 0 (Regional Core) is baseline - omitted to avoid multicollinearity
    # AREATYPE = 4 (Suburban) and 5 (Rural) excluded from predictions
]

# Model-to-feature mapping
# Linear models (Logistic Regression, SVM): Use BASE_FEATURES only
# Tree-based models (Random Forest, Gradient Boosting): Use BASE_FEATURES + AREATYPE_FEATURES
MODEL_FEATURE_SETS = {
    'Logistic Regression': BASE_FEATURES,
    'Random Forest': BASE_FEATURES + AREATYPE_FEATURES,
    'Gradient Boosting': BASE_FEATURES + AREATYPE_FEATURES,
    'SVM (RBF)': BASE_FEATURES
}


def get_features_for_model(model_name):
    """
    Get appropriate feature list for a given model.
    
    Tree-based models get AREATYPE features to learn spatial hierarchy,
    while linear models use density features only to avoid overfitting.
    
    Args:
        model_name (str): Name of the model (e.g., 'Random Forest', 'Logistic Regression')
    
    Returns:
        list: Feature column names for the model
    """
    return MODEL_FEATURE_SETS.get(model_name, BASE_FEATURES)


def get_observed_cities_from_scraped_data(scraped_file_path):
    """
    Extract unique city names from scraped parking data.
    
    Args:
        scraped_file_path (Path): Path to parking_scrape_location_cost.parquet file
    
    Returns:
        List[str]: Sorted list of unique city names with observed parking data.
                  Returns default cities ['San Francisco', 'Oakland', 'San Jose', 'Berkeley'] if file not found.
    """
    # Default observed cities (used if scraped data file doesn't exist)
    default_cities = ['San Francisco', 'Oakland', 'San Jose', 'Berkeley']
    
    if not scraped_file_path.exists():
        print(f"  Note: Scraped parking data file not found: {scraped_file_path}")
        print(f"  Using default observed cities: {', '.join(default_cities)}")
        return default_cities
    
    # Load scraped parking data
    scraped = pd.read_parquet(scraped_file_path)
    
    # Extract unique cities and sort alphabetically
    observed_cities = sorted(scraped['city'].unique().tolist())
    
    return observed_cities


def add_density_features(taz):
    """
    Add employment density features for parking cost estimation.
    
    Args:
        taz (GeoDataFrame): TAZ zones with employment columns and TOTACRE
    
    Returns:
        GeoDataFrame: TAZ with added density feature columns
    """
    print("Calculating density features for parking cost estimation...")
    
    # Map TAZ land use employment categories to parking model features
    # RETEMPN: Retail employment → commercial_emp
    # FPSEMPN: Financial and professional services employment → downtown_emp
    # HEREMPN: Health, education, and recreational employment → edhealthrec_emp
    taz['commercial_emp'] = taz['RETEMPN']
    taz['downtown_emp'] = taz['FPSEMPN']
    taz['edhealthrec_emp'] = taz['HEREMPN']
    
    # One-hot encode AREATYPE (0=Regional Core, 1=CBD, 2=Urban Business, 3=Urban)
    # Regional Core (0) is baseline - omitted to avoid multicollinearity
    # AREATYPE 4 (suburban) and 5 (rural) excluded from predictions
    taz['areatype_cbd'] = (taz['AREATYPE'] == 1).astype(int)
    taz['areatype_urban_business'] = (taz['AREATYPE'] == 2).astype(int)
    taz['areatype_urban'] = (taz['AREATYPE'] == 3).astype(int)
    
    # Calculate densities (jobs per acre)
    # Use np.where to avoid division by zero
    taz['commercial_emp_den'] = np.where(
        taz['TOTACRE'] > 0,
        taz['commercial_emp'] / taz['TOTACRE'],
        0
    )
    
    taz['downtown_emp_den'] = np.where(
        taz['TOTACRE'] > 0,
        taz['downtown_emp'] / taz['TOTACRE'],
        0
    )
    
    taz['edhealthrec_emp_den'] = np.where(
        taz['TOTACRE'] > 0,
        taz['edhealthrec_emp'] / taz['TOTACRE'],
        0
    )
    
    taz['emp_total_den'] = np.where(
        taz['TOTACRE'] > 0,
        taz['TOTEMP'] / taz['TOTACRE'],
        0
    )
    
    # Calculate population density
    taz['pop_den'] = np.where(
        taz['TOTACRE'] > 0,
        taz['TOTPOP'] / taz['TOTACRE'],
        0
    )
    
    # Report statistics
    print(f"  Commercial employment density (jobs/acre):")
    print(f"    Mean: {taz['commercial_emp_den'].mean():.2f}")
    print(f"    Median: {taz['commercial_emp_den'].median():.2f}")
    print(f"    90th percentile: {taz['commercial_emp_den'].quantile(0.90):.2f}")
    print(f"    95th percentile: {taz['commercial_emp_den'].quantile(0.95):.2f}")
    
    print(f"  Downtown employment density (jobs/acre):")
    print(f"    Mean: {taz['downtown_emp_den'].mean():.2f}")
    print(f"    Median: {taz['downtown_emp_den'].median():.2f}")
    print(f"    90th percentile: {taz['downtown_emp_den'].quantile(0.90):.2f}")
    print(f"    95th percentile: {taz['downtown_emp_den'].quantile(0.95):.2f}")
    
    print(f"  Population density (people/acre):")
    print(f"    Mean: {taz['pop_den'].mean():.2f}")
    print(f"    Median: {taz['pop_den'].median():.2f}")
    print(f"    90th percentile: {taz['pop_den'].quantile(0.90):.2f}")
    print(f"    95th percentile: {taz['pop_den'].quantile(0.95):.2f}")
    
    print(f"  Health/Education/Recreation employment density (jobs/acre):")
    print(f"    Mean: {taz['edhealthrec_emp_den'].mean():.2f}")
    print(f"    Median: {taz['edhealthrec_emp_den'].median():.2f}")
    print(f"    90th percentile: {taz['edhealthrec_emp_den'].quantile(0.90):.2f}")
    print(f"    95th percentile: {taz['edhealthrec_emp_den'].quantile(0.95):.2f}")
    
    # Report AREATYPE distribution
    print(f"\n  AREATYPE Distribution:")
    areatype_counts = taz['AREATYPE'].value_counts().sort_index()
    areatype_labels = {
        0: 'Regional Core',
        1: 'CBD',
        2: 'Urban Business',
        3: 'Urban',
        4: 'Suburban',
        5: 'Rural'
    }
    for areatype in sorted(areatype_counts.index):
        if areatype in areatype_labels:
            count = areatype_counts[areatype]
            pct = 100 * count / len(taz)
            label = areatype_labels[areatype]
            print(f"    {areatype} ({label:<20}): {count:>6,} TAZs ({pct:>5.1f}%)")
    
    # Check for multicollinearity among all model features
    print(f"\n  Feature Correlation Matrix:")
    all_features = ['commercial_emp_den', 'downtown_emp_den', 'pop_den', 'edhealthrec_emp_den',
                    'areatype_cbd', 'areatype_urban_business', 'areatype_urban']
    corr_matrix = taz[all_features].corr()
    
    # Print correlation matrix with formatting
    print(f"  {'':<20} {'comm':>7} {'dwtn':>7} {'pop':>7} {'edhlth':>7} {'cbd':>7} {'urb_b':>7} {'urb':>7}")
    print(f"  {'-'*80}")
    for idx, row_name in enumerate(all_features):
        row_label = row_name.replace('_emp_den', '').replace('_den', '').replace('areatype_', '')
        row_values = [f"{corr_matrix.iloc[idx, j]:>7.2f}" for j in range(len(all_features))]
        print(f"  {row_label:<20} {''.join(row_values)}")
    
    # Highlight high correlations (potential multicollinearity)
    print(f"\n  High Correlations (|r| >= 0.7, excluding diagonal):")
    high_corr_found = False
    for i in range(len(all_features)):
        for j in range(i+1, len(all_features)):
            r = corr_matrix.iloc[i, j]
            if abs(r) >= 0.7:
                feat1 = all_features[i].replace('_emp_den', '').replace('_den', '').replace('areatype_', '')
                feat2 = all_features[j].replace('_emp_den', '').replace('_den', '').replace('areatype_', '')
                print(f"    {feat1} <-> {feat2}: r = {r:.3f}")
                high_corr_found = True
    
    if not high_corr_found:
        print(f"    None found - features are relatively independent")
    
    return taz


def report_county_density_distributions(taz):
    """
    Report commercial employment density distributions by county for TAZs with off-street capacity.
    
    Shows percentile thresholds per county to inform long-term parking cost estimation.
    Only includes TAZs with off_nres > 0, place_name not null, and excludes AREATYPE 4-5.
    
    Args:
        taz (GeoDataFrame): TAZ zones with county_name, commercial_emp_den, and off_nres
    """
    print("\n" + "="*80)
    print("COUNTY-LEVEL COMMERCIAL EMPLOYMENT DENSITY DISTRIBUTIONS")
    print("="*80)
    print("For TAZs with off-street parking capacity (off_nres > 0) in cities")
    print("Excluding AREATYPE 4 (suburban) and 5 (rural)")
    print()
    
    # Filter to TAZs with off-street capacity and in cities, excluding suburban/rural
    eligible_tazs = taz[
        (taz['off_nres'] > 0) & 
        (taz['place_name'].notna()) & 
        (taz['county_name'].notna()) &
        ~(taz['AREATYPE'].isin([4, 5]))
    ].copy()
    
    print(f"Total eligible TAZs: {len(eligible_tazs):,}\n")
    
    # Cities with observed data (from scraped parking data)
    scraped_file_path = INTERIM_CACHE_DIR / "parking_scrape_location_cost.parquet"
    OBSERVED_CITIES = get_observed_cities_from_scraped_data(scraped_file_path)
    
    # Calculate percentiles by county
    county_stats = []
    
    for county in sorted(eligible_tazs['county_name'].unique()):
        county_tazs = eligible_tazs[eligible_tazs['county_name'] == county]
        
        # Check if county has observed data cities
        has_observed = county_tazs['place_name'].isin(OBSERVED_CITIES).any()
        observed_cities = county_tazs[county_tazs['place_name'].isin(OBSERVED_CITIES)]['place_name'].unique()
        
        stats = {
            'County': county,
            'N_TAZs': len(county_tazs),
            'Mean': county_tazs['commercial_emp_den'].mean(),
            'Median': county_tazs['commercial_emp_den'].median(),
            'P90': county_tazs['commercial_emp_den'].quantile(0.90),
            'P95': county_tazs['commercial_emp_den'].quantile(0.95),
            'P98': county_tazs['commercial_emp_den'].quantile(0.98),
            'P99': county_tazs['commercial_emp_den'].quantile(0.99),
            'Has_Observed': 'Yes' if has_observed else 'No',
            'Observed_Cities': ', '.join(observed_cities) if len(observed_cities) > 0 else 'None'
        }
        county_stats.append(stats)
    
    # Create DataFrame for nice printing
    df_stats = pd.DataFrame(county_stats)
    
    # Print table
    print("Commercial Employment Density (jobs/acre) Percentiles by County:")
    print("─" * 80)
    print(f"{'County':<20} {'N_TAZs':>8} {'Mean':>8} {'P90':>8} {'P95':>8} {'P98':>8} {'P99':>8} {'Obs':>4}")
    print("─" * 80)
    
    for _, row in df_stats.iterrows():
        obs_marker = '✓' if row['Has_Observed'] == 'Yes' else ''
        print(f"{row['County']:<20} {row['N_TAZs']:>8,} {row['Mean']:>8.2f} {row['P90']:>8.2f} "
              f"{row['P95']:>8.2f} {row['P98']:>8.2f} {row['P99']:>8.2f} {obs_marker:>4}")
    
    print("─" * 80)
    print("\nObserved Data Cities:")
    for _, row in df_stats[df_stats['Has_Observed'] == 'Yes'].iterrows():
        print(f"  {row['County']}: {row['Observed_Cities']}")
    
    print("\nInterpretation:")
    print("  - Percentiles shown: P90, P95, P98, P99")
    print("  - Higher percentiles = stricter criteria for paid parking prediction")
    print("  - Top percentiles capture high-density commercial/downtown areas")
    print("  - Counties with ✓ have observed parking cost data for validation")
    print("\nNote:")
    print("  - Long-term parking (PRKCST) percentile threshold is configurable")
    print("  - Default: P95 for long-term parking")
    print("="*80)
    
    return df_stats


def apply_hourly_parking_model(taz, probability_threshold, commercial_density_threshold=1.0, model=None, model_name="Logistic Regression"):
    """
    Estimate hourly parking costs (OPRKCST) for TAZs without observed data using machine learning classification.
    
    Uses binary classification to predict paid (1) vs free (0) parking, then assigns:
    - OPRKCST: $2.00 flat rate (typical hourly rate)
    
    Only predicts for cities OTHER than San Francisco, Oakland, San Jose, and Berkeley
    (those cities use observed data only).
    
    Capacity constraints:
    - OPRKCST: only predict where on_all > 0
    - All costs: only predict where place_name is not null
    - All costs: only predict where commercial_emp_den >= threshold
    - All predictions: exclude AREATYPE 4 (suburban) and 5 (rural)
    
    Args:
        taz (GeoDataFrame): TAZ zones with density features, observed costs, and capacity
        probability_threshold (float): REQUIRED. Classification threshold for model predictions.
                                       Should be determined from cross-validation results (e.g., stratified_kfold_validation)
                                       to optimize F1 score. Typical optimal values range from 0.45-0.55.
        commercial_density_threshold (float): Minimum commercial_emp_den for paid parking consideration
        model: Pre-initialized sklearn model instance (default None)
        model_name (str): Name of the model being used for reporting purposes
    
    Returns:
        GeoDataFrame: TAZ with estimated parking costs filled in
    """
    print(f"\nEstimating parking costs for TAZs without observed data...")
    print(f"  Model: {model_name}")
    print(f"  Approach: Binary classification + flat rates")
    print(f"  Excluding from prediction: San Francisco, Oakland, San Jose, Berkeley (observed data only)")
    print(f"  Commercial density threshold: {commercial_density_threshold:.2f} jobs/acre")
    print(f"  Probability threshold: {probability_threshold:.2f}")
    
    # Cities with observed data - exclude from predictions (from scraped parking data)
    scraped_file_path = INTERIM_CACHE_DIR / "parking_scrape_location_cost.parquet"
    OBSERVED_CITIES = get_observed_cities_from_scraped_data(scraped_file_path)
    
    # Feature columns for model (model-specific)
    feature_cols = get_features_for_model(model_name)
    print(f"  Using {len(feature_cols)} features: {', '.join(feature_cols[:3])}...")
    
    # Initialize predicted cost columns (start with NaN)
    taz['OPRKCST_pred'] = np.nan
    
    # Define flat rates
    HOURLY_FLAT_RATE = 2.00  
    
    # Process only hourly parking (long-term handled by county threshold function)
    for cost_type, capacity_col in [('OPRKCST', 'on_all')]:
        print(f"\n  Processing {cost_type}...")
        
        # Create training mask: has capacity AND has place_name in observed cities
        # Train on ALL four cities with observed data (including free parking)
        has_capacity = taz[capacity_col] > 0
        has_place = taz['place_name'].notna()
        in_observed_cities = taz['place_name'].isin(OBSERVED_CITIES)
        
        training_mask = has_capacity & has_place & in_observed_cities
        n_training = training_mask.sum()
        
        print(f"    Training samples (SF/Oakland/SJ/Berkeley): {n_training:,}")
        
        if n_training < 10:
            print(f"    WARNING: Insufficient training data (<10 samples). Skipping {cost_type} estimation.")
            continue
        
        # Extract training data
        X_train = taz.loc[training_mask, feature_cols].values
        y_train_raw = taz.loc[training_mask, cost_type].values
        
        # Handle NaN values in features (fill with 0 for density columns)
        X_train = np.nan_to_num(X_train, nan=0.0)
        
        # Binary classification: paid (1) vs free (0)
        # Treat NaN and 0 as free parking, > 0 as paid
        y_train_binary = (pd.Series(y_train_raw).fillna(0) > 0).astype(int).values
        
        # Check for variation
        if y_train_binary.sum() == 0 or y_train_binary.sum() == len(y_train_binary):
            print(f"    WARNING: No variation in paid/free parking. Skipping estimation.")
            continue
        
        # Calculate flat rate from observed paid parking
        paid_costs = pd.Series(y_train_raw).dropna()
        paid_costs = paid_costs[paid_costs > 0].values
        
        if cost_type == 'OPRKCST':
            flat_rate = HOURLY_FLAT_RATE
            print(f"    Using hourly flat rate: ${flat_rate:.2f}")
        else:
            flat_rate = np.median(paid_costs)
            print(f"    Using median of observed {cost_type}: ${flat_rate:.2f}")
        
        n_paid = y_train_binary.sum()
        n_free = len(y_train_binary) - n_paid
        
        print(f"    Training data - Paid: {n_paid:,} ({n_paid/len(y_train_binary)*100:.1f}%), Free: {n_free:,} ({n_free/len(y_train_binary)*100:.1f}%)")
        
        # Standardize features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        
        # Initialize model if not provided
        if model is None:
            model = LogisticRegression(random_state=42, max_iter=1000)
        
        # Train model
        model.fit(X_train_scaled, y_train_binary)
        
        # Report model parameters (coefficients or feature importances)
        if hasattr(model, 'coef_'):
            print(f"    Model coefficients:")
            for feat, coef in zip(feature_cols, model.coef_[0]):
                print(f"      {feat}: {coef:+.4f}")
        elif hasattr(model, 'feature_importances_'):
            print(f"    Feature importances:")
            for feat, importance in zip(feature_cols, model.feature_importances_):
                print(f"      {feat}: {importance:.4f}")
        
        # Create prediction mask: NO observed cost AND has capacity AND has place_name AND NOT in observed cities AND above density threshold
        has_observed = taz[cost_type].notna()
        needs_prediction = (
            ~has_observed & 
            has_capacity & 
            has_place &
            ~in_observed_cities &  # Exclude SF, Oakland, San Jose, Berkeley
            (taz['commercial_emp_den'] >= commercial_density_threshold) &  # Only predict for commercial areas
            ~(taz['AREATYPE'].isin([4, 5]))  # Exclude suburban and rural areas
        )
        n_predictions = needs_prediction.sum()
        
        print(f"    TAZs eligible for prediction (other cities): {n_predictions:,}")
        
        if n_predictions > 0:
            # Extract prediction features
            X_pred = taz.loc[needs_prediction, feature_cols].values
            
            # Handle NaN values in prediction features
            X_pred = np.nan_to_num(X_pred, nan=0.0)
            
            X_pred_scaled = scaler.transform(X_pred)
            
            # Predict probability of paid parking
            y_pred_proba = model.predict_proba(X_pred_scaled)[:, 1]  # Probability of class 1 (paid)
            
            # Apply probability threshold to classify
            y_pred_binary = (y_pred_proba >= probability_threshold).astype(int)
            
            # Assign flat rate to predicted paid parking TAZs
            y_pred = np.where(y_pred_binary == 1, flat_rate, 0)
            
            # Store predictions
            taz.loc[needs_prediction, f'{cost_type}_pred'] = y_pred
            
            n_predicted_paid = y_pred_binary.sum()
            print(f"    Predicted paid parking: {n_predicted_paid:,} TAZs at ${flat_rate:.2f}")
            print(f"    Predicted free parking: {n_predictions - n_predicted_paid:,} TAZs")
    
    # Fill in observed costs with predictions where missing
    # Fill NaN with predictions
    taz['OPRKCST'] = taz['OPRKCST'].fillna(taz['OPRKCST_pred'])
    
    # Fill any remaining NaN with 0 (free parking)
    taz['OPRKCST'] = taz['OPRKCST'].fillna(0)
    
    # Final cleanup: Ensure AREATYPE 4 (suburban) and 5 (rural) have zero parking costs
    suburban_rural_mask = taz['AREATYPE'].isin([4, 5])
    n_zeroed = suburban_rural_mask.sum()
    if n_zeroed > 0:
        taz.loc[suburban_rural_mask, 'OPRKCST'] = 0
        print(f"\n  Enforced zero OPRKCST for {n_zeroed:,} suburban/rural TAZs (AREATYPE 4-5)")
    
    # Report final statistics
    nonzero_count = (taz['OPRKCST'] > 0).sum()
    if nonzero_count > 0:
        print(f"\n  Final OPRKCST: {nonzero_count:,} TAZs with cost > $0 (mean=${taz.loc[taz['OPRKCST'] > 0, 'OPRKCST'].mean():.2f})")
    else:
        print(f"\n  Final OPRKCST: 0 TAZs with cost > $0")
    
    # Drop intermediate prediction columns
    taz = taz.drop(columns=['OPRKCST_pred'])
    
    return taz


def validate_parking_cost_estimation(taz, commercial_density_threshold=1.0, test_thresholds=None):
    """
    Perform leave-one-city-out cross-validation for hourly parking cost estimation using logistic regression.
    
    NOTE: This is an alternative validation method. The default/recommended approach is
    stratified_kfold_validation() which uses all data more efficiently with balanced folds.
    
    Trains binary classification models and tests on held-out city to evaluate generalization.
    Explicitly validates on San Francisco, Oakland, San Jose, and Berkeley (cities with observed data).
    
    Note: Only validates hourly parking (OPRKCST) since long-term uses county-level thresholds.
    
    Args:
        taz (GeoDataFrame): TAZ zones with density features, observed costs, and capacity
        commercial_density_threshold (float): Minimum commercial_emp_den for paid parking
        test_thresholds (list): List of probability thresholds to test
    
    Returns:
        dict: Validation metrics for each cost type, threshold, and held-out city
    """
    print("\n" + "="*80)
    print("LEAVE-ONE-CITY-OUT CROSS-VALIDATION (Logistic Regression)")
    print("="*80)
    print("Validating hourly parking only (long-term uses county thresholds)")
    
    # Default thresholds to test
    if test_thresholds is None:
        test_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    
    print(f"Testing probability thresholds: {test_thresholds}")
    
    # Cities with observed parking cost data (from scraped parking data)
    scraped_file_path = INTERIM_CACHE_DIR / "parking_scrape_location_cost.parquet"
    TARGET_CITIES = get_observed_cities_from_scraped_data(scraped_file_path)
    
    # Feature columns - uses Logistic Regression (no AREATYPE features for linear model)
    feature_cols = get_features_for_model('Logistic Regression')
    
    results = {}
    
    # Only validate hourly parking (OPRKCST) - long-term uses thresholds
    for cost_type, capacity_col in [('OPRKCST', 'on_all')]:
        print(f"\n{'='*80}")
        print(f"Validating {cost_type.upper()}")
        print(f"{'='*80}")
        
        # Count observed data by city (including free parking)
        # For SF/Oakland/SJ/Berkeley, treat any TAZ with capacity as "observed" (paid or free)
        has_capacity = taz[capacity_col] > 0
        has_place = taz['place_name'].notna()
        in_target_cities = taz['place_name'].isin(TARGET_CITIES)
        
        # "Observed" = has capacity in target cities (we know it's either paid or free)
        has_observed = has_capacity & has_place & in_target_cities
        
        # Count by city
        city_counts = taz[has_observed]['place_name'].value_counts()
        
        # Filter to target cities with sufficient data (at least 10 observations)
        cities_to_test = [city for city in TARGET_CITIES if city in city_counts.index and city_counts[city] >= 10]
        
        if len(cities_to_test) < 2:
            print(f"  Insufficient target cities with observed {cost_type} (need >= 2 of {TARGET_CITIES}). Skipping validation.")
            continue
        
        print(f"  Validating on cities: {', '.join(cities_to_test)}")
        print(f"  Observations per city: {dict(city_counts[cities_to_test])}")
        
        results[cost_type] = {}
        
        # Leave-one-city-out cross-validation
        for held_out_city in cities_to_test:
            # Determine training cities (all target cities except held-out)
            training_cities = [city for city in cities_to_test if city != held_out_city]
            
            print(f"\n  {'─'*70}")
            print(f"  TRAINING ON: {', '.join(training_cities)}")
            print(f"  TESTING ON:  {held_out_city}")
            print(f"  {'─'*70}")
            
            # For training cities: all TAZs with capacity are "observed" (ground truth)
            # Paid = cost > 0, Free = cost <= 0 or NaN (but has capacity)
            train_mask = (
                has_capacity & has_place & 
                (taz['place_name'].isin(training_cities))
            )
            
            # For test city: all observed data (do NOT apply density threshold)
            # NOTE: commercial_density_threshold is a prediction filter, not a validation filter
            test_mask = (
                has_capacity & has_place & 
                (taz['place_name'] == held_out_city)
            )
            
            n_train = train_mask.sum()
            n_test = test_mask.sum()
            
            print(f"    Training samples (other cities): {n_train:,}")
            print(f"    Test samples ({held_out_city}): {n_test:,}")
            
            if n_train < 10 or n_test < 5:
                print(f"    Insufficient data for validation. Skipping.")
                continue
            
            # Extract training data
            X_train = taz.loc[train_mask, feature_cols].values
            y_train_raw = taz.loc[train_mask, cost_type].values
            
            # Handle NaN values in features (fill with 0 for density columns)
            X_train = np.nan_to_num(X_train, nan=0.0)
            
            # Convert to binary: paid (1) or free (0)
            # Treat NaN and 0 as free parking, > 0 as paid
            y_train_binary = (pd.Series(y_train_raw).fillna(0) > 0).astype(int).values
            
            # Debug: show distribution of paid vs free
            n_train_paid = y_train_binary.sum()
            n_train_free = len(y_train_binary) - n_train_paid
            print(f"    Training data: {n_train_paid:,} paid, {n_train_free:,} free")
            
            # Check for variation
            if y_train_binary.sum() == 0 or y_train_binary.sum() == len(y_train_binary):
                print(f"    WARNING: No variation in paid/free parking. Skipping.")
                continue
            
            # Extract test data
            X_test = taz.loc[test_mask, feature_cols].values
            y_test_raw = taz.loc[test_mask, cost_type].values
            y_test_binary = (pd.Series(y_test_raw).fillna(0) > 0).astype(int).values
            
            # Handle NaN values in test features
            X_test = np.nan_to_num(X_test, nan=0.0)
            
            # Standardize features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train logistic regression model
            model = LogisticRegression(random_state=42, max_iter=1000)
            model.fit(X_train_scaled, y_train_binary)
            
            # Predict probabilities once
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            
            # Test multiple thresholds
            threshold_results = {}
            for threshold in test_thresholds:
                y_pred_binary = (y_pred_proba >= threshold).astype(int)
                
                # Calculate classification metrics
                accuracy = accuracy_score(y_test_binary, y_pred_binary)
                
                # Handle case where there are no positive predictions
                if y_pred_binary.sum() == 0:
                    precision = 0.0
                    recall = 0.0
                    f1 = 0.0
                else:
                    precision = precision_score(y_test_binary, y_pred_binary, zero_division=0)
                    recall = recall_score(y_test_binary, y_pred_binary, zero_division=0)
                    f1 = f1_score(y_test_binary, y_pred_binary, zero_division=0)
                
                # Count predictions
                n_actual_paid = y_test_binary.sum()
                n_actual_free = len(y_test_binary) - n_actual_paid
                n_predicted_paid = y_pred_binary.sum()
                n_predicted_free = len(y_pred_binary) - n_predicted_paid
                
                # Store results for this threshold
                threshold_results[threshold] = {
                    'accuracy': accuracy,
                    'precision': precision,
                    'recall': recall,
                    'f1': f1,
                    'n_predicted_paid': n_predicted_paid,
                    'n_predicted_free': n_predicted_free,
                }
            
            # Store results for all thresholds
            results[cost_type][held_out_city] = {
                'n_train': n_train,
                'n_test': n_test,
                'n_actual_paid': y_test_binary.sum(),
                'n_actual_free': len(y_test_binary) - y_test_binary.sum(),
                'thresholds': threshold_results,
            }
            
            # Print metrics for each threshold
            print(f"    Classification Metrics by Threshold:")
            print(f"    {'Threshold':>10} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>8} {'Pred Paid':>10}")
            print(f"    {'-'*68}")
            for threshold in test_thresholds:
                tr = threshold_results[threshold]
                print(f"    {threshold:>10.2f} {tr['accuracy']:>10.1%} {tr['precision']:>10.1%} {tr['recall']:>10.1%} {tr['f1']:>8.3f} {tr['n_predicted_paid']:>10,}")
            
            # Highlight best threshold by F1 score
            if threshold_results:
                best_threshold = max(threshold_results.keys(), key=lambda t: threshold_results[t]['f1'])
                print(f"    {'-'*68}")
                print(f"    Best threshold by F1: {best_threshold:.2f} (F1={threshold_results[best_threshold]['f1']:.3f})")
            else:
                print(f"    {'-'*68}")
                print(f"    No valid threshold results computed")
    
    # Print summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    # Map cities to counties
    CITY_TO_COUNTY = {
        'San Francisco': 'San Francisco',
        'Oakland': 'Alameda',
        'San Jose': 'Santa Clara',
        'Berkeley': 'Alameda'
    }
    
    for cost_type, city_results in results.items():
        if not city_results:
            continue
        
        print(f"\n{cost_type.upper()}:")
        
        # Calculate average metrics across cities for each threshold
        print(f"\n  Average Metrics Across Cities:")
        print(f"  {'Threshold':>10} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>8}")
        print(f"  {'-'*58}")
        
        for threshold in test_thresholds:
            avg_accuracy = np.mean([r['thresholds'][threshold]['accuracy'] for r in city_results.values()])
            avg_precision = np.mean([r['thresholds'][threshold]['precision'] for r in city_results.values()])
            avg_recall = np.mean([r['thresholds'][threshold]['recall'] for r in city_results.values()])
            avg_f1 = np.mean([r['thresholds'][threshold]['f1'] for r in city_results.values()])
            
            print(f"  {threshold:>10.2f} {avg_accuracy:>10.1%} {avg_precision:>10.1%} {avg_recall:>10.1%} {avg_f1:>8.3f}")
        
        # Find best threshold by average F1
        best_threshold = max(test_thresholds, key=lambda t: np.mean([r['thresholds'][t]['f1'] for r in city_results.values()]))
        best_f1 = np.mean([r['thresholds'][best_threshold]['f1'] for r in city_results.values()])
        print(f"  {'-'*58}")
        print(f"  ✓ RECOMMENDED THRESHOLD: {best_threshold:.2f} (avg F1={best_f1:.3f})")
        print(f"  {'-'*58}")
        
        # County-level breakdown for best threshold
        print(f"\n  City-Level Performance (Threshold={best_threshold:.2f}):")
        print(f"  {'─'*76}")
        print(f"  {'County':<20} {'City':<15} {'Accuracy':>10} {'Precision':>10} {'Recall':>10}")
        print(f"  {'─'*76}")
        
        for city, metrics in city_results.items():
            county = CITY_TO_COUNTY.get(city, 'Unknown')
            tr = metrics['thresholds'][best_threshold]
            print(f"  {county:<20} {city:<15} {tr['accuracy']:>9.1%} {tr['precision']:>9.1%} {tr['recall']:>9.1%}")
        
        print(f"  {'─'*76}")
    
    return results


def stratified_kfold_validation(taz, commercial_density_threshold=1.0, test_thresholds=None, n_splits=5):
    """
    Perform stratified k-fold cross-validation for hourly parking cost estimation.
    
    Uses all available data efficiently by splitting into k folds with balanced
    paid/free parking distribution. This provides more robust validation than
    leave-one-city-out when sample sizes are small.
    
    Args:
        taz (GeoDataFrame): TAZ zones with density features, observed costs, and capacity
        commercial_density_threshold (float): Minimum commercial_emp_den for paid parking
        test_thresholds (list): List of probability thresholds to test
        n_splits (int): Number of folds for cross-validation (default: 5)
    
    Returns:
        dict: Performance metrics for each model across all folds
    """
    print("\n" + "="*80)
    print(f"STRATIFIED {n_splits}-FOLD CROSS-VALIDATION")
    print("="*80)
    print("Uses all observed data with balanced paid/free parking in each fold")
    
    # Default thresholds to test
    if test_thresholds is None:
        test_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    
    print(f"Testing probability thresholds: {test_thresholds}")
    
    # Define models to test with model-specific features
    models = {
        'Logistic Regression': {
            'model': LogisticRegression(random_state=42, max_iter=1000),
            'features': get_features_for_model('Logistic Regression')
        },
        'Random Forest': {
            'model': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10, class_weight='balanced'),
            'features': get_features_for_model('Random Forest')
        },
        'Gradient Boosting': {
            'model': GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5, learning_rate=0.1),
            'features': get_features_for_model('Gradient Boosting')
        },
        'SVM (RBF)': {
            'model': SVC(probability=True, random_state=42, kernel='rbf', C=1.0),
            'features': get_features_for_model('SVM (RBF)')
        }
    }
    
    # Cities with observed data (from scraped parking data)
    scraped_file_path = INTERIM_CACHE_DIR / "parking_scrape_location_cost.parquet"
    TARGET_CITIES = get_observed_cities_from_scraped_data(scraped_file_path)
    
    # Prepare data: filter to eligible TAZs
    # NOTE: Include ALL TAZs with capacity in target cities, not just those with observed costs
    # Treat NaN/0 costs as free parking (0), costs > 0 as paid parking (1)
    has_capacity = taz['on_all'] > 0
    has_place = taz['place_name'].notna()
    in_target_cities = taz['place_name'].isin(TARGET_CITIES)
    
    eligible_mask = has_capacity & has_place & in_target_cities
    
    # Extract eligible TAZs
    taz_eligible = taz[eligible_mask].copy()
    
    # Convert costs to binary: paid (1) or free (0)
    # Treat NaN and 0 as free parking, > 0 as paid
    y_raw = taz_eligible['OPRKCST'].fillna(0).values
    y = (y_raw > 0).astype(int)
    
    n_total = len(taz_eligible)
    n_paid = y.sum()
    n_free = n_total - n_paid
    
    print(f"\nTotal eligible TAZs: {n_total:,}")
    print(f"  Paid parking: {n_paid:,} ({n_paid/n_total:.1%})")
    print(f"  Free parking: {n_free:,} ({n_free/n_total:.1%})")
    print(f"\nNote: Validating on ALL TAZs with on-street capacity in SF/Oakland/San Jose/Berkeley")
    print(f"      Commercial density threshold ({commercial_density_threshold:.1f} jobs/acre) used only for predictions")
    
    # Check for class imbalance
    if n_paid == 0 or n_free == 0:
        print(f"\n⚠ ERROR: Cannot perform stratified k-fold validation - only one class present!")
        print(f"         Need both paid and free parking examples for binary classification.")
        return {}
    
    # Initialize results
    results = {}
    
    # Test each model
    for model_name, model_config in models.items():
        print(f"\n{'='*80}")
        print(f"TESTING: {model_name}")
        print(f"{'='*80}")
        
        # Extract model and features for this model type
        base_model = model_config['model']
        feature_cols = model_config['features']
        
        print(f"Using {len(feature_cols)} features: {', '.join(feature_cols)}")
        
        # Extract model-specific features from eligible TAZs
        X = taz_eligible[feature_cols].values
        X = np.nan_to_num(X, nan=0.0)  # Handle NaN values
        
        # Initialize cross-validation
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        
        fold_results = []
        
        for fold_idx, (train_idx, test_idx) in enumerate(skf.split(X, y), 1):
            print(f"\n  Fold {fold_idx}/{n_splits}:")
            
            # Split data
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            n_train_paid = y_train.sum()
            n_train_free = len(y_train) - n_train_paid
            n_test_paid = y_test.sum()
            n_test_free = len(y_test) - n_test_paid
            
            print(f"    Train: {len(y_train)} TAZs ({n_train_paid} paid, {n_train_free} free)")
            print(f"    Test:  {len(y_test)} TAZs ({n_test_paid} paid, {n_test_free} free)")
            
            # Standardize features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = base_model.__class__(**base_model.get_params())
            model.fit(X_train_scaled, y_train)
            
            # Get probabilities
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            
            # Test all thresholds and find best
            best_f1 = -1
            best_threshold = 0.5
            best_metrics = {}
            
            for threshold in test_thresholds:
                y_pred = (y_pred_proba >= threshold).astype(int)
                
                accuracy = accuracy_score(y_test, y_pred)
                
                if y_pred.sum() == 0:
                    precision = 0.0
                    recall = 0.0
                    f1 = 0.0
                else:
                    precision = precision_score(y_test, y_pred, zero_division=0)
                    recall = recall_score(y_test, y_pred, zero_division=0)
                    f1 = f1_score(y_test, y_pred, zero_division=0)
                
                # Store metrics for this threshold
                current_metrics = {
                    'accuracy': accuracy,
                    'precision': precision,
                    'recall': recall,
                    'f1': f1,
                    'threshold': threshold
                }
                
                # Update best if this is better
                if f1 > best_f1 or best_f1 < 0:
                    best_f1 = f1
                    best_threshold = threshold
                    best_metrics = current_metrics
            
            fold_results.append(best_metrics)
            
            print(f"    Best F1: {best_f1:.3f} at threshold {best_threshold:.2f}")
            print(f"    Acc: {best_metrics['accuracy']:.1%}, Prec: {best_metrics['precision']:.1%}, Rec: {best_metrics['recall']:.1%}")
        
        # Calculate average metrics across folds
        avg_f1 = np.mean([r['f1'] for r in fold_results])
        avg_accuracy = np.mean([r['accuracy'] for r in fold_results])
        avg_precision = np.mean([r['precision'] for r in fold_results])
        avg_recall = np.mean([r['recall'] for r in fold_results])
        avg_threshold = np.mean([r['threshold'] for r in fold_results])
        
        # Calculate standard deviations
        std_f1 = np.std([r['f1'] for r in fold_results])
        std_accuracy = np.std([r['accuracy'] for r in fold_results])
        
        results[model_name] = {
            'avg_f1': avg_f1,
            'std_f1': std_f1,
            'avg_accuracy': avg_accuracy,
            'std_accuracy': std_accuracy,
            'avg_precision': avg_precision,
            'avg_recall': avg_recall,
            'avg_threshold': avg_threshold,
            'fold_results': fold_results
        }
        
        print(f"\n  {'─'*70}")
        print(f"  Average across {n_splits} folds:")
        print(f"    F1: {avg_f1:.3f} ± {std_f1:.3f}")
        print(f"    Accuracy: {avg_accuracy:.1%} ± {std_accuracy:.1%}")
        print(f"    Precision: {avg_precision:.1%}")
        print(f"    Recall: {avg_recall:.1%}")
        print(f"    Avg threshold: {avg_threshold:.2f}")
    
    # Summary comparison
    print(f"\n{'='*80}")
    print("STRATIFIED K-FOLD VALIDATION SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"{'Model':<25} {'Avg F1':>12} {'Std F1':>10} {'Accuracy':>10} {'Precision':>10} {'Recall':>10}")
    print(f"{'-'*90}")
    
    model_scores = []
    
    for model_name, metrics in results.items():
        print(f"{model_name:<25} {metrics['avg_f1']:>12.3f} {metrics['std_f1']:>10.3f} "
              f"{metrics['avg_accuracy']:>9.1%} {metrics['avg_precision']:>9.1%} {metrics['avg_recall']:>9.1%}")
        model_scores.append((model_name, metrics['avg_f1']))
    
    print(f"{'-'*90}")
    
    # Winner
    if model_scores:
        best_model, best_f1 = max(model_scores, key=lambda x: x[1])
        print(f"\n✓ BEST MODEL: {best_model} (F1={best_f1:.3f} ± {results[best_model]['std_f1']:.3f})")
        print(f"  Recommended threshold: {results[best_model]['avg_threshold']:.2f}")
        
        # Compare to baseline (Logistic Regression)
        if 'Logistic Regression' in results and best_model != 'Logistic Regression':
            baseline_f1 = results['Logistic Regression']['avg_f1']
            improvement = ((best_f1 - baseline_f1) / baseline_f1) * 100
            print(f"  Improvement over Logistic Regression: {improvement:+.1f}%")
    
    print(f"\nNote: Stratified k-fold uses all data efficiently and avoids city-specific biases.")
    print(f"Results are more stable than leave-one-city-out with small sample sizes.")
    
    return results


def compare_models(taz, commercial_density_threshold=1.0, test_thresholds=None):
    """
    Compare multiple model types using leave-one-city-out cross-validation.
    
    Tests Logistic Regression, Random Forest, Gradient Boosting, and SVM to find
    the best-performing model for parking cost classification.
    
    Args:
        taz (GeoDataFrame): TAZ zones with density features, observed costs, and capacity
        commercial_density_threshold (float): Minimum commercial_emp_den for paid parking
        test_thresholds (list): List of probability thresholds to test
    
    Returns:
        dict: Performance metrics for each model and city combination
    """
    print("\n" + "="*80)
    print("MODEL COMPARISON - LEAVE-ONE-CITY-OUT CROSS-VALIDATION")
    print("="*80)
    
    if test_thresholds is None:
        test_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    
    # Define models to test with model-specific features
    models = {
        'Logistic Regression': {
            'model': LogisticRegression(random_state=42, max_iter=1000),
            'features': get_features_for_model('Logistic Regression')
        },
        'Random Forest': {
            'model': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10),
            'features': get_features_for_model('Random Forest')
        },
        'Gradient Boosting': {
            'model': GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5, learning_rate=0.1),
            'features': get_features_for_model('Gradient Boosting')
        },
        'SVM (RBF)': {
            'model': SVC(probability=True, random_state=42, kernel='rbf', C=1.0),
            'features': get_features_for_model('SVM (RBF)')
        }
    }
    
    # Cities with observed data (from scraped parking data)
    scraped_file_path = INTERIM_CACHE_DIR / "parking_scrape_location_cost.parquet"
    TARGET_CITIES = get_observed_cities_from_scraped_data(scraped_file_path)
    
    results = {}
    
    for model_name, model_config in models.items():
        print(f"\n{'='*80}")
        print(f"TESTING: {model_name}")
        print(f"{'='*80}")
        
        # Extract model and features for this model type
        model = model_config['model']
        feature_cols = model_config['features']
        
        print(f"Using {len(feature_cols)} features")
        
        results[model_name] = {}
        
        # Leave-one-city-out cross-validation
        for held_out_city in TARGET_CITIES:
            training_cities = [c for c in TARGET_CITIES if c != held_out_city]
            
            print(f"\n  Training on {', '.join(training_cities)} → Testing on {held_out_city}")
            
            # Prepare data
            has_capacity = taz['on_all'] > 0
            has_place = taz['place_name'].notna()
            
            train_mask = has_capacity & has_place & taz['place_name'].isin(training_cities)
            # NOTE: Do NOT apply commercial_density_threshold - validate on ALL observed data
            # The threshold is only used at prediction time for new TAZs
            test_mask = (
                has_capacity & has_place & 
                (taz['place_name'] == held_out_city)
            )
            
            n_train = train_mask.sum()
            n_test = test_mask.sum()
            
            if n_train < 10 or n_test < 5:
                print(f"    Insufficient data. Skipping.")
                continue
            
            # Extract and prepare data
            X_train = taz.loc[train_mask, feature_cols].values
            y_train = (pd.Series(taz.loc[train_mask, 'OPRKCST'].values).fillna(0) > 0).astype(int).values
            
            X_test = taz.loc[test_mask, feature_cols].values
            y_test = (pd.Series(taz.loc[test_mask, 'OPRKCST'].values).fillna(0) > 0).astype(int).values
            
            # Handle NaN values in features (fill with 0 for density columns)
            X_train = np.nan_to_num(X_train, nan=0.0)
            X_test = np.nan_to_num(X_test, nan=0.0)
            
            # Check for variation
            if y_train.sum() == 0 or y_train.sum() == len(y_train):
                print(f"    No variation in training data. Skipping.")
                continue
            
            # Standardize
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            print(f"    Training {model_name}...")
            model.fit(X_train_scaled, y_train)
            
            # Get probabilities
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            
            # Test all thresholds and find best
            best_f1 = -1  # Start with -1 to ensure first threshold is captured
            best_threshold = 0.5
            best_metrics = {}
            
            for threshold in test_thresholds:
                y_pred = (y_pred_proba >= threshold).astype(int)
                
                accuracy = accuracy_score(y_test, y_pred)
                
                if y_pred.sum() == 0:
                    precision = 0.0
                    recall = 0.0
                    f1 = 0.0
                else:
                    precision = precision_score(y_test, y_pred, zero_division=0)
                    recall = recall_score(y_test, y_pred, zero_division=0)
                    f1 = f1_score(y_test, y_pred, zero_division=0)
                
                # Store metrics for this threshold
                current_metrics = {
                    'accuracy': accuracy,
                    'precision': precision,
                    'recall': recall,
                    'f1': f1,
                    'threshold': threshold
                }
                
                # Update best if this is better, or if it's the first threshold tested
                if f1 > best_f1 or best_f1 < 0:
                    best_f1 = f1
                    best_threshold = threshold
                    best_metrics = current_metrics
            
            results[model_name][held_out_city] = {
                'best_f1': best_f1,
                'best_threshold': best_threshold,
                'best_metrics': best_metrics,
                'n_train': n_train,
                'n_test': n_test
            }
            
            print(f"    Best F1: {best_f1:.3f} at threshold {best_threshold:.2f}")
            if best_metrics:
                print(f"    Accuracy: {best_metrics['accuracy']:.1%}, Precision: {best_metrics['precision']:.1%}, Recall: {best_metrics['recall']:.1%}")
            else:
                print(f"    No valid metrics computed")
    
    # Summary comparison
    print(f"\n{'='*80}")
    print("MODEL COMPARISON SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"{'Model':<25} {'Avg F1':>10} {'Avg Threshold':>15} {'SF F1':>8} {'Oak F1':>8} {'SJ F1':>8}")
    print(f"{'-'*85}")
    
    model_scores = []
    
    for model_name in models.keys():
        if results[model_name]:
            avg_f1 = np.mean([r['best_f1'] for r in results[model_name].values()])
            avg_threshold = np.mean([r['best_threshold'] for r in results[model_name].values()])
            
            # City-specific F1s
            sf_f1 = results[model_name].get('San Francisco', {}).get('best_f1', 0)
            oak_f1 = results[model_name].get('Oakland', {}).get('best_f1', 0)
            sj_f1 = results[model_name].get('San Jose', {}).get('best_f1', 0)
            
            print(f"{model_name:<25} {avg_f1:>10.3f} {avg_threshold:>15.2f} {sf_f1:>8.3f} {oak_f1:>8.3f} {sj_f1:>8.3f}")
            
            model_scores.append((model_name, avg_f1))
    
    print(f"{'-'*85}")
    
    # Winner
    if model_scores:
        best_model, best_f1 = max(model_scores, key=lambda x: x[1])
        print(f"\n✓ BEST MODEL: {best_model} (Average F1={best_f1:.3f})")
        
        # Show recommended threshold for winner
        best_threshold = np.mean([r['best_threshold'] for r in results[best_model].values()])
        print(f"  Recommended threshold: {best_threshold:.2f}")
        
        # Compare to baseline (Logistic Regression)
        if 'Logistic Regression' in results and best_model != 'Logistic Regression':
            baseline_f1 = np.mean([r['best_f1'] for r in results['Logistic Regression'].values()])
            improvement = ((best_f1 - baseline_f1) / baseline_f1) * 100
            print(f"  Improvement over Logistic Regression: {improvement:+.1f}%")
    
    return results


def estimate_parking_by_county_threshold(taz, percentile=0.95):
    """
    Estimate long-term parking costs using county-level density thresholds.
    
    Applies county-specific commercial employment density percentiles to identify
    high-density areas likely to have paid parking. Only predicts for cities OTHER
    than those with observed data (San Francisco, Oakland, San Jose).
    Excludes AREATYPE 4 (suburban) and 5 (rural) from predictions.
    
    Args:
        taz (GeoDataFrame): TAZ zones with county_name, commercial_emp_den, and off_nres
        percentile (float): Percentile threshold for long-term parking (default 0.95)
    
    Returns:
        GeoDataFrame: TAZ with PRKCST filled in
    """
    # Cities with observed parking data (from scraped parking data)
    scraped_file_path = INTERIM_CACHE_DIR / "parking_scrape_location_cost.parquet"
    observed_cities = get_observed_cities_from_scraped_data(scraped_file_path)
    
    # Initialize PRKCST if it doesn't exist (should be populated by merge_scraped_cost)
    if 'PRKCST' not in taz.columns:
        taz['PRKCST'] = 0.0
    else:
        # Fill NaN values with 0 for TAZs without scraped data
        taz['PRKCST'] = taz['PRKCST'].fillna(0)
    
    print(f"\nEstimating long-term parking costs using county-level thresholds...")
    print(f"  Long-term parking (PRKCST): {percentile*100:.0f}th percentile of commercial_emp_den per county")
    print(f"  Excluding from prediction: {', '.join(observed_cities)} (observed data only)")
    
    # Suburban discount factor: non-core cities typically have 60-70% of SF/Oakland/SJ/Berkeley costs
    SUBURBAN_DISCOUNT_FACTOR = 0.65
    
    # Calculate median rate from observed PRKCST data (SF/Oakland/SJ only)
    observed_longterm_median = taz[taz['PRKCST'] > 0]['PRKCST'].median()
    
    # Apply discount for suburban/non-core cities
    longterm_flat_rate = observed_longterm_median * SUBURBAN_DISCOUNT_FACTOR
    
    print(f"  Observed median long-term cost: ${observed_longterm_median:.2f}")
    print(f"  Suburban discount factor: {SUBURBAN_DISCOUNT_FACTOR:.0%}")
    print(f"  Predicted long-term rate for other cities: ${longterm_flat_rate:.2f}")
    
    # Initialize prediction column
    taz['PRKCST_pred'] = np.nan
    
    # Calculate county-level thresholds
    print(f"\n  County-Level Thresholds:")
    print(f"  {'─'*50}")
    print(f"  {'County':<20} {'N_TAZs':>8} {'LongTerm_P{int(percentile*100)}':>18}")
    print(f"  {'─'*50}")
    
    county_thresholds = {}
    
    for county in sorted(taz[taz['county_name'].notna()]['county_name'].unique()):
        # Get TAZs in county with off-street capacity and in cities (excluding observed cities and suburban/rural)
        county_tazs = taz[
            (taz['county_name'] == county) & 
            (taz['off_nres'] > 0) & 
            (taz['place_name'].notna()) &
            ~(taz['place_name'].isin(observed_cities)) &
            ~(taz['AREATYPE'].isin([4, 5]))
        ]
        
        if len(county_tazs) == 0:
            continue
        
        # Calculate threshold
        longterm_threshold = county_tazs['commercial_emp_den'].quantile(percentile)
        
        county_thresholds[county] = longterm_threshold
        
        print(f"  {county:<20} {len(county_tazs):>8,} {longterm_threshold:>18.2f}")
    
    print(f"  {'─'*50}")
    
    # Apply thresholds by county
    total_longterm_predicted = 0
    
    for county, threshold in county_thresholds.items():
        # Long-term parking prediction mask
        # Check for NaN, None, or <= 0 (no observed cost)
        longterm_mask = (
            (taz['county_name'] == county) &
            (taz['off_nres'] > 0) &
            (taz['place_name'].notna()) &
            ~(taz['place_name'].isin(observed_cities)) &
            ((taz['PRKCST'].isna()) | (taz['PRKCST'] <= 0)) &
            (taz['commercial_emp_den'] >= threshold) &
            ~(taz['AREATYPE'].isin([4, 5]))  # Exclude suburban and rural areas
        )
        
        # Apply flat rate
        taz.loc[longterm_mask, 'PRKCST_pred'] = longterm_flat_rate
        
        n_longterm = longterm_mask.sum()
        total_longterm_predicted += n_longterm
        
        if n_longterm > 0:
            print(f"  {county}: Predicted {n_longterm:,} long-term paid parking TAZs")
    
    # Fill in predictions ONLY for non-observed cities
    # Create mask for TAZs that are NOT in observed cities
    not_observed = ~(taz['place_name'].isin(observed_cities))
    
    # For non-observed cities: fill NaN with predictions
    taz.loc[not_observed, 'PRKCST'] = taz.loc[not_observed, 'PRKCST'].fillna(taz.loc[not_observed, 'PRKCST_pred'])
    
    # Fill remaining NaN with 0 (free parking) for ALL TAZs
    taz['PRKCST'] = taz['PRKCST'].fillna(0)
    
    # Drop intermediate column
    taz = taz.drop(columns=['PRKCST_pred'])
    
    # Final cleanup: Ensure AREATYPE 4 (suburban) and 5 (rural) have zero parking costs
    suburban_rural_mask = taz['AREATYPE'].isin([4, 5])
    n_zeroed = suburban_rural_mask.sum()
    if n_zeroed > 0:
        taz.loc[suburban_rural_mask, 'PRKCST'] = 0
        print(f"\n  Enforced zero PRKCST for {n_zeroed:,} suburban/rural TAZs (AREATYPE 4-5)")
    
    # Report final statistics
    print(f"\n  Summary:")
    print(f"    Total predicted long-term paid parking: {total_longterm_predicted:,} TAZs at ${longterm_flat_rate:.2f}")
    
    final_longterm = (taz['PRKCST'] > 0).sum()
    
    print(f"\n  Final PRKCST: {final_longterm:,} TAZs with cost > $0 (mean=${taz.loc[taz['PRKCST'] > 0, 'PRKCST'].mean():.2f})")
    
    return taz


def backfill_downtown_longterm_costs(taz):
    """
    Backfill missing long-term parking costs for downtown TAZs with capacity in core cities.
    
    For TAZs in San Francisco, Oakland, San Jose, and Berkeley with:
    - AREATYPE = 0 or 1 (regional core or central business district)
    - off_nres > 0 (off-street parking capacity exists)
    - PRKCST == 0 or NaN (no observed or predicted cost)
    
    Assign city-specific median long-term cost from observed downtown parking data.
    
    This ensures that TAZs with long-term parking capacity in regional cores and CBDs
    of core cities have associated costs, even when direct observations are missing.
    
    Must run AFTER:
    - merge_capacity() (off_nres exists)
    - merge_estimated_costs() (PRKCST has observed + predicted values or 0)
    
    Args:
        taz (GeoDataFrame): TAZ zones with place_name, AREATYPE, off_nres, and PRKCST
    
    Returns:
        GeoDataFrame: TAZ with backfilled PRKCST for eligible downtown TAZs
    """
    print(f"\n{'='*80}")
    print(f"BACKFILLING DOWNTOWN LONG-TERM PARKING COSTS")
    print(f"{'='*80}")
    print(f"For core city downtowns (AREATYPE 0-1) with parking capacity but missing costs\n")
    
    # Define core cities for backfill
    CORE_CITIES = ['San Francisco', 'Oakland', 'San Jose', 'Berkeley']
    
    total_backfilled = 0
    
    for city in CORE_CITIES:
        # Calculate city-specific median from observed data (PRKCST > 0)
        city_observed_mask = (taz['place_name'] == city) & (taz['PRKCST'] > 0)
        observed_costs = taz.loc[city_observed_mask, 'PRKCST']
        
        if len(observed_costs) == 0:
            print(f"  {city}: No observed long-term parking costs - skipping backfill")
            continue
        
        city_median = observed_costs.median()
        
        # Identify eligible TAZs for backfill:
        # - In this city
        # - In regional core or CBD (AREATYPE 0 or 1)
        # - Have off-street parking capacity (off_nres > 0)
        # - Missing long-term cost (PRKCST null or <= 0)
        
        eligible_mask = (
            (taz['place_name'] == city) &
            (taz['AREATYPE'].isin([0, 1])) &
            (taz['off_nres'] > 0) &
            ((taz['PRKCST'].isna()) | (taz['PRKCST'] <= 0))
        )
        
        n_eligible = eligible_mask.sum()
        
        if n_eligible > 0:
            # Apply city median to eligible TAZs
            taz.loc[eligible_mask, 'PRKCST'] = city_median
            total_backfilled += n_eligible
            print(f"  {city}: Backfilled {n_eligible:,} downtown TAZs with ${city_median:.2f} (median from {len(observed_costs):,} observed)")
        else:
            print(f"  {city}: No eligible TAZs for backfill (median=${city_median:.2f} from {len(observed_costs):,} observed)")
    
    print(f"\n  Total downtown TAZs backfilled: {total_backfilled:,}")
    
    # Final cleanup: Ensure AREATYPE 4 (suburban) and 5 (rural) have zero parking costs
    suburban_rural_mask = taz['AREATYPE'].isin([4, 5])
    n_zeroed_costs = (taz.loc[suburban_rural_mask, 'PRKCST'] > 0).sum()
    if n_zeroed_costs > 0:
        taz.loc[suburban_rural_mask, 'PRKCST'] = 0
        print(f"\n  Enforced zero PRKCST for {n_zeroed_costs:,} suburban/rural TAZs (AREATYPE 4-5)")
    
    if total_backfilled > 0:
        final_longterm = (taz['PRKCST'] > 0).sum()
        print(f"\n  Final PRKCST: {final_longterm:,} TAZs with cost > $0 (mean=${taz.loc[taz['PRKCST'] > 0, 'PRKCST'].mean():.2f})")
    
    print(f"{'='*80}\n")
    
    return taz


def update_longterm_stalls_with_predicted_costs(taz):
    """
    Report long-term parking costs and capacity.
    
    This function reports TAZs with long-term parking costs (PRKCST > 0)
    and their associated off-street non-residential parking capacity.
    
    Note: pstallsoth and pstallssam columns are no longer created.
    Use off_nres directly for off-street non-residential capacity.
    
    Args:
        taz (GeoDataFrame): TAZ with off_nres capacity and final PRKCST
    
    Returns:
        GeoDataFrame: TAZ unchanged (reporting only)
    """
    print(f"\n{'='*70}")
    print(f"Long-Term Parking Cost Summary")
    print(f"{'='*70}\n")
    
    # Report long-term parking costs based on final PRKCST (observed + predicted)
    if 'PRKCST' in taz.columns and 'off_nres' in taz.columns:
        has_longterm_cost = taz['PRKCST'].fillna(0) > 0
        tazs_with_longterm = has_longterm_cost.sum()
        total_tazs = len(taz)
        
        print(f"  TAZs with long-term parking costs: {tazs_with_longterm:,}/{total_tazs:,}")
        
        if tazs_with_longterm > 0:
            total_capacity = taz.loc[has_longterm_cost, 'off_nres'].sum()
            avg_cost = taz.loc[has_longterm_cost, 'PRKCST'].mean()
            print(f"  Total off-street capacity (off_nres): {total_capacity:,.0f} stalls")
            print(f"  Average long-term cost: ${avg_cost:.2f}")
    else:
        print(f"  ⚠ Warning: PRKCST or off_nres column not found, skipping report")
    
    print(f"{'='*70}\n")
    
    return taz


def estimate_and_validate_hourly_parking_models(
    taz,
    compare_models_flag=True,
    commercial_density_threshold=1.0
):
    """
    Run stratified k-fold validation and model comparison for hourly parking cost estimation.
    
    Uses 5-fold cross-validation with stratified sampling to ensure balanced paid/free
    parking in each fold. This provides robust model performance estimates and selects
    the best-performing model for production use.
    
    Args:
        taz (GeoDataFrame): TAZ zones with employment, capacity, observed costs, place_name, and county_name
        compare_models_flag (bool): If True, compare multiple model types (LR, RF, GB, SVM)
        commercial_density_threshold (float): Minimum commercial_emp_den for paid parking
    
    Returns:
        tuple: (selected_model, selected_model_name) where selected_model is a trained model instance and selected_model_name is the name of the selected model
    """
    print("\n" + "="*80)
    print("HOURLY PARKING MODEL ESTIMATION")
    print("="*80)
    
    print(f"\nNote: Hourly parking estimation uses observed data from San Francisco, Oakland, San Jose only\n")
    
    # Add density features (needed for validation/model training)
    taz = add_density_features(taz)
    
    # Report county distributions
    county_stats = report_county_density_distributions(taz)
    
    # Run stratified k-fold validation and model comparison
    selected_model = None
    selected_model_name = "Logistic Regression"
    optimal_threshold = None  # Will be extracted from validation results
    
    if compare_models_flag:
        # Run stratified 5-fold cross-validation
        stratified_results = stratified_kfold_validation(
            taz, commercial_density_threshold, n_splits=5
        )
        
        if stratified_results:
            # Calculate mean F1 score for each model
            model_f1_scores = {name: result['avg_f1'] for name, result in stratified_results.items()}
            
            # Find best model
            best_model_name = max(model_f1_scores, key=model_f1_scores.get)
            best_f1 = model_f1_scores[best_model_name]
            best_std_f1 = stratified_results[best_model_name]['std_f1']
            
            # Extract optimal threshold from validation results
            optimal_threshold = stratified_results[best_model_name]['avg_threshold']
            
            # Create model instance
            model_mapping = {
                'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
                'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10, class_weight='balanced'),
                'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5, learning_rate=0.1),
                'SVM (RBF)': SVC(kernel='rbf', probability=True, random_state=42, C=1.0)
            }
            
            selected_model = model_mapping.get(best_model_name)
            selected_model_name = best_model_name
            
            print("\n" + "="*80)
            print("MODEL SELECTION FOR PRODUCTION")
            print("="*80)
            print(f"\nComparing {len(model_f1_scores)} models:")
            for model_name, f1 in sorted(model_f1_scores.items(), key=lambda x: x[1], reverse=True):
                std_f1 = stratified_results[model_name]['std_f1']
                marker = "← SELECTED" if model_name == best_model_name else ""
                print(f"  {model_name:<25} F1={f1:.4f} ± {std_f1:.4f} {marker}")
            print(f"\nUsing {best_model_name} for hourly parking estimation (F1={best_f1:.4f} ± {best_std_f1:.4f})")
            print(f"Optimal probability threshold: {optimal_threshold:.2f} (from cross-validation)")
            print("="*80)
    
    return selected_model, selected_model_name, optimal_threshold


def merge_scraped_cost(taz):
    """
    Merge scraped parking costs from SpotHero data.
    
    Converts daily and monthly parking rates to hourly equivalents using
    consistent commuter assumptions:
    - Daily: price / 8 hours (typical workday)
    - Monthly: price / 176 hours (22 workdays × 8 hours)
    
    Creates PRKCST column with average hourly rate per TAZ.
    
    Args:
        taz (GeoDataFrame): TAZ data with geometry
    
    Returns:
        GeoDataFrame: TAZ with PRKCST column added
    """
    print(f"\n{'='*70}")
    print(f"Merging Scraped Parking Costs (SpotHero)")
    print(f"{'='*70}\n")
    
    scraped_file = INTERIM_CACHE_DIR / "parking_scrape_location_cost.parquet"
    
    # Check if scraped file exists
    if not scraped_file.exists():
        print(f"  ⚠ Warning: Scraped parking data file not found: {scraped_file}")
        print(f"  Initializing PRKCST to None (will use threshold-based estimation only)")
        taz['PRKCST'] = None
        return taz
    
    print(f"  Loading scraped parking data from: {scraped_file}")
    scraped = gpd.read_parquet(scraped_file).to_crs(ANALYSIS_CRS)
    
    # Filter to daily and monthly parking types
    daily = scraped[scraped['parking_type'] == 'daily'].copy()
    monthly = scraped[scraped['parking_type'] == 'monthly'].copy()
    
    print(f"  Loaded {len(daily):,} daily parking locations and {len(monthly):,} monthly parking locations")
    
    # Convert to hourly rates (consistent commuter assumption)
    # Daily: 8-hour workday
    # Monthly: 22 workdays × 8 hours = 176 hours
    if len(daily) > 0:
        daily['price_per_hour'] = daily['price_value'] / 8.0
        print(f"  Converting daily rates: price / 8 hours")
    
    if len(monthly) > 0:
        monthly['price_per_hour'] = monthly['price_value'] / 176.0
        print(f"  Converting monthly rates: price / 176 hours (22 days × 8 hrs)")
    
    # Combine daily and monthly hourly rates
    hourly_rates = []
    if len(daily) > 0:
        hourly_rates.append(daily[['geometry', 'price_per_hour']])
    if len(monthly) > 0:
        hourly_rates.append(monthly[['geometry', 'price_per_hour']])
    
    if len(hourly_rates) == 0:
        print(f"  No scraped parking data to merge")
        taz['PRKCST'] = None
        return taz
    
    # Concatenate all hourly rates
    all_hourly = pd.concat(hourly_rates, ignore_index=True)
    all_hourly = gpd.GeoDataFrame(all_hourly, geometry='geometry', crs=ANALYSIS_CRS)
    
    print(f"  Total parking locations with hourly rates: {len(all_hourly):,}")
    
    # Spatial join to TAZ
    taz_join = gpd.sjoin(taz[['TAZ1454', 'geometry']], all_hourly, how='left', predicate='intersects')
    
    # Group by TAZ and average hourly rates
    taz_avg = taz_join.groupby('TAZ1454')['price_per_hour'].mean().reset_index()
    taz_avg = taz_avg.rename(columns={'price_per_hour': 'PRKCST'})
    
    # Merge back to TAZ
    taz = taz.merge(taz_avg, on='TAZ1454', how='left')
    
    # Round to 2 decimal places
    if 'PRKCST' in taz.columns:
        taz['PRKCST'] = taz['PRKCST'].round(2)
    
    print(f"  Scraped costs merged")
    print(f"  TAZs with long-term parking cost (PRKCST): {taz['PRKCST'].notnull().sum():,}")
    
    if taz['PRKCST'].notnull().sum() > 0:
        print(f"  Average hourly rate: ${taz['PRKCST'].mean():.2f}")
        print(f"  Median hourly rate: ${taz['PRKCST'].median():.2f}")
    
    return taz


# def update_parkarea_with_predicted_costs(taz):
#     """
#     Update parkarea classification to include predicted parking costs.
    
#     parkarea codes:
#     - 1: Downtown core (from Local Moran's I analysis)
#     - 2: Within 1/4 mile of downtown core
#     - 3: Paid parking (predicted or observed outside downtown)
#     - 4: Free parking / no parking cost
    
#     Args:
#         taz (GeoDataFrame): TAZ with parkarea, OPRKCST, and PRKCST
    
#     Returns:
#         GeoDataFrame: TAZ with updated parkarea classifications
#     """
#     # Start with parkarea already assigned by merge_parking_area (0, 1, or 2)
#     # parkarea=1 already set for downtown cores
#     # parkarea=2 already set for TAZs within 1/4 mile of downtown
    
#    # Set parkarea=3 for non-downtown TAZs with any parking cost (observed or predicted)
#     has_parking_cost = (
#         (taz['OPRKCST'].notnull() & (taz['OPRKCST'] > 0)) |
#         (taz['PRKCST'].notnull() & (taz['PRKCST'] > 0))
#     )
    
#     # Only reassign parkarea if not already 1 or 2
#     taz.loc[has_parking_cost & (taz['parkarea'] == 0), 'parkarea'] = 3
    
#     # Set parkarea=4 for free parking (no cost areas)
#     # All remaining parkarea=0 (no paid parking) assigned to parkarea=4
#     taz.loc[taz['parkarea'] == 0, 'parkarea'] = 4
    
#     # Report final distribution
#     print(f"\n  Final parkarea distribution:")
#     for code in sorted(taz['parkarea'].unique()):
#         count = (taz['parkarea'] == code).sum()
#         print(f"    parkarea={int(code)}: {count:,} TAZs")
    
#     return taz


def main():
    """
    Execute parking cost estimation as a standalone script.
    
    Loads TAZ shapefile, land use data, parking capacity, and observed costs,
    then runs the full estimation workflow to produce hourly (OPRKCST) and
    long-term (PRKCST) parking costs.
    
    By default, runs stratified 5-fold cross-validation and compares multiple
    ML models (Logistic Regression, Random Forest, Gradient Boosting, SVM).
    
    Outputs:
        - parking_costs_taz.csv: TAZ1454, OPRKCST, PRKCST columns
        - parking_costs_taz.gpkg: Same columns + geometry
    
    Usage:
        python parking_estimation.py [--no-compare-models] 
                                     [--commercial-density-threshold 1.0]
                                     [--percentile 0.95]
                                     [--probability-threshold 0.5]
    """
    parser = argparse.ArgumentParser(
        description="Estimate parking costs for TAZ zones"
    )
    parser.add_argument(
        "--no-compare-models",
        action="store_false",
        dest="compare_models",
        help="Skip model comparison (runs by default, compares LR, RF, GB, SVM using stratified 5-fold CV)"
    )
    parser.add_argument(
        "--commercial-density-threshold",
        type=float,
        default=0.5,
        help="Minimum commercial employment density (jobs/acre) for paid parking (default: 0.5)"
    )
    parser.add_argument(
        "--percentile",
        type=float,
        default=0.95,
        help="Percentile threshold for long-term parking estimation (default: 0.95)"
    )
    parser.add_argument(
        "--probability-threshold",
        type=float,
        default=0.5,
        help="Classification probability threshold (fallback when --no-compare-models is used, default: 0.5)"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("PARKING COST ESTIMATION")
    print("="*80)
    print(f"\nParameters:")
    print(f"  Commercial density threshold: {args.commercial_density_threshold:.2f} jobs/acre")
    print(f"  Long-term percentile: {args.percentile:.0%}")
    print(f"  Hourly probability threshold: {args.probability_threshold:.2f}")
    print(f"  Compare models: {args.compare_models}")
    print(f"  Validation method: Stratified 5-Fold Cross-Validation")
    print()
    
    # Import utilities from parent directory
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils import load_taz_shp, load_bay_area_places, spatial_join_taz_to_place
    from setup import LU_FILE_2023, INTERIM_CACHE_DIR, CENSUS_API_KEY
    from parking_published import published_cost
    
    # Step 1: Load TAZ shapefile
    print("\n" + "="*80)
    print("LOADING DATA")
    print("="*80)
    print("\nLoading TAZ shapefile...")
    taz = load_taz_shp()
    print(f"  Loaded {len(taz):,} TAZ zones")
    
    # Step 1.5: Spatial join TAZ to Census places (needed for place_name and county_name)
    print("\nLoading Census place boundaries...")
    places = load_bay_area_places()
    print(f"  Loaded {len(places):,} Census places")
    
    taz = spatial_join_taz_to_place(taz, places)
    print(f"  Added place_name and county_name columns to TAZ")
    
    # Step 2: Load land use data (for AREATYPE and employment)
    print("\nLoading land use data...")
    land_use = pd.read_csv(LU_FILE_2023)
    print(f"  Loaded {len(land_use):,} land use records")
    
    # Rename ZONE to TAZ1454 for merge
    # Preserve existing parking costs with _2015 suffix to distinguish from newly calculated values
    rename_dict = {'ZONE': 'TAZ1454'}
    if 'OPRKCST' in land_use.columns:
        rename_dict['OPRKCST'] = 'OPRKCST_2015'
    if 'PRKCST' in land_use.columns:
        rename_dict['PRKCST'] = 'PRKCST_2015'
    land_use = land_use.rename(columns=rename_dict)
    
    # Merge land use to TAZ
    taz = taz.merge(land_use, on='TAZ1454', how='left')
    print(f"  Merged land use data to TAZ")
    if 'OPRKCST_2015' in taz.columns:
        print(f"    Preserved OPRKCST_2015 (original land use values)")
    if 'PRKCST_2015' in taz.columns:
        print(f"    Preserved PRKCST_2015 (original land use values)")
    
    # Step 2b: Add county_name if not already present
    if 'county_name' not in taz.columns:
        # Map from COUNTY column if it exists
        if 'COUNTY' in taz.columns:
            county_mapping = {
                'San Francisco': 'San Francisco',
                'San Mateo': 'San Mateo',
                'Santa Clara': 'Santa Clara',
                'Alameda': 'Alameda',
                'Contra Costa': 'Contra Costa',
                'Solano': 'Solano',
                'Napa': 'Napa',
                'Sonoma': 'Sonoma',
                'Marin': 'Marin'
            }
            taz['county_name'] = taz['COUNTY'].map(county_mapping)
            print(f"  Mapped county_name from COUNTY column")
        else:
            print(f"  WARNING: No COUNTY column found, county_name will be missing")
            taz['county_name'] = None
    
    # Step 2c: Add place_name if not already present
    if 'place_name' not in taz.columns:
        # Try to get it from land use data if available
        if 'CITY' in land_use.columns or 'place_name' in land_use.columns:
            place_col = 'place_name' if 'place_name' in land_use.columns else 'CITY'
            taz['place_name'] = taz[place_col] if place_col in taz.columns else None
            print(f"  Mapped place_name from {place_col} column")
        else:
            print(f"  WARNING: No place_name or CITY column found, place_name will be missing")
            taz['place_name'] = None
    
    # Step 3: Calculate parking capacity at runtime
    print("\nCalculating parking capacity...")
    capacity = get_parking_capacity(write=False)
    print(f"    First few rows of capacity frame: \n", capacity.head())
    capacity_cols = ['TAZ1454', 'off_nres', 'on_all']
    taz = taz.merge(capacity[capacity_cols], on='TAZ1454', how='left')
    print(f"\n  Merged parking capacity to TAZ")
    print(f"    Total off-street parking (off_nres): {taz['off_nres'].sum():,.0f}")
    print(f"    Total on-street parking (on_all): {taz['on_all'].sum():,.0f}")
    
    # Step 4: Load observed hourly costs from published data
    print("\nLoading observed hourly parking costs...")
    observed = published_cost()
    taz = taz.merge(observed, on='TAZ1454', how='left')
    observed_count = taz['OPRKCST'].notna().sum()
    print(f"  Loaded observed costs for {observed_count:,} TAZ zones")
    
    # Step 5: Run hourly parking model estimation and validation
    print("\n" + "="*80)
    print("HOURLY PARKING ESTIMATION (OPRKCST)")
    print("="*80)
    
    selected_model, selected_model_name, optimal_threshold = estimate_and_validate_hourly_parking_models(
        taz,
        compare_models_flag=args.compare_models,
        commercial_density_threshold=args.commercial_density_threshold
    )
    
    # Determine which probability threshold to use
    if optimal_threshold is not None:
        threshold_to_use = optimal_threshold
        threshold_source = f"validated optimal threshold: {threshold_to_use:.2f}"
    else:
        threshold_to_use = args.probability_threshold
        threshold_source = f"argparse default: {threshold_to_use:.2f}"
    
    print(f"\nUsing {threshold_source} for production predictions")
    
    # Step 6: Apply hourly parking model
    taz = apply_hourly_parking_model(
        taz,
        commercial_density_threshold=args.commercial_density_threshold,
        probability_threshold=threshold_to_use,
        model=selected_model,
        model_name=selected_model_name
    )
    
    # Step 6.5: Merge scraped long-term parking costs (daily/monthly → hourly)
    taz = merge_scraped_cost(taz)
    
    # Step 7: Estimate long-term parking costs
    print("\n" + "="*80)
    print("LONG-TERM PARKING ESTIMATION (PRKCST)")
    print("="*80)
    
    taz = estimate_parking_by_county_threshold(
        taz,
        percentile=args.percentile
    )
    
    # Step 8: Backfill downtown long-term costs
    taz = backfill_downtown_longterm_costs(taz)
    
    # Step 9: Report final statistics
    taz = update_longterm_stalls_with_predicted_costs(taz)
    
    # Step 10: Output results
    print("\n" + "="*80)
    print("WRITING OUTPUT FILES")
    print("="*80)
    
    output_dir = Path(__file__).parent
    
    # Select output columns
    output_cols = ['TAZ1454', 'OPRKCST', 'PRKCST']
    
    # CSV output (no geometry)
    csv_file = output_dir / "parking_costs_taz.csv"
    taz[output_cols].to_csv(csv_file, index=False)
    print(f"\nWrote CSV: {csv_file}")
    print(f"  Columns: {', '.join(output_cols)}")
    print(f"  Records: {len(taz):,}")
    
    # GeoPackage output (with geometry)
    gpkg_file = output_dir / "parking_costs_taz.gpkg"
    taz_output = taz[output_cols + ['geometry']].copy()
    taz_output.to_file(gpkg_file, driver='GPKG')
    print(f"\nWrote GeoPackage: {gpkg_file}")
    print(f"  Columns: {', '.join(output_cols)} + geometry")
    print(f"  Records: {len(taz_output):,}")
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    hourly_paid = (taz['OPRKCST'] > 0).sum()
    longterm_paid = (taz['PRKCST'] > 0).sum()
    
    print(f"\nHourly parking (OPRKCST):")
    print(f"  TAZs with cost > $0: {hourly_paid:,} ({hourly_paid/len(taz)*100:.1f}%)")
    if hourly_paid > 0:
        print(f"  Mean cost: ${taz.loc[taz['OPRKCST'] > 0, 'OPRKCST'].mean():.2f}")
        print(f"  Median cost: ${taz.loc[taz['OPRKCST'] > 0, 'OPRKCST'].median():.2f}")
    
    print(f"\nLong-term parking (PRKCST):")
    print(f"  TAZs with cost > $0: {longterm_paid:,} ({longterm_paid/len(taz)*100:.1f}%)")
    if longterm_paid > 0:
        print(f"  Mean cost: ${taz.loc[taz['PRKCST'] > 0, 'PRKCST'].mean():.2f}")
        print(f"  Median cost: ${taz.loc[taz['PRKCST'] > 0, 'PRKCST'].median():.2f}")
    
    print("\n" + "="*80)
    print("PARKING COST ESTIMATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()

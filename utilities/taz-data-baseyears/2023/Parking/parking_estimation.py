"""
Parking Cost Estimation Module

This module estimates parking costs in TAZs
without observed data for short-term parking rates.
It also loads and merges web-scraped data for long-term
parking rates.  The web scrape script part of tm2py-utils.

Architecture:
- **Hourly parking (OPRKCST)**: Machine learning classification with model comparison
  - Supports multiple models: Logistic Regression, Random Forest, Gradient Boosting, SVM
  - Trains on San Francisco, Oakland, San Jose, Berkeley observed meter data (paid vs free)
  - Uses stratified 5-fold cross-validation for model selection
  - Ensures balanced paid/free parking distribution in each fold
  - Predicts paid/free for other cities with parking capacity
  - Assigns flat rate to predicted paid parking TAZs (observed median)

- **Long-term parking (PRKCST)**: Scraped SpotHero data (daily/monthly rates → hourly)
  - Daily rates converted at price / 8 hours
  - Monthly rates converted at price / 160 hours (4 weeks × 5 days × 8 hrs)
  - Spatially joined to TAZ; TAZs without scraped data receive PRKCST = 0

Key Constraints:
- Hourly predictions (OPRKCST) only where on_all > 0 (on-street capacity)
- All predictions only in incorporated cities (place_name not null)
- Predictions exclude SF/Oakland/SJ/Berkeley (those use observed data only)
- Minimum commercial_emp_den threshold for paid parking consideration
- AREATYPE 4 (suburban) and 5 (rural) always receive OPRKCST = 0

Workflow:
1. add_density_features(): Calculate employment densities + AREATYPE one-hot encoding
2. stratified_kfold_validation(): 5-fold CV with balanced paid/free samples (always runs)
3. estimate_and_validate_hourly_parking_models(): Model comparison + selection orchestration
4. apply_hourly_parking_model(): Apply selected model for hourly parking (OPRKCST)
5. merge_scraped_cost(): Merge SpotHero scraped data for long-term parking (PRKCST)
6. CPI deflation from 2023 dollars to year 2000 cents

Model-Specific Features:
- Linear models (Logistic Regression, SVM): 4 density features
- Tree-based models (Random Forest, Gradient Boosting): 4 density + 3 AREATYPE features

CLI Overrides (with --force-model):
- --probability-threshold: override CV-derived threshold for the forced model
- --max-depth: override tree max_depth for random-forest or gradient-boosting production model

Entry Point:
- main(): Standalone script execution

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

from setup import INTERIM_CACHE_DIR, ANALYSIS_CRS, CPI_VALUES
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
    # AREATYPE = 0 (Regional Core) is baseline - omitted bc exclusively in an observed city so carries no signal for generalization in unseen areas
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
    
    # One-hot encode AREATYPE (1=CBD, 2=Urban Business, 3=Urban)
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
            flat_rate = np.median(paid_costs)
            print(f"    Using median of observed {cost_type}: ${flat_rate:.2f}")
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
    # Capture which TAZs have observed costs before filling
    had_observed_oprkcst = taz['OPRKCST'].notna()
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

    # Assign provenance labels
    taz.loc[had_observed_oprkcst & (taz['OPRKCST'] > 0), 'OPRKCST_TYPE'] = 'observed'
    taz.loc[~had_observed_oprkcst & (taz['OPRKCST'] > 0), 'OPRKCST_TYPE'] = 'predicted'
    taz.loc[taz['OPRKCST'] == 0, 'OPRKCST_TYPE'] = ''

    # Report final statistics
    nonzero_count = (taz['OPRKCST'] > 0).sum()
    if nonzero_count > 0:
        print(f"\n  Final OPRKCST: {nonzero_count:,} TAZs with cost > $0 (mean=${taz.loc[taz['OPRKCST'] > 0, 'OPRKCST'].mean():.2f})")
    else:
        print(f"\n  Final OPRKCST: 0 TAZs with cost > $0")
    
    # Drop intermediate prediction columns
    taz = taz.drop(columns=['OPRKCST_pred'])
    
    return taz


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
            'model': LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced'),
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
            'model': SVC(probability=True, random_state=42, kernel='rbf', C=1.0, class_weight='balanced'),
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
    
    
    return results


def estimate_and_validate_hourly_parking_models(
    taz,
    commercial_density_threshold=1.0,
    force_model=None,
    max_depth=None,
):
    """
    Run stratified k-fold validation and model comparison for hourly parking cost estimation.

    CV always runs across all four model types (LR, RF, GB, SVM) to compare performance
    and derive the optimal probability threshold for each model.

    When force_model is set, the specified model is used for production regardless of CV F1
    score, but its CV-derived threshold is still used by default (overridable via
    --probability-threshold in main). When max_depth is set, the production model instance
    for random-forest or gradient-boosting is rebuilt with the overridden depth; CV always
    runs with default depths (RF=10, GB=5) for fair cross-model comparison.

    Args:
        taz (GeoDataFrame): TAZ zones with employment, capacity, observed costs, place_name, and county_name
        commercial_density_threshold (float): Minimum commercial_emp_den for paid parking
        force_model (str or None): If set, select this model regardless of CV F1. CV still runs
                                   to derive thresholds. One of: 'logistic', 'random-forest',
                                   'gradient-boosting', 'svm'.
        max_depth (int or None): Override tree max_depth for the production model when force_model
                                 is 'random-forest' or 'gradient-boosting'. CV runs with default
                                 depths. Ignored for other models.

    Returns:
        tuple: (selected_model, selected_model_name, optimal_threshold)
               selected_model: unfitted sklearn model instance ready for production training
               selected_model_name: display name (e.g. 'Random Forest')
               optimal_threshold: CV-derived avg probability threshold for the selected model;
                                  always non-None since CV always runs
    """
    print("\n" + "="*80)
    print("HOURLY PARKING MODEL ESTIMATION")
    print("="*80)


    # Add density features (needed for validation/model training)
    taz = add_density_features(taz)

    _force_name_map = {
        'logistic':           'Logistic Regression',
        'random-forest':      'Random Forest',
        'gradient-boosting':  'Gradient Boosting',
        'svm':                'SVM (RBF)',
    }

    # CV default depths (used for fair cross-model comparison regardless of --max-depth)
    _rf_default_depth = 10
    _gb_default_depth = 5

    # Run stratified 5-fold cross-validation across all models
    stratified_results = stratified_kfold_validation(
        taz, commercial_density_threshold, n_splits=5
    )

    # Model instances at default depths (used for CV comparison and as production default)
    model_mapping = {
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced'),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=_rf_default_depth, class_weight='balanced'),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=_gb_default_depth, learning_rate=0.1),
        'SVM (RBF)': SVC(kernel='rbf', probability=True, random_state=42, C=1.0, class_weight='balanced'),
    }

    # Calculate mean F1 score for each model
    model_f1_scores = {name: result['avg_f1'] for name, result in stratified_results.items()}

    # Find best model by F1
    best_model_name = max(model_f1_scores, key=model_f1_scores.get)
    best_f1 = model_f1_scores[best_model_name]
    best_std_f1 = stratified_results[best_model_name]['std_f1']

    print("\n" + "="*80)
    print("MODEL SELECTION FOR PRODUCTION")
    print("="*80)
    print(f"\nComparing {len(model_f1_scores)} models:")
    for model_name, f1 in sorted(model_f1_scores.items(), key=lambda x: x[1], reverse=True):
        std_f1 = stratified_results[model_name]['std_f1']
        marker = "← BEST F1" if model_name == best_model_name else ""
        print(f"  {model_name:<25} F1={f1:.4f} ± {std_f1:.4f} {marker}")
    print("="*80)

    # Select model: forced or best-F1
    if force_model:
        forced_name = _force_name_map[force_model]
        selected_model_name = forced_name
        optimal_threshold = stratified_results[forced_name]['avg_threshold']
        forced_f1 = model_f1_scores[forced_name]
        forced_std_f1 = stratified_results[forced_name]['std_f1']
        print(f"\n⚠ --force-model: {forced_name} selected (CV best was {best_model_name}, F1={best_f1:.4f})")
        print(f"  {forced_name} CV F1={forced_f1:.4f} ± {forced_std_f1:.4f}, CV threshold={optimal_threshold:.2f}")

        # Apply max_depth override to production model if applicable
        if max_depth is not None and force_model in ('random-forest', 'gradient-boosting'):
            cv_default = _rf_default_depth if force_model == 'random-forest' else _gb_default_depth
            print(f"  max_depth: {cv_default} (CV default) → {max_depth} (--max-depth override)")
            if force_model == 'random-forest':
                selected_model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=max_depth, class_weight='balanced')
            else:
                selected_model = GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=max_depth, learning_rate=0.1)
        else:
            selected_model = model_mapping[forced_name]
    else:
        selected_model_name = best_model_name
        selected_model = model_mapping[best_model_name]
        optimal_threshold = stratified_results[best_model_name]['avg_threshold']
        print(f"\n✓ Selected: {best_model_name} (F1={best_f1:.4f} ± {best_std_f1:.4f})")
        print(f"  CV optimal threshold: {optimal_threshold:.2f}")

    print("="*80)

    return selected_model, selected_model_name, optimal_threshold


def merge_scraped_cost(taz):
    """
    Merge scraped parking costs from SpotHero data.
    
    Converts daily and monthly parking rates to hourly equivalents using
    consistent commuter assumptions:
    - Daily: price / 8 hours (typical workday)
    - Monthly: price / 160 hours (4 weeks × 5 days × 8 hours)
    
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
    # Monthly: 4 weeks × 5 days × 8 hours = 160 hours
    if len(daily) > 0:
        daily['price_per_hour'] = daily['price_value'] / 8.0
        print(f"  Converting daily rates: price / 8 hours")
    
    if len(monthly) > 0:
        monthly['price_per_hour'] = monthly['price_value'] / 160.0
        print(f"  Converting monthly rates: price / 160 hours (4 weeks × 5 days × 8 hrs)")
    
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


class _Tee:
    """Mirror stdout to a log file for the duration of the script."""
    def __init__(self, log_path):
        self._stdout = sys.stdout
        self._log = open(log_path, "w", encoding="utf-8")
        sys.stdout = self

    def write(self, data):
        self._stdout.write(data)
        self._log.write(data)

    def flush(self):
        self._stdout.flush()
        self._log.flush()

    def close(self):
        sys.stdout = self._stdout
        self._log.close()


def main():
    """
    Execute parking cost estimation as a standalone script.

    Loads TAZ shapefile, land use data, parking capacity, and observed costs,
    then runs the full estimation workflow to produce hourly (OPRKCST) and
    long-term (PRKCST) parking costs.

    OPRKCST: ML classification (stratified 5-fold CV, multi-model comparison).
    PRKCST:  Scraped SpotHero daily/monthly rates spatially joined to TAZ.

    Outputs:
        - parking_costs_taz.csv:  TAZ1454, OPRKCST, PRKCST
        - parking_costs_taz.gpkg: same columns + OPRKCST_TYPE, PRKCST_TYPE + geometry
        - parking_costs_taz_log.txt: full stdout log

    Usage:
        python parking_estimation.py [--commercial-density-threshold 0.5]
                                     [--force-model {logistic,random-forest,gradient-boosting,svm}]
                                     [--probability-threshold THRESHOLD]
                                     [--max-depth DEPTH]
    """
    parser = argparse.ArgumentParser(
        description="Estimate parking costs for TAZ zones"
    )
    parser.add_argument(
        "--commercial-density-threshold",
        type=float,
        default=0.5,
        help="Minimum commercial employment density (jobs/acre) for paid parking (default: 0.5)"
    )
    parser.add_argument(
        "--force-model",
        choices=["logistic", "random-forest", "gradient-boosting", "svm"],
        default=None,
        help="Select this model regardless of CV F1 score. CV still runs across all models "
             "to derive the optimal threshold for the forced model."
    )
    parser.add_argument(
        "--probability-threshold",
        type=float,
        default=None,
        help="Override the CV-derived probability threshold (only meaningful with --force-model). "
             "Default: use CV optimal threshold for the selected model."
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Override tree max_depth for the production model when --force-model is "
             "random-forest (CV default 10) or gradient-boosting (CV default 5). "
             "CV always runs with default depths for fair comparison. Ignored for other models."
    )
    
    args = parser.parse_args()

    import atexit
    output_dir = Path(__file__).parent
    log_file = output_dir / "parking_costs_taz_log.txt"
    tee = _Tee(log_file)
    atexit.register(tee.close)
    print(f"Logging to: {log_file}")

    print("="*80)
    print("PARKING COST ESTIMATION")
    print("="*80)
    print(f"\nParameters:")
    print(f"  Commercial density threshold: {args.commercial_density_threshold:.2f} jobs/acre")
    print(f"  Validation method: Stratified 5-Fold Cross-Validation (always runs)")
    if args.force_model:
        print(f"  Force model: {args.force_model}")
    if args.probability_threshold is not None:
        print(f"  Probability threshold override: {args.probability_threshold:.2f}")
    if args.max_depth is not None:
        print(f"  Max depth override: {args.max_depth}")
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

    # Initialize provenance type columns (populated during estimation steps)
    taz['OPRKCST_TYPE'] = ''
    taz['PRKCST_TYPE'] = ''

    # Step 5: Run hourly parking model estimation and validation
    print("\n" + "="*80)
    print("HOURLY PARKING ESTIMATION (OPRKCST)")
    print("="*80)
    
    selected_model, selected_model_name, optimal_threshold = estimate_and_validate_hourly_parking_models(
        taz,
        commercial_density_threshold=args.commercial_density_threshold,
        force_model=args.force_model,
        max_depth=args.max_depth,
    )

    # Determine which probability threshold to use
    # --probability-threshold overrides CV optimal (only meaningful with --force-model)
    if args.probability_threshold is not None:
        threshold_to_use = args.probability_threshold
        threshold_source = f"--probability-threshold override: {threshold_to_use:.2f}"
    else:
        threshold_to_use = optimal_threshold
        threshold_source = f"CV optimal: {threshold_to_use:.2f}"

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
    
    taz["PRKCST"] = taz["PRKCST"].fillna(0)
    
    # Step 10: Output results
    print("\n" + "="*80)
    print("WRITING OUTPUT FILES")
    print("="*80)
    
    # Step 10a: Convert from 2023 dollars to year 2000 cents
    print("\nConverting parking costs to year 2000 cents...")
    
    # Calculate conversion factor: deflate from 2023 to 2000, then convert dollars to cents
    CONVERSION_FACTOR = (CPI_VALUES[2000] / CPI_VALUES[2023]) * 100
    
    print(f"  Source year: 2023 (CPI-U: {CPI_VALUES[2023]:.3f})")
    print(f"  Target year: 2000 (CPI-U: {CPI_VALUES[2000]:.1f})")
    print(f"  Conversion factor: {CONVERSION_FACTOR:.4f} (2023 dollars → 2000 cents)")
    
    # Store example before conversion for reporting
    example_taz_idx = taz[taz['OPRKCST'] > 0].index[0] if (taz['OPRKCST'] > 0).sum() > 0 else None
    if example_taz_idx is not None:
        before_oprkcst = taz.loc[example_taz_idx, 'OPRKCST']
        before_prkcst = taz.loc[example_taz_idx, 'PRKCST']
        example_taz_id = taz.loc[example_taz_idx, 'TAZ1454']
    
    # Apply conversion to both parking cost columns
    taz['OPRKCST'] = taz['OPRKCST'] * CONVERSION_FACTOR
    taz['PRKCST'] = taz['PRKCST'] * CONVERSION_FACTOR
    
    # Report conversion example
    if example_taz_idx is not None:
        after_oprkcst = taz.loc[example_taz_idx, 'OPRKCST']
        after_prkcst = taz.loc[example_taz_idx, 'PRKCST']
        print(f"\n  Example conversion (TAZ {example_taz_id}):")
        print(f"    OPRKCST: ${before_oprkcst:.2f} (2023) → {after_oprkcst:.2f} cents (2000)")
        if before_prkcst > 0:
            print(f"    PRKCST:  ${before_prkcst:.2f} (2023) → {after_prkcst:.2f} cents (2000)")
    
    print(f"\n  Conversion complete. All costs now in year 2000 cents.")
    
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
    gpkg_type_cols = ['OPRKCST_TYPE', 'PRKCST_TYPE']
    taz_output = taz[output_cols + gpkg_type_cols + ['geometry']].copy()
    taz_output.to_file(gpkg_file, driver='GPKG')
    print(f"\nWrote GeoPackage: {gpkg_file}")
    print(f"  Columns: {', '.join(output_cols + gpkg_type_cols)} + geometry")
    print(f"  Records: {len(taz_output):,}")
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY (costs in year 2000 cents)")
    print("="*80)
    
    hourly_paid = (taz['OPRKCST'] > 0).sum()
    longterm_paid = (taz['PRKCST'] > 0).sum()
    
    print(f"\nHourly parking (OPRKCST):")
    print(f"  TAZs with cost > 0: {hourly_paid:,} ({hourly_paid/len(taz)*100:.1f}%)")
    if hourly_paid > 0:
        mean_oprkcst = taz.loc[taz['OPRKCST'] > 0, 'OPRKCST'].mean()
        median_oprkcst = taz.loc[taz['OPRKCST'] > 0, 'OPRKCST'].median()
        print(f"  Mean cost: {mean_oprkcst:.2f} cents (${mean_oprkcst/100:.2f} in year 2000 dollars)")
        print(f"  Median cost: {median_oprkcst:.2f} cents (${median_oprkcst/100:.2f} in year 2000 dollars)")
    
    print(f"\nLong-term parking (PRKCST):")
    print(f"  TAZs with cost > 0: {longterm_paid:,} ({longterm_paid/len(taz)*100:.1f}%)")
    if longterm_paid > 0:
        mean_prkcst = taz.loc[taz['PRKCST'] > 0, 'PRKCST'].mean()
        median_prkcst = taz.loc[taz['PRKCST'] > 0, 'PRKCST'].median()
        print(f"  Mean cost: {mean_prkcst:.2f} cents (${mean_prkcst/100:.2f} in year 2000 dollars)")
        print(f"  Median cost: {median_prkcst:.2f} cents (${median_prkcst/100:.2f} in year 2000 dollars)")
    
    print("\n" + "="*80)
    print("PARKING COST ESTIMATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()

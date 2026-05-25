
# Truck Generation Estimation

This module is an engine for executing OLS regression defined via YAML configurations. It serves as the core estimation logic for updating the TM-1.7 Travel Demand Model truck generation equations.

The script performs the following steps:

1. Loads model specifications from a YAML file  
2. Loads input data: target and feature datasets
3. Executes a suite of regression models  
4. Saves outputs (predictions, diagnostics, etc.) to a timestamped directory  
5. Copies input files for reproducibility  


### How to Run

Run the estimation script as a module from this directory (`utilities/trucks/trucks_2026_updates`):

```bash
python -m src.models.estimate \
  --specs path/to/model_specs.yaml \
  --model-configs path/to/model_configs.yaml \
```

## Requried YAML files

The model pipeline is driven entirely by two YAML configuration files. 

1. **`--specs`**: Path to the YAML file that defines all regression models to be estimated. This file specifies model names, dependent variables, features, and optional parameters.

2. **`--model-configs`**: Path to YAML file with model configuration. Defines path to model targets and featues dataset. 

### YAML Structure Overview  **`--specs`**

At the top level, the YAML file contains a `models` list, where each entry represents one regression model to be estimated:

```yaml
models:
  - name: <model name>
    target: <dependent variable>
    features:
      - <independent variable 1>
      - <independent variable 2>
    model_type: <model type>        # optional. default: "ols"
    weight_col: <column name>       # optional. default: null
    group_col: <column name>        # optional. default: null
    geography_id_col: <column name> # optional. default: "taz_id"
    description: <text>             # optional. default: ""
    tags: [<tag1>, <tag2>]          # optional. default: []
```

#### YAML Parameter Definitions

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | N/A | Unique identifier for the model. Used in output files and logging. |
| `target` | string | Yes | N/A | Name of the dependent variable (column in input data). |
| `features` | list | Yes | N/A | List of independent variable names (columns in input data). |
| `model_type` | string | No | `"ols"` | Type of regression model. Currently supports: `"ols"` (Ordinary Least Squares). |
| `weight_col` | string | No | `null` | Column name for observation weights. If provided, models are estimated using weighted regression. |
| `group_col` | string | No | `null` | Column name for grouping/stratification. If provided, separate models are estimated for each group. |
| `description` | string | No | `""` | Descriptive text for the model, included in outputs for documentation. |
| `tags` | list | No | `[]` | List of categorical tags for organizing and filtering models in outputs. |

#### Example YAML Configuration

```yaml
models:
  - name: truck_generation_primary
    target: daily_trucks
    features:
      - employment
      - retail_sqft
      - manufacturing_sqft
    model_type: ols
    weight_col: zone_weight
    description: "Primary truck generation model for major employment zones"
    tags: ["baseline", "primary"]
    
  - name: truck_generation_secondary
    target: daily_trucks
    features:
      - employment
      - population
    model_type: ols
    description: "Secondary truck generation model using simplified feature set"
    tags: ["baseline", "secondary"]
    
  - name: truck_generation_by_county
    target: daily_trucks
    features:
      - employment
      - retail_sqft
    group_col: county
    weight_col: zone_weight
    description: "County-specific truck generation models"
    tags: ["county_disaggregated"]
```

---



### YAML Structure Overview  **`--model-configs`**

The model configuration YAML file specifies the input data sources and output paths for the model pipeline. It defines where to find the target and feature datasets, how to join them, and where to save results.

At the top level, the YAML file contains the following sections:

```yaml
data_sources:
  features:
    path: <path/to/features.csv>
    id: <feature_id_column>
  targets:
    path: <path/to/targets.csv>
    id: <target_id_column>

output: <path/to/output/directory>

additional_columns:
  - <column_name_1>
  - <column_name_2>
```

#### YAML Parameter Definitions

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data_sources.features.path` | string | Yes | Path to the features dataset (CSV or Parquet) containing independent variables. |
| `data_sources.features.id` | string | Yes | ID/join column name in the features dataset. |
| `data_sources.targets.path` | string | Yes | Path to the targets dataset (CSV or Parquet) containing the dependent variable and observations. |
| `data_sources.targets.id` | string | Yes | ID/join column name in the targets dataset. Must align with features.id for proper merging. |
| `output` | string | Yes | Base output directory where model results will be saved. |
| `additional_columns` | list | No | List of additional column names to include in prediction outputs (e.g., geography identifiers, county, district). |

#### Example YAML Configuration

```yaml
data_sources:
  features:
    path: data/external/mtc/2023_TM161_IPA_35/landuse/tazData.csv
    id: ZONE
  targets:
    path: data/processed/truck_trip_generation_zone.csv
    id: TAZ1454

output: models/truck_trip_generation

additional_columns:
  - TAZ1454
  - COUNTY
  - DISTRICT
```

---

## Outputs

The script generates standardized, long-format outputs for each model run, designed to support downstream analysis, validation, and visualization (e.g., in Tableau), including the following primary output files:

1. `model_comparison.csv`  
2. `model_coefficients.csv`  
3. `model_predictions.csv`  

An additional file is created if aggregation is requested:

4. `aggregate_validation.csv` *(optional)*  

---

## Data Dictionary

### 1. Model Comparison (`model_comparison.csv`)

Summary statistics and performance metrics for each model.

| Column        | Description |
|--------------|------------|
| model_name   | Name of the model |
| target       | Dependent variable being modeled |
| model_type   | Type of regression model used |
| features     | Comma-separated list of input variables |
| n_features   | Number of features in the model |
| description  | Model description from YAML |
| tags         | Comma-separated tags |
| r2           | R-squared value (if available) |
| adj_r2       | Adjusted R-squared (if available) |
| aic          | Akaike Information Criterion (if available) |
| bic          | Bayesian Information Criterion (if available) |
| mae          | Mean Absolute Error |
| rmse         | Root Mean Squared Error |
| mape         | Mean Absolute Percentage Error |

> Note: Not all metrics are available for all model types.

---

### 2. Model Coefficients (`model_coefficients.csv`)

Detailed parameter estimates for each model.

| Column        | Description |
|--------------|------------|
| model_name   | Name of the model |
| target       | Dependent variable |
| term         | Model term (feature/dependent variable) |
| coefficient  | Estimated coefficient value |
| std_error    | Standard error of the estimate |
| t_value      | T-statistic |
| p_value      | Statistical significance (p-value) |

---

### 3. Model Predictions (`model_predictions.csv`)

Observed vs predicted values at the input data level.

| Column        | Description |
|--------------|------------|
| model_name   | Name of the model |
| target       | Dependent variable |
| geography_id | Geographic identifier (e.g., `taz_id`) |
| observed     | Observed value from input data |
| predicted    | Model-predicted value |
| residual     | Difference between observed and predicted |
| ...          | Additional columns specified via `--geo-cols` |

---

### 4. Aggregate Validation (`aggregate_validation.csv`) *(optional)*

Aggregated validation metrics by user-defined group(s).

| Column        | Description |
|--------------|------------|
| group_cols   | Aggregation columns (e.g., county, district) |
| observed     | Total observed values within group |
| predicted    | Total predicted values within group |
| mae          | Mean Absolute Error (aggregated) |
| rmse         | Root Mean Squared Error (aggregated) |
| mape         | Mean Absolute Percentage Error (aggregated) |

> This file is only generated if `--agg-cols` is provided.

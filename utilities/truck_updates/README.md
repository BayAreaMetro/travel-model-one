
# Model Suite Runner

This script runs a suite of OLS regression models defined in a YAML configuration file using a specified dataset. It supports flexible output management, reproducibility tracking, and optional aggregation for validation.

---

## Overview

The script performs the following steps:

1. Loads model specifications from a YAML file  
2. Loads input data (CSV or Parquet)  
3. Executes a suite of regression models  
4. Saves outputs (predictions, diagnostics, etc.) to a timestamped directory  
5. Copies input files for reproducibility  

---

## Requirements
Required packages:
- `pandas`
- `numpy`
- `PyYaml`
- `statsmodels`
- `pyarrow` (for Parquet support)

---

## Usage

Run the script from the command line:

```bash
python -m src.models.estimate \
  --specs path/to/model_specs.yaml \
  --data path/to/data.csv \
  --output path/to/output_dir \
  --geo-cols col1 col2 \  # TODO 
  --agg-cols col3 col4  # TODO
```

## Model Specification (YAML)

The model suite is driven by a YAML configuration file that defines each regression model to be estimated. Each entry in the YAML file represents one model.

At a high level, the YAML file follows this structure:

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

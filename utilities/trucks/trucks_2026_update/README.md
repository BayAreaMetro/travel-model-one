# Truck Model Updates (TM-1.7)

This directory contains the end-to-end pipeline for updating the truck generation equations for the TM-1.7.

---

## Project Structure

- `config/`  : YAML model specifications and pipeline settings.
- `data/`    : Local data storage. **Note:** This folder is git-ignored; all project data is hosted on **Box**: https://mtcdrive.box.com/s/7p99h020p361bzzmltwp5q2sa8oaxah1
- `notebooks/` : Jupyter notebooks for exploration, validation, and final reporting (the "Source of Truth" for model selection).
- `src/`     : Core source code for data cleaning and the OLS estimation engine.

---

## Quick Start

### 1. Installation
```bash
pip install pandas numpy pyyaml statsmodels pyarrow
```

### 2. Run Estimation
Execute the OLS suite as a module from this directory:
```bash
python -m src.models.estimate --specs config/model_specs.yaml --data data/processed/cleaned_data.csv --output output/run_name
```


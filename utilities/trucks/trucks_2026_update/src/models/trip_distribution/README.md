
# Truck Trip Distribution

This module calibrates the gamma parameters (`b`, `c`) to estimate new friction factors to support the TM-1.7 commercial vehicle model update. It fits `b` and `c` against target truck trip length frequency distributions (TLFDs) using a **doubly-constrained gravity model**. The module does **not** produce the friction factors used by the model — that step is done separately in [`notebooks/friction_factors.ipynb`](../../../notebooks/friction_factors.ipynb), which takes the calibrated `b` and `c` and generates the actual friction-factor set for the model.

The pipeline is driven entirely by a single YAML configuration file and processes one or more *runs* (one per truck type / impedance combination).

For each configured run, the module performs the following steps:

1. Loads productions and attractions from a production-attraction (PA) table
2. Loads the travel-impedance skim from an OMX file
3. Calibrates the gamma parameters (`b`, `c`) by fitting the modeled trip length frequency distribution (TLFD) to a target one
4. Runs the gravity model internally (via iterative proportional fitting) to evaluate each candidate `b`/`c` against the target TLFD
5. Writes validation outputs (Excel + plots) reporting the calibrated parameters and fit quality

Runs are independent. A failure in one run is caught, logged at `ERROR` level, and marked `FAILED` in the report; all other runs continue.

> **Downstream:** the calibrated `b` and `c` feed [`notebooks/friction_factors.ipynb`](../../../notebooks/friction_factors.ipynb), which produces the friction factors consumed by the TM-1.7 model.

### How to Run

Run the model as a module from this directory (`utilities/trucks/trucks_2026_update`):

```bash
python -m src.models.trip_distribution.calibrate \
  --config configs/trip_distribution.yaml
```

If `--config` is omitted, it defaults to `configs/trip_distribution.yaml`.

## The Gravity Model

Trips are distributed with a doubly-constrained gravity model solved by iterative proportional fitting (IPF):

```
T_ij = a_i * P_i * b_j * A_j * F_ij
```

where `P_i` and `A_j` are productions and attractions, `a_i` / `b_j` are internal balancing factors, and `F_ij` is the gamma friction factor:

```
F(t) = t^b * exp(c * t)
```

Both `b` and `c` are negative, so `F(t)` decreases monotonically — longer/more-costly trips receive lower weight. The scale parameter `a` is fixed at `1.0` (it cancels in the doubly-constrained denominator). Zero-impedance cells (intrazonal) receive `F = 0`, suppressing intrazonal trips consistent with the observed TLFD, which also excludes them.

The IPF returns a matrix whose **row sums equal `P` exactly** and whose **column sums converge toward `A`** within `gravity_max_rmse` vehicle trips.

## Calibration

The gamma parameters `b` and `c` are calibrated per run with `scipy.optimize.minimize` (default `Nelder-Mead`), minimizing a weighted loss between the modeled and observed TLFD:

```
loss = weighted_SSE + atl_penalty_weight * ATL_penalty

weighted_SSE = sum_k [ observed_share_k * (modeled_share_k - observed_share_k)^2 ]
ATL_penalty  = ((modeled_ATL - observed_ATL) / observed_ATL)^2
```

`weighted_SSE` uses the observed bin shares as weights, so well-populated short-trip bins matter more than the sparse long-distance tail. The `ATL_penalty` (average trip length) term keeps the mean of the distribution on target; set `atl_penalty_weight: 0.0` to optimize on TLFD shape only. Each optimizer evaluation runs the full gravity model internally. Calibration is deterministic, meaning identical YAML and inputs always produce identical parameters.

## Required YAML Configuration

The pipeline is driven by a single YAML file passed via `--config`. It has three top-level sections: `model_settings`, `inputs`, and `runs`. All settings in `model_settings` are optional (defaults shown below); `inputs` and at least one entry under `runs` are required.

`TripDistributionConfig.from_yaml` fully validates the file before any computation begins. If it returns without raising, the pipeline can trust that all required fields are present and typed, `name`/`short_name` are unique, all declared file paths exist, all PA columns exist in the parquet schema, and all `skim_column` values exist in the OMX file.

### YAML Structure Overview

```yaml
model_settings:
  gravity_max_iters: 99              # optional. default: 99
  gravity_max_rmse: 10.0             # optional. default: 10.0
  optimizer_method: "Nelder-Mead"    # optional. default: "Nelder-Mead"
  optimizer_max_iters: 500           # optional. default: 500
  atl_penalty_weight: 0.1            # optional. default: 0.1
  gamma_b_bounds: [-3.0, -0.01]      # optional. default: [-3.0, -0.01]
  gamma_c_bounds: [-0.5, -0.001]     # optional. default: [-0.5, -0.001]
  verbosity: "INFO"                  # optional. default: "INFO"
  output_dir: models/trip_distribution   # optional. default: outputs/trip_distribution

inputs:
  pa_path: <path/to/productions_attractions.parquet>
  skim_path: <path/to/skims.omx>
  geo_agg_cols:                      # optional. default: []
    - <zone_attribute_column>

runs:
  - name: <run name>
    short_name: <tab prefix>
    productions_column: <PA column>
    attractions_column: <PA column>
    skim_column: <OMX matrix name>
    gamma_b0: <initial b>
    gamma_c0: <initial c>
    tlfd_path: <path/to/observed_tlfd.csv>
    target_od_path: <path/to/target_od.parquet>   # optional. default: null
```

#### `model_settings` Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `gravity_max_iters` | int | No | `99` | Maximum IPF iterations per gravity run. |
| `gravity_max_rmse` | float | No | `10.0` | Convergence threshold — RMSE of column sums vs target attractions, in vehicle trips. |
| `optimizer_method` | string | No | `"Nelder-Mead"` | `scipy.optimize.minimize` method name. |
| `optimizer_max_iters` | int | No | `500` | Maximum optimizer function evaluations. |
| `atl_penalty_weight` | float | No | `0.1` | Weight of the average-trip-length penalty in the calibration loss. Set to `0.0` to fit on TLFD shape only. |
| `gamma_b_bounds` | [float, float] | No | `[-3.0, -0.01]` | Search bounds `(lo, hi)` for the gamma `b` parameter. Both values must be negative. |
| `gamma_c_bounds` | [float, float] | No | `[-0.5, -0.001]` | Search bounds `(lo, hi)` for the gamma `c` parameter. Both values must be negative. |
| `verbosity` | string | No | `"INFO"` | Logging level: `"DEBUG"`, `"INFO"`, or `"WARNING"`. |
| `output_dir` | string | No | `outputs/trip_distribution` | Root directory for all outputs (Excel, plots, matrices, log). |

#### `inputs` Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pa_path` | string | Yes | N/A | Parquet with productions, attractions, and zone attributes. Index must be 1-based integer zone IDs. |
| `skim_path` | string | Yes | N/A | OMX file with one pre-processed impedance matrix per truck type. |
| `geo_agg_cols` | list | No | `[]` | Zone attribute columns (in the PA parquet) used for geographic aggregation in outputs. Omit to skip all geo-aggregated tabs and plots. |

#### `runs` Parameters (one entry per truck type)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | N/A | Full run name used in output filenames and parquet columns. Must be unique across runs. |
| `short_name` | string | Yes | N/A | Short label used as the Excel tab prefix (keep ≤ 4 characters). Must be unique across runs. |
| `productions_column` | string | Yes | N/A | PA parquet column with trip productions (daily vehicle trips) for this truck type. |
| `attractions_column` | string | Yes | N/A | PA parquet column with trip attractions (daily vehicle trips) for this truck type. |
| `skim_column` | string | Yes | N/A | Matrix name in the OMX file with the impedance (time or distance) for this truck type. |
| `gamma_b0` | float | Yes | N/A | Initial value for the gamma `b` parameter passed to the optimizer. Should be negative. |
| `gamma_c0` | float | Yes | N/A | Initial value for the gamma `c` parameter passed to the optimizer. Should be negative. |
| `tlfd_path` | string | Yes | N/A | CSV with the observed TLFD. Required columns: `bin_start`, `bin_end`, `share`. |
| `target_od_path` | string | No | `null` | Optional parquet with observed OD trips for validation. If omitted, all OD comparison outputs are skipped for this run. |

---

## Inputs

### PA table (parquet) — `pa_path`

One row per zone; index is 1-based integer zone IDs. Must contain the production and attraction columns referenced by every run, plus any zone attribute columns listed in `geo_agg_cols`.

| Column | Type | Description |
|--------|------|-------------|
| `{productions_column}` | float | Daily vehicle-trip productions (per run). |
| `{attractions_column}` | float | Daily vehicle-trip attractions (per run). |
| `{geo_agg_cols}` | any | Optional zone attributes (e.g. `county_id`, `district_id`) for geographic aggregation. |

### Skim file (OMX) — `skim_path`

Pre-processed OMX file with one impedance matrix per truck type; matrix names must match the `skim_column` values in the YAML. Units follow the observed TLFD (minutes for time-based runs, miles for distance-based runs). Any blending of time periods (e.g. `1/3 AM + 2/3 MD`) must be done **before** running this model — the package expects a single ready-to-use impedance matrix per truck type. If the OMX contains more zones than the PA table (e.g. gateway zones), it is filtered to the PA zone list automatically.

### TLFD files (CSV) — `tlfd_path` (one per run)

Observed trip length frequency distribution used as the calibration target.

| Column | Type | Description |
|--------|------|-------------|
| `bin_start` | float | Left edge of the impedance bin (inclusive). |
| `bin_end` | float | Right edge of the impedance bin (exclusive). |
| `share` | float | Fraction of trips in this bin (shares must sum to ≈ 1.0; re-normalized on load). |

Bins may be irregular but must be contiguous and non-overlapping. Additional columns are allowed and ignored.

### Target OD matrix (parquet, optional) — `target_od_path` (one per run)

Observed or reference OD trip table for validation only (not used in calibration). If provided, the model produces OD scatter plots and summary statistics comparing modeled flows to observed.

| Column | Type | Description |
|--------|------|-------------|
| `origin` | int | 1-based origin zone ID. |
| `destination` | int | 1-based destination zone ID. |
| `trips` | float | Daily vehicle trips. |

### Zone Index Convention

The PA parquet uses **1-based** zone IDs as the index (zones 1…N). OMX skims use **0-based** array indexing internally (zone ID `z` corresponds to row/column `z-1`). This mapping is applied automatically at load time.

---

## Outputs

All outputs are written to the `output_dir` declared in `model_settings`.

```
output_dir/
├── summary.xlsx        Calibration results, PA diagnostics, and TLFD
│                       comparison tables (one tab per run per table type).
├── plots/              PNG figures for visual validation.
│   ├── tlfd_comparison.png          Observed vs modeled TLFD per run
│   ├── friction_curves.png          Gamma F(t) curves per run
│   ├── calibration_loss.png         Optimizer convergence per run
└── calibrate.log       Full log of the run, including warnings and timing.
```

---

## Data Dictionary

### 1. Validation Report (`summary.xlsx`)

Per run, the workbook reports calibration diagnostics and comparison tables (tab names prefixed with each run's `short_name`), including:

| Content | Description |
|---------|-------------|
| Calibration summary | Initial vs final `b`/`c`, optimizer convergence flag, evaluation count, final loss. The final `b`/`c` are the values fed into `notebooks/friction_factors.ipynb`. |
| TLFD comparison | Per-bin `observed_share`, `modeled_share`, `abs_diff`, `pct_diff`. |
| PA diagnostics | Target vs modeled productions/attractions with per-zone and (optionally) per-geography residuals. |
| OD statistics | Modeled vs observed OD summary and log-log fit (R², slope) — only when `target_od_path` is set. |

### Run-Level Warnings

Written to `calibrate.log` (and stdout) rather than raising:

- **Parameter at bound** — a calibrated `b` or `c` settled on a search bound. 
- **P/A imbalance** — total productions and attractions for a run differ by more than 5%.
- **Gravity non-convergence** — the final gravity run did not reach `gravity_max_rmse` within `gravity_max_iters`. The returned matrix still has exact row sums = `P`.

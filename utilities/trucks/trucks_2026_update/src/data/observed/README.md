# Observed Truck Counts

This is a **data pipeline**. It processes raw observed truck counts from two independent sources into a single, standardized dataset that can be used to validate the TM-1.x commercial vehicle model.

- **Caltrans 2018** — permanent count-station data, hourly counts by FHWA vehicle class, one set of CSVs per district. Requires geospatial processing to locate each station and match it to MTC network links.
- **BATA 2023** — Bay Area Toll Authority toll-plaza axle counts, provided as a single Excel workbook with a manually built plaza-to-link crosswalk.

Every sub-pipeline produces the same [observed schema](#the-observed-schema), so their outputs can be concatenated into one dataset.

## How to Run

Run any stage as a module from the project root (`utilities/trucks/trucks_2026_update`).

**Full merged dataset** (runs both sub-pipelines and merges):

```bash
python -m src.data.observed.build_observed_dataset \
  --caltrans-config configs/observed/caltrans_2018.yaml \
  --bata-config configs/observed/bata_2023.yaml \
  --output data/interim/observed_data/observed_dataset_merged.csv
```

**A single source** (useful while iterating on one pipeline):

```bash
python -m src.data.observed.caltrans.pipeline --config configs/observed/caltrans_2018.yaml
```

```bash
python -m src.data.observed.bata.pipeline --config configs/observed/bata_2023.yaml
```

All flags have defaults (shown above), so each command also runs with no arguments.

## The Observed Schema

This schema is the contract of the whole pipeline — it is what every source produces and what downstream validation consumes. It is enforced by [`validate_observed_schema`](schema.py), which checks that all columns exist, coerces dtypes, drops any extras, and fails if `volume` contains nulls.

| Column | Type | Description |
|--------|------|-------------|
| `count_location_id` | str | Source-specific station/plaza identifier (Caltrans control-station ID, or BATA plaza). |
| `link_id` | str | MTC network link the count is assigned to, formatted `{A}-{B}` (from/to node IDs). |
| `tod` | str | Time-of-day period: `EA`, `AM`, `MD`, `PM`, or `EV` (see [TOD periods](#shared-conventions)). |
| `truck_type_1` | str | Truck class: `vstruck`, `struck`, `mtruck`, or `ctruck` (see [truck classes](#shared-conventions)). |
| `truck_type_2` | str | Coarser class used to compare against model assignment output: `SM` (small/medium) or `HV` (heavy). |
| `type` | str | Always `observed` (distinguishes from modeled data in downstream joins). |
| `source` | str | Provenance: `caltrans_2018` or `bata_2023`. |
| `quality_flag`| str| Either `good`, `fair` or `poor ` depending on the observed sample size. |
| `volume` | float | Mean daily truck volume for that location / TOD / truck type. |

### Shared Conventions

Both sub-pipelines use the same definitions, declared in their respective YAML configs:

**Time-of-day (TOD) periods** — map clock hours to the five TM periods:

| Period | Hours |
|--------|-------|
| `EA` (early AM) | 3–5 |
| `AM` (AM peak) | 6–9 |
| `MD` (midday) | 10–14 |
| `PM` (PM peak) | 15–18 |
| `EV` (evening) | 19–23, 0–2 |

**Truck classes** (`truck_type_1`) — the source-specific class definitions differ, but map to the same four labels:

| Label | Meaning | Caltrans (FHWA class → `CNT*`) | BATA (axles) |
|-------|---------|--------------------------------|--------------|
| `vstruck` | Very small truck | `CNT3` | not distinguished|
| `struck` | Small truck | `CNT5` | not distinguished|
| `mtruck` | Medium truck | `CNT6` | 3 axles |
| `ctruck` | Combination / heavy | `CNT7`–`CNT13` | 4+ axles |

`truck_type_2` collapses these into `SM` (`vstruck`/`struck`/`mtruck`) and `HV` (`ctruck`), matching the TM-1.6 assignment aggregation.

---

## Caltrans 2018 Sub-pipeline

Directory: [`caltrans/`](caltrans/) · Config: [`configs/observed/caltrans_2018.yaml`](../../../configs/observed/caltrans_2018.yaml) · Orchestrator: [`caltrans/pipeline.py`](caltrans/pipeline.py)

This is the more involved source because the raw counts are not tied to the TM1.x network. Therefore, stations have to be located in space and matched to the TM-1.x network links first.

### Steps

| # | Step | Module | What it does |
|---|------|--------|--------------|
| 1 | Estimate AADTT | [`aadtt.py`](caltrans/aadtt.py) | Load per-district class CSVs; assign a stable `control_station_id` per (district, control no., direction); remove per-station outliers (IQR fence, `k=3`); keep only typical weekdays (Tue/Wed/Thu, holidays excluded); map hours→TOD; sum `CNT*` columns into truck classes; compute per-station **mean**, **std**, and percentile volumes with quality metrics. |
| 2 | Georeference stations | [`georeference_caltrans_station_counts.py`](caltrans/georeference_caltrans_station_counts.py) | Join each station's route/county/postmile from the Traffic Counts lookup, then locate it on the **State Highway Network** (SHN postmile shapefile) by nearest postmile within route + county + direction. Attaches `longitude`/`latitude`/`geometry`. |
| 3 | Match stations to links | [`match_stations_to_links.py`](caltrans/match_stations_to_links.py) | Match each located station to an **MTC network link** using a route-first strategy (route number is the hard filter; proximity breaks ties). Produces a station→link crosswalk with a `match_quality` label. |
| 4 | Standardize | [`standardize.py`](caltrans/standardize.py) | Join AADTT estimates to the crosswalk, rename to the observed schema, derive `truck_type_2`, and validate. |

### Estimate quality

Step 1 assigns `quality_flag` from the per-station typical-weekday sample size `n`:

| Flag | Sample size `n` |
|------|-----------------|
| `poor` | `n < 5` |
| `fair` | `5 ≤ n < 20` |
| `good` | `n ≥ 20` |

The intermediate `caltrans_aadtt.csv` also carries diagnostics not kept in the final schema (`cv`, `ci_width`, `ci_width_rel`, `rse`) for analyst review.

### Link-match quality

Step 3 labels each station→link match:

| `match_quality` | Meaning |
|-----------------|---------|
| `exact` | Route number **and** direction agree. |
| `route_only` | Route agrees, direction does not. |
| `proximity` | No route match; nearest link within the search radius. |
| `no_match` | Route not present in the network within the buffer (**dropped** from the crosswalk). |

`route_only` and `proximity` matches are written to a **review** file for manual inspection. See [Manual steps](#manual-steps--known-limitations).

### Inputs

| Config key | File | Description |
|------------|------|-------------|
| `inputs.caltrans_2018` | folder of CSVs | Hourly counts by FHWA vehicle class, one file per district. |
| `inputs.caltrans_control_stations` | folder of CSVs | Traffic Counts files providing route/county/postmile per control station. |
| `inputs.shn_postmiles` | `SHN_Postmiles_Tenth.shp` | State Highway Network points every 0.1 mile, for georeferencing. |
| `inputs.mtc_network_links` | `mtc_links.shp` | MTC network links (`A`, `B`, `ROUTENUM`, `ROUTEDIR`), for link matching. |

### Outputs (`data/interim/observed_data/caltrans/`)

| Config key | File | Purpose |
|------------|------|---------|
| `caltrans_aadtt` | `caltrans_aadtt.csv` | Per-station AADTT estimates + quality diagnostics (intermediate). |
| `station_locations_shp` / `_csv` | `station_locations.*` | Georeferenced stations with coordinates (intermediate / QA). |
| `crosswalk` | `station_mtc_link_crosswalk.csv` | Station→link mapping used by standardization. |
| `station_link_match_qa` | `qa/station_link_match_qa.shp` | All best matches with geometry, for spatial QA. |
| `stations_review` | `qa/count_station_to_review.csv` | Low-confidence matches flagged for manual review. |
| `standardized_observed_aadtt` | `caltrans_standardized_observed_aadtt.csv` | **Final output** in the observed schema. |

---

## BATA 2023 Sub-pipeline

Directory: [`bata/`](bata/) · Config: [`configs/observed/bata_2023.yaml`](../../../configs/observed/bata_2023.yaml) · Orchestrator: [`bata/pipeline.py`](bata/pipeline.py)

Toll-plaza counts are already point locations tied to known plazas, so no georeferencing is needed — a hand-built plaza→link crosswalk is supplied as an input.

### Steps

| # | Step | Module | What it does |
|---|------|--------|--------------|
| 1 | Estimate AADTT | [`aadtt.py`](bata/aadtt.py) | Read the Excel workbook; keep 2023 rows; sum counts by hour→TOD; map **axle counts** to truck classes (2→`struck`, 3→`mtruck`, 4+→`ctruck`); average daily totals to a mean volume per plaza / TOD / class. |
| 2 | Standardize | [`standardize.py`](bata/standardize.py) | Join to the plaza→link crosswalk, rename to the observed schema, derive `truck_type_2`, set `quality_flag = "none"`, and validate. |

BATA estimates carry `quality_flag = "none"` — no sample-size grading is applied to toll data.

### Inputs

| Config key | File | Description |
|------------|------|-------------|
| `inputs.bata_2023.path` / `.tab` | `BATA_counts_by_plaza_hour_axles.xlsx` | Raw counts by plaza, hour, and axle class; `tab` names the sheet. |
| `inputs.crosswalk` | `BATA_TM_network_link_matching.csv` | **Manually built** plaza→link crosswalk. |

### Output (`data/interim/observed_data/bata/`)

| Config key | File | Purpose |
|------------|------|---------|
| `standardized_observed_aadtt` | `bata_standardized_observed_aadtt.csv` | **Final output** in the observed schema. |

---

## Merge Step

[`build_observed_dataset.py`](build_observed_dataset.py) runs both sub-pipelines, concatenates the two standardized frames, re-runs `validate_observed_schema` on the result, logs summary statistics (record counts, unique links/locations, class/source/TOD/flag inventories, volume range), and saves the merged dataset (default: `data/interim/observed_data/observed_dataset_merged.csv`). This merged file is the dataset used for model validation.

---

## Spatial Reference (CRS)

Caltrans spatial steps run in **`EPSG:26910`** (NAD83 / UTM zone 10N), the native CRS of the MTC network and TAZ shapefile. The MTC links shapefile ships without an embedded projection and is assigned this CRS at load; the SHN and any WGS-84 inputs are reprojected on load. Coordinates are additionally emitted as `longitude`/`latitude` (`EPSG:4326`).

## Manual Steps & Known Limitations

- **Crosswalks are partly manual.** The BATA plaza→link crosswalk is built by hand and supplied as an input. For Caltrans, low-confidence matches (`route_only`, `proximity`) are exported to `count_station_to_review.csv` for manual inspection.
- **Manual overrides are stubbed.** `match_stations_to_links.apply_manual_overrides` is currently a no-op (`# TODO`), so a `manual` match quality is not produced yet even if an overrides file is provided. 
- **Directory layout mirrors the pipeline.** Each source lives in its own package under `src/data/observed/`, with a `pipeline.py` orchestrator, an `aadtt.py` estimator, and a `standardize.py` that enforces the shared schema in [`schema.py`](schema.py).

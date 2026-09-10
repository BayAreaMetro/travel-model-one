# Trip Distribution Inputs

This data pipeline builds the calibration inputs consumed by the truck trip distribution model in [`src/models/trip_distribution`](../../models/trip_distribution). Its job is to turn raw MTC skims and CSF2TDM truck OD matrices into the three inputs the trips distribution calibration expects: **blended skims**, **production/attraction (P/A) tables**, and **observed trip length frequency distributions (TLFDs)**.

Think of it as the bridge between raw model I/O and the calibration step:

```
raw MTC skims + statewide truck OD  ──►  build_inputs  ──►  data/interim/trip_distribution_inputs/  ──►  src.models.trip_distribution.calibrate
```

## How to Run

Run as a module from the project root (`utilities/trucks/trucks_2026_update`):

```bash
python -m src.data.trip_distribution.build_inputs
```

There are no CLI arguments. Input and output paths are constants at the top of [`build_inputs.py`](build_inputs.py), and the set of blended skims is declared in the `blended_skim_defs` dict in that file. Edit `blended_skim_defs` to add, remove, or retune a blended skim.

## What It Builds

The pipeline reads the raw MTC highway skims and the statewide truck OD matrices, restricts both to the **1,454 internal TAZs**, and produces three groups of outputs.

| # | Output | How it's built                                                                                                                                                                                                                                                                                                                   |
|---|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | **Blended skims** | Blends per-time-period highway skims (toll + non-toll) into a single impedance matrix per truck type, for both **time** and **distance**. Time skims blend `1/3 AM + 2/3 MD`; distance skims use `MD` only. Toll/non-toll are combined at a 50/50 share (matching `TRUCK_DISTRIB_LOS_TOLL_PART` in the TM-1.6 `hwyParam.block`). |
| 2 | **P/A tables** | Aggregates CSF2TDM truck trips to TAZ-level productions (by origin) and attractions (by destination) for very small, small, medium, and large truck classes.                                                                                                                                                                     |
| 3 | **Observed TLFDs** | Bins the CSF2TDM OD trips by their blended time/distance impedance into frequency distributions, one per truck type × impedance. These are the calibration targets.                                                                                                                                                              |

> **Very small trucks:** the statewide OD data has no very-small-truck class, so those productions/attractions are carried over from the TM-1.6 `2023_TM161_IPA_35` inputs upstream of this pipeline.

## Inputs

Both inputs are read from earlier stages of the broader data workflow (paths are constants in `build_inputs.py`):

| Input | Path pattern | Description |
|-------|--------------|-------------|
| MTC highway skims | `data/interim/cube_io/mtc_skims/COM_HWYSKIM{tod}.omx` | Per-time-period highway skims (time + distance, toll + non-toll), read via `src.data.EDA.mtc_od.read_mtc_skims`. |
| Statewide truck OD | `data/interim/matrix_projection/sw_od_trips_with_mtc_format/TripsTrk{tod}x.omx` | Statewide truck OD trip matrices in MTC format, read via `src.data.EDA.mtc_od.read_mtc_trips`. |

`{tod}` expands over the five time-of-day periods (`EA`, `AM`, `MD`, `PM`, `EV`).

## Outputs

All outputs are written to **`data/interim/trip_distribution_inputs/`**.

| File | Format | Description |
|------|--------|-------------|
| `mtc_blended_skims.omx` | OMX | One blended impedance matrix per truck type × impedance. Matrix names match the keys of `blended_skim_defs` (e.g. `blended_time_strucks`, `blended_distance_ctrucks`). |
| `SW_trip_generation_TAZ1454.parquet` | Parquet | TAZ-level P/A table (see schema below). Consumed by the calibration as `pa_path`. |
| `SW_trip_generation_TAZ1454.csv` | CSV | Same content as the parquet, for inspection. |
| `observed_frequency_distribution_{skim}.csv` | CSV | One observed TLFD per truck type × impedance (see schema below). Consumed by the calibration as each run's `tlfd_path`. |

These paths line up with the [`configs/trip_distribution.yaml`](../../../configs/trip_distribution.yaml) `pa_path`, `skim_path`, and `tlfd_path` fields — this pipeline is what populates them.

### P/A table schema (`SW_trip_generation_TAZ1454.*`)

One row per TAZ, indexed by `TAZ1454` (1-based zone ID). Eight value columns: a production and an attraction column per truck class.

| Column | Type | Description |
|--------|------|-------------|
| `TAZ1454` | int | 1-based internal TAZ ID (index). |
| `very_small_trucks_production` | float | Daily very-small-truck productions (trips originating in the zone). |
| `small_trucks_production` | float | Daily small-truck productions. |
| `medium_trucks_production` | float | Daily medium-truck productions. |
| `large_trucks_production` | float | Daily large-truck productions. |
| `very_small_trucks_attraction` | float | Daily very-small-truck attractions (trips destined for the zone). |
| `small_trucks_attraction` | float | Daily small-truck attractions. |
| `medium_trucks_attraction` | float | Daily medium-truck attractions. |
| `large_trucks_attraction` | float | Daily large-truck attractions. |

### Observed TLFD schema (`observed_frequency_distribution_*.csv`)

One row per impedance bin (5-unit width — 5 minutes for time skims, 5 miles for distance skims).

| Column | Type | Description |
|--------|------|-------------|
| `bin_id` | int | Sequential bin index. |
| `bin_start` | float | Left edge of the bin (inclusive). |
| `bin_end` | float | Right edge of the bin (exclusive). |
| `center` | float | Bin midpoint. |
| `trips` | float | Total trips falling in the bin. |
| `share` | float | Fraction of total trips in the bin (shares sum to ~1.0). |

The calibration's TLFD loader uses the `bin_start`, `bin_end`, and `share` columns; the others are for inspection.

## Blended Skim Definitions

The blended skims produced in output 1 are declared in `blended_skim_defs` in [`build_inputs.py`](build_inputs.py). Each entry names a source skim, its toll counterpart, and the time-period weights to blend:

| Output matrix | Source skim | Toll skim | Weights |
|---------------|-------------|-----------|---------|
| `blended_time_{v,s,m,c}trucks` | `TIME{VSM,SML,MED,LRG}` | `TOLLTIME{…}` | `2/3 MD + 1/3 AM` |
| `blended_distance_{v,s,m,c}trucks` | `DIST{VSM,SML,MED,LRG}` | `TOLLDIST{…}` | `MD` only |

For each pair the toll and non-toll components are blended at a **50/50 toll share**, then written as a matrix in `mtc_blended_skims.omx`. The distance-based skims support evaluating distance impedance as an alternative to the legacy time-based formulation ([travel-model-one #99](https://github.com/BayAreaMetro/travel-model-one/issues/99)).

## Notes

- **Internal zones only.** Skims and trips are filtered to origin/destination ≤ 1,454 before any computation, so gateway/external zones are excluded from every output.
- **Bin width.** TLFDs use 5-minutes/5-miles bins; the calibration and friction-factor step can re-bin as needed. The 1-minute / 1-mile structure of the TM-1.6 `truckFF.dat` friction factors is the reference interval this replicates at a coarser resolution.

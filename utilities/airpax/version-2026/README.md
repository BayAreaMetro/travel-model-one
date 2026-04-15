# Make Air Passenger Demand

Build 2023 and 2050 airport ground-access origin-destination matrices (`.dbf`) for SFO, OAK,
and SJC by expanding airport-level ground-access trip totals down to the
TAZ level.

## Quick start (Python)

Install [uv](https://docs.astral.sh/uv/) and then:

```
uv sync
uv run python make_air_passenger_demand.py
```

Reads `Parameters.xlsx`, uses `utilities/geographies/taz-superdistrict-county.csv` for the
TAZ -> super-district correspondence, and writes 24 DBFs to `output/`.

Please see this [Box location](https://mtcdrive.box.com/s/b73mnd358nl3j7i09881vjr3w6qn4tmr) for the output files. 

To point at a different Excel file:

```
uv run python make_air_passenger_demand.py --params path/to/MyParameters.xlsx
```

You can also step through the script interactively in VS Code - it is divided into `# %%` cells that can be executed one by one.

## Comparing Python output against the R reference

`compare_outputs.py` diffs every DBF in `output/` against a matching file in
`reference_output/` (or any two directories you specify). Copy the 24 DBFs
produced by the R script into `reference_output/`, then run:

```
uv run python compare_outputs.py
```

The script prints a per-file table of row counts, column counts, and the
maximum absolute and relative difference across all numeric columns, with a
pass / fail verdict. To override directories or the tolerance:

```
uv run python compare_outputs.py --py output --r reference_output --tol 0.01
```

Exit status is 0 if every file matches within tolerance, 1 otherwise.

## Files

| File | Purpose |
| --- | --- |
| `make_air_passenger_demand.py` | Main Python pipeline. Reads the parameters workbook, expands the OD matrices, applies vehicle-occupancy factors, and writes DBFs. Organised into `# %%` cells for interactive execution. |
| `Parameters.xlsx`              | All model inputs. See sheet descriptions below. |
| `taz-superdistrict-county.csv` | TAZ -> super-district -> county correspondence. Replaces the shapefile used by the R version. Columns of interest: `ZONE` (TAZ) and `SD` (super district). |
| `pyproject.toml`               | uv / pip project metadata - pins `pandas` and `openpyxl`. |
| `uv.lock`                      | uv-resolved dependency lockfile. Commit alongside `pyproject.toml`. |
| `make-air-passenger-demand.R`  | Original R implementation. Kept for reference; not required to run the Python version. |
| `presentation-on-development-outcomes.pdf` | Background deck on the assumptions and methodology. |
| `output/`                      | 12 non-transit vehicle-trip DBFs (3 airports x 2 directions x 2 years). Produced at run time. Stored in [Box](https://mtcdrive.box.com/s/b73mnd358nl3j7i09881vjr3w6qn4tmr) (see above). |
| `compare_outputs.py`           | Utility to diff Python output DBFs against a reference set (e.g. from the original R script). See section above. |

## `Parameters.xlsx` sheets

| Sheet | Description |
| --- | --- |
| `Airport_File_Map`          | Maps each of the 12 output file names to an airport, direction, year, airport TAZ, and TAZ range. |
| `Air_Pax_Targets`           | One-way ground-access person-trip target per file. |
| `Super_Dist_Shares`         | Super-district share of trips per file (34 districts x 12 files = 408 rows). |
| `Zone_Shares`               | Within-district zonal shares per (airport, direction) for the eight non-transit access modes (1454 zones x 3 airports x 2 directions = 8724 rows). |
| `TOD_Access_Submode_Shares` | TOD x access mode x submode shares per file. Column values in the output DBFs are `SHARE_TOD * SHARE_ACCESSMODE * SHARE_SUBMODE`. |
| `Transit_TOD_Access_Shares` | Transit mode share and TOD splits per file. |
| `Transit_Zone_Shares`       | Zonal share of transit person-trips per (airport, direction, zone). |
| `Veh_Occupancy`             | Person-to-vehicle conversion factors. `SUBMODE='VN_HT_CH_S3'` overrides the default S3 factor for VN / HT / CH. |

Additional sheets (`Lookups`, `Source`, `Notes`) are documentation only and are
ignored by the pipeline.

## Outputs

Two DBF sets, all at the TAZ level, each file containing 1454 rows
(one per TAZ):

- `Output/<file>.dbf` - non-transit vehicle trips. 90 numeric columns named
  `<TOD>_<ACCESS>_<SUBMODE>` (e.g. `AM_PK_DA`), plus `ORIG` and `DEST`.
- `Output_Transit/TR_<file>.dbf` - transit person trips. 5 numeric columns
  `EA_TR, AM_TR, MD_TR, PM_TR, EV_TR`, plus `ORIG` and `DEST`.

## How the pipeline works

1. Load all eight sheets from `Parameters.xlsx` and coerce share values to
   decimals.
2. Load `taz-superdistrict-county.csv` for the TAZ -> super-district
   correspondence.
3. For every `FILE_NAME` in `Airport_File_Map`, build one OD row per TAZ with
   ORIG / DEST set from the airport TAZ and direction.
4. Compute `ROW_SHARE_<mode> = super_district_share * within_district_zone_share`
   for each access mode.
5. Non-transit: multiply `ROW_SHARE_<mode>` by `SHARE_TOD * SHARE_ACCESSMODE *
   SHARE_SUBMODE` and by the file-level `TARGET` to get person trips, then
   divide by the occupancy factor to get vehicle trips.
6. Transit: multiply the transit zonal share by `SHARE_ACCESSMODE * SHARE_TOD`
   and by the base-file `TARGET` to get transit person trips.
7. Write each table as a dBASE-III DBF (10-character field names, 2 decimals).

## Notes on the R -> Python port

- The R shapefile join is replaced by a CSV lookup (`taz-superdistrict-county.csv`).
  `SD` in the CSV corresponds to `DISTRICT` throughout the parameter file.
- Column-name cleaning follows the same convention as R's `janitor::clean_names`
  followed by uppercase (spaces and punctuation become underscores).
- DBF output is written by a small in-repo writer (`dbf_writer.py`) that
  matches `foreign::write.dbf` for the numeric fields used here.
- Share values are accepted as fractions (0.05) or percentages (5), just like
  the R script's `to_share`.

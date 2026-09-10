# Airport Passenger Demand Parameters

The CSV files in this directory provide the configuration, assumptions, and source-derived distributions used to create the airport passenger demand matrices. Files identified as user-maintained may be edited when model assumptions or targets change. Source-derived files should be regenerated with `build_parameters.py` rather than edited directly.

## Parameter manifest

| File | User editable? | Description | Source |
|---|---|---|---|
| `airport_output_file_map.csv` | Yes | Defines each airport demand output, including airport, direction, model year, airport TAZ, and modeled TAZ range. | Model configuration maintained by the user. |
| `airport_passenger_targets.csv` | Yes | Airport passenger ground-access person-trip target for each airport, direction, and model year. | Model configuration maintained by the user. |
| `airport_non_transit_vehicle_occupancy.csv` | Yes | Person-to-vehicle conversion factors used to convert non-transit person trips to vehicle trips. | Model assumptions. |
| `airport_non_transit_tod_shares.csv` | Yes | Time-of-day distribution for non-transit airport ground-access trips by airport and direction. | 2023: FourAirportStudy (2023). The 2050 assumptions use the same TOD distributions as 2023. |
| `airport_non_transit_access_mode_shares.csv` | Yes | Non-transit airport access-mode distribution by airport and direction. | `from` shares are assumed to be same as `to`. OAK `to`: SFO Ground Access Survey 2024. SFO `to`: Ground Access Survey 2024. SJC `to`: ASQ Departures Survey (2025). |
| `airport_transit_tod_shares.csv` | Yes | Time-of-day distribution for transit airport ground-access trips by airport and direction. | Transit passenger survey (TPS) summaries supplied by MTC for non-work trips: 2022 SamTrans and 2024 BART summaries for OAK/SFO and 2017 VTA for SJC. |
| `airport_transit_mode_shares.csv` | Yes | Overall transit share of airport ground-access trips by airport and direction. | Airport access-mode assumptions using the airport-specific survey sources described above. |
| `airport_non_transit_super_district_shares.csv` | No | Super-district distribution for each airport, direction, and model year. | Gosling airport summary DBFs in `../inputs/gosling_summaries/` and the model TAZ-to-super-district correspondence. Model year 2023 uses the 2007 Gosling summaries; model year 2050 uses the 2035b summaries. |
| `airport_non_transit_submode_shares.csv` | No | DA/S2/S3 person-trip distribution by airport, direction, model year, and non-transit access mode. | Gosling airport summary DBFs in `../inputs/gosling_summaries/`. Model year 2023 uses the 2007 summaries and model year 2050 uses the 2035b summaries. |
| `airport_non_transit_zone_access_mode_shares.csv` | No | Within-super-district TAZ distribution for each non-transit airport access mode. | 2007 Gosling airport summary DBFs in `../inputs/gosling_summaries/` and the model TAZ-to-super-district correspondence. |
| `airport_transit_zone_shares.csv` | No | TAZ distribution of transit airport trips by airport and direction. | `../inputs/TPS_TAZ_airport_TOD.xlsx`. The `TAZ from Airport` and `TAZ to Airport` worksheets are aggregated to airport totals by TAZ before zonal shares are calculated. Transit-operator columns serving the same airport are combined before the shares are calculated. |

## Source data outside the parameters directory

### `../input/gosling_summaries/`

Contains airport summary DBFs for 2007, 2035, and 2035b for OAK, SFO, and SJC in both travel directions. The parameter build uses:

- 2007 summaries for the 2023 super-district and non-transit submode distributions.
- 2035b summaries for the 2050 super-district and non-transit submode distributions.
- 2007 summaries for non-transit within-super-district zonal distributions.

### `../input/TPS_TAZ_airport_TOD.xlsx`

Contains transit airport trips by TAZ, survey year, time period, transit operator, and airport. The parameter build aggregates these records to TAZ-level airport totals separately for trips to and from the airports and calculates the transit zonal distributions.

### `../../geographies/taz-superdistrict-county.csv`

The model geography correspondence used to assign TAZs to super districts. The file remains in the model geography directory and is read directly from that location. The airport demand matrices use internal TAZs 1 through 1454.

## Building source-derived parameters

Run the parameter builder whenever the Gosling summaries, transit TAZ workbook, geography correspondence, or relevant assumptions are updated:

```bash
python build_parameters.py
```

The demand script also supports rebuilding these source-derived parameter files immediately before creating the airport matrices:

```bash
python make_air_passenger_demand.py --rebuild-parameters
```

The detailed TOD, access-mode, and submode combinations used by the calculations are assembled in memory from the component parameter files and are not stored as separate CSVs.

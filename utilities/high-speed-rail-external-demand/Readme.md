
This directory contains the script and mapping needed to create TM1 input files from 
HSR model output files.

Files in this directory
=======================

## Travel Model 1.6

See October 2023 task, [Update interregional rail (CAHSR) travel assumptions](https://app.asana.com/0/1204085012544660/1203768378006034/f)

* [`createInputTripTablesFromHSR.py`](createInputTripTablesFromHSR.py) - Script to read the HSR model access tables and convert CHSR zones to
  TM1 zones. Outputs trips to the Bay Area HSR tables from within-region and external.  This script uses
  [Box: CHSR_data_from_DB-ECO_July2023 (internal only)](https://mtcdrive.box.com/s/pbf7j2taz45ulfl22ltauorninx6wwq6)
  and includes assumptions regarding annual-to-daily factors, daily-to-timeperiod distributions, and
  person trips to vehicle trip conversions.  It also creates detailed egress tables from the access tables
  using the relationship between egress/access by station from the previous version of the data.

  * [`createInputTripTablesFromHSR_log.txt`](createInputTripTablesFromHSR_log.txt) - Log file from running
    `python .\createInputTripTablesFromHSR.py > .\createInputTripTablesFromHSR_log.txt 2>&1`

* [`HSR_access_egress.twb`](HSR_access_egress.twb) tableau workbook visualizing the results of the Travel Model v0.6-1.5
  version of the input, alongside the updated input. This is published (internally) to 
  [Tableau Online: Modeling/Plan Bay Area 2050+/HSR_access_egress](https://10ay.online.tableau.com/#/site/metropolitantransportationcommission/views/HSR_access_egress/RTP2025CHSRInputUpdate?:iid=1)

* [`convert_access_egress_trips_to_matrix.job`](convert_access_egress_trips_to_matrix.job) - Script to convert resulting trips from
  `createInputTripTablesFromHSR.py` to Cube matrices for use during the model run.

  * [`convert_access_egress_trips_to_matrix_2040log.txt`](convert_access_egress_trips_to_matrix_2040log.txt) - Log file from
    running `convert_access_trips_to_matrix.job` for year 2040.

  * [`convert_access_egress_trips_to_matrix_2050log.txt`](convert_access_egress_trips_to_matrix_2050log.txt) - Log file from
    running `convert_access_trips_to_matrix.job` for year 2050.

## Travel Model One v0.6-v1.5

See June 2016 task, [Add high speed rail external demand](https://app.asana.com/0/13098083395690/97041507197227/f)

These files have been superceded by the above.

* `HSR_taz7000_to_externalTM1taz.csv` - This file maps the HSR TAZs to external TM1 TAZs so that trips
  that come through the Bay Area to access a Bay Area HSR station can originate from an external TM1 node.
  This file was created in ArcGIS via `M:\Development\Travel Model One\Version 06\GIS Exports\Networks.mxd`.
  Asana task: Add high speed rail external demand > [Map out-of-Bay Area TAZs to external TAZ](https://app.asana.com/0/15119358130897/141338152083779)

* `renumberHRSRtoTM1.csv` - This file is similar to `HSR_taz7000_to_externalTM1taz.csv` but formatted for
  Cube's RENUMBER (MATRIX program) directive.  It also renumbers the HSR station nodes to the TM1 TAZs
  corresponding to the locations of those stations.

* `createInputTripTablesFromHSR.job` - This file reads in the HSR model access and egress tables, filters
  only to those access and egress trips for Bay Area HSR stations, and renumbers them to TM1 nodes using
  `renumberHRSRtoTM1.csv`.  It outputs `INPUT\nonres\tripsHsrXX_YYYY.tpp` where `xx` is a timeperiod and
  `YYYY` is the model year.  Asana task: Add high speed rail external demand > [Create input trip tables for HSR access/egress](https://app.asana.com/0/15119358130897/141338152083782)

* [`export_TM1.5_trip_matrix_to_csv.job`](export_TM1.5_trip_matrix_to_csv.job) exports matrices from this
  process to CSV to visualize alongside more recent versions

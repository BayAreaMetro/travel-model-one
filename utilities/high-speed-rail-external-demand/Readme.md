
This directory contains the script and mapping needed to create TM1 input files from 
HSR model output files.

Files in this directory
=======================

## Travel Model 1.6

See October 2023 task, [Update interregional rail (CAHSR) travel assumptions](https://app.asana.com/0/1204085012544660/1203768378006034/f)

* TBD

## Travel Model One v0.6

See June 2016 task, [Add high speed rail external demand](https://app.asana.com/0/13098083395690/97041507197227/f)

These files have been superceded by the above.

* `HSR_taz7000_to_externalTM1taz.csv` - This file maps the HSR TAZs to external TM1 TAZs so that trips
  that come through the Bay Area to access a Bay Area HSR station can originate from an external TM1 node.
  This file was created in ArcGIS via `M:\Development\Travel Model One\Version 06\GIS Exports\Networks.mxd`.
  Asana task: https://app.asana.com/0/15119358130897/141338152083779

* `renumberHRSRtoTM1.csv` - This file is similar to `HSR_taz7000_to_externalTM1taz.csv` but formatted for
  Cube's RENUMBER (MATRIX program) directive.  It also renumbers the HSR station nodes to the TM1 TAZs
  corresponding to the locations of those stations.

* `createInputTripTablesFromHSR.job` - This file reads in the HSR model access and egress tables, filters
  only to those access and egress trips for Bay Area HSR stations, and renumbers them to TM1 nodes using
  `renumberHRSRtoTM1.csv`.  It outputs `INPUT\nonres\tripsHsrXX_YYYY.tpp` where `xx` is a timeperiod and
  `YYYY` is the model year.  Asana task: https://app.asana.com/0/15119358130897/141338152083782


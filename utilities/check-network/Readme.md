
## Check and update network

This directory contains the scripts relevant to checking networks and doing final network coding.

Use *pre_roadway_network.bat* to create **_INPUT\hwy\freeflow.net_** from **_INPUT\hwy\source\descriptive_name.net_**.

Use *build_transit_network.bat* to check the transit networks in **_INPUT\trn_** (with **_INPUT\hwy_**)

## Directory Structure

The following directory structure is expected

```
M:\Application\Model One\STIP2017\2040_06_XXX\ = use this for MODEL_DIR
  INPUT\
    hwy\
      source\
        descriptive_name.net    = source roadway network, use this for ROADWAY_FILE
        descriptive_name.xlsx   = information about what projects are in (and not in) the network, roadway and transit
    trn\
      transit_fares\
      transit_lines\
      transit_support\
    trn_check\                  = used for checking transit
  CTRAMP\
    scripts\
      preprocess\
        SetTolls.JOB            = file with bridge and express lane tolls.  Otherwise, github version is used (which is probably wrong!)
```


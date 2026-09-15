

# Experiments


This document summarizes the experimental model runs conducted during the TM-1.7 truck model update effort. The experiments were designed to evaluate the individual and combined impacts of proposed modifications to the commercial model. Results from these experiments informed the selection of the final TM-1.7 truck model specification documented in [TM-1.7 Updates](../README.md#tm-17--truck-model-updates)

All experiments were performed as incremental modifications to a 2023 TM-1.6 baseline model run ([2023_TM161_IPA_35](https://mtcdrive.box.com/s/rrgnyrc73uogqvxtzvkihxz8cqlyeg67)). Each experiment isolates one or more model changes to quantify their effect on validation performance.

Experiment configurations, scenario definitions, and model scripts are maintained [travel_model_scenarios.yaml](../configs/travel_model_scenarios.yaml). The scenario configuration files document the specific model components, inputs, and scripts used for each experiment and provide a reproducible record of the testing process. 

The table below summarizes the progression of experiments evaluated during development of TM-1.7 and identifies the model components modified in each scenario.

| Experiment | Trip Generation | Trip Distribution | Time of Day | IX/XI/XX Demand | Special Generators |
|------------|-----------------|-------------------|-------------|-----------------|--------------------|
| **TM-1.6** | No change | No change | No change  | No change  | No change  |
| **TM-1.6_FIX_ROUNDING_ISSUE** | No change  | No Change | Rounding Fix | No change | No change |
| **TM-1.6_FIXES** | No change  | Fix large trucks blended time parenthesis | Rounding Fix | No change | No change |
| **TM-1.6_TRK_SW**\* | N/A | N/A | N/A | N/A | N/A |
| **TM-1.7_GEN_REEST** | Keeps TM-1.6 model specs and re-estimates with CSF2TDM data | Distance-based Friction Factors | Estimated based on observed data + Rounding Fix | No change | No change |
| **TM-1.7_GEN_NEWSPEC** | Relaxes specification to improve fit using CSF2TDM data.| Distance-based Friction Factors | Estimated based on observed data + Rounding Fix | No change | No change |
| **TM-1.7_GEN_IX** | Relaxes specification to improve fit using CSF2TDM data.| Distance-based Friction Factors | Estimated based on observed data + Rounding Fix | Adjusts XI-XI factors to match CSF2TDM XI-IX total trips.| No change |
| **TM-1.7_GEN_IX_NVF** | Relaxes specification to improve fit using CSF2TDM data + remove 0.4 factor from very small trip production equation | Distance-based Friction Factors | Estimated based on observed data + Rounding Fix | Adjusts XI-XI factors to match CSF2TDM XI-IX total trips.| No change |
| **TM-1.7_SPECIAL_GENERATORS** | Relaxes specification to improve fit using CSF2TDM data | Distance-based Friction Factors | Estimated based on observed data + Rounding Fix | Adjusts XI-XI factors to match CSF2TDM XI-IX total trips.| Adds observed special generator trip totals from CSF2TDM and the ALACC\*\* models |
| **TM-1.7_CTRUCKS_MODIFIED_FF** | Relaxes specification to improve fit using CSF2TDM data | Distance-based Friction Factors + Artifical increase average trip length for large trucks | Estimated based on observed data + Rounding Fix | Adjusts XI-XI factors to match CSF2TDM XI-IX total trips.| Adds observed special generator trip totals from CSF2TDM and the ALACC\*\* models  |
| **TM-1.7_FINAL** | Relaxes specification to improve fit using CSF2TDM data | Distance-based Friction Factors | Estimated based on observed data + Rounding Fix | Adjusts XI-XI factors to match CSF2TDM XI-IX total trips.| Estimates special generator trips using Trips/region_TOTEMP rates derived from the CSF2TDM and ALACC** models. |

Notes: 
- \* TM-1.6_TRK_SW assigns CSF2TDM truck OD trips for small, medium, and large truck classes while preserving the very small OD truck trips from TM-1.6.
- \*\* ALACC - Alameda and Contra Costa bi-county model 

The CUBE scripts an experiment swaps in (`.bat` restart variants, `.job` model steps, and the friction-factor `.dat`) live in [`TruckTripGeneration_scripts/`](TruckTripGeneration_scripts/). The CUBE→Python output-conversion scripts used in step 4 — `.tpp`→`.omx` and `.net`→shapefile — live in [`cube_scripts/`](cube_scripts/).

## Outputs

Per scenario, under `output_root/<name>/`. This are run locally, a copy from this runs are stored in Box [Trucks/data/model_runs](https://mtcdrive.box.com/s/mdsfvmr2r6juf3obfflumaa37ksieq84)

- `hwy/iter<ITER>/`: assigned networks for this run (`ITER=TEST` by default), kept separate from the base run's iterations.

Per run, under the timestamped experiment directory:

- `configurations_used.yaml`: the exact resolved config, for reproducibility.
- Evaluation outputs (scatter plots, VMT comparison, Excel workbook, validation shapefile).
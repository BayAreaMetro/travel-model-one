
# Scripts and data used to create 2023 travel model land use inputs

##  [`../create_tazdata_2020_and_after.R`](../create_tazdata_2020_and_after.R)

This script brings in all inputs and creates 2023 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and 
[tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for 
[Travel Model 1.6](https://github.com/BayAreaMetro/travel-model-one).  
It also utilizes functions in [`../common.R`](../common.R).

See the detailed note regarding methodology at the top of [`../create_tazdata_2020_and_after.R`](../create_tazdata_2020_and_after.R), 
as well as source tables in [../Readme.md](../Readme.md).
  
### Outputs:
* [TAZ1454 2023 Land Use.csv](TAZ1454%202023%20Land%20Use.csv)
* [TAZ1454 2023 District Summary.csv](TAZ1454%202023%20District%20Summary.csv)
* [TAZ1454 2023 Popsim Vars.csv](TAZ1454%202023%20Popsim%20Vars.csv)
* [TAZ1454 2023 Popsim Vars Region.csv](TAZ1454%202023%20Popsim%20Vars%20Region.csv)
* [TAZ1454 2023 Popsim Vars County.csv](TAZ1454%202023%20Popsim%20Vars%20County.csv)

See also:
  * [Asana task: Prepare 2023 land use input](https://app.asana.com/0/0/1204384692879834/f)
  * [Asana task: Refresh 2023 travel model tazdata](https://app.asana.com/0/15119358130897/1208403592422847/f)


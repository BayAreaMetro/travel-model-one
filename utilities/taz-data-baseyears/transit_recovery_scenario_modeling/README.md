
# Create land use data for Transit Recovery Scenario Modeling

### [Asana project](https://app.asana.com/0/1202096261083752/1202096261083752)

### Scripts in this folder

[transit_recovery_plan_2020_land_use.ipynb](transit_recovery_plan_2020_land_use.ipynb)

Creates 2020 land use to represent the base year for transit recovery scenarios. Instead of creating the full set of land use data for Travel Model (TM1.5), this scripts compares Bay Area UrbanSim Final Blueprint 2020 output 'taz_summaries' with available demographic and employment data from Census and ESRI Business Analyst, and scales attributes that deviate significantly from these referencing data sources. The detailed methodology of comparison and scaling is included in the script. The scaled 'taz_summaries' will feed into [populationsim](https://github.com/BayAreaMetro/populationsim) to create full set of land use inputs for Travel Model.  

## Off-model calculation

Travel Model One is not sensitive to the full range of policies MTC and ABAG may choose to pursue in RTP. Marketing and education campaigns, as well as non-capacity-increasing transportation investments likebikeshare programs, are examples of strategies with the potential to change behavior in ways that result in reduced vehicle emissions. Travel Model 1.5 and EMFAC do not estimate reductions in emissions in response to these types of changes in traveler behavior. As such, “off-model” approaches are used to quantify the GHG reduction benefits of these important climate initiatives.

The off-model calculation process follows Travel Model One run. It contains the following steps, not fully automated.
    
### Prepare model data for off-model calculation

1. Run [trip-distance-by-mode-superdistrict.R](https://github.com/BayAreaMetro/travel-model-one/tree/master/utilities/bespoke-requests/trip-distance-by-mode-superdistrict) to create a super-district trip distance summary, which is not a standard model output. 
  * run the script on modeling server where the full run data is stored:
  ```
  2050_TM160_DBP_Plan_04/
    core_summaries/
      trip-distance-by-mode-superdistrict.csv
  ```
  * copy the output file into M:
  ```
  2050_TM160_DBP_Plan_04/
    OUTPUT/
      bespoke/
        trip-distance-by-mode-superdistrict.csv
  ```
 
2. Run the following scripts. Example call: `Rscript BikeInfrastructure.R "X:\travel-model-one-master\utilities\RTP\config_RTP2025\ModelRuns_RTP2025.xlsx" output_dir`
  * [BikeInfrastructure.R](BikeInfrastructure.R)
  * [Bikeshare.R](Bikeshare.R)
  * [Carshare.R](Carshare.R)
  * [EmployerShuttles.R](EmployerShuttles.R) (vanpools strategy)
  * [TargetedTransportationAlternatives.R](TargetedTransportationAlternatives.R)

### Create off-model calculation Excel worbooks for a given run set (including a 2035 run and a 2050 run)

Start with a master version off-model calculation Excel workbook, e.g. `OffModel_Bikeshare.xlsx`.
Run [update_offmodel_calculator_workbooks_with_TM_output.py](update_offmodel_calculator_workbooks_with_TM_output.py) with model_run_id as the arguments to create a copy of the master workbook, fill in the relevant model output data, and update the index in "Main Sheet".
  * Example call: `python update_offmodel_calculator_workbooks.py bike_share 2035_TM160_DBP_Plan_04 2050_TM160_DBP_Plan_04`. This creates `OffModel_Bikeshare__2035_TM160_DBP_Plan_04__2050_TM160_DBP_Plan_04.xlsx`.

### Manually open and save the newly created Excel workbook to trigger the calculation

### Summarize off-model calculation results

Once all the off-model calculation Excel workbooks for a set of model run have been created, run [summarize_offmodel_results.py](summarize_offmodel_results.py) to pull data from the Excel workbooks, summarize the results, and create summary tables, which will be automatically loaded into Travel Model Tableau dashboard ([internal link](https://10ay.online.tableau.com/#/site/metropolitantransportationcommission/views/across_RTP2025_runs/EmissionsandOff-model)). 

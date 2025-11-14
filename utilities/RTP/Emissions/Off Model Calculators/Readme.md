# Off-model calculation
Travel Model One is not sensitive to the full range of policies MTC and ABAG may choose to pursue in RTP. Marketing and education campaigns, as well as non-capacity-increasing transportation investments like bike share programs, are examples of strategies with the potential to change behavior in ways that result in reduced vehicle emissions. Travel Model 1.5 and EMFAC do not estimate reductions in emissions in response to these types of changes in traveler behavior. As such, “off-model” approaches are used to quantify the GHG reduction benefits of these important climate initiatives.

## Current Off-Model Calculators
In Plan Bay Area 2050, MTC/ABAG conducted off-model analysis to evaluate the GHG impacts of initiatives that could not be captured in the regional travel model. These initiatives constituted most of the key subcomponents of Strategy EN8: Expand Clean Vehicle Initiatives and Strategy EN9: Expand Transportation Demand Management Initiatives:

-	Strategy EN8: Initiative EN8a – Regional Electric Vehicle Chargers
-	Strategy EN8: Initiative EN8b – Vehicle Buyback Program 
-	Strategy EN8: Initiative EN8c – Electric Bicycle Rebate Program - NEW
-	Strategy EN9: Initiative EN9a – Bike Share
-	Strategy EN9: Initiative EN9b – Car Share
-	Strategy EN9: Initiative EN9c – Targeted Transportation Alternatives
-	Strategy EN9: Initiative EN9d – Vanpools


The off-model calculation process follows Travel Model One run. It contains the following steps. The process is fully automated.

## Latest Updates
- **Full automation of the process:** pulling from the RTP config files to summarizing outputs ready to be used in a Tableau dashboard.
- **Simplification of the output tab:** the ‘Output’ tab of each calculator will no longer append a running history of the calculator ‘system state’ – only the current run – instead, this duty of storing a running history will be taken on by Tableau Online (eventually).
- **Added to 'Variable_locations.csv':** the csv has now two columns, pointing the automated scripts to the appropriate cell locations based on whether the Travel Model run is a year 2035 or 2050 run.

# General Process Workflow
Below is the general process workflow triggered when running the main script `update_offmodel_calculator_workbooks_with_TM_output.py`:

![Off-model calculator workflow](assets/off-model%20calculator%20workflow.png)

## Identify model run
The program reads the `ModelRuns_RTP2025.xlsx` file located in `utilities\RTP\config_RTP2025` and filters its data based on the condition that the column J, or Off-Model Calculator, has a "Y". 

## Get model data
The program then gets the model data belonging to the model run (e.g. 2050_TM160_DBP_Plan_04) which is required in the off-model calculator (when applicable) by creating a bespoke request.

The program gets the model data from two R scripts, which run automatically:

## Get SB 375 calculation
The SB 375 tab in each calculator now lists 2005 data. There is a `SB375.csv` which holds 2005 data and will be updated manually as needed. This value is pushed automatically to each calculator.

The 2005 change is only triggered by a Travel Model update, therefore, its considered a type of "off-model calculator update." When a new version of the Travel Model exists, it would recalculate 2005 and create a new version of the off-model calculators.

## Calculator updates
Each Excel Off-model calculator is updated with the following data:
- Model run
- Year
- Model data
- SB 375 data
- Variable locations

Note: the variable locations is a file that specifies all variables used in each calculator and their corresponding cell locations in Excel format (e.g. A1).

Then, the results are saved in new excel workbooks.

## Results from the run
The program then stores the outputs of the Excel workbooks into a centralized logger in the server. It also creates a summarized table with the outputs of each calculator, which will be automatically loaded into the Travel Model Tableau dashboard ([internal link](https://10ay.online.tableau.com/#/site/metropolitantransportationcommission/views/across_RTP2025_runs/EmissionsandOff-model)). 
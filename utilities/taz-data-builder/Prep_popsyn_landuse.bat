:: this batch script is assumed to be run from the relevant subdirectory within the INPUT_DEVELOPMENT directory 
:: M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\PopSyn_n_LandUse\Basic_00\2050

:: to call this batch script, type the script name and then four arugments
:: also make sure to add "> prep_popsyn_landuse.log 2>&1" when you call the batch file so a log will be produced
:: e.g. 
:: X:\travel-model-one-master\utilities\taz-data-builder\prep_popsyn_landuse.bat NoProject 20240307 PBA50Plus_NP_InitialRun_v8 2035 M:\urban_modeling\baus\PBA50Plus\PBA50Plus_NP_InitialRun\outputs\PBA50Plus_NP_InitialRun_v8 > prep_popsyn_landuse.log 2>&1
:: 
:: the 3 arugments are:
:: 1. Scenario/Future Name - e.g. NoProject, DBP
:: 2. Date of populationsim run - e.g. 20200622
:: 3. Land use run name - e.g. PBA50Plus_Preservation
:: 4. Model Year - e.g. 2035
:: 5. UrbanSim output folder
::

:: expand variables at execution time rather than parse time
SETLOCAL EnableDelayedExpansion
:: note we dequote arg 5 
echo ARG1=[%1]  ARG2=[%2]  ARG3=[%3]  ARG4=[%4]  ARG5=[%~5]

::-----------------------------
:: pop syn files
::-----------------------------
mkdir popsyn

echo
echo *****THE SOURCES OF THE POPSYN FILES ARE:*****
copy \\model3-a\Model3A-Share\populationsim_outputs\hh_gq\output_%1_%2_%4_%3\synthetic_households_recode.csv     popsyn\hhFile.%1.%4.%3.csv
copy \\model3-a\Model3A-Share\populationsim_outputs\hh_gq\output_%1_%2_%4_%3\synthetic_persons_recode.csv        popsyn\personFile.%1.%4.%3.csv

::-----------------------------
:: land use files
::-----------------------------
mkdir landuse

echo
echo *****THE SOURCE OF THE TAZDATA FILE IS:*****
copy \\model3-a\Model3A-Share\populationsim_outputs\hh_gq\output_%1_%2_%4_%3\taz_summaries.csv  landuse\taz_summaries_%1_%2_%4_%3.csv

:: to generate tazData.csv
:: todo: test this script is ok for python3
:: ---
cd landuse
python X:\travel-model-one-master\utilities\taz-data-builder\buildTazdata.py taz_summaries_%1_%2_%4_%3.csv

:: to convert csv to dbf
:: ---
set R_HOME=C:\Program Files\R\R-3.4.4\bin
IF %USERNAME%==lzorn (
  set R_HOME=C:\Program Files\R\R-4.2.0\bin
)
IF %USERNAME%==ftsang (
  set R_HOME=C:\Program Files\R\R-4.1.2\bin
)
IF %USERNAME%==mtcpb (
  set R_HOME=C:\Program Files\R\R-3.5.2\bin
)
set F_INPUT=tazData.csv
Set F_OUTPUT=tazData.dbf
"%R_HOME%\Rscript.exe" X:\travel-model-one-master\utilities\taz-data-csv-to-dbf\taz-data-csv-to-dbf.R

:: parking strategy variant
mkdir parking_strategy
cd parking_strategy
python X:\travel-model-one-master\utilities\taz-data-builder\updateParkingCostForParkingStrategy.py ..\tazData.csv tazData_parkingStrategy_v01.csv

set F_INPUT=tazData_parkingStrategy_v01.csv
set F_OUTPUT=tazData_parkingStrategy_v01.dbf
"%R_HOME%\Rscript.exe" X:\travel-model-one-master\utilities\taz-data-csv-to-dbf\taz-data-csv-to-dbf.R


cd ..\..
:: also need to copy the walk access file for 2010 and before
:: otherwise create it with clear name and then copy to walkAccessBuffers.float.csv
:: see https://app.asana.com/0/403262763383022/1161734609745564/f
if %4 LEQ 2010 (
  copy "M:\Application\Model One\RTP2017\Scenarios\2040_06_694_Amd1\INPUT_fullcopy\landuse\walkAccessBuffers.float.csv"          landuse\
)
if %4 EQU 2015 (
  copy "M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\PopSyn_n_LandUse\POPLU_v225\2015\landuse\walkAccessBuffers.float.csv" landuse\
)
IF %4 GTR 2015 (
  rem the only parcel data files output are 2020, 2035, 2050
  rem https://github.com/BayAreaMetro/bayarea_urbansim/blob/32ef490082fc604ab02ae408b55752768ae11520/baus/summaries.py#L1216
  set PARCEL_YEAR=2020
  if %4 GEQ 2035 (set PARCEL_YEAR=2035)
  if %4 GEQ 2050 (set PARCEL_YEAR=2050)
  echo PARCEL_YEAR=!PARCEL_YEAR!
  python x:\travel-model-one-master\utilities\taz-data-builder\tally_household_share_by_taz_subzone.py "%~5\core_summaries\%3_parcel_summary_!PARCEL_YEAR!.csv" landuse\taz_subzone_hhshare_%3_%4.csv
  copy landuse\taz_subzone_hhshare_%3_%4.csv landuse\walkAccessBuffers.float.csv
)




:: this batch script is assumed to be run from the relevant subdirectory within the INPUT_DEVELOPMENT directory 
:: M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\PopSyn_n_LandUse\Basic_00\2050

:: to call this batch script, type the script name and then four arugments
:: also make sure to add "> prep_popsyn_landuse.log 2>&1" when you call the batch file so a log will be produced
:: e.g. 
:: X:\travel-model-one-master\utilities\taz-data-builder\prep_popsyn_landuse.bat BackToTheFuture 20190724 run10 2035 > prep_popsyn_landuse.log
:: X:\travel-model-one-master\utilities\taz-data-builder\prep_popsyn_landuse.bat PBA50 20200522 run939 2050 > prep_popsyn_landuse.log
:: 
:: the 3 arugments are:
:: 1. Future Name - e.g. PBA50PlusCrossing
:: 2. Date of land use model run - e.g. 20200622
:: 3. Land use run number - e.g. run98
:: 4. Model Year - e.g. 2035
:: 5. UrbanSim outut folder
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
copy \\mainmodel\MainModelShare\populationsim\bay_area\output_%4_%1_%2_%3\synthetic_households.csv     popsyn\hhFile.%3.%1.%4.csv
copy \\mainmodel\MainModelShare\populationsim\bay_area\output_%4_%1_%2_%3\synthetic_persons.csv        popsyn\personFile.%3.%1.%4.csv

::-----------------------------
:: land use files
::-----------------------------
mkdir landuse

echo
echo *****THE SOURCE OF THE TAZDATA FILE IS:*****
copy \\mainmodel\MainModelShare\populationsim\bay_area\hh_gq\data\taz_summaries_%1_%2_%3_%4.csv        landuse\

:: to generate tazData.csv
:: ---
cd landuse
set path=%path%;c:\python27
python X:\travel-model-one-master\utilities\taz-data-builder\buildTazdata.py taz_summaries_%1_%2_%3_%4.csv

:: to convert csv to dbf
:: ---
set R_HOME=C:\Program Files\R\R-3.4.4\bin
IF %USERNAME%==lzorn (
  set R_HOME=C:\Program Files\R\R-4.1.1\bin
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

) else (
  rem the only parcel data files output are 2010, 2015, 2035, 2050
  rem https://github.com/BayAreaMetro/bayarea_urbansim/blob/32ef490082fc604ab02ae408b55752768ae11520/baus/summaries.py#L1216
  set PARCEL_YEAR=2015
  if %4 GEQ 2035 (set PARCEL_YEAR=2035)
  if %4 GEQ 2050 (set PARCEL_YEAR=2050)
  echo PARCEL_YEAR=!PARCEL_YEAR!
  python X:\petrale\applications\tally_household_share_by_taz_subzone.py "%~5\%3_parcel_data_!PARCEL_YEAR!.csv" landuse\taz_subzone_hhshare_%3_%4.csv
  copy landuse\taz_subzone_hhshare_%3_%4.csv landuse\walkAccessBuffers.float.csv
)




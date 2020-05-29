:: this batch script is assumed to be run from the relevant subdirectory within the INPUT_repo directory 
:: M:\Application\Model One\RTP2021\Blueprint\INPUT_repo\PopSyn_n_LandUse\Basic_00\2050

:: to call this batch script, type the script name and then four arugments
:: also make sure to add "> prep_popsyn_landuse.log" when you call the batch file so a log will be produced
:: e.g. 
:: X:\travel-model-one-master\utilities\taz-data-builder\prep_popsyn_landuse.bat BackToTheFuture 20190724 run10 2035 > prep_popsyn_landuse.log
:: X:\travel-model-one-master\utilities\taz-data-builder\prep_popsyn_landuse.bat PBA50 20200522 run939 2050 > prep_popsyn_landuse.log
:: 
:: the 3 arugments are:
:: 1. Future Name
:: 2. Date of land use model run
:: 3. Land use run number
:: 4. Model Year

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
  set R_HOME=C:\Program Files\R\R-3.5.1\bin
)
set F_INPUT=tazData.csv
Set F_OUTPUT=tazData.dbf
"%R_HOME%\Rscript.exe" X:\travel-model-one-master\utilities\taz-data-csv-to-dbf\taz-data-csv-to-dbf.R

:: also need to copy the walk access file
:: which hasn't change since 2010
:: ---
cd ..
copy "M:\Application\Model One\RTP2017\Scenarios\2040_06_694_Amd1\INPUT_fullcopy\landuse\walkAccessBuffers.float.csv"          landuse\




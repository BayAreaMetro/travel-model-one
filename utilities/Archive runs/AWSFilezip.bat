:: This script donlaods the model runs from AWS and zips the run to the cloud
::
:: s3 is here: https://s3.console.aws.amazon.com/s3/buckets/travel-model-runs/
:: run from L:\RTP2021_PPA\Projects_onAWS
:: List of the model runs to be zipped:
for /d %%%f in (
2050_TM151_PPA_BF_07_1_Crossings2_00
2050_TM151_PPA_BF_07_1_Crossings1_01
)    do    (

rem if not confident, do a dry run first
rem aws s3 sync --dryrun s3://travel-model-runs/%%modelrun %%modelrun
rem execute
rem -------------------------------------------
aws s3 sync s3://travel-model-runs/%%f %%f
REM Use 7Zip to Zip travel model runs and place the zip archive 
REM in "mtcarchives\cloudmodels1\Archived Travel Model Runs". Then renames folder to X.archived
REM
ECHO
ECHO Zipping all files in %%%f
REM set PROJECT_DIR=%%f
set myfolder=%%f
REM
REM Checks for extractor folder. If not avaialblble, zips individual folders otherwise saved in extractor folder.
REM
If exist "%%f\extractor" (
  "C:\Program Files\7-Zip\7z.exe" a "\\mtcarchives\cloudmodels1\Archived Travel Model Runs\%%f" "%%f\CTRAMP*" "%%f\extractor*" "%%f\INPUT*" "%%f\*.bat" "%%f\*.csv" -mx9
) ELSE (
  "C:\Program Files\7-Zip\7z.exe" a "\\mtcarchives\cloudmodels1\Archived Travel Model Runs\%%f" "%%f\CTRAMP*" "%%f\accessibilities" "%%f\core_summaries" "%%f\main" "%%f\metrics" "%%f\skims" "%%f\trn" "%%f\updated_output" "%%f\INPUT" "%%f\*.bat" "%%f\*.csv" -mx9
)
ren %%f %%~nxf.archived 

)


pause
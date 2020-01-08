:: This script donlaods the model runs from AWS and zips the run to the cloud
::
:: s3 is here: https://s3.console.aws.amazon.com/s3/buckets/travel-model-runs/
:: run from L:\RTP2021_PPA\Projects_onAWS
:: List of the model runs to be zipped:
for /d %%%f in (
2050_TM151_PPA_BF_12_3107_SR87_Tunnel_00
2050_TM151_PPA_BF_12_3110_East_West_Connector_00

)    do    (

rem if not confident, do a dry run first
rem aws s3 sync --dryrun s3://travel-model-runs/%%modelrun %%modelrun
rem execute
rem -------------------------------------------
rem Use this if downlading the whole run:
rem aws s3 sync s3://travel-model-runs/%%f %%f
rem 
rem Use this if only downloading the CTRAMP, extractor and Input folders of the model run:
aws s3 sync s3://travel-model-runs/%%f %%f --exclude 'core_summaries/*' --exclude 'database/*' --exclude 'landuse/*' --exclude 'logs/*' --exclude 'logsums/*' --exclude 'main/*' --exclude 'metrics/*' --exclude 'nonres/*' --exclude 'popsyn/*' --exclude 'skims/*' --exclude 'trn/*' --exclude 'updated_output/*' --exclude '*.log' --exclude '*.prj' --exclude '*.var'
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
REM This will add the extension .archived to the folder downloaded
REM ren %%f %%~nxf.archived 
REM del %%f %%~nxf

REM Keep this to delete the directory and files downloaded from S3 from the local computer
del /F/Q/S %%f %%~nxf > NUL
RMDIR /Q/S %%f %%~nxf

)

Exit

:: s3 is here: https://s3.console.aws.amazon.com/s3/buckets/travel-model-runs/

:: the command to sync:
:: aws s3 sync --dryrun [from directory] [to directory]
:: aws s3 sync --dryrun [aws directory] [local directory]

:: run from L:\RTP2021_PPA\Projects_onAWS
for /d %%f in (

2050_TM151_PPA_RT_06_2300_CaltrainDTX_00

)    do    (

rem if not confident, do a dry run first
rem aws s3 sync --dryrun s3://travel-model-runs/%%modelrun %%modelrun
rem execute
rem -------------------------------------------
aws s3 sync s3://travel-model-runs/%%f %%f

rem copy extract key files
rem -------------------------------------------
set run_id=%%f
echo %run_id%

rem somehow timeout is needed to make sure the variable run_id is registered
timeout 5

set proj_id=%run_id:~21,-3%
echo %proj_id%

mkdir "..\Projects\%proj_id%\%run_id%\OUTPUT"
c:\windows\system32\Robocopy.exe /E %%f\extractor ..\Projects\%proj_id%\%run_id%\OUTPUT

)

:: s3 is here: https://s3.console.aws.amazon.com/s3/buckets/travel-model-runs/

:: the command to sync:
:: aws s3 sync --dryrun [from directory] [to directory]
:: aws s3 sync --dryrun [aws directory] [local directory]

:: run from L:\RTP2021_PPA\Projects_onAWS
for /d %%f in (

2050_TM151_PPA_CG_09
2050_TM151_PPA_BF_09

)    do    (

rem if not confident, do a dry run first
rem aws s3 sync --dryrun s3://travel-model-runs/%%modelrun %%modelrun
rem execute
aws s3 sync s3://travel-model-runs/%%f %%f

)

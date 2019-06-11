
:: s3 is here: https://s3.console.aws.amazon.com/s3/buckets/travel-model-runs/

:: the command to sync:
:: aws s3 sync --dryrun [from directory] [to directory]
:: aws s3 sync --dryrun [aws directory] [local directory]

:: run from L:\RTP2021_PPA\Projects_onAWS
for /d %%f in (

2050_TM151_PPA_RT_05_2101_Geary_BRT_Phase2_00
2050_TM151_PPA_RT_05_2102_ElCaminoReal_BRT_00
2050_TM151_PPA_RT_05_2205_BARTtoSV_Phase2_00
2050_TM151_PPA_RT_05_2402_SJC_People_Mover_00
2050_TM151_PPA_RT_05_2403_Vasona_LRT_Phase2_00

)    do    (

rem if not confident, do a dry run first
rem aws s3 sync --dryrun s3://travel-model-runs/%%modelrun %%modelrun
rem execute
aws s3 sync s3://travel-model-runs/%%f %%f

)


:: s3 is here: https://s3.console.aws.amazon.com/s3/buckets/travel-model-runs/

:: the command to sync:
:: aws s3 sync --dryrun [from directory] [to directory]
:: aws s3 sync --dryrun [aws directory] [local directory]
:: or copy s3 object to a local file
:: aws s3 cp s3://mybucket/test.txt test2.txt

:: run from \\mainmodel\MainModelShare\extract_for_emfac
for /d %%f in (

2050_TM151_FU1_BF_00
2050_TM151_FU1_CG_00
2050_TM151_FU1_RT_00


)    do    (

rem if not confident, do a dry run first
rem aws s3 sync --dryrun s3://travel-model-runs/%%modelrun %%modelrun
rem execute

rem from "\hwy\" directory
aws s3 cp s3://travel-model-runs/%%f/hwy/iter3/avgload5period.net %%f/hwy/iter3/avgload5period.net

rem from "\main\" directory
aws s3 cp s3://travel-model-runs/%%f/main/tripsEA.tpp %%f/main/tripsEA.tpp
aws s3 cp s3://travel-model-runs/%%f/main/tripsAM.tpp %%f/main/tripsAM.tpp
aws s3 cp s3://travel-model-runs/%%f/main/tripsMD.tpp %%f/main/tripsMD.tpp
aws s3 cp s3://travel-model-runs/%%f/main/tripsPM.tpp %%f/main/tripsPM.tpp
aws s3 cp s3://travel-model-runs/%%f/main/tripsEV.tpp %%f/main/tripsEV.tpp

rem from "\nonres\" directory
aws s3 cp s3://travel-model-runs/%%f/nonres/tripstrkEA.tpp %%f/nonres/tripstrkEA.tpp
aws s3 cp s3://travel-model-runs/%%f/nonres/tripstrkAM.tpp %%f/nonres/tripstrkAM.tpp
aws s3 cp s3://travel-model-runs/%%f/nonres/tripstrkMD.tpp %%f/nonres/tripstrkMD.tpp
aws s3 cp s3://travel-model-runs/%%f/nonres/tripstrkPM.tpp %%f/nonres/tripstrkPM.tpp
aws s3 cp s3://travel-model-runs/%%f/nonres/tripstrkEV.tpp %%f/nonres/tripstrkEV.tpp

rem from "\skims\" directory
aws s3 cp s3://travel-model-runs/%%f/skims/COM_HWYSKIMEA.tpp %%f/skims/COM_HWYSKIMEA.tpp
aws s3 cp s3://travel-model-runs/%%f/skims/COM_HWYSKIMAM.tpp %%f/skims/COM_HWYSKIMAM.tpp
aws s3 cp s3://travel-model-runs/%%f/skims/COM_HWYSKIMMD.tpp %%f/skims/COM_HWYSKIMMD.tpp
aws s3 cp s3://travel-model-runs/%%f/skims/COM_HWYSKIMPM.tpp %%f/skims/COM_HWYSKIMPM.tpp
aws s3 cp s3://travel-model-runs/%%f/skims/COM_HWYSKIMEV.tpp %%f/skims/COM_HWYSKIMEV.tpp

aws s3 cp s3://travel-model-runs/%%f/skims/HWYSKMEA.tpp %%f/skims/HWYSKMEA.tpp
aws s3 cp s3://travel-model-runs/%%f/skims/HWYSKMAM.tpp %%f/skims/HWYSKMAM.tpp
aws s3 cp s3://travel-model-runs/%%f/skims/HWYSKMMD.tpp %%f/skims/HWYSKMMD.tpp
aws s3 cp s3://travel-model-runs/%%f/skims/HWYSKMPM.tpp %%f/skims/HWYSKMPM.tpp
aws s3 cp s3://travel-model-runs/%%f/skims/HWYSKMEV.tpp %%f/skims/HWYSKMEV.tpp

)

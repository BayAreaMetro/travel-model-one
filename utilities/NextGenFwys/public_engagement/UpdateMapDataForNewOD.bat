:: update paths based on mapped drives on respective modeling server

set ORIGIN_LIST=1,2,3,4,5
set DESTINATION_LIST=10,20,30,40,50

@echo off

:: saved on \\model3-a\Model3A-Share
X:
cd X:\Projects\2035_TM152_NGF_NP10_Path1a_02
Set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
call X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TraceDApaths.bat %ORIGIN_LIST% %DESTINATION_LIST%

:: saved on \\model3-a\Model3A-Share
X:
cd X:\Projects\2035_TM152_NGF_NP10_Path1a_02
Set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
call X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TraceTransitPaths.bat 

::saved on \\MODEL2-C\Model2C-Share
Z:
cd Z:\Projects\2035_TM152_NGF_NP10_Path4_02
Set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
call X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TraceTransitPaths.bat 

:: saved on \\MODEL2-D\Model2D-Share
F:
cd F:\Projects\2035_TM152_NGF_NP10
Set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
call X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TraceTransitPaths.bat 

pause
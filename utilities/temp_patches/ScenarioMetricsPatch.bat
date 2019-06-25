REM see info about setting variables inside a loop here: https://stackoverflow.com/questions/13805187/how-to-set-a-variable-inside-a-loop-for-f
REM run only scenarioMetrics.py
REM --------------------------------------

REM before running the script
set PATH=%PATH%;C:\Python27;C:\Python27\Scripts
set ITER=3
set SAMPLESHARE=0.50


setlocal enabledelayedexpansion
REM see info about "setlocal enabledelayedexpansion" and setting variables inside a loop here: 
REM https://stackoverflow.com/questions/13805187/how-to-set-a-variable-inside-a-loop-for-f


REM run from L:\RTP2021_PPA\Projects_onAWS
for /d %%f in (

		2050_TM151_PPA_RT_07_1_Crossings1_00
		2050_TM151_PPA_RT_07_1_Crossings2_00
		2050_TM151_PPA_RT_07_1_Crossings3_01
		2050_TM151_PPA_RT_07_1_Crossings4_01
		2050_TM151_PPA_RT_07_1_Crossings4_05
		2050_TM151_PPA_RT_07_1_Crossings5_00
		2050_TM151_PPA_RT_07_1_Crossings6_00
		2050_TM151_PPA_RT_07_1_Crossings7_01
		2050_TM151_PPA_CG_07_1_Crossings1_01
		2050_TM151_PPA_CG_07_1_Crossings2_00
		2050_TM151_PPA_CG_07_1_Crossings3_00
		2050_TM151_PPA_CG_07_1_Crossings4_00
		2050_TM151_PPA_CG_07_1_Crossings4_06
		2050_TM151_PPA_CG_07_1_Crossings5_00
		2050_TM151_PPA_CG_07_1_Crossings6_00
		2050_TM151_PPA_CG_07_1_Crossings7_00
		2050_TM151_PPA_BF_07_1_Crossings1_01
		2050_TM151_PPA_BF_07_1_Crossings2_00
		2050_TM151_PPA_BF_07_1_Crossings3_00
		2050_TM151_PPA_BF_07_1_Crossings4_00
		2050_TM151_PPA_BF_07_1_Crossings4_06
		2050_TM151_PPA_BF_07_1_Crossings5_00
		2050_TM151_PPA_BF_07_1_Crossings6_00
		2050_TM151_PPA_BF_07_1_Crossings7_00
		2050_TM151_PPA_RT_07_2303_Caltrain_16tph_00
		2050_TM151_PPA_CG_07_2303_Caltrain_16tph_00
		2050_TM151_PPA_BF_07_2303_Caltrain_16tph_00
		2050_TM151_PPA_RT_07_2201_BART_CoreCap_00
		2050_TM151_PPA_CG_07_2201_BART_CoreCap_00
		2050_TM151_PPA_BF_07_2201_BART_CoreCap_00
		2050_TM151_PPA_RT_07_2306_Dumbarton_Rail_01
		2050_TM151_PPA_CG_07_2306_Dumbarton_Rail_00
		2050_TM151_PPA_BF_07_2306_Dumbarton_Rail_00
		2050_TM151_PPA_RT_07_2308_Valley_Link_00

)    do    (

REM run the script
cd %%f
copy INPUT\metrics\CommunitiesOfConcern.csv metrics
python \\mainmodel\MainModelShare\travel-model-one-1.5.1.2\utilities\PBA40\metrics\scenarioMetrics.py
cd ..

REM copy the output to the right place
set run_id=%%f
echo %run_id%
echo !run_id!

set proj_id=!run_id:~21,-3!
echo %proj_id%
echo !proj_id!

copy %%f\metrics\scenario_metrics.csv %%f\extractor\metrics\scenario_metrics.csv 
copy %%f\extractor\metrics\scenario_metrics.csv ..\Projects\!proj_id!\!run_id!\OUTPUT\metrics\scenario_metrics.csv


)


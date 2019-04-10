set COBRA_DIR=%CD%
::python "%COBRA_DIR%\TransitCrowding.py" "2030_TM125_PPA_RT_00" 

REM NO-PROJECT BASELINES

REM transit crowding
::python "TransitCrowding.py" "2030_TM125_PPA_RT_00" 
::python "TransitCrowding.py" "2030_TM125_PPA_CG_00" 
::python "TransitCrowding.py" "2030_TM125_PPA_BF_00" 
::python "TransitCrowding.py" "2050_TM150_PPA_RT_00" 
::python "TransitCrowding.py" "2050_TM150_PPA_CG_00" 
::python "TransitCrowding.py" "2050_TM150_PPA_BF_00" 
::python "TransitCrowding.py" "2050_TM151_PPA_RT_00" 
::python "TransitCrowding.py" "2050_TM151_PPA_CG_00" 
::python "TransitCrowding.py" "2050_TM151_PPA_BF_00" 
python "TransitCrowding.py" "2050_TM151_PPA_RT_01" 
::python "TransitCrowding.py" "2050_TM151_PPA_CG_01" 
::python "TransitCrowding.py" "2050_TM151_PPA_BF_01" 

REM run results
::python "RunResults.py" "2030_TM125_PPA_RT_00" all_projects_metrics
::python "RunResults.py" "2030_TM125_PPA_CG_00" all_projects_metrics
::python "RunResults.py" "2030_TM125_PPA_BF_00" all_projects_metrics
::python "RunResults.py" "2050_TM150_PPA_RT_00" all_projects_metrics
::python "RunResults.py" "2050_TM150_PPA_CG_00" all_projects_metrics
::python "RunResults.py" "2050_TM150_PPA_BF_00" all_projects_metrics
::python "RunResults.py" "2050_TM151_PPA_RT_00" all_projects_metrics
::python "RunResults.py" "2050_TM151_PPA_CG_00" all_projects_metrics
::python "RunResults.py" "2050_TM151_PPA_BF_00" all_projects_metrics
python "RunResults.py" "2050_TM151_PPA_RT_01" all_projects_metrics
::python "RunResults.py" "2050_TM151_PPA_CG_01" all_projects_metrics
::python "RunResults.py" "2050_TM151_PPA_BF_01" all_projects_metrics

::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

REM PROJECTS
REM mkdir all_projects_metrics


REM Transit Crowding with baseline 00

::python "TransitCrowding.py" "1_Crossings5\2050_TM150_PPA_RT_00_1_Crossings5" 
::python "TransitCrowding.py" "1_Crossings5\2050_TM150_PPA_CG_00_1_Crossings5" 
::python "TransitCrowding.py" "1_Crossings5\2050_TM150_PPA_BF_00_1_Crossings5" 

::python "TransitCrowding.py" "1_Crossings1\2050_TM151_PPA_RT_00_1_Crossings1" 
::python "TransitCrowding.py" "1_Crossings1\2050_TM151_PPA_CG_00_1_Crossings1" 
::python "TransitCrowding.py" "1_Crossings1\2050_TM151_PPA_BF_00_1_Crossings1" 

::python "TransitCrowding.py" "1_Crossings2\2050_TM151_PPA_RT_00_1_Crossings2" 
::python "TransitCrowding.py" "1_Crossings2\2050_TM151_PPA_CG_00_1_Crossings2_00" 
::python "TransitCrowding.py" "1_Crossings2\2050_TM151_PPA_BF_00_1_Crossings2" 

::python "TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_RT_00_1_Crossings3_01" 
::python "TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_CG_00_1_Crossings3_01" 
::python "TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_BF_00_1_Crossings3_01" 

::python "TransitCrowding.py" "1_Crossings4\2050_TM151_PPA_RT_00_1_Crossings4" 
::python "TransitCrowding.py" "1_Crossings4\2050_TM151_PPA_CG_00_1_Crossings4_00" 
::python "TransitCrowding.py" "1_Crossings4\2050_TM151_PPA_BF_00_1_Crossings4" 

::python "TransitCrowding.py" "1_Crossings5\2050_TM151_PPA_RT_00_1_Crossings5_00" 
::python "TransitCrowding.py" "1_Crossings5\2050_TM151_PPA_CG_00_1_Crossings5_00" 
::python "TransitCrowding.py" "1_Crossings5\2050_TM151_PPA_BF_00_1_Crossings5_00" 

::python "TransitCrowding.py" "1_Crossings6\2050_TM151_PPA_RT_00_1_Crossings6" 
::python "TransitCrowding.py" "1_Crossings6\2050_TM151_PPA_CG_00_1_Crossings6" 
::python "TransitCrowding.py" "1_Crossings6\2050_TM151_PPA_BF_00_1_Crossings6_00" 

::python "TransitCrowding.py" "1_Crossings7\2050_TM151_PPA_BF_00_1_Crossings7" 
::python "TransitCrowding.py" "1_Crossings7\2050_TM151_PPA_RT_00_1_Crossings7" 
::python "TransitCrowding.py" "1_Crossings7\2050_TM151_PPA_CG_00_1_Crossings7" 

REM Transit Crowding with baseline 01
::////////python "TransitCrowding.py" "1_Crossings2\2050_TM151_PPA_CG_01_1_Crossings2_00" 
::python "TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_CG_01_1_Crossings3_00" 
::python "TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_BF_01_1_Crossings3_00" 

::python "TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_CG_01_1_Crossings3_01" 
::python "TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_RT_01_1_Crossings3_00" 



::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


REM run results baseline 00
::python "RunResults.py" "1_Crossings5\2050_TM150_PPA_RT_00_1_Crossings5" all_projects_metrics
::python "RunResults.py" "1_Crossings5\2050_TM150_PPA_CG_00_1_Crossings5" all_projects_metrics
::python "RunResults.py" "1_Crossings5\2050_TM150_PPA_BF_00_1_Crossings5" all_projects_metrics

::python "RunResults.py" "1_Crossings1\2050_TM151_PPA_RT_00_1_Crossings1" all_projects_metrics
::python "RunResults.py" "1_Crossings1\2050_TM151_PPA_CG_00_1_Crossings1" all_projects_metrics
::python "RunResults.py" "1_Crossings1\2050_TM151_PPA_BF_00_1_Crossings1" all_projects_metrics

::python "RunResults.py" "1_Crossings2\2050_TM151_PPA_RT_00_1_Crossings2" all_projects_metrics
::python "RunResults.py" "1_Crossings2\2050_TM151_PPA_CG_00_1_Crossings2_00" all_projects_metrics
::python "RunResults.py" "1_Crossings2\2050_TM151_PPA_BF_00_1_Crossings2" all_projects_metrics

::python "RunResults.py" "1_Crossings3\2050_TM151_PPA_RT_00_1_Crossings3_01" all_projects_metrics
::python "RunResults.py" "1_Crossings3\2050_TM151_PPA_CG_00_1_Crossings3_01" all_projects_metrics
::python "RunResults.py" "1_Crossings3\2050_TM151_PPA_BF_00_1_Crossings3_01" all_projects_metrics

::python "RunResults.py" "1_Crossings4\2050_TM151_PPA_RT_00_1_Crossings4" all_projects_metrics
::python "RunResults.py" "1_Crossings4\2050_TM151_PPA_CG_00_1_Crossings4_00" all_projects_metrics
::python "RunResults.py" "1_Crossings4\2050_TM151_PPA_BF_00_1_Crossings4" all_projects_metrics

::python "RunResults.py" "1_Crossings5\2050_TM151_PPA_RT_00_1_Crossings5_00" all_projects_metrics
::python "RunResults.py" "1_Crossings5\2050_TM151_PPA_CG_00_1_Crossings5_00" all_projects_metrics
::python "RunResults.py" "1_Crossings5\2050_TM151_PPA_BF_00_1_Crossings5_00" all_projects_metrics

::python "RunResults.py" "1_Crossings6\2050_TM151_PPA_RT_00_1_Crossings6" all_projects_metrics
::python "RunResults.py" "1_Crossings6\2050_TM151_PPA_CG_00_1_Crossings6" all_projects_metrics
::python "RunResults.py" "1_Crossings6\2050_TM151_PPA_BF_00_1_Crossings6_00" all_projects_metrics

::python "RunResults.py" "1_Crossings7\2050_TM151_PPA_BF_00_1_Crossings7" all_projects_metrics
::python "RunResults.py" "1_Crossings7\2050_TM151_PPA_RT_00_1_Crossings7" all_projects_metrics
::python "RunResults.py" "1_Crossings7\2050_TM151_PPA_CG_00_1_Crossings7" all_projects_metrics

REM run results with baseline 01
::////////python "RunResults.py" "1_Crossings2\2050_TM151_PPA_CG_01_1_Crossings2_00" all_projects_metrics
::python "RunResults.py" "1_Crossings3\2050_TM151_PPA_CG_01_1_Crossings3_00" all_projects_metrics
::python "RunResults.py" "1_Crossings3\2050_TM151_PPA_BF_01_1_Crossings3_00" all_projects_metrics

::python "RunResults.py" "1_Crossings3\2050_TM151_PPA_CG_01_1_Crossings3_01" all_projects_metrics
python "RunResults.py" "1_Crossings3\2050_TM151_PPA_RT_01_1_Crossings3_00" all_projects_metrics


REM rollup
cd all_projects_metrics
python "rollupAllProjects.py"
cd ..

pause

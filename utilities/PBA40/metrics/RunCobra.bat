set COBRA_DIR=%CD%

REM NO-PROJECT BASELINES

REM transit crowding
::python "%COBRA_DIR%\TransitCrowding.py" "2030_TM125_PPA_RT_00" 
::python "%COBRA_DIR%\TransitCrowding.py" "2030_TM125_PPA_CG_00" 
::python "%COBRA_DIR%\TransitCrowding.py" "2030_TM125_PPA_BF_00" 
::python "%COBRA_DIR%\TransitCrowding.py" "2050_TM150_PPA_RT_00" 
::python "%COBRA_DIR%\TransitCrowding.py" "2050_TM150_PPA_CG_00" 
::python "%COBRA_DIR%\TransitCrowding.py" "2050_TM150_PPA_BF_00" 
::python "%COBRA_DIR%\TransitCrowding.py" "2050_TM151_PPA_RT_00" 
::python "%COBRA_DIR%\TransitCrowding.py" "2050_TM151_PPA_CG_00" 
::python "%COBRA_DIR%\TransitCrowding.py" "2050_TM151_PPA_BF_00" 

REM run results
::python "%COBRA_DIR%\RunResults.py" "2030_TM125_PPA_RT_00" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "2030_TM125_PPA_CG_00" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "2030_TM125_PPA_BF_00" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "2050_TM150_PPA_RT_00" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "2050_TM150_PPA_CG_00" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "2050_TM150_PPA_BF_00" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "2050_TM151_PPA_RT_00" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "2050_TM151_PPA_CG_00" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "2050_TM151_PPA_BF_00" all_projects_metrics


::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

REM PROJECTS
REM mkdir all_projects_metrics

REM transit crowding
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings5\2050_TM150_PPA_RT_00_1_Crossings5" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings5\2050_TM150_PPA_CG_00_1_Crossings5" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings5\2050_TM150_PPA_BF_00_1_Crossings5" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings1\2050_TM151_PPA_RT_00_1_Crossings1" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings1\2050_TM151_PPA_CG_00_1_Crossings1" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings1\2050_TM151_PPA_BF_00_1_Crossings1" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings2\2050_TM151_PPA_RT_00_1_Crossings2" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings2\2050_TM151_PPA_CG_00_1_Crossings2" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings2\2050_TM151_PPA_BF_00_1_Crossings2" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_RT_00_1_Crossings3" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_CG_00_1_Crossings3" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings3\2050_TM151_PPA_BF_00_1_Crossings3" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings4\2050_TM151_PPA_RT_00_1_Crossings4" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings4\2050_TM151_PPA_CG_00_1_Crossings4" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings4\2050_TM151_PPA_BF_00_1_Crossings4" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings5\2050_TM151_PPA_RT_00_1_Crossings5" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings5\2050_TM151_PPA_CG_00_1_Crossings5" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings5\2050_TM151_PPA_BF_00_1_Crossings5" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings6\2050_TM151_PPA_RT_00_1_Crossings6" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings6\2050_TM151_PPA_CG_00_1_Crossings6" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings6\2050_TM151_PPA_BF_00_1_Crossings6" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings7\2050_TM151_PPA_RT_00_1_Crossings7" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings7\2050_TM151_PPA_CG_00_1_Crossings7" 
::python "%COBRA_DIR%\TransitCrowding.py" "1_Crossings7\2050_TM151_PPA_BF_00_1_Crossings7" 

REM run results
::python "%COBRA_DIR%\RunResults.py" "1_Crossings5\2050_TM150_PPA_RT_00_1_Crossings5" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings5\2050_TM150_PPA_CG_00_1_Crossings5" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings5\2050_TM150_PPA_BF_00_1_Crossings5" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings1\2050_TM151_PPA_RT_00_1_Crossings1" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings1\2050_TM151_PPA_CG_00_1_Crossings1" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings1\2050_TM151_PPA_BF_00_1_Crossings1" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings2\2050_TM151_PPA_RT_00_1_Crossings2" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings2\2050_TM151_PPA_CG_00_1_Crossings2" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings2\2050_TM151_PPA_BF_00_1_Crossings2" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings3\2050_TM151_PPA_RT_00_1_Crossings3" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings3\2050_TM151_PPA_CG_00_1_Crossings3" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings3\2050_TM151_PPA_BF_00_1_Crossings3" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings4\2050_TM151_PPA_RT_00_1_Crossings4" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings4\2050_TM151_PPA_CG_00_1_Crossings4" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings4\2050_TM151_PPA_BF_00_1_Crossings4" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings5\2050_TM151_PPA_RT_00_1_Crossings5" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings5\2050_TM151_PPA_CG_00_1_Crossings5" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings5\2050_TM151_PPA_BF_00_1_Crossings5" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings6\2050_TM151_PPA_RT_00_1_Crossings6" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings6\2050_TM151_PPA_CG_00_1_Crossings6" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings6\2050_TM151_PPA_BF_00_1_Crossings6" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings7\2050_TM151_PPA_BF_00_1_Crossings7" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings7\2050_TM151_PPA_RT_00_1_Crossings7" all_projects_metrics
::python "%COBRA_DIR%\RunResults.py" "1_Crossings7\2050_TM151_PPA_CG_00_1_Crossings7" all_projects_metrics

REM rollup
cd all_projects_metrics
python "rollupAllProjects.py"
cd ..

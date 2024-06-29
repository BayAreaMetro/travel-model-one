::
:: This batch script runs the metric scripts needed to update the metrics tableau for the NextGenFwys study.
:: run this from L:\Application\Model_One\NextGenFwys_Round2\Metrics
:: optional environment variable SKIP, default set to True
:: example usage:
:: set SKIP=n
:: "X:\travel-model-one-master\utilities\NextGenFwys\metrics\Metrics_Round2\run_NGF_Tableau_scripts.bat"
::

:: Stamp the feedback report with the date and time
echo STARTED NGFS METRICS  %DATE% %TIME%

IF defined SKIP (echo Using SKIP=%SKIP%)

:: Location of the metrics scripts
set CODE_DIR=X:\travel-model-one-master\utilities\NextGenFwys\metrics\Metrics_Round2

rem run post_run_model_steps.py
call python "%CODE_DIR%\post_run_model_steps.py"

:: Location of the model files
set TARGET_DIR=%CD%

rem Check if the variable SKIP equals "n"
IF "%SKIP%"=="n" (
  echo not skipping
  call python "%CODE_DIR%\Affordable1_transportation_costs.py"
  call python "%CODE_DIR%\Affordable2_ratio_time_cost.py"
  call python "%CODE_DIR%\Safe2_vmt_from_auto_times.py"
  call python "%CODE_DIR%\Safe2_vmt_from_loaded_network.py"
  call python "%CODE_DIR%\Efficient1_ratio_travel_time.py"
  call python "%CODE_DIR%\Efficient2_commute_tours_mode_share.py"
  call python "%CODE_DIR%\Efficient2b_non_commute_trips_mode_share.py"
  call python "%CODE_DIR%\Reliable1_change_travel_time.py"
  call python "%CODE_DIR%\Reliable2_ratio_peak_nonpeak.py"
  call python "%CODE_DIR%\Top_level_metrics_toll_revenues.py"
  call python "%CODE_DIR%\Safe1_run_fatalities_Rscript.py"

) else (
  echo skipping if files exist
  call python "%CODE_DIR%\Affordable1_transportation_costs.py" --skip_if_exists
  call python "%CODE_DIR%\Affordable2_ratio_time_cost.py" --skip_if_exists
  call python "%CODE_DIR%\Safe2_vmt_from_auto_times.py" --skip_if_exists
  call python "%CODE_DIR%\Safe2_vmt_from_loaded_network.py" --skip_if_exists
  call python "%CODE_DIR%\Efficient1_ratio_travel_time.py" --skip_if_exists
  call python "%CODE_DIR%\Efficient2_commute_tours_mode_share.py" --skip_if_exists
  call python "%CODE_DIR%\Efficient2b_non_commute_trips_mode_share.py" --skip_if_exists
  call python "%CODE_DIR%\Reliable1_change_travel_time.py" --skip_if_exists
  call python "%CODE_DIR%\Reliable2_ratio_peak_nonpeak.py" --skip_if_exists
  call python "%CODE_DIR%\Top_level_metrics_toll_revenues.py" --skip_if_exists
  call python "%CODE_DIR%\Safe1_run_fatalities_Rscript.py" --skip_if_exists
)

rem Update Round 2 across_runs_union folder
cd L:\Application\Model_One\NextGenFwys_Round2\across_runs_union
call python "X:\travel-model-one-master\utilities\CoreSummaries\copyFilesAcrossScenarios.py" X:\travel-model-one-master\utilities\NextGenFwys\ModelRuns_Round2.xlsx --dest_dir . --status_to_copy current --delete_other_run_files n

rem run ngfs_corridor_map_data.py
call python "X:\travel-model-one-master\utilities\NextGenFwys\metrics\Additional Scripts\ngfs_corridor_map_data.py"

:success
echo FINISHED run_NGF_Tableau_scripts successfully!
echo ENDED NGFS METRICS  %DATE% %TIME%

:error
echo ERRORLEVEL=%ERRORLEVEL%

rem Keep the command prompt window open for review in case of errors
pause
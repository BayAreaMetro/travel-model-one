@echo on
Setlocal EnableDelayedExpansion
:: run this for all the relevant directories
::
set JOBFILE=X:\travel-model-one-master\utilities\bespoke-requests\vmt-passengervehicle-ii-ixxi-xx\vmt-passengervehicle-ii-ixxi-xx.job
set DESTDIR=M:\Application\Model One\RTP2025\Blueprint\across_runs_CARB

call:run_job "F:\Projects\2005_TM161_IPA_01"

call:run_job "B:\Projects\2023_TM161_IPA_35"

call:run_job "B:\Projects\2035_TM161_FBP_Plan_16"

call:run_job "I:\Projects\2050_TM161_FBP_Plan_16"

EXIT /B %ERRORLEVEL%

:run_job
set RUNDIR=%*
echo Running job in !RUNDIR!
set filedrive=%~d1
set filepath=%~n1

echo filedrive=[!filedrive!]
echo filepath=[!filepath!]
rem switch to the drive
!filedrive!
cd !RUNDIR!

rem run the script
runtpp %JOBFILE%

rem copy the result
copy "metrics\II_IXXI_XX.csv" "%DESTDIR%\II_XXXI_XX_!filepath!.csv"

C:
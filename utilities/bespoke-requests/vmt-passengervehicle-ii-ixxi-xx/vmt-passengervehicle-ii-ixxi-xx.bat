@echo on
Setlocal EnableDelayedExpansion
:: run this for all the relevant directories
::
set JOBFILE=C:\Users\lzorn\Documents\travel-model-one-v05\utilities\bespoke-requests\vmt-passengervehicle-ii-ixxi-xx\vmt-passengervehicle-ii-ixxi-xx.job
set DESTDIR=M:\Application\Model One\RTP2017\Scenarios\Across-Scenarios-ARB

call:run_job "B:\Projects\2005_05_003.archived (do not delete)"
call:run_job "D:\Projects\2010_06_003"

call:run_job "D:\Projects\2020_06_690"
call:run_job "I:\Projects\2020_06_694"

call:run_job "D:\Projects\2035_06_690"
call:run_job "E:\Projects\2035_06_694"

call:run_job "A:\Projects\2040_06_690"
call:run_job "D:\Projects\2040_06_694"

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
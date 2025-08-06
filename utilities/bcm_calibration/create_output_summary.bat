echo STARTED CREATING OUTPUT SUMMARIES %DATE% %TIME% >> logs\feedback.rpt

::set CONDAPATH=C:\Users\USKK709532\Anaconda3
set CONDAPATH="C:\Users\USJH706661\Anaconda3"
echo CONDAPATH set to [!CONDAPATH!]

:: Call the PopulationSim environment. Typically PopulationSim should be installed in the same environment as ActivitySim

call %CONDAPATH%\Scripts\activate.bat

set CODE_DIR=D:\Projects\2015_BaseY_BCM2015\Calibration Scripts

set RUN=%1
::goto tlfd
::set run_name = "main_Run_20"
mkdir main_Run_%RUN%

copy main\*.csv       main_Run_%RUN%\
copy CTRAMP\model\DestinationChoice.xls			       main_Run_%RUN%\DestinationChoice_Run_%RUN%.xls	
: start
%CONDAPATH%\python.exe "%CODE_DIR%"\01-create_work_location_summary.py --run_name main_Run_%RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\01_create_work_location_comparison.py --run_number %RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\02-create_auto_ownership_summary.py --run_name main_Run_%RUN%
%CONDAPATH%\python.exe "%CODE_DIR%"\02_create_autoOwnership_comparison.py --run_number %RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\03-create_cdap_summary.py --run_name main_Run_%RUN%
%CONDAPATH%\python.exe "%CODE_DIR%"\03-create_cdap_comparison.py --run_number %RUN% 

%CONDAPATH%\python.exe "%CODE_DIR%"\04-create_mandatory_tour_freq_summary.py --run_name main_Run_%RUN%
%CONDAPATH%\python.exe "%CODE_DIR%"\04-create_mandatory_tour_freq_comparison.py --run_number %RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\05-create_nonmandatory_tour_freq_summary.py --run_name main_Run_%RUN%
%CONDAPATH%\python.exe "%CODE_DIR%"\05-create_nonmandatory_tour_freq_comparison.py --run_number %RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\06_create_TourTODSummary.py --run_name main_Run_%RUN%
%CONDAPATH%\python.exe "%CODE_DIR%"\06_create_TourTODSummary_comparison.py --run_number %RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\07-create_tourModeChoiceSummary.py --run_name main_Run_%RUN%
%CONDAPATH%\python.exe "%CODE_DIR%"\07-create_tourModeChoiceSummary_comparison.py --run_number %RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\08-tour_length_frequency_distribution.py --run_name main_Run_%RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\08-tour_length_frequency_distribution_comparison.py --run_number %RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\10_schoolLocationTLFD.py --run_name main_Run_%RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\091_assignedTripsByTourMode_Summary.py --run_name main_Run_%RUN%



%CONDAPATH%\python.exe "%CODE_DIR%"\10-trip_mode_choice_summary.py --run_name main_Run_%RUN%

%CONDAPATH%\python.exe "%CODE_DIR%"\11-create_vmt_estimates.py --run_name main_Run_%RUN% --sample_share 10

: tlfd
%CONDAPATH%\python.exe "%CODE_DIR%"\12_assignabletripsAndVMT.py --run_name main_Run_%RUN%
::%CONDAPATH%\python.exe "%CODE_DIR%"\11-create_vmt_estimates.py --run_name main_Run_55 --sample_share 10
::%CONDAPATH%\python.exe "%CODE_DIR%"\11-create_vmt_estimates.py --run_name main_Run_47 --sample_share 5

::%CONDAPATH%\python.exe "%CODE_DIR%"\11-create_vmt_estimates.py --run_name main_Run_TM15 --sample_share 15

:done
echo done
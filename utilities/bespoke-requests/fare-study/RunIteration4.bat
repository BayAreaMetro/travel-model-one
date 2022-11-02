::
:: Iteration 4 run for Fare Coordination/Integration Study (FCIS)
:: See https://github.com/alexmitrani/travel-model-one


:: Figure out SCENARIO - this is the folder name
set MODEL_DIR=%CD%
:: get the base dir only
for %%f in (%CD%) do set SCENARIO=%%~nxf
echo SCENARIO=[%SCENARIO%]
title %SCENARIO%

:: ------------------------------------------------------------------------------------------------------
:: Copy model source
:: ------------------------------------------------------------------------------------------------------
set GITHUB_DIR=\\tsclient\X\travel-model-one-master
:: copy over CTRAMP
mkdir CTRAMP\model
mkdir CTRAMP\runtime
mkdir CTRAMP\scripts
mkdir CTRAMP\scripts\metrics
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\model"                   CTRAMP\model
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\runtime"                 CTRAMP\runtime
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\scripts"                 CTRAMP\scripts
copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\extract_trnskim_tables.job"        CTRAMP\scripts\database\extract_trnskim_tables.job
copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\combine_indiv_joint_tours_trips.R" CTRAMP\scripts\core_summaries
copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\join_trips_with_skims.R"           CTRAMP\scripts\core_summaries
copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\summarize_trips_by_mode.R"         CTRAMP\scripts\core_summaries

set ADDFARE=0

IF "%SCENARIO%" == "2015_FCIS_Base" (
   copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims.job"               CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_RegLoc25Discount" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_Regional_Local2.5_Discount.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_max12at74mi" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_max1220at74mi" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_max1220at74mi_plus12c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance.job"  CTRAMP\scripts\skims\TransitSkims.job
  set ADDFARE=12
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_max12at74mi" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance_flatLocal.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_max1220at74mi" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance_flatLocal.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_max1220at74mi_plus16c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance_flatLocal.job"  CTRAMP\scripts\skims\TransitSkims.job
  set ADDFARE=16
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_max1220at74mi_plus23c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance_flatLocal.job"  CTRAMP\scripts\skims\TransitSkims.job
  set ADDFARE=23
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_20pctIncrease" (
  rem same skim but different lookup table
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_5pctIncrease" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance_flatLocal_5pctIncrease.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_20pctIncrease" (
  rem flat local skim but different lookup table
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByDistance_flatLocal.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByZone_Seamless" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByZone_Seamless.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByZone_Seamless_plus10pct" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByZone_Seamless_plus10pct.job"  CTRAMP\scripts\skims\TransitSkims.job
)
IF "%SCENARIO%" == "2015_FCIS_FareByZone_LargeRegional_LocalFlatFare_plus28c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByZone_LargeRegionalZone_flatLocal.job"  CTRAMP\scripts\skims\TransitSkims.job
  set ADDFARE=28
)
IF "%SCENARIO%" == "2015_FCIS_FareByZone_LargeRegional_LocalFlatFare_plus62c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_FareByZone_LargeRegionalZone_flatLocal.job"  CTRAMP\scripts\skims\TransitSkims.job
  set ADDFARE=62
)
IF "%SCENARIO%" == "2015_FCIS_RegRegDiscount" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\TransitSkims_RegRegDiscount.job"  CTRAMP\scripts\skims\TransitSkims.job
)

:: Set the Baseline (complete three iteration run) that we're pivoting from
set BASELINE_FULL_RUN=\\MODEL2-B\Model2B-Share\Projects\2015_TM152_IPA_17
SET MODEL_YEAR=2015

:: ------------------------------------------------------------------------------------------------------
:: copy required input files
:: ------------------------------------------------------------------------------------------------------
mkdir INPUT
c:\windows\system32\Robocopy.exe /E "%BASELINE_FULL_RUN%\INPUT\landuse"        INPUT\landuse
c:\windows\system32\Robocopy.exe /E "%BASELINE_FULL_RUN%\INPUT\nonres"         INPUT\nonres
c:\windows\system32\Robocopy.exe /E "%BASELINE_FULL_RUN%\INPUT\popsyn"         INPUT\popsyn
c:\windows\system32\Robocopy.exe /E "%BASELINE_FULL_RUN%\INPUT\warmstart"      INPUT\warmstart
c:\windows\system32\Robocopy.exe /E "%BASELINE_FULL_RUN%\INPUT\hwy"            INPUT\hwy
c:\windows\system32\Robocopy.exe /E "%BASELINE_FULL_RUN%\INPUT\trn"            INPUT\trn
copy /Y "%BASELINE_FULL_RUN%\INPUT\params.properties"                          INPUT\params.properties

IF "%SCENARIO%" == "2015_FCIS_FareByDistance" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup.csv"  INPUT\trn
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_max12at74mi" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_max12usd_at_74mi.csv"  INPUT\trn\\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_max1220at74mi" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_max1220c_at_74mi.csv"  INPUT\trn\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_max1220at74mi_plus12c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_max1220c_at_74mi.csv"  INPUT\trn\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_max12at74mi" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_max12usd_at_74mi.csv"  INPUT\trn\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_max1220at74mi" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_max1220c_at_74mi.csv"  INPUT\trn\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_max1220at74mi_plus16c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_max1220c_at_74mi.csv"  INPUT\trn\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_max1220at74mi_plus23c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_max1220c_at_74mi.csv"  INPUT\trn\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_20pctIncrease" (
  rem same skim but different lookup table
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_plus20pct.csv"  INPUT\trn\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_5pctIncrease" (
  :: use same distance file; increase fare in code
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup.csv"  INPUT\trn
)
IF "%SCENARIO%" == "2015_FCIS_FareByDistance_flatLocal_20pctIncrease" (
  :: use same distance file; increase fare in code
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByDistanceLookup_plus20pct.csv"  INPUT\trn\FareByDistanceLookup.csv
)
IF "%SCENARIO%" == "2015_FCIS_FareByZone_Seamless" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByZone_Seamless.tpp"  INPUT\trn
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\ZoneLookup_Seamless.csv"  INPUT\trn
)
IF "%SCENARIO%" == "2015_FCIS_FareByZone_Seamless_plus10pct" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByZone_Seamless.tpp"  INPUT\trn
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\ZoneLookup_Seamless.csv"  INPUT\trn
)
IF "%SCENARIO%" == "2015_FCIS_FareByZone_LargeRegional_LocalFlatFare_plus28c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByZone_LargeRegional.tpp"  INPUT\trn
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\ZoneLookup_LargeRegional.csv"  INPUT\trn
)
IF "%SCENARIO%" == "2015_FCIS_FareByZone_LargeRegional_LocalFlatFare_plus62c" (
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\FareByZone_LargeRegional.tpp"  INPUT\trn
  copy /Y "%GITHUB_DIR%\utilities\bespoke-requests\fare-study\ZoneLookup_LargeRegional.csv"  INPUT\trn
)

:: ------------------------------------------------------------------------------------------------------
:: Create the working directories
:: ------------------------------------------------------------------------------------------------------
mkdir hwy
mkdir trn
mkdir skims
mkdir landuse
mkdir popsyn
mkdir nonres
mkdir main
mkdir logs

:: ------------------------------------------------------------------------------------------------------
:: Copy the input files to the working directories
:: ------------------------------------------------------------------------------------------------------
copy INPUT\hwy\                 hwy\
copy INPUT\trn\                 trn\
copy INPUT\landuse\             landuse\
copy INPUT\popsyn\              popsyn\
copy INPUT\nonres\              nonres\
copy INPUT\warmstart\main\      main\
copy INPUT\warmstart\nonres\    nonres\

::  Set the IP address of the host machine which sends tasks to the client machines 
if %computername%==MODEL2-A set HOST_IP_ADDRESS=192.168.1.206
if %computername%==MODEL2-B set HOST_IP_ADDRESS=192.168.1.207
if %computername%==MODEL2-C set HOST_IP_ADDRESS=192.168.1.208
if %computername%==MODEL2-D set HOST_IP_ADDRESS=192.168.1.209
if %computername%==MODEL3-A set HOST_IP_ADDRESS=10.164.0.200

:: Set the paths for executables
call CTRAMP\runtime\SetPath.bat

:: Runtime configuration: set project directory, auto operating cost, 
:: and synthesized household/population files in the appropriate places
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py
if ERRORLEVEL 1 goto done

:: Start the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Starthide Exit

:: ------------------------------------------------------------------------------------------------------
:: copy over iter3 files
:: ------------------------------------------------------------------------------------------------------
copy /Y "%BASELINE_FULL_RUN%\hwy\avgload*.net"               hwy
copy /Y "%BASELINE_FULL_RUN%\main\ShadowPricing_7.csv"       main
copy /Y "%BASELINE_FULL_RUN%\main\telecommute_constants.csv" main
copy /Y "%BASELINE_FULL_RUN%\skims\nonmotskm.tpp"            skims
mkdir trn\TransitAssignment.iter3
copy /Y "%BASELINE_FULL_RUN%\trn\TransitAssignment.iter3\transit*.lin" trn\TransitAssignment.iter3

:: set to 5 so trnAssign.bat will copy skims for use
set MAXITERATIONS=5


:: --------TrnAssignment Setup -- Standard Configuration
:: CHAMP has dwell  configured for buses (local and premium)
:: CHAMP has access configured for for everything
:: set TRNCONFIG=STANDARD
:: set COMPLEXMODES_DWELL=21 24 27 28 30 70 80 81 83 84 87 88
:: set COMPLEXMODES_ACCESS=21 24 27 28 30 70 80 81 83 84 87 88 110 120 130

:: --------TrnAssignment Setup -- Fast Configuration
:: NOTE the blank ones should have a space
set TRNCONFIG=FAST
set COMPLEXMODES_DWELL= 
set COMPLEXMODES_ACCESS= 

:: Step 4.5: Build initial transit files
set PYTHONPATH=%USERPROFILE%\Documents\GitHub\NetworkWrangler;%USERPROFILE%\Documents\GitHub\NetworkWrangler\_static
python CTRAMP\scripts\skims\transitDwellAccess.py NORMAL NoExtraDelay Simple complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
if ERRORLEVEL 2 goto done

: iter4

echo STARTED ITERATION %ITER%  %DATE% %TIME% >> logs\feedback.rpt 

:: Set the iteration parameters
set ITER=4
set PREV_ITER=3
set WGT=1.00
set PREV_WGT=0.00
set SAMPLESHARE=0.50
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:skims

:: Create the automobile level-of-service matrices
runtpp CTRAMP\scripts\skims\HwySkims.job
if ERRORLEVEL 2 goto done

:trnAssignSkim
:: copy a local version for easier restarting
copy CTRAMP\scripts\skims\trnAssign.bat trnAssign_iter%ITER%.bat
call trnAssign_iter%ITER%.bat
if ERRORLEVEL 2 goto done

copy trn\TransitAssignment.iter4\trnskm_*.

:: Create accessibility measures for use by the automobile ownership sub-model
runtpp CTRAMP\scripts\skims\Accessibility.job
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Execute the choice models using CT-RAMP java code
::
:: ------------------------------------------------------------------------------------------------------

:core

if %ITER%==4 (
  rem run matrix manager, household manager and jppf driver
  cd CTRAMP\runtime
  call javaOnly_runMain.cmd 

  rem run jppf node
  cd CTRAMP\runtime
  call javaOnly_runNode0.cmd
)

::  Call the MtcTourBasedModel class
java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased -iteration %ITER% -sampleRate %SAMPLESHARE% -sampleSeed %SEED%
if ERRORLEVEL 2 goto done


:: skip the rest
goto done_iter

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Execute the internal/external and commercial vehicle models
::
:: ------------------------------------------------------------------------------------------------------

:nonres

:: Create production/attraction tables based on growth assumptions
runtpp CTRAMP\scripts\nonres\IxForecasts_horizon.job
if ERRORLEVEL 2 goto done

:: Apply diurnal factors to the fixed internal/external demand matrices
runtpp CTRAMP\scripts\nonres\IxTimeOfDay.job
if ERRORLEVEL 2 goto done

:: Apply a value toll choice model for the interna/external demand
runtpp CTRAMP\scripts\nonres\IxTollChoice.job
if ERRORLEVEL 2 goto done

:: Apply the commercial vehicle generation models
runtpp CTRAMP\scripts\nonres\TruckTripGeneration.job
if ERRORLEVEL 2 goto done

:: Apply the commercial vehicle distribution models
runtpp CTRAMP\scripts\nonres\TruckTripDistribution.job
if ERRORLEVEL 2 goto done

:: Apply the commercial vehicle diurnal factors
runtpp CTRAMP\scripts\nonres\TruckTimeOfDay.job
if ERRORLEVEL 2 goto done

:: Apply a value toll choice model for eligibile commercial demand
runtpp CTRAMP\scripts\nonres\TruckTollChoice.job
if ERRORLEVEL 2 goto done

:: Apply a transit submode choice model for transit trips to bay area HSR stations
runtpp CTRAMP\scripts\nonres\HsrTransitSubmodeChoice.job
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4:  Build matrices from trip lists and assign trips to the highway network
::
:: ------------------------------------------------------------------------------------------------------

:hwyAssign

:: If demand models were executed, translate the trip lists to demand matrices
if %ITER% GTR 0 (
	runtpp CTRAMP\scripts\assign\PrepAssign.job
	if ERRORLEVEL 2 goto done
)

:: Assign the demand matrices to the highway network
runtpp CTRAMP\scripts\assign\HwyAssign.job
if ERRORLEVEL 2 goto done

:trnAssignSkim
:: copy a local version for easier restarting
copy CTRAMP\scripts\skims\trnAssign.bat trnAssign_iter%ITER%.bat
call trnAssign_iter%ITER%.bat
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 5:  Prepare the networks for the next iteration
::
:: ------------------------------------------------------------------------------------------------------

:feedback


:: Move assigned networks to a iteration-specific directory
mkdir hwy\iter%ITER%      

move hwy\LOADEA.net hwy\iter%ITER%\LOADEA.net
move hwy\LOADAM.net hwy\iter%ITER%\LOADAM.net
move hwy\LOADMD.net hwy\iter%ITER%\LOADMD.net
move hwy\LOADPM.net hwy\iter%ITER%\LOADPM.net
move hwy\LOADEV.net hwy\iter%ITER%\LOADEV.net

:: Give the default TP+ variables more intuitive names
runtpp CTRAMP\scripts\feedback\RenameAssignmentVariables.job

:: Average the demand for this and the previous iteration and compute a speed estimate for each link 
IF %ITER% GTR 1 (
	runtpp CTRAMP\scripts\feedback\AverageNetworkVolumes.job
	if ERRORLEVEL 2 goto done
	runtpp CTRAMP\scripts\feedback\CalculateSpeeds.job
	if ERRORLEVEL 2 goto done
) ELSE (
	copy hwy\iter%ITER%\LOADEA_renamed.net hwy\iter%ITER%\avgLOADEA.net /Y
	copy hwy\iter%ITER%\LOADAM_renamed.net hwy\iter%ITER%\avgLOADAM.net /Y
	copy hwy\iter%ITER%\LOADMD_renamed.net hwy\iter%ITER%\avgLOADMD.net /Y
	copy hwy\iter%ITER%\LOADPM_renamed.net hwy\iter%ITER%\avgLOADPM.net /Y
	copy hwy\iter%ITER%\LOADEV_renamed.net hwy\iter%ITER%\avgLOADEV.net /Y
)

:: Compute network statistics to measure convergence
runtpp CTRAMP\scripts\feedback\TestNetworkConvergence.job
if ERRORLEVEL 2 goto done

:: Combine the time-of-day-specific networks into a single network
runtpp CTRAMP\scripts\feedback\MergeNetworks.job  
if ERRORLEVEL 2 goto done                

:: Place a copy of the loaded networks into the root \hwy directory for access by the next iteration
copy hwy\iter%ITER%\avgLOADEA.net hwy\avgLOADEA.net /Y
copy hwy\iter%ITER%\avgLOADAM.net hwy\avgLOADAM.net /Y
copy hwy\iter%ITER%\avgLOADMD.net hwy\avgLOADMD.net /Y
copy hwy\iter%ITER%\avgLOADPM.net hwy\avgLOADPM.net /Y
copy hwy\iter%ITER%\avgLOADEV.net hwy\avgLOADEV.net /Y

:: Delete temporary files
del hwy\iter%ITER%\x*.net

:done_iter

:: ------------------------------------------------------------------------------------------------------
::
:: Last Step:  Stamp the time of completion to the feedback report file
::
:: ------------------------------------------------------------------------------------------------------

echo FINISHED ITERATION %ITER%  %DATE% %TIME% >> logs\feedback.rpt 

python "CTRAMP\scripts\notify_slack.py" "Finished iteration %ITER% in %MODEL_DIR%"

:: Shut down java
C:\Windows\SysWOW64\taskkill /f /im "java.exe"

:: summary scripts
:database

mkdir database
runtpp CTRAMP\scripts\database\SkimsDatabase.job
if ERRORLEVEL 2 goto done

set MODEL_DIR=%CD%
runtpp CTRAMP\scripts\database\extract_trnskim_tables.job
if ERRORLEVEL 2 goto done
:: move the results to database
move trnskm* database

:: Close the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Close Exit

:core_summaries
set TARGET_DIR=%CD%
"%R_HOME%\bin\RScript" --vanilla CTRAMP\scripts\core_summaries\combine_indiv_joint_tours_trips.R
if ERRORLEVEL 1 goto done

:: combine them with skims
"%R_HOME%\bin\RScript" --vanilla CTRAMP\scripts\core_summaries\join_trips_with_skims.R
if ERRORLEVEL 1 goto done

:: summarize by mode
"%R_HOME%\bin\RScript" --vanilla CTRAMP\scripts\core_summaries\summarize_trips_by_mode.R
if ERRORLEVEL 1 goto done

:: copy results to Box
copy updated_output\trips_with_skims.rds "\\tsclient\C\Users\lzorn\Box\Modeling\MTC Modeling\trips_with_skims_%SCENARIO%.rds"
copy updated_output\trip_summary.csv     "\\tsclient\C\Users\lzorn\Box\Modeling\MTC Modeling\trip_summary_%SCENARIO%.csv"

goto done_no_error

:: this is the done for errors
:done
ECHO FINISHED with ERROR

:done_no_error
ECHO FINISHED.

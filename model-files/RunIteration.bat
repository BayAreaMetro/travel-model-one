::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunIteration.bat
::
:: MS-DOS batch file to execute a single iteration of the MTC travel model.  This script is repeatedly 
:: called by the RunModel batch file.  
::
:: For complete details, please see http://mtcgis.mtc.ca.gov/foswiki/Main/RunIterationBatch.
::
:: dto (2012 02 15) gde (2009 10 9)
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:: ------------------------------------------------------------------------------------------------------
::
:: Step 0:  If iteration equals zero, go to step four (i.e. skip the demand models)
::
:: ------------------------------------------------------------------------------------------------------

if %ITER%==0 goto hwyAssign
:: bmp debugging
::goto core

:: calibration run , bmp
::if %ITER%==1 goto hwyAssign
if %ITER%==1 goto core

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Build highway and transit skims
::
:: ------------------------------------------------------------------------------------------------------

:skims

:: Create the automobile level-of-service matrices
runtpp CTRAMP\scripts\skims\HwySkims.job
if ERRORLEVEL 2 goto done

:: No need to build transit skims here; they were built by the previous assignment


:: Create accessibility measures for use by the automobile ownership sub-model
runtpp CTRAMP\scripts\skims\Accessibility.job
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Execute the choice models using CT-RAMP java code
::
:: ------------------------------------------------------------------------------------------------------

:core

::if %ITER%==1 (
if %ITER%==1 (
  rem run matrix manager, household manager and jppf driver
  cd CTRAMP\runtime
  call javaOnly_runMain.cmd 
  rem give hh manager some time to start
  ping -n 10 localhost

  rem run jppf node
  cd CTRAMP\runtime
  call javaOnly_runNode0.cmd
)

::  Call the MtcTourBasedModel class


java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased -iteration %ITER% -sampleRate %SAMPLESHARE% -sampleSeed %SEED%
if ERRORLEVEL 2 goto done

:: calibration run , bmp
if %ITER%==1 goto hwyAssign

goto done
:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Execute the internal/external and commercial vehicle models
::
:: ------------------------------------------------------------------------------------------------------

:nonres

:::: Create production/attraction tables based on growth assumptions
::runtpp CTRAMP\scripts\nonres\IxForecasts_horizon.job
::if ERRORLEVEL 2 goto done

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

:::: Apply a transit submode choice model for transit trips to bay area HSR stations
::runtpp CTRAMP\scripts\nonres\HsrTransitSubmodeChoice.job
::if ERRORLEVEL 2 goto done

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
:: debug, bmp
goto trnAssignSkim
:: Assign the demand matrices to the highway network
runtpp CTRAMP\scripts\assign\HwyAssign.job
if ERRORLEVEL 2 goto done
:: debug, bmp
::goto done

:trnAssignSkim
:: copy a local version for easier restarting
copy CTRAMP\scripts\skims\trnAssign.bat trnAssign_iter%ITER%.bat
call trnAssign_iter%ITER%.bat
if ERRORLEVEL 2 goto done
:: debug, bmp
goto done

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


:: ------------------------------------------------------------------------------------------------------
::
:: Last Step:  Stamp the time of completion to the feedback report file
::
:: ------------------------------------------------------------------------------------------------------

echo FINISHED ITERATION %ITER%  %DATE% %TIME% >> logs\feedback.rpt 

if "%COMPUTER_PREFIX%" == "WIN-" (
   python "CTRAMP\scripts\notify_slack.py" "Finished iteration %ITER% in %MODEL_DIR%"
)

:done

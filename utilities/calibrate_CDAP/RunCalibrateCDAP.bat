
:: ------------------------------------------------------------------
:: Background: 
:: ------------
:: With the new "Simple WFH model" in TM1.6, WFH workers are taken out of the CDAP universe 
:: so we need more of the remaining workers to travel to work. 
:: (Previously in TM1.5 the WFH workers were within the CDAP universe)
:: 
:: This is achieved by two additional constants in the Coordinated Daily Activity Pattern (CDAP) Model
:: They are in row 86 and 87 in CoordinatedDailyActivityPattern.xls
:: "Adjustment to FT workers (since WFH people are already taken out of the universe so we want more of the remaining people to travel to work)"
:: "Adjustment to PT workers (since WFH people are already taken out of the universe so we want more of the remaining people to travel to work)"
:: 
:: Calibration approach: 
:: ------------
:: To calibrate, we only need to run core from the beginnng up to CDAP. 
:: This means editing CTRAMP\runtime\mtcTourBased.properties to turn off model components after CDAP
:: 
:: Additionally, to speed things up, again in mtcTourBased.properties we feed it the best ShadowPrice.Input.File we have
:: And we turn UsualWorkAndSchoolLocationChoice.ShadowPricing.MaximumIterations = 1
:: The example mtcTourBased.properties is committed with this batch file
::
:: Furthermore, to speed things up, each calibration run uses a 20% sample only (see below: SAMPLESHARE=0.20)
::
:: After each calibration iteration, we calculated the 
:: change in the constant = ln(target/modelled) 
:: The spreadsheet is in: M:\Application\Model One\RTP2025\IncrementalProgress\validation_targets\2015_WorkersTravelingToWork.xlsx
:: The Tableau workbook that summarizes the CDAP results across different calibration run is in: M:\Application\Model One\RTP2025\IncrementalProgress\across_runs\across_RTP2025_IP_cdapResults.twb
::
:: Asana task: https://app.asana.com/0/0/1205704508591537/f
:: ------------------------------------------------------------------

: iter3

:: Set the iteration parameters
set ITER=3
set PREV_ITER=2
set WGT=0.33
set PREV_WGT=0.67
::set SAMPLESHARE=0.50
set SAMPLESHARE=0.20
set SEED=0


:core

if %ITER%==3 (
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


pause

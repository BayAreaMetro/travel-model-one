echo on

set ALLTIMEPERIODS=AM MD PM EV EA

:: AverageNetworkVolumes.job uses PREV_ITER=1 for ITER=1
set PREV_TRN_ITER=%PREV_ITER%
IF %ITER% EQU 1 SET PREV_TRN_ITER=0

set ALLTRIPMODES=wlk_com_wlk drv_com_wlk wlk_com_drv wlk_hvy_wlk drv_hvy_wlk wlk_hvy_drv wlk_lrf_wlk drv_lrf_wlk wlk_lrf_drv wlk_exp_wlk drv_exp_wlk wlk_exp_drv wlk_loc_wlk drv_loc_wlk wlk_loc_drv
set ALLTOURMODES=wlk_trn_wlk drv_trn_wlk wlk_trn_drv

mkdir trn\TransitAssignment.iter%ITER%
cd trn\TransitAssignment.iter%ITER%

echo START TRNASSIGN BuildTransitNetworks %DATE% %TIME% >> ..\..\logs\feedback.rpt

:: Prepare the highway network for use by the transit network
runtpp ..\..\CTRAMP\scripts\skims\PrepHwyNet.job
if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  goto donedone
)

:: Create the transit networks
runtpp ..\..\CTRAMP\scripts\skims\BuildTransitNetworks.job
if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  goto donedone
)

echo START TRNASSIGN TransitAsign %DATE% %TIME% >> ..\..\logs\feedback.rpt

:: Assign the transit trips to the transit network
:: Outputs: 
::    trnlink[ea|am|md|pm|ev]_[wlk|drv]_[loc|lrf|exp|hvy|com]_[wlk|drv].[csv,dbf]
::    trnline[ea|am|md|pm|ev]_[wlk|drv]_[loc|lrf|exp|hvy|com]_[wlk|drv].csv
runtpp ..\..\CTRAMP\scripts\assign\TransitAssign.job
if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  echo ERRORLEVEL is %ERRORLEVEL%
  goto donedone
)

echo START TRNASSIGN TransitSkims %DATE% %TIME% >> ..\..\logs\feedback.rpt

:: And skims
:: Outputs:
::    trnskm[ea|am|md|pm|ev]_[wlk|drv]_[loc|lrf|exp|hvy|com|trn]_[wlk|drv].tpp
runtpp ..\..\CTRAMP\scripts\skims\TransitSkims.job
if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  echo ERRORLEVEL is %ERRORLEVEL%
  goto donedone
)

:: Apply Regional Transit Fare Strategy
:: This file should only be present if the Strategy is meant to be applied
if exist "..\..\CTRAMP\scripts\skims\apply_regional_transit_fares_to_skims.job" (
  runtpp "..\..\CTRAMP\scripts\skims\apply_regional_transit_fares_to_skims.job"
  if ERRORLEVEL 2 (
    set TRN_ERRORLEVEL=2
    echo ERRORLEVEL is %ERRORLEVEL%
    goto donedone
  )
)

:copyup

:: for core
if %ITER% NEQ %MAXITERATIONS% (
  FOR %%A in (%ALLTRIPMODES% %ALLTOURMODES%) DO (
    copy /y trnskmea_%%A.tpp ..\..\skims\trnskmea_%%A.tpp
    copy /y trnskmam_%%A.tpp ..\..\skims\trnskmam_%%A.tpp
    copy /y trnskmmd_%%A.tpp ..\..\skims\trnskmmd_%%A.tpp
    copy /y trnskmpm_%%A.tpp ..\..\skims\trnskmpm_%%A.tpp
    copy /y trnskmev_%%A.tpp ..\..\skims\trnskmev_%%A.tpp
  )
)
 
:: copy the latest transit assignment dbf into the parent dir
if %ITER% EQU %MAXITERATIONS% (
  python ..\..\CTRAMP\scripts\skims\aggregateTransitLinks.py EA
  python ..\..\CTRAMP\scripts\skims\aggregateTransitLinks.py AM
  python ..\..\CTRAMP\scripts\skims\aggregateTransitLinks.py MD
  python ..\..\CTRAMP\scripts\skims\aggregateTransitLinks.py PM
  python ..\..\CTRAMP\scripts\skims\aggregateTransitLinks.py EV
  copy .\%LASTSUBDIR_EA%\trnlinkEA.dbf ..
  copy .\%LASTSUBDIR_AM%\trnlinkAM.dbf ..
  copy .\%LASTSUBDIR_MD%\trnlinkMD.dbf ..
  copy .\%LASTSUBDIR_PM%\trnlinkPM.dbf ..
  copy .\%LASTSUBDIR_EV%\trnlinkEV.dbf ..
)

echo DONE TRNASSIGN %DATE% %TIME% >> ..\..\logs\feedback.rpt

:donedone
cd ..
cd ..

:: pass on errorlevel
EXIT /B %TRN_ERRORLEVEL%
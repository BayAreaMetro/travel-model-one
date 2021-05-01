echo on

set ALLTIMEPERIODS=AM MD PM EV EA
set TRNASSIGNITER=0
set PREVTRNASSIGNITER=NEG1
set PHTDIFFCOND=0.0001
set VOLDIFFCOND=0.005
set TRNASSIGNMODE=NORMAL
set TOTMAXTRNITERS=30
set MAXPATHTIME=240
set PCT=%%
set PYTHONPATH=E:\projects\clients\solanoNapa\SNABM\NetworkWrangler;E:\projects\clients\solanoNapa\SNABM\NetworkWrangler\_static
set TRN_ERRORLEVEL=0

:: AverageNetworkVolumes.job uses PREV_ITER=1 for ITER=1
set PREV_TRN_ITER=%PREV_ITER%
IF %ITER% EQU 1 SET PREV_TRN_ITER=0

set ALLTRIPMODES=wlk_com_wlk drv_com_wlk wlk_com_drv wlk_hvy_wlk drv_hvy_wlk wlk_hvy_drv wlk_lrf_wlk drv_lrf_wlk wlk_lrf_drv wlk_exp_wlk drv_exp_wlk wlk_exp_drv wlk_loc_wlk drv_loc_wlk wlk_loc_drv
set ALLTOURMODES=wlk_trn_wlk drv_trn_wlk wlk_trn_drv
IF NOT DEFINED TRNFASTERTHANFREEFLOW (set TRNFASTERTHANFREEFLOW=0)

:: For postprocessing, uncomment and set the following (which are normally set in runmodel.bat)
::set CHAMPVERSION=Y:\champ\dev\4.3modeChoice
::set ITERATION=POSTPROC
::set MAXITERATIONS=POSTPROC
::set MACHINES=TEHAMA
::set NODES=12
::set COMMPATH=Y:\COMMPATH\TEHAMA
::set COMPLEXMODES_DWELL=11 12 16 17 18 19 22 23 24 25
::set COMPLEXMODES_ACCESS=11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32
::set ALLTIMEPERIODS=AM MD PM EV EA

:: Also verify that transit[AM,MD,PM,EV,EA].lin exist, transitOriginal[AM,MD,PM,EV,EA].lin as simple delay versions
:: by doing the following:
:: python %CHAMPVERSION%\scripts\trnSkims\transitDwellAccess.py NORMAL Simple complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
:: if ERRORLEVEL 2 goto done
:: FOR %%H in (AM MD PM EV EA) DO (copy transit%%H.lin transitOriginal%%H.lin)

:: and that the required transitLineToVehicle.csv, transitVehicleToCapacity.csv, and transitPrefixToVehicle.csv exist
::


mkdir trn\TransitAssignment.iter%ITER%
cd trn\TransitAssignment.iter%ITER%

:copyTransitLin
:: bring in the latest transit files -- original if postprocessing
IF %ITER% EQU POSTPROC (
  FOR %%H in (%ALLTIMEPERIODS%) DO copy /y ..\transitOriginal%%H.lin transit%%H_0.lin
)
IF NOT %ITER% EQU POSTPROC (
  IF %ITER% EQU 0 (
    FOR %%H in (%ALLTIMEPERIODS%) DO copy /y ..\transitOriginal%%H.lin transit%%H_0.lin
  )
  :: otherwise go from where the previous iteration left off
  IF %ITER% GTR 0 (
    FOR %%H in (%ALLTIMEPERIODS%) DO copy /y ..\TransitAssignment.iter%PREV_TRN_ITER%\transit%%H.lin transit%%H_0.lin
  )
)
FOR %%H in (%ALLTIMEPERIODS%) DO (
  copy /y transit%%H_0.lin transit%%H.lin
  set LASTITER_%%H=0
  set LASTSUBDIR_%%H=Subdir0
)

:: for fast config, only do 1
:: for standard config, keep it short for initial assign
if "%TRNCONFIG%"=="FAST" (set MAXTRNITERS=0)
if "%TRNCONFIG%"=="STANDARD" (
  set MAXTRNITERS=%TOTMAXTRNITERS%
  IF %ITER% EQU 0 (set MAXTRNITERS=4)
)
IF %ITER% EQU POSTPROC (set TRNASSIGNMODE=POSTPROC)
IF %ITER% EQU %MAXITERATIONS% (set PHTDIFFCOND=0)

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


::============================== BEGIN LOOP ==============================
:trnassign_loop
echo START TRNASSIGN            SubIter %TRNASSIGNITER% %DATE% %TIME% >> ..\..\logs\feedback.rpt

:transitSubAssign

:: Assign the transit trips to the transit network
runtpp ..\..\CTRAMP\scripts\assign\TransitAssign.job
if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  goto donedone
)
:: And skim
runtpp ..\..\CTRAMP\scripts\skims\TransitSkims.job
if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  goto donedone
)

:: RUNNING OUT OF SPACE - delete this from the recycle bin too
set THISDIR=%cd:X:\=X:\Recycle Bin\%
IF "%THISDIR:~3,11%"=="Recycle Bin" (
  del /Q "%THISDIR%"
)


set SUBDIR=Subdir%TRNASSIGNITER%
IF NOT EXIST %SUBDIR% mkdir %SUBDIR%

:: can opt out of this later if it's not useful
set KEEP_ASGN_DBFS=0
IF %KEEP_ASGN_DBFS% EQU 1 (
    copy *.dbf %SUBDIR%
)

:routelinkMSA
:: For the final iteration, MSA our link volumes and use that to check for convergence
if %ITER% EQU %MAXITERATIONS% (
  echo START   routelinkMSA       SubIter %TRNASSIGNITER% %DATE% %TIME% >> ..\..\logs\feedback.rpt

  E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py EA %TRNASSIGNITER% %VOLDIFFCOND%
  E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py AM %TRNASSIGNITER% %VOLDIFFCOND%
  E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py MD %TRNASSIGNITER% %VOLDIFFCOND%
  E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py PM %TRNASSIGNITER% %VOLDIFFCOND%
  E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py EV %TRNASSIGNITER% %VOLDIFFCOND%

)

:modifyDwellAccess
echo START   transitDwellAccess SubIter %TRNASSIGNITER% %DATE% %TIME% >> ..\..\logs\feedback.rpt

:: Initialize with header line
if %TRNASSIGNITER% EQU 0 (
  echo trnAssignIter,timeperiod,mode,PHT,pctPHTdiff,RMSE_IVTT,RMSE_TOTT,AvgPaths,CurrPaths,CurrBoards,PathsFromBoth,PathsFromIter,PathsFromAvg,PHTCriteriaMet > PHT_total.csv
)

E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex EA %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex AM %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex MD %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex PM %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
E:\projects\clients\solanoNapa\Anaconda2\python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex EV %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%

echo DONE    transitDwellAccess SubIter %TRNASSIGNITER% %DATE% %TIME% >> ..\..\logs\feedback.rpt

:: did all of them reach end condition? count files and if there are new ones, copy them
:: into place so the transit assignment will use them
set EXISTCOUNT=0
set /a NEXTTRNASSIGNITER = %TRNASSIGNITER%+1

FOR %%H in (%ALLTIMEPERIODS%) DO (
  IF EXIST transit%%H_%NEXTTRNASSIGNITER%.lin (
    set /a EXISTCOUNT+=1
    set LASTSUBDIR_%%H=Subdir%NEXTTRNASSIGNITER%
    set LASTITER_%%H=%NEXTTRNASSIGNITER%
    copy /y transit%%H_%NEXTTRNASSIGNITER%.lin transit%%H.lin
  )
)

:: if EA is the only holdout then that's not enough reason to keep iterating
IF EXIST transitEA_%NEXTTRNASSIGNITER%.lin (
  IF %EXISTCOUNT%==1 (
    set EXISTCOUNT=0
    set LASTSUBDIR_EA=Subdir%TRNASSIGNITER%
    set LASTITER_EA=%TRNASSIGNITER%
    move transitEA_%NEXTTRNASSIGNITER%.lin transitEA_unused.lin
    copy transitEA_%TRNASSIGNITER%.lin transitEA.lin
  )
)

:: cleanup?

:: converged! done
IF %EXISTCOUNT%==0 goto donetrnassign

echo COMPLETED TRNASSIGN        SubIter %TRNASSIGNITER% %DATE% %TIME% (with %EXISTCOUNT% new line files) >> ..\..\logs\feedback.rpt
set PREVTRNASSIGNITER=%TRNASSIGNITER%
set /a TRNASSIGNITER+=1

goto trnassign_loop
::============================== END LOOP ==============================
:donetrnassign
:: if we have an error then stop
if ERRORLEVEL 2 goto donedone

echo Done transit assignment; LastIters are %LASTITER_AM%, %LASTITER_MD%, %LASTITER_PM%, %LASTITER_EV%, %LASTITER_EA%

:copyup

:: for core
if %ITER% NEQ %MAXITERATIONS% (
  FOR %%A in (%ALLTRIPMODES% %ALLTOURMODES%) DO (
    copy /y trnskmea_%%A.avg.iter%LASTITER_EA%.tpp ..\..\skims\trnskmea_%%A.tpp
    copy /y trnskmam_%%A.avg.iter%LASTITER_AM%.tpp ..\..\skims\trnskmam_%%A.tpp
    copy /y trnskmmd_%%A.avg.iter%LASTITER_MD%.tpp ..\..\skims\trnskmmd_%%A.tpp
    copy /y trnskmpm_%%A.avg.iter%LASTITER_PM%.tpp ..\..\skims\trnskmpm_%%A.tpp
    copy /y trnskmev_%%A.avg.iter%LASTITER_EV%.tpp ..\..\skims\trnskmev_%%A.tpp
  )
)
 
:: copy the latest transit assignment dbf into the parent dir
if %ITER% EQU %MAXITERATIONS% (
  copy .\%LASTSUBDIR_EA%\trnlinkEA_ALLMSA.dbf ..
  copy .\%LASTSUBDIR_AM%\trnlinkAM_ALLMSA.dbf ..
  copy .\%LASTSUBDIR_MD%\trnlinkMD_ALLMSA.dbf ..
  copy .\%LASTSUBDIR_PM%\trnlinkPM_ALLMSA.dbf ..
  copy .\%LASTSUBDIR_EV%\trnlinkEV_ALLMSA.dbf ..
)

:donedone
cd ..
cd ..

set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin;%PYTHON_PATH%

:: pass on errorlevel
EXIT /B %TRN_ERRORLEVEL%
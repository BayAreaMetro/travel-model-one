:: --------------------------------------------------------------------------------------------------------------------
:: this batch file includes a subset of the commands in CTRAMP\scripts\skims\trnAssign.bat
:: except that it uses a special TransitAssign_NGFtrace.job to include specfic ODs chosen for NGF public engagement 
:: runtpp X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TransitAssign_NGFtrace.job
:: --------------------------------------------------------------------------------------------------------------------


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
set TRN_ERRORLEVEL=0

:: AverageNetworkVolumes.job uses PREV_ITER=1 for ITER=1
set PREV_TRN_ITER=%PREV_ITER%
IF %ITER% EQU 1 SET PREV_TRN_ITER=0

set ALLTRIPMODES=wlk_com_wlk drv_com_wlk wlk_com_drv wlk_hvy_wlk drv_hvy_wlk wlk_hvy_drv wlk_lrf_wlk drv_lrf_wlk wlk_lrf_drv wlk_exp_wlk drv_exp_wlk wlk_exp_drv wlk_loc_wlk drv_loc_wlk wlk_loc_drv
set ALLTOURMODES=wlk_trn_wlk drv_trn_wlk wlk_trn_drv
IF NOT DEFINED TRNFASTERTHANFREEFLOW (set TRNFASTERTHANFREEFLOW=0)


mkdir trn\TransitAssignment.iter%ITER%
cd trn\TransitAssignment.iter%ITER%

::============================== BEGIN LOOP ==============================
:trnassign_loop
echo START TRNASSIGN            SubIter %TRNASSIGNITER% %DATE% %TIME% >> ..\..\logs\feedback.rpt

:transitSubAssign

:: Assign the transit trips to the transit network
:: runtpp ..\..\CTRAMP\scripts\assign\TransitAssign.job
runtpp X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TransitAssign_NGFtrace.job
if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  echo ERRORLEVEL is %ERRORLEVEL%
  goto donedone
)
:: And skim
runtpp ..\..\CTRAMP\scripts\skims\TransitSkims.job
if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  echo ERRORLEVEL is %ERRORLEVEL%
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

  python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py EA %TRNASSIGNITER% %VOLDIFFCOND%
  python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py AM %TRNASSIGNITER% %VOLDIFFCOND%
  python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py MD %TRNASSIGNITER% %VOLDIFFCOND%
  python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py PM %TRNASSIGNITER% %VOLDIFFCOND%
  python ..\..\CTRAMP\scripts\skims\routeLinkMSA.py EV %TRNASSIGNITER% %VOLDIFFCOND%

  if ERRORLEVEL 2 (
    set TRN_ERRORLEVEL=2
    echo ERRORLEVEL is %ERRORLEVEL%
    goto donedone
  )
)

:modifyDwellAccess
echo START   transitDwellAccess SubIter %TRNASSIGNITER% %DATE% %TIME% >> ..\..\logs\feedback.rpt

:: Initialize with header line
if %TRNASSIGNITER% EQU 0 (
  echo trnAssignIter,timeperiod,mode,PHT,pctPHTdiff,RMSE_IVTT,RMSE_TOTT,AvgPaths,CurrPaths,CurrBoards,PathsFromBoth,PathsFromIter,PathsFromAvg,PHTCriteriaMet > PHT_total.csv
)

:: debug print out python version
python --version
python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex EA %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex AM %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex MD %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex PM %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
python ..\..\CTRAMP\scripts\skims\transitDwellAccess.py %TRNASSIGNMODE% NoExtraDelay Complex EV %TRNASSIGNITER% %PHTDIFFCOND% %MAXTRNITERS% complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%

if ERRORLEVEL 2 (
  set TRN_ERRORLEVEL=2
  echo ERRORLEVEL is %ERRORLEVEL%
  goto donedone
)

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
    copy /y transitEA_%TRNASSIGNITER%.lin transitEA.lin
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
echo donetrnassign with errorlevel %ERRORLEVEL%
if ERRORLEVEL 2 goto donedone

echo Done transit assignment; LastIters are %LASTITER_AM%, %LASTITER_MD%, %LASTITER_PM%, %LASTITER_EV%, %LASTITER_EA%


:donedone
cd ..
cd ..

:: pass on errorlevel
EXIT /B %TRN_ERRORLEVEL%
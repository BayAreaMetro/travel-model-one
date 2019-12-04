echo on
setlocal enabledelayedexpansion
set CODE_DIR=X:\travel-model-one-master

mkdir nonres
copy "M:\Development\Travel Model One\InternalExternal\ixDaily2015.tpp"        nonres
copy "M:\Development\Travel Model One\InternalExternal\ixDaily2015_totals.dbf" nonres


:futures
copy "%USERPROFILE%\Box\Horizon and Plan Bay Area 2050\Futures Planning\Modeling Characteristics\Interregional Volume Assumptions\ixex_config.dbf" nonres

:: FUTURE should be one of [PBA50, CleanAndGreen, BackToTheFuture, RisingTidesFallingFortunes]
FOR %%H in (CleanAndGreen BackToTheFuture RisingTidesFallingFortunes) DO (
  FOR %%G in (2015 2030 2050) DO (

    SET FUTURE=%%H
    set MODEL_YEAR=%%G
    echo FUTURE=[!FUTURE!] MODEL_YEAR=[!MODEL_YEAR!]

    runtpp "%CODE_DIR%\model-files\scripts\nonres\IxForecasts_horizon.job"
    IF ERRORLEVEL 1 goto done
    move nonres\ixDailyx4.tpp nonres\ixDailyx4_!MODEL_YEAR!_!FUTURE!.tpp
  )
)

:blueprint_ipa
copy "%USERPROFILE%\Box\Horizon and Plan Bay Area 2050\Blueprint\Transportation\ixex_config.dbf" nonres
SET FUTURE=PBA50
set MODEL_YEAR=2035

runtpp "%CODE_DIR%\model-files\scripts\nonres\IxForecasts_horizon.job"
IF ERRORLEVEL 1 goto done
move nonres\ixDailyx4.tpp nonres\ixDailyx4_%MODEL_YEAR%_%FUTURE%.tpp

:done
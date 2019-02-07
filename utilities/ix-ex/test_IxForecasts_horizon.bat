echo on
setlocal enabledelayedexpansion

:: should be one of [PBA50, CleanAndGreen, BackToTheFuture, RisingTidesFallingFortunes]
set CODE_DIR=C:\Users\lzorn\Documents\travel-model-one

mkdir nonres
copy "M:\Development\Travel Model One\InternalExternal\IXDaily2006x4.may2208.mat" nonres
copy "M:\Development\Travel Model One\InternalExternal\ixex_config.dbf"           nonres

:: create 2015
runtpp "%CODE_DIR%\utilities\ix-ex\create_ix_2015.job"
IF ERRORLEVEL 1 goto done

FOR %%H in (CleanAndGreen BackToTheFuture RisingTidesFallingFortunes) DO (
  FOR %%G in (2015 2030 2050) DO (

    SET FUTURE=%%H
    set MODEL_YEAR=%%G
    echo FUTURE=[!FUTURE!] MODEL_YEAR=[!MODEL_YEAR!]

    runtpp "%CODE_DIR%\model-files\scripts\nonres\IxForecasts_horizon.job"
    IF ERRORLEVEL 1 goto done
  )
)

:done
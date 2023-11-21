echo on
setlocal enabledelayedexpansion
set CODE_DIR=E:\GitHub\travel-model-one

mkdir nonres
copy /Y "M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\nonres\nonres_05\ixDaily2005.tpp"        nonres
copy /Y "M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\nonres\nonres_05\ixDaily2015.tpp"        nonres
copy /Y "M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\nonres\nonres_05\ixDaily2015_totals.dbf" nonres
copy /Y "M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\nonres\nonres_05\ixDaily2021.tpp"        nonres
copy /Y "M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\nonres\nonres_05\ixDaily2021_totals.dbf" nonres
copy /Y "M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\nonres\nonres_05\ixex_config.dbf"        nonres

:: disabled -- skip
goto blueprint_ipa
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
SET FUTURE=PBA50

FOR %%G in (2015 2019 2021 2022 2035 2050 2005) DO (
  set MODEL_YEAR=%%G
  runtpp "%CODE_DIR%\model-files\scripts\nonres\IxForecasts_horizon.job"
  rem IF ERRORLEVEL 1 goto done
  rem Testing error with 2019 so don't goto done

  IF !MODEL_YEAR! NEQ 2019 (
    runtpp "%CODE_DIR%\model-files\scripts\nonres\IxTimeOfDay.job
  )
  move nonres\ixDailyx4.tpp nonres\ixDailyx4_!MODEL_YEAR!.tpp

)
:done
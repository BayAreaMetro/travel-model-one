:: prep_roadway_network
::
:: Script to create freeflow.net from a network file.
::
:: 2017 Nov 9 lmz


:: Location of travel-model-one local repo (probably including this dir)
set CODE_DIR=C:\Users\lzorn\Documents\travel-model-one-master

:: Location of INPUT and CTRAMP directory.
:: set MODEL_DIR=M:\Application\Model One\STIP2017\2040_06_700_CC130046_680SR4Int

:: Name of the input roadway network, in %MODEL_DIR%\INPUT\hwy\source
:: set ROADWAY_FILE=680_4.net

:: City shape file
set CITYSHAPE_FILE=M:\Development\Travel Model One\Version 05\Adding City to Master Network\Cityshapes\PBA_Cities_NAD_1983_UTM_Zone_10N.shp

cd %MODEL_DIR%\INPUT

::   Input: %MODEL_DIR%\INPUT\hwy\source\%ROADWAY_FILE%
::  Output: %MODEL_DIR%\INPUT\hwy\source\1_withCapclass.net
:: Summary: Sets capacities and free flow speeds and times for network links
::          Based on columns AT, FT, TOS, SIGCOR, TSIN, TOLLCLASS, OT
::          Updates columns: CAPCLASS, SPDCLASS, FFS, FFT, CAP, OT
runtpp "%CODE_DIR%\utilities\check-network\set_capclass.job"
if ERRORLEVEL 2 goto done

:: save this for the next script
copy hwy\source\1_withCapclass.net hwy\freeflow.net

:: Assumes this script is an input
::   Input: hwy\freeflow.net
::  Output: hwy\withTolls.net
:: Summary: Sets the prices in the roadway network
::          Based on columns TOLLCLASS, DISTANCE
::          Updates columns: TOLL[EA,AM,MD,PM,EV]_[DA,S2,S3,VSM,SML,MED,LRG]
runtpp "%MODEL_DIR%\CTRAMP\scripts\preprocess\SetTolls.job"
if ERRORLEVEL 2 goto done

:: name this more clearly and keep in source
move hwy\withTolls.net hwy\source\2_withTolls.net

:: Add city to links
::   Input: hwy\source\withTolls.net
::  Output: hwy\source\withCities.net
:: Summary: Adds city information to shapefile
::          Based on location of links
::          Updates columns: alpha_id, cityid, cityname
python "%CODE_DIR%\utilities\AttachShapeToNetwork\attachShapeToNetwork.py" -s alpha_id -s name -c cityid -c cityname hwy\source\2_withTolls.net "%CITYSHAPE_FILE%" hwy\source\3_withCities.net
if ERRORLEVEL 2 goto done

:: save the TPPL files into source
move TPPL* hwy\source

:: this is it!
copy hwy\source\3_withCities.net hwy\freeflow.net

goto victory

:done
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem Failure
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
goto end

:victory
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem Victory
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:end


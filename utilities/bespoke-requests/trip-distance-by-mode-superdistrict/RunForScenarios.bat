@echo on
Setlocal EnableDelayedExpansion

:: The location of R and R libraries
set R_HOME=C:\Program Files\R\R-3.2.3
set R_LIB=C:/Users/mtcpb/Documents/R/win-library/3.2

:: run this here
set BASE_DIR=M:\Application\Model One\RTP2017\Scenarios\
:: for these dirs
set DIRS=2030_06_694_Amd1 2035_06_694_Amd1 2040_06_694_Amd1
::2035_06_697 2040_06_697
::2005_05_003 2010_06_003 2015_06_002 2035_06_696 2040_06_696
::2020_06_690 2020_06_691 2020_06_693 2020_06_694 2020_06_695 2035_06_690 2035_06_691 2035_06_693 2035_06_694 2035_06_695 2040_06_690 2040_06_691 2040_06_693 2040_06_694 2040_06_695

set SCRIPT=C:/Users/lzorn/Documents/travel-model-one-master/utilities/bespoke-requests/trip-distance-by-mode-superdistrict/trip-distance-by-mode-superdistrict.R

for %%H in (%DIRS%) do (
  echo Processing [%%H]
  set MODEL_DIR=%%H
  echo MODEL_DIR=!MODEL_DIR!

  set BESPOKE=!MODEL_DIR!\OUTPUT\bespoke
  if exist "!BESPOKE!\*" rmdir /s /q "!BESPOKE!"
  if exist "!BESPOKE!" del /q "!BESPOKE!"

  rem run trip-distance-by-mode-superdistrict
  "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%SCRIPT%"
  IF %ERRORLEVEL% GTR 0 goto done
)

:done
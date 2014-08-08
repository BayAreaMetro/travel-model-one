@echo on
set RUN_NAME=2010_04_ZZZ

:: destination directory - on the local disk
set TARGET_DIR=C:\Users\lzorn\Documents\%RUN_NAME%
set TIMEPERIODS=EA AM MD PM EV

:: map this drive for the copy -- it's failing otherwise :(
:: it will prompt for the password
set MAINMODELSHARE=\\mainmodel\MainModelShare
set NETUSEDRIVE=B:

net use %NETUSEDRIVE%
if %ERRORLEVEL% EQU 2 (
  net use %NETUSEDRIVE% %mainmodelshare% /user:mtcpub *
)
net use

set OUTPUT_DIR=M:\Development\Travel Model One\Version 04\%RUN_NAME%\OUTPUT
set POPSYN_DIR=B:\Projects\%RUN_NAME%.archived\popsyn
set DB_DIR=B:\Projects\%RUN_NAME%.archived\database

if not exist "%TARGET_DIR%\hhFile.p2011s3a1.2010.csv" ( copy "%POPSYN_DIR%\hhFile.p2011s3a1.2010.csv"  "%TARGET_DIR%  )
if not exist "%TARGET_DIR%\householdData_3.csv"       ( copy "%OUTPUT_DIR%\householdData_3.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\tazData.csv"               ( copy "%OUTPUT_DIR%\tazData.csv"                "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\indivTripData_3.csv"       ( copy "%OUTPUT_DIR%\indivTripData_3.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\jointTripData_3.csv"       ( copy "%OUTPUT_DIR%\jointTripData_3.csv"        "%TARGET_DIR%" )

FOR %%H in (%TIMEPERIODS%) DO (
  if not exist "%TARGET_DIR%\ActiveTimeSkimsDatabase%%H.csv" (
    copy "%DB_DIR%\ActiveTimeSkimsDatabase%%H.csv" "%TARGET_DIR%"
  )
)

:: disconnect NETUSEDRIVE
net use /delete %NETUSEDRIVE%
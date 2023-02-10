:: ---------------------------------
::
:: This batch script helps QAQC of
:: - AV share
:: - Telecommute
:: - Bike mode share (for the Complete Street strategy)
:: - Max congested speed (for the Vision Zero strategy)
::
:: ---------------------------------

mkdir OUTPUT/QAQC

:: ---------------------------------
:: check household-owned AV share
:: ---------------------------------

set GITHUB_MASTER=E:\Projects\Clients\gm\models\travel-model-one

:: assume this script is being run from the directory with the full model run
mkdir QAQC
copy /y "%GITHUB_MASTER%\utilities\RTP\QAQC\Car_ownership_AVHV.r"             QAQC\Car_ownership_AVHV.r

cd main
call "%R_HOME%\bin\x64\Rscript.exe" ..\QAQC\Car_ownership_AVHV.R
cd ..

copy /y "%GITHUB_MASTER%\utilities\RTP\QAQC\Car_ownership_summary_2035.xlsx"       "OUTPUT\QAQC\Car_ownership_summary_2035.xlsx"
copy /y "%GITHUB_MASTER%\utilities\RTP\QAQC\Car_ownership_summary_2050.xlsx"       "OUTPUT\QAQC\Car_ownership_summary_2050.xlsx"

:: ---------------------------------
:: check telecommute
:: ---------------------------------
copy /y "%GITHUB_MASTER%\utilities\RTP\QAQC\Report_TelecommuteLevel.py"       QAQC\Report_TelecommuteLevel.py
python QAQC/report_telecommutelevel.py
cd QAQC
copy /y "PBA50_QAQC.csv"                                                "OUTPUT\QAQC\PBA50_QAQC.csv"
cd ..

:: ---------------------------------
:: check bike mode share
:: --------------------------------- 
copy /y "%GITHUB_MASTER%\utilities\RTP\QAQC\Mode_share.twb"             "OUTPUT\QAQC\Mode_share.twb"
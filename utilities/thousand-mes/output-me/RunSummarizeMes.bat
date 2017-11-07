::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunSummarizeMes.bat
::
:: MS-DOS batch file to summarize the thousand (or however many) mes variant of a Travel Model One run. 
::
:: lmz (2016 7 20)
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:: Use R to create versions of main output files with only MY household
set TARGET_DIR=%CD%
set R_USER=mtcpb
set R_LIB=C:/Users/mtcpb/Documents/R/win-library/3.2

call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\utilities\thousand-mes\output-me\filter-main-to-mes.R"
if ERRORLEVEL 1 goto done
echo %DATE% %TIME% ...Done filtering main

SET JUST_MES=1
call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\model-files\scripts\core_summaries\CoreSummaries.R"
if ERRORLEVEL 1 goto done
echo %DATE% %TIME% ...Done CoreSummaries

:done

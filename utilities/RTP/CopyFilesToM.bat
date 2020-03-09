::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: CopyFilesToM.bat
::
:: MS-DOS batch file to copy files (CTRAMP, INPUT, batch files and extracted output)
:: to M: drive.  Run this within the model directory after the ExtractKeyFiles.bat
:: has executed on a machine that also has access to the DEST_DIR, below.
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FOR %%I IN (.) DO SET CurrentD=%%~nI%%~xI
echo %CurrentD%

:: This is where we'll eventually keep everything.  See copy_to_dest below
set DEST_DIR=M:\Application\Model One\RTP2017\Project Performance Assessment\Test\Sampling and Iterations\Scenarios
mkdir "%DEST_DIR%\%currentD%"

:copy_to_dest

copy *.bat "%DEST_DIR%\%currentD%"
robocopy /MIR CTRAMP     "%DEST_DIR%\%currentD%\CTRAMP"
robocopy /MIR INPUT      "%DEST_DIR%\%currentD%\INPUT"
robocopy /MIR extractor  "%DEST_DIR%\%currentD%\OUTPUT"

:done
REM Use 7Zip to Zip travel model runs (for example in folder "Y:\Projects\2015_06_002_inc075") and place the zip archive 
REM in "mtcarchives\cloudmodels1\Archived Travel Model Runs". Then renames folder to X.archived
REM Folder path of the run to be zipped is an argument
REM
ECHO
ECHO Zipping all files in %1
set PROJECT_DIR=%~f1
set myfolder=%~nx1
REM
REM Checks for extractor folder. If not avaialblble, zips individual folders otherwise saved in extractor folder.
REM
If exist "%PROJECT_DIR%\extractor" (
  "C:\Program Files\7-Zip\7z.exe" a "\\mtcarchives\cloudmodels1\Archived Travel Model Runs\%myfolder%" "%1\CTRAMP*" "%1\extractor*" "%1\INPUT*" "%1\*.bat" -mx9
) ELSE (
  "C:\Program Files\7-Zip\7z.exe" a "\\mtcarchives\cloudmodels1\Archived Travel Model Runs\%myfolder%" "%1\CTRAMP*" "%1\accessibilities" "%1\core_summaries" "%1\main" "%1\metrics" "%1\skims" "%1\trn" "%1\updated_output" "%1\INPUT" "%1\*.bat" -mx9
)
ren %PROJECT_DIR% %myfolder%.archived

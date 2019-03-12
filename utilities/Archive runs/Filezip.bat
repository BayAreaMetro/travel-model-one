REM Use 7Zip to Zip travel model runs (for example in folder "Z:\Projects\2015_06_002_inc075") and place the zip archive 
REM in "U:\Archived Travel Model Runs". Then renames folder to XXX.archived
ECHO
ECHO Zipping all files in Z:\Projects\2015_06_002_inc125
ECHO
"C:\Program Files\7-Zip\7z.exe" a "U:\Archived Travel Model Runs\2015_06_002_inc125.7z" "Z:\Projects\2015_06_002_inc125\CTRAMP" "Z:\Projects\2015_06_002_inc125\extractor" "Z:\Projects\2015_06_002_inc125\INPUT" "Z:\Projects\2015_06_002_inc125\*.bat" -mx9
ECHO
Z:
cd Projects\
ren 2015_06_002_inc125 2015_06_002_inc125.archived
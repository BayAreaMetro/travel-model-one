REM Use 7Zip to Zip travel model runs (for example in folder "Z:\Projects\2015_06_002_inc075") and place the zip archive 
REM in "U:\Archived Travel Model Runs". Then renames folder to X.archived
ECHO
ECHO Zipping all files in Z:\Projects\2015_06_002_inc125
ECHO
"C:\Program Files\7-Zip\7z.exe" a -t7z "U:\Archived Travel Model Runs\2015_06_002_inc125.7z" "Z:\Projects\2015_06_002_inc125" -mx9
ECHO
Z:
cd Projects\
ren 2015_06_002_inc125 2015_06_002_inc125.archived
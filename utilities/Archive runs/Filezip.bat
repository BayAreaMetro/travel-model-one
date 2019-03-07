REM Use 7Zip to Zip files in folder "U:\Archived Travel Model Runs" and place the zip archive 
REM in C:\DATA

ECHO
ECHO Zipping all files in C:\Users\bespin\Documents\2035_06_690
ECHO
"C:\Program Files\7-Zip\7z.exe" a -tzip "U:\Archived Travel Model Runs\2030_06_701.7z" "Y:\Projects\2030_06_701" -mx5
ECHO

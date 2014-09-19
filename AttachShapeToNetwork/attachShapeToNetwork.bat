
set CODEDIR=C:\Users\lzorn\Documents\Travel Model One Utilities\AttachShapeToNetwork

:: copy B:\Projects\2010_04_ZZZ.archived\INPUT\hwy\freeflow.net .

python "%CODEDIR%\attachShapeToNetwork.py" -s id -s name -c cityid -c cityname freeflow.NET "G:\Workspace Users\lzorn\PBA_Cities_NAD_1983_UTM_Zone_10N.shp" freeflow_cities.net
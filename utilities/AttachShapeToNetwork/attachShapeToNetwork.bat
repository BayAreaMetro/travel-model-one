
set CODEDIR=%~dp0

:: copy B:\Projects\2010_04_ZZZ.archived\INPUT\hwy\freeflow.net .

python "%CODEDIR%\attachShapeToNetwork.py" -s alpha_id -s name -c cityid -c cityname freeflow.NET "M:\UTIL\Cityshapes\PBA_Cities_NAD_1983_UTM_Zone_10N.shp" freeflow_cities.net

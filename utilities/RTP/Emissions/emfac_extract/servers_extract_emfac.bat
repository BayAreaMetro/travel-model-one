:: run from \\mainmodel\MainModelShare\extract_for_emfac

set SERVER_DIR=\\MODEL2-C\Model2C-Share\Projects

for /d %%f in (

2015_TM151_PPA_09


)    do    (


mkdir %%f
mkdir %%f\hwy\iter3
mkdir %%f\main
mkdir %%f\nonres
mkdir %%f\skims


rem from "\hwy\" directory
copy /y "%SERVER_DIR%\%%f\hwy\iter3\avgload5period.net" %%f\hwy\iter3\avgload5period.net

rem from "\main\" directory
copy /y %SERVER_DIR%\%%f\main\tripsEA.tpp %%f\main\tripsEA.tpp
copy /y %SERVER_DIR%\%%f\main\tripsAM.tpp %%f\main\tripsAM.tpp
copy /y %SERVER_DIR%\%%f\main\tripsMD.tpp %%f\main\tripsMD.tpp
copy /y %SERVER_DIR%\%%f\main\tripsPM.tpp %%f\main\tripsPM.tpp
copy /y %SERVER_DIR%\%%f\main\tripsEV.tpp %%f\main\tripsEV.tpp

rem from "\nonres\" directory
copy /y %SERVER_DIR%\%%f\nonres\tripstrkEA.tpp %%f\nonres\tripstrkEA.tpp
copy /y %SERVER_DIR%\%%f\nonres\tripstrkAM.tpp %%f\nonres\tripstrkAM.tpp
copy /y %SERVER_DIR%\%%f\nonres\tripstrkMD.tpp %%f\nonres\tripstrkMD.tpp
copy /y %SERVER_DIR%\%%f\nonres\tripstrkPM.tpp %%f\nonres\tripstrkPM.tpp
copy /y %SERVER_DIR%\%%f\nonres\tripstrkEV.tpp %%f\nonres\tripstrkEV.tpp

rem from "\skims\" directory
copy /y %SERVER_DIR%\%%f\skims\COM_HWYSKIMEA.tpp %%f\skims\COM_HWYSKIMEA.tpp
copy /y %SERVER_DIR%\%%f\skims\COM_HWYSKIMAM.tpp %%f\skims\COM_HWYSKIMAM.tpp
copy /y %SERVER_DIR%\%%f\skims\COM_HWYSKIMMD.tpp %%f\skims\COM_HWYSKIMMD.tpp
copy /y %SERVER_DIR%\%%f\skims\COM_HWYSKIMPM.tpp %%f\skims\COM_HWYSKIMPM.tpp
copy /y %SERVER_DIR%\%%f\skims\COM_HWYSKIMEV.tpp %%f\skims\COM_HWYSKIMEV.tpp

copy /y %SERVER_DIR%\%%f\skims\HWYSKMEA.tpp %%f\skims\HWYSKMEA.tpp
copy /y %SERVER_DIR%\%%f\skims\HWYSKMAM.tpp %%f\skims\HWYSKMAM.tpp
copy /y %SERVER_DIR%\%%f\skims\HWYSKMMD.tpp %%f\skims\HWYSKMMD.tpp
copy /y %SERVER_DIR%\%%f\skims\HWYSKMPM.tpp %%f\skims\HWYSKMPM.tpp
copy /y %SERVER_DIR%\%%f\skims\HWYSKMEV.tpp %%f\skims\HWYSKMEV.tpp

)

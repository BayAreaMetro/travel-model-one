:: SetPath.bat
:: Utility to set the path.  Used in RunModel as well as RunMain and RunNodeX. 
echo %SOFTWARE_DIR%
call %MODEL_DIR%\Set_Software_Dr.cmd
echo %SOFTWARE_DIR%
:: The commpath
SET COMMPATH=%SOFTWARE_DIR%\COMMPATH
::if "%COMPUTER_PREFIX%" == "WIN-" (  SET COMMPATH=D:\COMMPATH)
::if %computername%==MODEL2-A      (  set COMMPATH=E:\Model2A-Share\COMMPATH)
::if %computername%==MODEL2-B      (  set COMMPATH=E:\Model2B-Share\COMMPATH)
::if %computername%==MODEL2-C      (  set COMMPATH=E:\Model2C-Share\COMMPATH)
::if %computername%==MODEL2-D      (  set COMMPATH=E:\Model2D-Share\COMMPATH)

:: The location of the 64-bit java development kit
set JAVA_PATH=%SOFTWARE_DIR%\jdk1.8.0_162

:: The location of the GAWK binary executable files
set GAWK_PATH=%SOFTWARE_DIR%\GnuWin32
::if "%COMPUTER_PREFIX%" == "WIN-" (
::  set GAWK_PATH=%MODEL_DIR%\Software\R\GnuWin32
::)

:: The location of R and R libraries
set R_HOME=%SOFTWARE_DIR%\R-4.0.4\bin\x64
set R_LIB=%SOFTWARE_DIR%\4.0
::if "%COMPUTER_PREFIX%" == "WIN-" (
::  set R_LIB=%MODEL_DIR%\Software\R\4.0
::)

:: The location of the RUNTPP executable from Citilabs
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;%SOFTWARE_DIR%\VoyagerFileAPI

:: The location of python
set PYTHON_PATH=%SOFTWARE_DIR%\user_py27

:: The location of the MTC.JAR file
set RUNTIME=CTRAMP/runtime

:: Add these variables to the PATH environment variable, moving the current path to the back
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin;%PYTHON_PATH%;%R_HOME%;%PATH%

::  Set the Java classpath (locations where Java needs to find configuration and JAR files)
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar


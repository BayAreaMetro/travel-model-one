:: SetPath.bat
:: Utility to set the path.  Used in RunModel as well as RunMain and RunNodeX. 

:: The commpath
@REM SET COMMPATH=X:\COMMPATH
SET COMMPATH=C:\mtc_transit_2050\TM15_initial_setup\2015_TM152_IPA_19_run_dir
if "%COMPUTER_PREFIX%" == "WIN-" (  SET COMMPATH=D:\COMMPATH)
if %computername%==MODEL2-A      (  set COMMPATH=E:\Model2A-Share\COMMPATH)
if %computername%==MODEL2-B      (  set COMMPATH=E:\Model2B-Share\COMMPATH)
if %computername%==MODEL2-C      (  set COMMPATH=E:\Model2C-Share\COMMPATH)
if %computername%==MODEL2-D      (  set COMMPATH=E:\Model2D-Share\COMMPATH)
if %computername%==MODEL3-A      (  set COMMPATH=E:\Model3A-Share\COMMPATH)
if %computername%==MODEL3-B      (  set COMMPATH=E:\Model3B-Share\COMMPATH)
if %computername%==MODEL3-C      (  set COMMPATH=E:\Model3C-Share\COMMPATH)
if %computername%==MODEL3-D      (  set COMMPATH=E:\Model3D-Share\COMMPATH)

:: The location of the 64-bit java development kit
set JAVA_PATH=C:\Program Files\Java\jdk1.8.0_181

:: The location of the GAWK binary executable files
set GAWK_PATH=C:\mtc_transit_2050\TM15_initial_setup\util\gawk
if "%COMPUTER_PREFIX%" == "WIN-" (
  set GAWK_PATH=C:\Software\Gawk
)

:: The location of R and R libraries
@REM set R_HOME=C:\Program Files\R\R-3.5.2
set R_HOME=C:\Program Files\R\R-4.3.1
set R_LIB=C:\Users\david.hensle\AppData\Local\R\win-library\4.3
if "%COMPUTER_PREFIX%" == "WIN-" (
  set R_LIB=C:\Users\Administrator\Documents\R\win-library\3.5
)
if "%computername%" == "MODEL3-A" (
  set R_HOME=C:\Program Files\R\R-4.2.1
  set R_LIB=C:\Users\mtcpb\AppData\Local\R\win-library\4.2
)
if "%computername%" == "MODEL3-B" (
  set R_HOME=C:\Program Files\R\R-4.2.1
  set R_LIB=C:\Users\mtcpb\AppData\Local\R\win-library\4.2
)
if "%computername%" == "MODEL3-C" (
  set R_HOME=C:\Program Files\R\R-4.2.1
  set R_LIB=C:\Users\mtcpb\AppData\Local\R\win-library\4.2
)
if "%computername%" == "MODEL3-D" (
  set R_HOME=C:\Program Files\R\R-4.2.1
  set R_LIB=C:\Users\mtcpb\AppData\Local\R\win-library\4.2
)

:: The location of the RUNTPP executable from Citilabs
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerAPI\Dlls\x64

:: The location of the MTC.JAR file
set RUNTIME=CTRAMP/runtime

::  Set the Java classpath (locations where Java needs to find configuration and JAR files)
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar

:: The location of Anaconda; this run will use the conda environment tm15-python310
set CONDA_PATH=C:\ProgramData\Anaconda3;C:\ProgramData\Anaconda3\Library\mingw-w64\bin;C:\ProgramData\Anaconda3\Library\usr\bin;C:\ProgramData\Anaconda3\Library\bin;C:\ProgramData\Anaconda3\Scripts;C:\ProgramData\Anaconda3\bin;C:\ProgramData\Anaconda3\condabin
set ENV_NAME=tm15-python310

:: Add these variables to the PATH environment variable, moving the current path to the back
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin;%CONDA_PATH%

:: Activate the correct conda environment -- this will update the PATH
call activate %ENV_NAME%



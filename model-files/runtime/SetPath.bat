:: SetPath.bat
:: Utility to set the path.  Used in RunModel as well as RunMain and RunNodeX. 

:: The commpath
SET COMMPATH=E:\projects\clients\solanoNapa\SNABM\2015_TM151_PPA_V1
if "%COMPUTER_PREFIX%" == "WIN-" (
  SET COMMPATH=E:\projects\clients\solanoNapa\SNABM
)

:: The location of the 64-bit java development kit
set JAVA_PATH=C:\Program Files\Java\jre1.8.0_171

:: The location of the GAWK binary executable files
set GAWK_PATH=E:\projects\clients\solanoNapa\SNABM\util
if "%COMPUTER_PREFIX%" == "WIN-" (
  set GAWK_PATH=C:\Software\Gawk
)

:: The location of R and R libraries
set R_HOME=C:\Program Files\R\R-3.4.0
set R_LIB=C:/Users/joel.freedman/Documents/R/win-library/3.4
if "%COMPUTER_PREFIX%" == "WIN-" (
  set R_LIB=C:/Users/Administrator/Documents/R/win-library/3.4
)

:: The location of the RUNTPP executable from Citilabs
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI

:: The location of python
set PYTHON_PATH=e:\anaconda2

:: The location of the MTC.JAR file
set RUNTIME=CTRAMP/runtime

:: Add these variables to the PATH environment variable, moving the current path to the back
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin;%PYTHON_PATH%

::  Set the Java classpath (locations where Java needs to find configuration and JAR files)
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar


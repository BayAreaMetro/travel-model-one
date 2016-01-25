:: SetPath.bat
:: Utility to set the path.  Used in RunModel as well as RunMain and RunNodeX. 

:: The location of the 64-bit java development kit
set JAVA_PATH=C:\Program Files\Java\jdk1.7.0_71

:: The location of the GAWK binary executable files
set GAWK_PATH=M:\UTIL\Gawk

:: The location of R
set R_HOME=C:\Program Files\R\R-3.2.3

:: The location of the RUNTPP executable from Citilabs
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI;C:\Program Files (x86)\Citilabs\CubeVoyager

:: The location of python
set PYTHON_PATH=C:\Python27

:: The location of the MTC.JAR file
set RUNTIME=CTRAMP/runtime

:: Add these variables to the PATH environment variable, moving the current path to the back
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin;%PYTHON_PATH%

::  Set the Java classpath (locations where Java needs to find configuration and JAR files)
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar


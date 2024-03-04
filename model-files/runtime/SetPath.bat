:: SetPath.bat
:: Utility to set the path.  Used in RunModel as well as RunMain and RunNodeX. 

:: The commpath
SET COMMPATH=%CD%
if "%COMPUTER_PREFIX%" == "WIN-" (
  SET COMMPATH=D:\COMMPATH
)

:: The location of the 64-bit java development kit
set JAVA_PATH=C:\Program Files\Java\jdk1.8.0_181

:: The location of the GAWK binary executable files
set GAWK_PATH=Z:\RTP2025_PPA\code\TM151\travel-model-one\utilities\gawk
if "%COMPUTER_PREFIX%" == "WIN-" (
  set GAWK_PATH=C:\Software\Gawk
)

:: The location of R and R libraries
set R_HOME=C:\Program Files\R\R-4.3.2
if %computername%==azmdlppw06          set R_HOME=C:\Program Files\R\R-4.3.1
if %computername%==azmdlppw07          set R_HOME=C:\Program Files\R\R-4.3.1
if %computername%==azmdlppw08          set R_HOME=C:\Program Files\R\R-4.3.2
if %computername%==azmdlppw09          set R_HOME=C:\Program Files\R\R-4.3.2
if %computername%==AZMDLPPW10          set R_HOME=C:\Program Files\R\R-4.3.2
if %computername%==AZMDLPPW11          set R_HOME=C:\Program Files\R\R-4.3.2
if %computername%==AZMDLPPW12          set R_HOME=C:\Program Files\R\R-4.3.2
if %computername%==AZMDLPPW13          set R_HOME=C:\Program Files\R\R-4.3.2
if %computername%==MODEL-GRTM          set R_HOME=C:\Program Files\R\R-4.3.1
@REM set R_LIB=C:\Users\david.hensle\AppData\Local\R\win-library\4.3
set R_LIB=C:\Users\%username%\AppData\Local\R\win-library\4.3
if "%COMPUTER_PREFIX%" == "WIN-" (
  set R_LIB=C:/Users/Administrator/Documents/R/win-library/3.5
)

:: The location of the RUNTPP executable from Citilabs
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerAPI\Dlls\x64

:: The location of python
::set PYTHON_PATH=C:\Python27

:: The location of the MTC.JAR file
set RUNTIME=CTRAMP/runtime

:: The location of Anaconda; this run will use the conda environment tm15-python310
set CONDA_PATH=C:\ProgramData\Anaconda3;C:\ProgramData\Anaconda3\Library\mingw-w64\bin;C:\ProgramData\Anaconda3\Library\usr\bin;C:\ProgramData\Anaconda3\Library\bin;C:\ProgramData\Anaconda3\Scripts;C:\ProgramData\Anaconda3\bin;C:\ProgramData\Anaconda3\condabin
set ENV_NAME=tm151-python27

:: Add these variables to the PATH environment variable, moving the current path to the back
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin;%CONDA_PATH%

::  Set the Java classpath (locations where Java needs to find configuration and JAR files)
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar

:: Activate the correct conda environment -- this will update the PATH
call activate %ENV_NAME%

:: Deactivating and re-activating seems necessary for the python 2 env to work correctly..
call conda deactivate
call activate %ENV_NAME%
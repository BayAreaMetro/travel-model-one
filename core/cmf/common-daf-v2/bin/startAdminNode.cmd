@echo off
REM 'BASEDIR' should be set as an environment variable local to users machine
REM and should be the path to the common-base, common-daf-v2 and common-daf-v2-tests
REM modules.  The following lines will check for the existence of this variable.
REM If not set, it will exit and the command will not be run.

if "%BASEDIR%"=="" goto errorMustExit

set LOGFILE=%BASEDIR%/common-base/config/info_logging.properties

set CLASSPATH=%BASEDIR%/common-base/build/classes;
set CLASSPATH=%CLASSPATH%;%BASEDIR%/common-daf-v2/build/classes;
set CLASSPATH=%CLASSPATH%;%BASEDIR%/common-daf-v2-tests/config

java -Djava.util.logging.config.file=%LOGFILE% -DnodeName=adminNode com.pb.common.daf.admin.StartAdminNode
goto end

:errorMustExit
echo The BASEDIR environment variable MUST be set before running this command.
echo This variable should point to a directory containing these projects:
echo    common-base
echo    common-daf-v2
echo    common-dav-v2-tests
echo Example: set BASEDIR=c:/files/workspace
:end
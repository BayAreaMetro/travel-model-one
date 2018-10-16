@echo off
rem
rem --- Runs the LogServerTest class ---
rem
rem Environment variable REPOSITORY_DIR must be set or set it in this file
rem

set classpath=%REPOSITORY_DIR%\cmf\common-base\build\classes
set classpath=%classpath%;%REPOSITORY_DIR%\third-party\logging-log4j-1.2.9\log4j-1.2.9.jar

java com.pb.common.logging.LogServerTest
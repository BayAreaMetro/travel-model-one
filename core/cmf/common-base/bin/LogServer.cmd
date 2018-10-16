@echo off
rem
rem --- Starts a LogServer in a separate VM ---
rem
rem Environment variable REPOSITORY_DIR must be set
rem

set classpath=%REPOSITORY_DIR%\cmf\common-base\build\classes
set classpath=%classpath%;%REPOSITORY_DIR%\third-party\logging-log4j-1.2.9\log4j-1.2.9.jar

java com.pb.common.logging.LogServer
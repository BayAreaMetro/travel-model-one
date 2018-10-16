@echo off
rem
rem --- Runs the ClassFileServer class ---
rem
rem Environment variable REPOSITORY_DIR must be set or set it in this file
rem

rem set REPOSITORY_DIR=C:/subversion

set classpath=%REPOSITORY_DIR%\cmf\common-base\build\classes

java -classpath %REPOSITORY_DIR%\cmf\common-base\build\classes com.pb.common.http.ClassFileServerTest
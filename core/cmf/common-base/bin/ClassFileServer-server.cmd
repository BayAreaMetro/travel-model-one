@echo off
rem
rem --- Runs the ClassFileServer class ---
rem
rem Environment variable REPOSITORY_DIR must be set or set it in this file
rem

rem set REPOSITORY_DIR=C:/subversion

set classpath=%REPOSITORY_DIR%\cmf\common-base\build\classes

rem Remove class files so they are not in the classpath of the ClassFileLoader
xcopy %REPOSITORY_DIR%\cmf\common-base\build\classes\com\pb\common\http\SimpleClass.class %TMP%\com\pb\common\http\SimpleClass.class
xcopy %REPOSITORY_DIR%\cmf\common-base\build\classes\com\pb\common\http\Dependency.class %TMP%\com\pb\common\http\Dependency.class
del %REPOSITORY_DIR%\cmf\common-base\build\classes\com\pb\common\http\SimpleClass.class
del %REPOSITORY_DIR%\cmf\common-base\build\classes\com\pb\common\http\Dependency.class

rem %TMP% folder contains SimpleClass.class
java com.pb.common.http.ClassFileServer 2001 %TMP%
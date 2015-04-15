::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: psexec_helper.bat
::
:: USAGE: psexec_helper.bat MODELDIR CMDFILE
::
:: This helps with starting java nodes using psexec.exe.
::
:: When first starting up a command line process on the remote server, the remote server doesn't know about
:: the M: drive.  This script assists by mounting it, going to the correct directory and running the appropriate
:: command.
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

set MODELDIR=%~1
set CMDFILE=%2

net use M: \\MAINMODEL\MAINMODELSHARE

M:
cd %MODELDIR%
echo Going to call %CMDFILE%

call %CMDFILE%

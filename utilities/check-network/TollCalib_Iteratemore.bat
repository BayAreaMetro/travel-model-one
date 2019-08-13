:: ------------------------------------------------------------------------------------------------------
:: 
:: This batch file calls TollCalib_RunModel.bat multiple times
:: assuming all the paths are set by TollCalib_Iterate.bat
::
:: ------------------------------------------------------------------------------------------------------

set ITER=10
call TollCalib_RunModel

set ITER=11
call TollCalib_RunModel

set ITER=12
call TollCalib_RunModel

set ITER=13
call TollCalib_RunModel

set ITER=14
call TollCalib_RunModel

set ITER=15
call TollCalib_RunModel
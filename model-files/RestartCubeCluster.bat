:: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RestartCubeCluster
::
:: MS-DOS batch file that re-starts Cube Cluster.  The ping statements
:: give Cluster time to re-start before the model stream continues.
::
:: 2011 11 04 dto
::
:: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

rem Close cluster and then kill the executable
start Cluster M:\COMMPATH\CTRAMP 1-16 Close Exit
call Taskkill/IM Cluster.exe /F

rem  Re-start cluster
start Cluster M:\COMMPATH\CTRAMP 1-16 Start

rem  Delay to give cluster time to start with ping calls
ping 192.168.1.200 -n 8
ping 192.168.1.201 -n 8
ping 192.168.1.202 -n 8
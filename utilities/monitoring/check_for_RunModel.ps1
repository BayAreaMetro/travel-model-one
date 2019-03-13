#
# Run from Task Scheduler as
#
# C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
#
# -NoProfile -Executionpolicy bypass -file "\\model2-d\Model2D-Share\UTIL\check_for_RunModel.ps1"
#
#

# get hostname to get drive
$my_hostname = (Get-WmiObject -Class Win32_ComputerSystem -Property Name).Name
$my_drive = $env:TEMP
if ($my_hostname -eq 'MODEL2-A') { $my_drive = '\\model2-a\Model2A-Share'}
if ($my_hostname -eq 'MODEL2-B') { $my_drive = '\\model2-b\Model2B-Share'}
if ($my_hostname -eq 'MODEL2-C') { $my_drive = '\\model2-c\Model2C-Share'}
if ($my_hostname -eq 'MODEL2-D') { $my_drive = '\\model2-d\Model2D-Share'}

# print the date to make sure this is triggering at all
date > $my_drive\UTIL\RunModelStatus.txt

# print info about me (for debugging)
# [System.Security.Principal.WindowsIdentity]::GetCurrent().Name >> \\model2-d\Model2D-Share\UTIL\RunModelStatus.txt
#

# print all cmd process information
# Get-Process -Name cmd | Format-List -Property Id,Name,CPU,mainWindowTitle >> $my_drive\UTIL\RunModelStatus.txt
#

# print the process information
Get-Process -Name cmd | where {$_.mainWindowTitle -match "(test|run|resume|calibrate)model(.bat)?$"} | Format-List -Property Id,Name,CPU,mainWindowTitle >> $my_drive\UTIL\RunModelStatus.txt

# lets look up the children
$p = Get-Process -Name cmd | where {$_.mainWindowTitle -match "(test|run|calibrate)model(.bat)?$"}
if ($p.Count -ne 1) {
  exit
}
$children = (gwmi win32_process | ? parentprocessid -eq $p.Id)
Write-Output $children.Count >> $my_drive\UTIL\RunModelStatus.txt
if ($children.Count -gt 0) {
  Write-Output $children.Name >> $my_drive\UTIL\RunModelStatus.txt
}

# print the date again to make sure it did not crash
date >> $my_drive\UTIL\RunModelStatus.txt
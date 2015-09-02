:: batch file to fetch the activitysim build
set TARGET_DIR="M:\Development\Travel Model One\Accessibility\accessibility-activitysim\_working"
set ASIM_DIR="D:\files\GitHub\activitysim"

:: copy files
:: copy %ASIM_DIR%\*.* %TARGET_DIR%\activitysim\*.*

:: build python
set path=C:\Users\dory\AppData\Local\Continuum\Anaconda;C:\Users\dory\AppData\Local\Continuum\Anaconda\Scripts
cd %TARGET_DIR%\activitysim
call conda install --channel synthicity --channel jiffyclub activitysim

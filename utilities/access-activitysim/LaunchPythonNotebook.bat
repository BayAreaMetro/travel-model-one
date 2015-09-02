@echo off
set ANACONDA=C:\Users\dory\AppData\Local\Continuum\Anaconda
set path=%ANACONDA%;%ANACONDA%\Scripts
set PYTHONPATH=%ANACONDA%\Lib\site-packages;%ANACONDA%\Lib;%pythonpath%
start python.exe -c "import sys; from IPython.html.notebookapp import launch_new_instance; sys.exit(launch_new_instance())" %*
exit /B %ERRORLEVEL%

Experimental setup for monitoring Travel Model runs

On Modeling Machine
===================

Create a task in Task Scheduler to run the [check_for_RunModel.ps1](check_for_RunModel.ps1) powershell script

* General
  * Name: Check for RunModel
  * Description: Check if there's a cmd.exe running with the main window title that matches a run model pattern; print info about that to `\\model2-[abcd]\Model2[ABCD]-Share\UTIL\RunModelStatus.txt`
  * Security options:
    * When running the task, use the following user account: _runmodel user_
    * Run only when user is logged in (I found that doign otherwise doesn't give access to window titles)
    * Run with highest privileges
* Triggers
  * Daily, start whenever and Recur every: 1 days
  * Repeat task every: 10 minutes for a duration of: 1 day
  * Enabled
* Actions
  * Action: Start a program
  * Program/script: `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`
  * Add arguments (optional): `-NoProfile -Executionpolicy bypass -file "\\model2-[abcd]\Model2[ABCD]-Share\\UTIL\check_for_RunModel.ps1"`
* Conditions
  * Left as default: Start the task only if the computer is on AC power, Stop if the computer switches to battery power
* Settings
  * Allow the task to be run on demand
  * Stop the task if it runs longer than: 1 hour
  * If the running task does not end when requested, force it to stop
  * If the task is already running, then the following rule applies: Do not start a new instance

On Monitoring Machine
=====================

This machine must have access to the modeling machines shared drive, as well as access to the internet.
It must also have access to the `WEBHOOK_URL_FILE` in `travel_model_monitor.py`

* Run [travel_model_monitor.py](travel_model_monitor.py)

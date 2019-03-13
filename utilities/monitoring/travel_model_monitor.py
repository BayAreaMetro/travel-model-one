USAGE = """

Travel Model Monitor

This script will poll Travel Model states and post state changes to our slack channel via the 
Travel Model 1.5 Slack App (https://api.slack.com/apps/AGWEM7CF5)

"""

import argparse, datetime, os, re, sys, time
import requests

SLACK_WEBHOOK_URL_FILE = "M:\Software\Slack\TravelModel_SlackWebhook.txt"
SLACK_WEBHOOK_URL      = None # will be read
MODEL_MACHINES = {
    "model2-a" : "\\\\model2-a\Model2A-Share\UTIL",
    "model2-b" : "\\\\model2-b\Model2B-Share\UTIL",
    "model2-c" : "\\\\model2-c\Model2C-Share\UTIL",
    "model2-d" : "\\\\model2-d\Model2D-Share\UTIL"
}

STATE_Uninitialized, STATE_NoStatusFile, STATE_InvalidStatusFile, STATE_StaleStatusFile, STATE_NoModelsRunning, STATE_ModelRunning = range(6)


def post_message(message):
    """
    Posts the given message to the slack channel via the webhook if SLACK_WEBHOOK_URL
    Also prints to console
    """
    headers  = { 'Content-type':'application/json'}
    data     = '{"text":"' + message + '"}'
    if SLACK_WEBHOOK_URL:
        response = requests.post(SLACK_WEBHOOK_URL, headers=headers, data=data)

    print("*** {}".format(message))
    print("")

def check_model_status(machine):
    """
    Checks the model status via the status file.  Returns dictionary
    { "STATE"            : state code,
      "status_time"      : datetime of status,
      "error"            : error message
      "main_window_title": title of window running model
      "num_children"     : number of child processes
      "child_procs"      : list of those child processes
    }
    """
    return_dict = {}

    print("Checking model status for {}".format(machine))
    status_file = os.path.join(MODEL_MACHINES[machine], "RunModelStatus.txt")
    if not os.path.exists(status_file):
        print("  Status file {} not found".format(status_file))
        return_dict["STATE"] = STATE_NoStatusFile
        return return_dict

    f = open(status_file, 'rb')
    status_file_text = f.read().decode('utf-16')
    f.close()

    # split into lines
    status_lines = status_file_text.splitlines()
    print("  Read {} lines from {}:".format(len(status_lines), status_file))

    # skip blanks
    while ((len(status_lines) > 0) and status_lines[0]==""): status_lines.pop(0)

    # first, expect date, e.g. Wednesday, March 13, 2019 12:30:00 PM
    status_time_str = status_lines.pop(0)
    try:
        status_time = datetime.datetime.strptime(status_time_str, "%A, %B %d, %Y %I:%M:%S %p")
    except:
        return_dict["STATE"] = STATE_InvalidStatusFile
        return_dict["error"] = "Couldn't parse status time from {}".format(status_lines[0])
        return return_dict

    print("  Status time: {}".format(status_time))
    return_dict["status_time"] = status_time
    status_age = datetime.datetime.now() - status_time
    # stale means 12 minutes or older
    if status_age.total_seconds() > 12*60:
        return_dict["STATE"] = STATE_StaleStatusFile
        return_dict["error"] = "Status file is stale: {}".format(status_time_str)
        return return_dict

    # skip blanks
    while ((len(status_lines) > 0) and status_lines[0]==""): status_lines.pop(0)

    # if no other lines - no model run found
    if len(status_lines) == 0:
        return_dict["STATE"] = STATE_NoModelsRunning
        return return_dict

    # next lines: Id, Name, CPU, MainWindowTitle
    status_lines.pop(0) # Id
    status_lines.pop(0) # Name
    status_lines.pop(0) # CPU

    main_window_title_str = status_lines.pop(0)
    if not main_window_title_str.startswith("MainWindowTitle :"):
        return_dict["STATE"] = STATE_InvalidStatusFile
        return_dict["error"] = "Couldn't find/parse MainwindowTitle from {}".format(main_window_title_str)
        return return_dict

    main_window_title_str = main_window_title_str[18:]
    print("  Main window title: {}".format(main_window_title_str))
    return_dict["main_window_title"] = main_window_title_str

    # skip blanks
    while ((len(status_lines) > 0) and status_lines[0]==""): status_lines.pop(0)

    num_children_str = status_lines.pop(0)
    num_children     = int(num_children_str)
    child_procs      = status_lines[:num_children]
    status_lines     = status_lines[num_children:]

    print("  {} children: {}".format(num_children, child_procs))
    return_dict["STATE"]        = STATE_ModelRunning
    return_dict["num_children"] = num_children
    return_dict["child_procs"]  = child_procs

    return return_dict


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("--no_slack", action="store_true", help="Don't post to slack")
    parser.add_argument("--quiet_startup", action="store_true", help="Skip the startup messages -- assume it was just running")
    args = parser.parse_args()

    if args.no_slack:
        print("Running without posting to slack")
    else:
        f = open(SLACK_WEBHOOK_URL_FILE)
        SLACK_WEBHOOK_URL = f.read()
        f.close()
        print("Read slack webhook URL: {}".format(SLACK_WEBHOOK_URL))

    if args.quiet_startup:
        pass #  ssssh
    else:
        msg = "Travel Model Monitor Starting on {}".format(os.environ["COMPUTERNAME"])
        post_message(msg)

    # keep the machine states here
    machine_state_dict = {}
    for machine_name in MODEL_MACHINES.keys():
        machine_state_dict[machine_name] = {"STATE":STATE_Uninitialized}

    while True:
        # check on everybody
        print("Awake @ {}".format(datetime.datetime.now()))
        for machine_name in MODEL_MACHINES.keys():
            state_dict = check_model_status(machine_name)

            # if it didn't change state, don't report -- just save update
            if state_dict["STATE"] == machine_state_dict[machine_name]["STATE"]:
                print("=> No state change")
                machine_state_dict[machine_name] = state_dict
                continue

            # if quiet startup and it changed state from initial -- just save update
            if args.quiet_startup and (machine_state_dict[machine_name]["STATE"] == STATE_Uninitialized):
                print("=> Quiet startup")
                machine_state_dict[machine_name] = state_dict
                continue

            # state changed -- report update
            msg = "*{}*: ".format(machine_name)
            if machine_state_dict[machine_name]["STATE"] == STATE_Uninitialized:
                msg += "Initial state -- "

            if state_dict["STATE"] == STATE_NoStatusFile:
                msg += "No status file -- setup Task Scheduler?"

            elif state_dict["STATE"] == STATE_InvalidStatusFile:
                msg += "Invalid status file.  Error: {}".format(state_dict["error"])

            elif state_dict["STATE"] == STATE_StaleStatusFile:
                msg += state_dict["error"]

            elif state_dict["STATE"] == STATE_NoModelsRunning:
                msg += "No model is running as of {}".format(state_dict["status_time"])

            elif state_dict["STATE"] == STATE_ModelRunning:
                msg += "Model appears to be :woman-running: as of {}. *{}* has {} children: {}".format(
                            state_dict["status_time"],  state_dict["main_window_title"],
                            state_dict["num_children"], state_dict["child_procs"])
            # post the message
            post_message(msg)

            # save state
            machine_state_dict[machine_name] = state_dict


        # sleep 5 minutes
        print("")
        time.sleep(5*60)

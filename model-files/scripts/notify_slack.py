USAGE = """

Notify slack of model run status

"""

import argparse, os, socket, sys
import json,requests

def post_message(message):
    """
    Posts the given message to the slack channel via the webhook if SLACK_WEBHOOK_URL
    Also prints to console
    """
    hostname = socket.getfqdn()
    instance = os.environ['INSTANCE']
    if hostname.endswith(".mtc.ca.gov"):
        SLACK_WEBHOOK_URL_FILE = "M:\Software\Slack\TravelModel_SlackWebhook.txt"
        print("Running on mtc host; using {}".format(SLACK_WEBHOOK_URL_FILE))
    else:
        SLACK_WEBHOOK_URL_FILE = "C:\Software\Slack\TravelModel_SlackWebhook.txt"
        print("Running on non-mtc host; using {}".format(SLACK_WEBHOOK_URL_FILE))

    SLACK_WEBHOOK_URL      = None # will be read
    f = open(SLACK_WEBHOOK_URL_FILE)
    SLACK_WEBHOOK_URL = f.read()
    f.close()
    print("Read slack webhook URL: {}".format(SLACK_WEBHOOK_URL))

    headers  = { 'Content-type':'application/json'}
    data     = { "text": message }
    if SLACK_WEBHOOK_URL:
        response = requests.post(SLACK_WEBHOOK_URL, headers=headers, json=data)

    full_message = f"*{instance}*: {message}"
    print("*** {}".format(full_message))
    print("response: {}".format(response))
    print("")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument("message", type=str, help="The message to send")
    args = parser.parse_args()

    post_message(args.message)
    # that's all
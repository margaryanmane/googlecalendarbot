from flask import Flask, request, make_response, Response, render_template
import os
import json
import requests
import slack
from slackeventsapi import SlackEventAdapter

from settings import *
from gcalendar import get_auth_url, set_auth_token, calendar_usage, schedule_event

app = Flask(__name__, static_url_path='/static')

app.debug = True


SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

USER_OAUTH_ACCESS_TOKEN = os.getenv("USER_OAUTH_ACCESS_TOKEN")
slack_client = slack.WebClient(USER_OAUTH_ACCESS_TOKEN)


@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    command_text = message.get('text').split()
    command = command_text and command_text[1] or ''
    channel = message["channel"]
    user = message["user"]
    attachments = ""
    response = ""

    team = event_data["team_id"]
    home_dir = os.getcwd()
    credential_dir = os.path.join(home_dir, 'user_credentials')
    credential_path = os.path.join(credential_dir, 'tokens.json')
    with open(credential_path) as json_file:
        try:
            all_team_data = json.load(json_file)
        except json.decoder.JSONDecodeError:
            all_team_data = []

    access_token = USER_OAUTH_ACCESS_TOKEN
    for team_data in all_team_data:
        if team_data['team_id'] == team:
            access_token = team_data["access_token"]

    slack_client = slack.WebClient(access_token)

    if command.startswith("token"):
        store_status = set_auth_token(user, command_text[2].strip())
        if store_status is None:
            response = "You must first start the authorization process with  @gcalendar reauth command."
        elif store_status == -1:
            response = "The authentication token you sent is wrong."
        elif store_status == 0:
            response = "Authentication successful!You can now communicate with @gcalendar."
    elif command.startswith("reauth"):
        response = f'Go throw this url {get_auth_url(user)}'
    else:
        if command in ['token', 'reauth', 'free_event', 'scheduled']:
            if command == "scheduled":
                response = "Here are your upcoming events: "
                attachments = calendar_usage(user, command)
            elif command == "free_event":
                response = calendar_usage(user, command)
    if command in ['token', 'reauth', 'free_event', 'scheduled']:
        slack_client.chat_postMessage(channel=channel, text=response, attachments=attachments)

    if command == 'schedule_event':
        callback_id = 'set_calendar_event'
        slack_client.chat_postMessage(
            as_user=True,
            channel=channel,
            text="Hi I'm google calendar bot",
            attachments=[{
                "text": "",
                "callback_id": callback_id,
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [{
                    "name": "schedule_event",
                    "text": "Schedule Event",
                    "type": "button",
                    "value": "schedule_event"
                }]
            }]
        )


@app.route("/", methods=["GET"])
def message_index():

    return render_template('index.html')


@app.route("/slack/install", methods=["GET"])
def message_install():
    client_id = os.environ["SLACK_CLIENT_ID"]
    client_secret = os.environ["SLACK_CLIENT_SECRET"]

    code = request.args.get('code')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    url = 'https://slack.com/api/oauth.v2.access'
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code
    }
    response = requests.post(url, payload, headers=headers)
    data = json.loads(response.text)
    home_dir = os.getcwd()
    credential_dir = os.path.join(home_dir, 'user_credentials')
    credential_path = os.path.join(credential_dir, 'tokens.json')
    team_data = dict(
        team=data['team']['name'],
        team_id=data['team']['id'],
        access_token=data['access_token']
    )

    with open(credential_path) as json_file:
        try:
            all_team_data = json.load(json_file)
        except json.decoder.JSONDecodeError:
            all_team_data = []

    all_team_data.append(team_data)
    with open(credential_path, 'w') as outfile:
        json.dump(all_team_data, outfile)

    return render_template('success.html', title=code)


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    message_action = json.loads(request.form["payload"])
    user_id = message_action["user"]["id"]
    callback_id = 'set_calendar_event'

    team = message_action["team"]["id"]
    home_dir = os.getcwd()
    credential_dir = os.path.join(home_dir, 'user_credentials')
    credential_path = os.path.join(credential_dir, 'tokens.json')
    with open(credential_path) as json_file:
        try:
            all_team_data = json.load(json_file)
        except json.decoder.JSONDecodeError:
            all_team_data = []

    access_token = USER_OAUTH_ACCESS_TOKEN
    for team_data in all_team_data:
        if team_data['team_id'] == team:
            access_token = team_data["access_token"]

    slack_client = slack.WebClient(access_token)

    if message_action["type"] == "interactive_message":
        slack_client.dialog_open(
            trigger_id=message_action["trigger_id"],
            dialog={
                "title": "Schedule An Event",
                "submit_label": "Submit",
                "callback_id": callback_id,
                "elements": [
                    {
                        "label": "Event Title",
                        "type": "text",
                        "name": "title",
                        "placeholder": "Event Title",
                    },
                    {
                        "label": "Start datetime",
                        "type": "text",
                        "name": "start_date",
                        "placeholder": "Start datetime",
                    },
                    {
                        "label": "End datetime",
                        "type": "text",
                        "name": "end_date",
                        "placeholder": "End datetime",
                    },
                    {
                        "label": "Event Attendees emails",
                        "type": "text",
                        "subtype": "email",
                        "name": "attendees",
                        "placeholder": "Event attendees emails write with spaces",
                    },
                ]
            }
        )

    elif message_action["type"] == "dialog_submission":
        schedule_event(message_action['submission'], user_id)
        slack_client.chat_postMessage(channel=message_action['channel']['id'], text='Event has been added successfully')

    return make_response("", 200)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=os.getenv("PORT"))



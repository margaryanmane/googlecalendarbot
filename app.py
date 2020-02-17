import os
from flask import Flask
from redis import Redis
from slackclient import SlackClient
from slackeventsapi import SlackEventAdapter

from settings import *
from gcalendar import get_auth_url, set_auth_token, calendar_usage

redis = Redis(host='redis', port=6379)

app = Flask(__name__)

app.debug = True


SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

USER_OAUTH_ACCESS_TOKEN = os.getenv("USER_OAUTH_ACCESS_TOKEN")
slack_client = SlackClient(USER_OAUTH_ACCESS_TOKEN)


@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    command_text = message.get('text').split()
    command = command_text[1]
    channel = message["channel"]
    user = message["user"]
    attachments = ""
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
            elif command == "free_time":
                response = calendar_usage(user, command)
    if command in ['token', 'reauth', 'free_event', 'scheduled']:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, attachments=attachments)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)



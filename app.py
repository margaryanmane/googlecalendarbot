import os
from flask import Flask
from redis import Redis
from slackclient import SlackClient
from slackeventsapi import SlackEventAdapter

from settings import *

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
    if message.get("subtype") is None and "calendar" in message.get('text'):
        channel = message["channel"]
        send_message = "<@%s>" % message["user"]
        x = slack_client.api_call("chat.postMessage", channel=channel, text=send_message)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)



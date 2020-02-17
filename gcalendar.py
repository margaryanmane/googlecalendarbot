import os
from os import path
import datetime
import httplib2
import pickle
from apiclient import discovery
import oauth2client
from oauth2client import client

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

FLOW_MAP = {}

CLIENT_SECRET_FILE = 'credentials.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'


def get_credentials(user):
    home_dir = os.getcwd()
    credential_dir = os.path.join(home_dir, 'user_credentials')
    credential_path = os.path.join(credential_dir, 'calendar-python-quickstart-' + user + '.json')
    if path.exists(credential_path):
        with open(credential_path, 'rb') as config_dictionary_file:
            config = pickle.load(config_dictionary_file)

        return config['credentials']
    else:
        return None


def get_auth_url(user):
    existing_flow = FLOW_MAP.get(user)
    if existing_flow is None:
        flow = client.flow_from_clientsecrets(filename=CLIENT_SECRET_FILE, scope=SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob")
        flow.user_agent = APPLICATION_NAME
        auth_url = flow.step1_get_authorize_url()
        FLOW_MAP[user] = flow
        return auth_url
    else:
        return existing_flow.step1_get_authorize_url()


def set_auth_token(user, token):
    flow = FLOW_MAP.get(user)
    if flow is not None:
        try:
            credentials = flow.step2_exchange(token)
        except oauth2client.client.FlowExchangeError:
            return -1
        home_dir = os.getcwd()
        credential_dir = os.path.join(home_dir, 'user_credentials')
        if not path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'calendar-python-quickstart-' + user + '.json')

        with open(credential_path, 'wb') as config_dictionary_file:
            pickle.dump({'credentials': credentials}, config_dictionary_file)
        return 0
    else:
        return None


def calendar_usage(user, intent):
    credentials = get_credentials(user)

    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary', timeMin=now, maxResults=20, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])
    if intent == 'free_event':
        return get_free_events(events)

    elif intent == 'scheduled':
        return get_scheduled_events(events)


def get_free_events(events):
    if not events:
        response = "You are free all day."
    else:
        date, time = events[0]['start']['dateTime'].split('T')

        check_time = datetime.datetime.strptime(date + "T09:00:00", "%Y-%m-%dT%H:%M:%S")
        end_time = datetime.datetime.strptime(date + "T18:00:00", "%Y-%m-%dT%H:%M:%S")
        response = "You are free"

        for event in events:
            start = datetime.datetime.strptime(event['start']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S")
            if start < end_time:
                if start > check_time:
                    response += " from " + check_time.strftime("%I:%M %p") + " to " + start.strftime(
                        "%I:%M %p") + ","
                check_time = datetime.datetime.strptime(event['end']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S")

        if check_time < end_time:
            response += " and from " + check_time.strftime("%I:%M %p") + " to 06:00 PM"
        else:
            response = response[:-1]
            r = response.rsplit(',', 1)
            if len(r) > 1:
                response = r[0] + ", and" + r[1]
            if response == "You are fre":
                response = "No free times"

    return response


def get_scheduled_events(events):
    data_list = []
    if not events:
        data_list = 'No upcoming events found.'
    for event in events:
        start = datetime.datetime.strptime(event['start']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S").strftime(
            "%I:%M %p, %a %b %d")

        attachment = dict()
        attachment['color'] = "#2952A3"
        attachment['title'] = event['summary']
        attachment['text'] = start
        data_list.append(attachment)

    return data_list

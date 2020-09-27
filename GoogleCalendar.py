# Provides ability to interact with Google Calendar

# Imports
import datetime
import os.path
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Get google calendar credentials
def get_gcal_creds():
    # Initialize
    gcal_scope = ['https://www.googleapis.com/auth/calendar']
    creds = None

    # Access cached credentials in token.pickle (if the file exists)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", gcal_scope)
            creds = flow.run_local_server(port=0)
        # Cache the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


# Pull upcoming events of a given name from Google Calendar
def check_gcal_events(event_name, time_max=datetime.datetime.combine(datetime.date.today() + datetime.timedelta(365),
                                                                     datetime.time(12, 0, 0))):
    # Build service
    service = build('calendar', 'v3', credentials=get_gcal_creds())

    # Get upcoming Google Calendar events
    now = datetime.datetime.utcnow().isoformat() + 'Z'      # 'Z' indicates UTC time
    time_max = time_max.isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=time_max,
                                          singleEvents=True).execute()
    events = events_result.get('items', [])

    event_times = {}
    # Restrict to events matching the specific name
    if not events:
        print('No upcoming events named ' + event_name + ' found.')
    for event in events:
        if event['summary'] == event_name:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            event_times[event['id']] = [start, end]
    return event_times


# Update Google Calendar event summary based on ID
def change_gcal_event_title(event_id, new_name):
    # Build service
    service = build('calendar', 'v3', credentials=get_gcal_creds())

    # Get event using ID
    event = service.events().get(calendarId='primary', eventId=event_id).execute()

    # Update event summary (title)
    event['summary'] = new_name
    service.events().update(calendarId='primary', eventId=event_id, body=event).execute()


# Add gym time to Google Calendar
def create_gcal_event(event_name, event_times):
    # Build service
    gcal_service = build('calendar', 'v3', credentials=get_gcal_creds())

    # Set up event dictionary
    event = {
        'summary': event_name,
        'start': {
            'dateTime': event_times[0],
            'timeZone': 'America/New_York'
        },
        'end': {
            'dateTime': event_times[1],
            'timeZone': 'America/New_York'
        }
    }

    # Insert event
    gcal_gym_event = gcal_service.events().insert(calendarId='primary', body=event, sendNotifications=True).execute()
    print('Event called ' + event_name + ' from ' + event_times[0] + ' to ' + event_times[1] + ' created: %s'
          % (gcal_gym_event.get('htmlLink')))
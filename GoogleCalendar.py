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


# Determine calendar ID from calendar name
def pick_calendar(name):
    # Build service
    service = build('calendar', 'v3', credentials=get_gcal_creds())

    # Choose calendar ID from calendar name
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary'] == name:
                cal_id = calendar_list_entry['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break

    # Return calendar ID
    return cal_id


# Pull upcoming events of a given name from Google Calendar
def check_gcal_events(event_name, calendar_name, time_max=datetime.datetime.combine(datetime.date.today() + datetime.timedelta(365),
                                                                     datetime.time(12, 0, 0))):
    # Build service
    service = build('calendar', 'v3', credentials=get_gcal_creds())

    # Choose calendar ID from calendar name
    calendar_id = pick_calendar(calendar_name)

    # Get upcoming Google Calendar events
    now = datetime.datetime.utcnow().isoformat() + '-05:00'      # '-05:00' indicates EST
    time_max = time_max.isoformat() + '-05:00'
    events_result = service.events().list(calendarId=calendar_id, timeMin=now, timeMax=time_max,
                                          singleEvents=True).execute()
    events = events_result.get('items', [])

    # Restrict to events matching the specific name
    event_times = {}
    if not events:
        print('No upcoming events named ' + event_name + ' found.')
    for event in events:
        if event['summary'] == event_name:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            event_times[event['id']] = [start, end]
    return event_times


# Update Google Calendar event summary based on ID
def change_gcal_event_title(c_name, event_id, new_name):
    # Choose calendar ID from calendar name
    c_id = pick_calendar(c_name)

    # Build service
    service = build('calendar', 'v3', credentials=get_gcal_creds())

    # Get event using ID
    event = service.events().get(calendarId=c_id, eventId=event_id).execute()

    # Update event summary (title)
    event['summary'] = new_name
    service.events().update(calendarId=c_id, eventId=event_id, body=event).execute()


# Add gym time to Google Calendar
def create_gcal_event(gcal_name, event_name, event_times):
    # Choose calendar ID from calendar name
    gcal_id = pick_calendar(gcal_name)

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
    gcal_gym_event = gcal_service.events().insert(calendarId=gcal_id, body=event, sendNotifications=True).execute()
    print('Event called ' + event_name + ' from ' + event_times[0] + ' to ' + event_times[1] + ' created: %s'
          % (gcal_gym_event.get('htmlLink')))

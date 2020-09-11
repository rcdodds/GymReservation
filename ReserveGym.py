from __future__ import print_function
import time
import datetime
import pytz
import pandas as pd
import numpy as np
import pickle
import os.path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from webdriver_manager.chrome import ChromeDriverManager


# Global variables
SCOPES = ['https://www.googleapis.com/auth/calendar']


# Open a Selenium browser while printing status updates. Return said browser for use in scraping.
def open_gym_scheduler():
    # Open a selenium browser
    nickname = 'Lyon Place Login Page'
    login_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/userlogin.aspx'
    reservations_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/' \
                       'conciergereservations.aspx#tab_MakeAReservation'

    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    print('Opening Selenium browser')
    sele = webdriver.Chrome(ChromeDriverManager().install())
    print('Selenium browser opened')
    print('Opening ' + nickname)
    sele.get(login_url)
    print(nickname + ' opened')

    # Log in
    username, password = read_login('lyon_login.txt')
    sele.find_element_by_id('Username').send_keys(username)
    sele.find_element_by_id('Password').send_keys(password)
    sele.find_element_by_id('SignIn').click()
    time.sleep(5)

    # Move to reservations tab
    sele.get(reservations_url)
    time.sleep(5)

    return sele


# Read username and password from local text file
def read_login(filename):
    with open(filename, mode='r') as file:
        username = file.readline()
        password = file.readline()
    return username, password


# Submit Lyon Place gym reservation
def schedule_gym_time(start_date, start_time, duration):
    # Open website and get to reservations page
    driver = open_gym_scheduler()
    time.sleep(5)

    # Choose gym
    driver.find_element_by_id('ResourceId').send_keys('Fitness Center Lyon Place')
    time.sleep(5)

    # Choose date 5 days in future
    start_date_str = start_date.strftime("%m/%d/%y")
    month_day = str(int(start_date.strftime("%d")))
    driver.find_element_by_id('StartDate').click()
    cells = driver.find_elements_by_xpath('//td')
    dates = [date.text for date in cells]
    cells[dates.index(month_day)].click()
    time.sleep(5)

    # Choose duration
    driver.find_element_by_id('Duration').click()
    driver.find_element_by_xpath("//option[@value='" + str(duration) + "']").click()
    time.sleep(5)
    driver.find_element_by_id('divReservationRequestAdd').click()

    # Choose start time
    start_time_str = start_time.strftime("%I:%M %p")
    start_time_hour = str(int(start_time.strftime("%I")))
    start_time_mins = str(int(start_time.strftime("%M")))
    start_time_ampm = start_time.strftime("%p")
    driver.find_element_by_id('HoursStart').send_keys(start_time_hour)
    time.sleep(5)
    driver.find_element_by_id('MinutesStart').send_keys(start_time_mins)
    time.sleep(5)
    driver.find_element_by_id('AmPmStart').send_keys(start_time_ampm)
    time.sleep(5)

    try:
        # Submit reservation
        driver.find_element_by_id('btnCreateReservation').click()
        time.sleep(10)
        driver.find_element_by_id('btnPayNow').click()
        time.sleep(10)
    except:
        print('Reservation could not be submitted')
        driver.close()
    else:
        print('Reservation created for ' + start_date_str + ' at ' + start_time_str)
        driver.switch_to.alert.dismiss()
        driver.close()


# Retrieve all Lyon Place gym reservations
def check_scheduled_gym_times():
    # Open website and get to reservations page
    driver = open_gym_scheduler()

    # For moving around page
    builder = ActionChains(driver)

    # Pull reservations
    event_times = []

    # Find all events on current week visible
    cal_xpath = '//*[@id="calendar"]/div/div[1]/div/div[3]/div/div/a'
    ignored_exceptions = (NoSuchElementException, StaleElementReferenceException,)
    cal_wait = WebDriverWait(driver, 10, ignored_exceptions=ignored_exceptions) \
        .until(expected_conditions.presence_of_element_located((By.XPATH, cal_xpath)))
    cal = driver.find_elements_by_xpath('//*[@id="calendar"]/div/div[1]/div/div[3]/div/div/a')

    for i in range(len(cal)):
        # Open event pop up window
        builder.move_to_element(cal[i]).perform()
        cal[i].click()
        time.sleep(2)
        # Pull the times from the pop up window
        labels = [label.text for label in driver.find_elements_by_class_name('span4')]
        start_datetime = labels[5]
        end_datetime = labels[6]
        # Store data
        event_times.append([start_datetime, end_datetime])
        # Close the pop up window
        driver.find_element_by_id('CloseModalDialogButton').click()

    event_times_df = pd.DataFrame(event_times, columns=['start', 'end'])
    event_times_df.to_csv('event_times.csv')
    return event_times


# Get google calendar credentials
def get_gcal_creds():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


# Check for gym times on Google Calendar
def check_gcal_gym_times():
    # Build service
    service = build('calendar', 'v3', credentials=get_gcal_creds())

    # Get upcoming Google Calendar events
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    events_result = service.events().list(calendarId='primary', timeMin=now, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    gym_times = []
    # Restrict to gym reservations
    if not events:
        print('No upcoming events found.')
    for event in events:
        if event['summary'] == 'Gym':
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            gym_times.append([start, end])
    return gym_times


# Add gym time to Google Calendar
def add_gcal_gym_time(times):
    # Build service
    gcal_service = build('calendar', 'v3', credentials=get_gcal_creds())
    # Set up event
    event = {
        'summary': 'Gym',
        'start': {
            'dateTime': times[0],
            'timeZone': 'America/New_York'
        },
        'end': {
            'dateTime': times[1],
            'timeZone': 'America/New_York'
        }
    }

    # Insert event
    gcal_gym_event = gcal_service.events().insert(calendarId='primary', body=event, sendNotifications=True).execute()
    print('Event created: %s' % (gcal_gym_event.get('htmlLink')))


# Let's reserve the gym
def main():
    # Separator for print logging
    separator = '=-=' * 50

    # Choose date 5 days in future
    st_day = datetime.date.today() + datetime.timedelta(days=5)

    # Generate list of event info - [[st_day, st_time1, dur1], [st_day, st_time2, dur2]]
    gym_reservations = []
    if st_day.weekday() < 5:
        # 7 - 8 am
        st_time = datetime.time(7, 0, 0)
        dur = 60
        gym_reservations.append([st_day, st_time, dur])

        # 5:30 - 6 pm
        st_time = datetime.time(17, 30, 0)
        dur = 30
        gym_reservations.append([st_day, st_time, dur])
    else:
        # 12 - 1 pm
        st_time = datetime.time(12, 0, 0)
        dur = 60
        gym_reservations.append([st_day, st_time, dur])

    # Create reservations
    for reservation in gym_reservations:
        schedule_gym_time(reservation[0], reservation[1], reservation[2])

    # Get all scheduled gym times
    print(separator)
    print('Retrieving Scheduled Times from Lyon Place')
    scheduled_times = check_scheduled_gym_times()
    print('Lyon Place Scheduled Times')
    print(scheduled_times)

    # Pull upcoming Google calendar gym reservations
    print(separator)
    print('Retrieving Google Calendar Events')
    gcal_times = check_gcal_gym_times()
    print('Google Calendar Events')
    print(gcal_times)

    # Create Google calendar events if necessary
    print(separator)
    print('Creating Google Calendar Events (if necessary)')

    for event in scheduled_times:
        # Format as gcal time stamp
        dt_stamp = [datetime.datetime.strptime(event[0], "%m/%d/%Y %I:%M %p"),
                    datetime.datetime.strptime(event[1], "%m/%d/%Y %I:%M %p")]
        gcal_timestamp = [dt_stamp[0].strftime("%Y-%m-%dT%H:%M:%S") + '-04:00',
                          dt_stamp[1].strftime("%Y-%m-%dT%H:%M:%S") + '-04:00']

        # Add to google calendar if it isn't already present
        if dt_stamp[0] >= datetime.datetime.now() and gcal_timestamp not in gcal_times:
            add_gcal_gym_time(gcal_timestamp)
            gcal_times = check_gcal_gym_times()


# Let's get it going
if __name__ == "__main__":
    # Call main
    main()
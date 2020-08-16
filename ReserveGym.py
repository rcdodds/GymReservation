import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# Global variables
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Lyon Place Gym Reservations'


# Open a Selenium browser while printing status updates. Return said browser for use in scraping.
def open_selenium_browser(nickname, website):
    print('----------Scraping ' + nickname + '----------')
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    print('Opening Selenium browser')
    driver_path = 'C:\\Users\\rcdodds\\Documents\\chromedriver_win32\\chromedriver.exe'
    sele = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
    print('Selenium browser opened')
    print('Opening ' + nickname)
    sele.get(website)
    print(nickname + ' opened')
    return sele


# Read username and password from local text file
def read_login(filename):
    with open(filename, mode='r') as file:
        username = file.readline()
        password = file.readline()
    return username, password


# Submit Lyon Place gym reservation
def create_reservation(driver):
    # Navigate to reservations page
    reservations_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/' \
                       'conciergereservations.aspx#tab_MakeAReservation'
    driver.get(reservations_url)
    time.sleep(5)

    # Pick gym
    driver.find_element_by_id('ResourceId').send_keys('Fitness Center Lyon Place')

    # Choose date 5 days in futue
    start_date = datetime.date.today() + datetime.timedelta(days=5)
    start_date_str = start_date.strftime("%m/%d/%y")
    month_day = start_date.strftime("%d")
    driver.find_element_by_id('StartDate').click()
    cells = driver.find_elements_by_xpath('//td')
    dates = [date.text for date in cells]
    cells[dates.index(month_day)].click()
    time.sleep(1)

    # Choose start time
    start_time = datetime.time(5, 0, 0)
    start_time_str = start_time.strftime("%I:%M %p")
    start_time_hour = start_time.strftime("%I").replace('0', '')
    start_time_mins = start_time.strftime("%M").replace('00',  '0')
    start_time_ampm = start_time.strftime("%p")
    driver.find_element_by_id('HoursStart').send_keys(start_time_hour)
    driver.find_element_by_id('MinutesStart').send_keys(start_time_mins)
    driver.find_element_by_id('AmPmStart').send_keys(start_time_ampm)

    # Choose duration
    driver.find_element_by_id('Duration').click()
    driver.find_element_by_xpath("//option[@value='60']").click()
    time.sleep(5)

    try:
        # Submit reservation
        driver.find_element_by_id('btnCreateReservation').click()
        time.sleep(5)
        driver.find_element_by_id('btnPayNow').click()
        time.sleep(5)
    except:
        print('Reservation could not be submitted')
    else:
        print('Reservation created for ' + start_date_str + ' at ' + start_time_str)


# Retrieve all Lyon Place gym reservations
def get_reservations(driver):
    # Navigate to reservations page
    reservations_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/' \
                       'conciergereservations.aspx#tab_MakeAReservation'
    driver.get(reservations_url)
    time.sleep(5)

    # Pull reservations
    event_times = []
    cal = driver.find_elements_by_xpath('//*[@id="calendar"]/div/div[1]/div/div[3]/div/div/a')
    for event in cal:
        print(event.text)
        # Open event pop up window
        event.click()
        time.sleep(2)
        # Pull the times from the pop up window
        labels = [label.text for label in driver.find_elements_by_xpath('//*[@id="divMain"]/label')]
        start_datetime = labels[8]
        end_datetime = labels[10]
        # Store data
        event_times.append([start_datetime, end_datetime])
        # Close the pop up window
        driver.find_element_by_id('CloseModalDialogButton').click()

    return event_times


# Get google calendar credentials
def get_credentials():
    print('Getting credentials')
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is created automatically when the
    # authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)


# Add all gym reservations to Google Calendar
def google_calendar(datetimes):
    print('Adding reservations to Google Calendar')
    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                        maxResults=10, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

# Let's reserve the gym
def main():
    # Open a selenium browser
    login_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/userlogin.aspx'
    browser = open_selenium_browser('Lyon Place Login Page', login_url)

    # Log in
    username, password = read_login('lyon_login.txt')
    browser.find_element_by_id('Username').send_keys(username)
    browser.find_element_by_id('Password').send_keys(password)
    browser.find_element_by_id('SignIn').click()
    time.sleep(5)

    # Create reservation for 5 days in future
    # create_reservation(browser)

    # Get all previously scheduled gym sessions
    reservations = get_reservations(browser)

    # Ensure all gym sessions are on Google calendar
    google_calendar(reservations)


# Let's get it going
if __name__ == "__main__":
    # Call main
    main()
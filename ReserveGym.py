from __future__ import print_function

import datetime
import time
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager

from GoogleCalendar import check_gcal_events, change_gcal_event_title


# Open a Selenium browser while printing status updates. Return said browser for use in scraping.
def open_gym_scheduler():
    # Open a selenium browser
    login_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/userlogin.aspx'
    reservations_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/' \
                       'conciergereservations.aspx#tab_MakeAReservation'

    chrome_options = Options()
    # chrome_options.headless = True
    sele = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    sele.get(login_url)

    # Log in
    username, password = read_login('lyon_login.json')
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
        login_dict = json.load(file)
    return login_dict["username"], login_dict["password"]


# Submit Lyon Place gym reservation
def schedule_gym_time(start_date, start_time, duration):
    # Number of seconds to sleep after
    sleeptime = 5

    # Open website and get to reservations page
    driver = open_gym_scheduler()

    # Choose gym
    driver.find_element_by_id('ResourceId').send_keys('Fitness Center Lyon Place')

    # Choose date
    start_date_str = start_date.strftime("%m/%d/%y")
    reservation_month_day = int(start_date.strftime("%d"))              # Reservation day of the month (1 - 31)
    today_month_day = int(datetime.date.today().strftime("%d"))         # Today's day of the month (1 - 31)
    driver.find_element_by_id('StartDate').click()                      # Open date picker
    if reservation_month_day < today_month_day:         # If reserving a slot in the next month, move to next month
        driver.find_element_by_class_name('ui-datepicker-next.ui-corner-all').click()
    cells = driver.find_elements_by_xpath('//td')
    dates = [date.text for date in cells]
    cells[dates.index(str(reservation_month_day))].click()              # Pick reservation date

    # Choose duration
    driver.find_element_by_id('Duration').click()
    driver.find_element_by_xpath("//option[@value='" + str(duration) + "']").click()
    time.sleep(sleeptime)
    driver.find_element_by_id('divReservationRequestAdd').click()

    # Choose start time
    start_time_str = start_time.strftime("%I:%M %p")
    start_time_hour = str(int(start_time.strftime("%I")))
    start_time_mins = str(int(start_time.strftime("%M")))
    start_time_ampm = start_time.strftime("%p")
    driver.find_element_by_id('HoursStart').send_keys(start_time_hour)
    time.sleep(sleeptime)
    driver.find_element_by_id('MinutesStart').send_keys(start_time_mins)
    time.sleep(sleeptime)
    driver.find_element_by_id('AmPmStart').send_keys(start_time_ampm)
    time.sleep(sleeptime)

    # Click create reservation button
    driver.find_element_by_id('btnCreateReservation').click()
    time.sleep(sleeptime)
    # Check that reservation is being created at the desired time
    desired_start_time = start_date_str + ' ' + start_time_str
    actual_start_time = driver.find_element_by_class_name('span9').text
    if actual_start_time == desired_start_time:
        # Confirm reservation
        driver.find_element_by_id('btnPayNow').click()
        time.sleep(sleeptime)
        print('Reservation created for ' + actual_start_time)
        driver.switch_to.alert.dismiss()
        event_created = True
    else:
        print('Reservation could not be submitted for ' + desired_start_time)
        event_created = False
    driver.close()
    return event_created


# Let's reserve the gym
def main():
    # Variables
    gcal_pending_event_title = 'Pending Gym'        # Name of pending gym events for Google Calendar
    gcal_confirmed_event_title = 'Gym'              # Name of confirmed gym events for Google Calendar

    # Create gym reservations based on upcoming, pending Google calendar gym reservations in the next 5 calendar days
    time_max = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=5), datetime.time(23, 59, 59))
    pending_gcal_timestamps = check_gcal_events(gcal_pending_event_title, time_max)
    print('Google Calendar Pending Gym Times')
    for pending_event in pending_gcal_timestamps.values():
        print(pending_event)

    # Loop through pending events
    for pending_event_id in pending_gcal_timestamps.keys():
        # Parse Google Calendar timestamp and split data into necessary pieces
        pending_gcal_datetimes = [datetime.datetime.strptime(dt.replace('-04:00', ''), "%Y-%m-%dT%H:%M:%S")
                                  for dt in pending_gcal_timestamps[pending_event_id]]
        st_day = pending_gcal_datetimes[0].date()
        st_time = pending_gcal_datetimes[0].time()
        dur = int((pending_gcal_datetimes[1] - pending_gcal_datetimes[0]).total_seconds()/60)

        # Attempt to create reservation
        if schedule_gym_time(st_day, st_time, dur):
            # If successful, update Google Calendar event title
            change_gcal_event_title(pending_event_id, gcal_confirmed_event_title)
        else:
            # Send text notification
            print('Send a text via Twilio')


# Let's get it going
if __name__ == "__main__":
    # Call main
    main()
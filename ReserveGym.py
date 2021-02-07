from __future__ import print_function

import datetime
import time
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager

from GoogleCalendar import check_gcal_events, change_gcal_event_title   # Custom import
from TwilioTexts import send_text   # Custom import


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
    return login_dict['username'], login_dict['password']


# Wait for page to load (if required)
def wait_page_load(drv):
    # Variables
    short_timeout = 5                   # Wait a short amount of time for page loading element to appear
    long_timeout = 60                   # Wait a longer time for page loading element to disappear
    page_loading_id = 'page_loading'    # ID of page loading element

    try:
        # Wait for page loading element to appear
        WebDriverWait(drv, short_timeout).until(ec.presence_of_element_located((By.ID, 'page_loading')))
        # Wait for page loading element to disappear
        WebDriverWait(drv, long_timeout).until_not(ec.presence_of_element_located((By.ID, page_loading_id)))
    except TimeoutException:
        pass

    # Wait a second then let program resume
    time.sleep(1)


# Submit Lyon Place gym reservation
def schedule_gym_time(start_datetime, duration):
    # Open website and get to reservations page
    driver = open_gym_scheduler()

    # Choose gym
    driver.find_element_by_id('ResourceId').send_keys('Fitness Center Lyon Place')

    # Check Waitlist box. This stops the website from trying to dynamically show available timeslots.
    wait_page_load(driver)
    driver.find_element_by_id('Waitlist').click()
    wait_page_load(driver)

    # Choose date
    reservation_month_day = int(start_datetime.strftime("%d"))          # Reservation day of the month (1 - 31)
    today_month_day = int(datetime.date.today().strftime("%d"))         # Today's day of the month (1 - 31)
    driver.find_element_by_id('StartDate').click()                      # Open date picker
    if reservation_month_day < today_month_day:         # If the date is in the next month, move to next month
        driver.find_element_by_class_name('ui-datepicker-next.ui-corner-all').click()
    cells = driver.find_elements_by_xpath('//td')
    dates = [date.text for date in cells]
    cells[dates.index(str(reservation_month_day))].click()              # Pick reservation date
    wait_page_load(driver)

    # Choose duration
    driver.find_element_by_id('Duration').click()
    wait_page_load(driver)
    driver.find_element_by_xpath("//option[@value='" + str(duration) + "']").click()
    wait_page_load(driver)
    driver.find_element_by_id('divReservationRequestAdd').click()
    wait_page_load(driver)

    # Choose start time
    start_time_hour = str(int(start_datetime.strftime("%I")))
    start_time_mins = str(int(start_datetime.strftime("%M")))
    start_time_ampm = start_datetime.strftime("%p")
    driver.find_element_by_id('AmPmStart').send_keys(start_time_ampm)
    wait_page_load(driver)
    driver.find_element_by_id('HoursStart').send_keys(start_time_hour)
    wait_page_load(driver)
    driver.find_element_by_id('MinutesStart').send_keys(start_time_mins)
    wait_page_load(driver)

    # If the wait list warning is not present, submit the reservation
    event_created = False
    if not driver.find_element_by_id('lblTimeError').is_displayed():
        # Click create reservation button
        driver.find_element_by_id('btnCreateReservation').click()
        wait_page_load(driver)
        # Check that reservation is being created at the desired time
        actual_start_str = driver.find_element_by_class_name('span9').text
        actual_start_dt = datetime.datetime.strptime(actual_start_str, '%m/%d/%Y %I:%M %p')
        deviation = max(actual_start_dt, start_datetime) - min(actual_start_dt, start_datetime)
        if deviation.seconds <= 1.5 * 3600:
            # Confirm reservation
            driver.find_element_by_id('btnPayNow').click()
            time.sleep(5)
            print('Reservation created for ' + actual_start_dt.strftime('%m/%d/%y %I:%M %p'))
            driver.switch_to.alert.dismiss()
            event_created = True

    driver.close()
    return event_created


# Let's reserve the gym
def main():
    # Variables
    gcal_calendar_name = 'Gym'                      # Name of Google Calendar holding reservations
    gcal_pending_event_title = 'Pending Gym'        # Name of pending gym events for Google Calendar
    gcal_confirmed_event_title = 'Gym'              # Name of confirmed gym events for Google Calendar

    # Create gym reservations based on upcoming, pending Google calendar gym reservations in the next 5 calendar days
    time_max = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=5), datetime.time(23, 59, 59))
    pending_gcal_timestamps = check_gcal_events(gcal_pending_event_title, gcal_calendar_name, time_max)
    print('Google Calendar Pending Gym Times')
    for pending_event in pending_gcal_timestamps.values():
        print(pending_event)

    # Loop through pending events
    for pending_event_id in pending_gcal_timestamps.keys():
        # Parse Google Calendar timestamp and split data into necessary pieces
        pending_gcal_datetimes = [datetime.datetime.strptime(dt[:-6], "%Y-%m-%dT%H:%M:%S")
                                  for dt in pending_gcal_timestamps[pending_event_id]]
        start_dt = pending_gcal_datetimes[0]
        dur = int((pending_gcal_datetimes[1] - pending_gcal_datetimes[0]).total_seconds()/60)

        # Attempt to create reservation
        if schedule_gym_time(start_dt, dur):
            # If successful, update Google Calendar event title
            change_gcal_event_title(pending_event_id, gcal_confirmed_event_title)
            # Set up success message
            message = 'SUCCESS - Gym reserved - ' + start_dt.strftime('%m/%d/%y %I:%M %p')
        else:
            # Set up failure message
            message = 'FAILURE - Gym NOT reserved - ' + start_dt.strftime('%m/%d/%y %I:%M %p')

        # Print and text resultant message
        print(message)
        send_text(message, '+14847233363')


# Let's get it going
if __name__ == "__main__":
    # Call main
    main()

from __future__ import print_function

import datetime
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager

from GoogleCalendar import check_gcal_events, create_gcal_event, change_gcal_event_title


# Open a Selenium browser while printing status updates. Return said browser for use in scraping.
def open_gym_scheduler():
    # Open a selenium browser
    nickname = 'Lyon Place Login Page'
    login_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/userlogin.aspx'
    reservations_url = 'https://lyonplace.securecafe.com/residentservices/lyon-place-at-clarendon-center/' \
                       'conciergereservations.aspx#tab_MakeAReservation'

    chrome_options = Options()
    # chrome_options.headless = True
    print('Opening Selenium browser')
    sele = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
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

    try:
        # Click create reservation button
        driver.find_element_by_id('btnCreateReservation').click()
        time.sleep(sleeptime)
        # Check that reservation is being created at the desired time

        driver.find_element_by_id('btnPayNow').click()
        time.sleep(sleeptime)
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

    event_times = []
    # Find all events currently visible
    cal_xpath = '//*[@id="calendar"]/div/div[1]/div/div[3]/div/div/a'
    ignored_exceptions = (NoSuchElementException, StaleElementReferenceException,)
    try:
        WebDriverWait(driver, 10, ignored_exceptions=ignored_exceptions) \
            .until(expected_conditions.presence_of_element_located((By.XPATH, cal_xpath)))
        events = driver.find_elements_by_xpath(cal_xpath)
    except TimeoutException:
        events = []
        print("No events currently visible")

    for event in events:
        # Open event pop up window
        builder.move_to_element(event).perform()
        event.click()
        time.sleep(2)
        # Pull the times from the pop up window
        labels = [label.text for label in driver.find_elements_by_class_name('span4')]
        start_datetime = labels[5]
        end_datetime = labels[6]
        # Store data
        event_times.append([start_datetime, end_datetime])
        # Close the pop up window
        driver.find_element_by_id('CloseModalDialogButton').click()

    # Move to next week
    # driver.find_element_by_class_name('fc-button.fc-button-next.fc-state-default.fc-corner-right.hidden-phone').click()

    return event_times


# Let's reserve the gym
def main():
    # Variables
    gcal_pending_event_title = 'Pending Gym'        # Name of pending gym events for Google Calendar
    gcal_confirmed_event_title = 'Gym'              # Name of confirmed gym events for Google Calendar
    separator = '=-=' * 50                          # Separator for print logging

    # Create gym reservations based on upcoming, pending Google calendar gym reservations in the next 5 calendar days
    time_max = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=5), datetime.time(23, 59, 59))
    print(separator)
    print('Retrieving Pending Gym Times from Google Calendar')
    pending_gcal_timestamps = check_gcal_events(gcal_pending_event_title, time_max)
    for pending_event_id in pending_gcal_timestamps.keys():
        # Parse Google Calendar timestamp and split data into necessary pieces
        pending_gcal_datetimes = [datetime.datetime.strptime(dt.replace('-04:00', ''), "%Y-%m-%dT%H:%M:%S")
                                  for dt in pending_gcal_timestamps[pending_event_id]]
        st_day = pending_gcal_datetimes[0].date()
        st_time = pending_gcal_datetimes[0].time()
        dur = int((pending_gcal_datetimes[1] - pending_gcal_datetimes[0]).total_seconds()/60)

        # Attempt to create reservation and update Google Calendar if successful
        schedule_gym_time(st_day, st_time, dur)
        change_gcal_event_title(pending_event_id, gcal_confirmed_event_title)

    # # Get all scheduled gym times
    # print(separator)
    # print('Retrieving Gym Times from Lyon Place')
    # scheduled_gym_times = check_scheduled_gym_times()
    # print('Lyon Place Gym Times')
    # for scheduled_gym_time in scheduled_gym_times:
    #     print(scheduled_gym_time)
    #
    # # Pull upcoming, confirmed Google calendar gym reservations
    # print(separator)
    # print('Retrieving Gym Times from Google Calendar')
    # confirmed_gcal_times = check_gcal_events(gcal_confirmed_event_title)
    # print('Google Calendar Gym Times')
    # for gcal_time in confirmed_gcal_times:
    #     print(gcal_time)
    #
    # # Create Google calendar events if necessary
    # print(separator)
    # created_gcal = False
    # for event in scheduled_gym_times:
    #     # Format as gcal time stamp
    #     dt_stamp = [datetime.datetime.strptime(event[0], "%m/%d/%Y %I:%M %p"),
    #                 datetime.datetime.strptime(event[1], "%m/%d/%Y %I:%M %p")]
    #     gcal_timestamp = [dt_stamp[0].strftime("%Y-%m-%dT%H:%M:%S") + '-04:00',
    #                       dt_stamp[1].strftime("%Y-%m-%dT%H:%M:%S") + '-04:00']
    #
    #     # Add to google calendar if it isn't already present
    #     if dt_stamp[0] >= datetime.datetime.now() and gcal_timestamp not in confirmed_gcal_times:
    #         created_gcal = True
    #         create_gcal_event(gcal_confirmed_event_title, gcal_timestamp)
    # if not created_gcal:
    #     print('No Google Calendar events were created')

    # All done
    print(separator)
    print('The program finished successfully.')
    print(separator)


# Let's get it going
if __name__ == "__main__":
    # Call main
    main()
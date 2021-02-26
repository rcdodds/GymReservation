# Automating Gym Reservations

## An RPA bot to reserve my apartment's gym based on my Google Calendar and send status updates via Twilio SMS.

#### Main Components
1. ReserveGym.py
    - Log into apartment site and create gym reservation
    - Utilize Google Calendar for dates / times of proposed reservations
    - Utilize Twilio to send notifcations via SMS

2. ReserveGym.bat
    - Run ReserveGym.py

3. Windows Task Scheduler Task
    - Trigger = 12:00:01 AM every day
    - Action = Execute ReserveGym.bat
    

#### Other Files Referenced
These files have not been included for security reasons.
- lyon_login.txt == apartment login details
- client_secret.json == Google Calendar credentials
- token.pickle == cached Google Calendar credentials
- twilio_credentials.json == Twilio API credentials
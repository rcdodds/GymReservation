# Automating Gym Reservation

#### Main Components
1. ReserveGym.py
    - Log into apartment site and create gym reservation
    - Log into apartment site and pull existing gym reservations
    - Log into Google Calendar and create gym event
    - Log into Google Calendar and pull existing gym event

2. ReserveGym.bat
    - Run ReserveGym.py

3. Windows Task Scheduler Task
    - Trigger = 1:00 AM every day
    - Action = Execute ReserveGym.bat
    

#### Other Files Referenced
These files have not been included for security reasons.
- lyon_login.txt == apartment login details
- client_secret.json == Google Calendar credentials
- token.pickle == cached Google Calendar credentials
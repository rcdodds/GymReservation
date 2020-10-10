# Imports
from twilio.rest import Client
import json


# Send a motivational text
def send_text(text_body, to):
    # Read in Twilio Account data from JSON file
    with open('twilio_credentials.json', mode='r') as file:
        twilio_dict = json.load(file)

    # Store required variables
    account_sid = twilio_dict['account_sid']
    auth_token = twilio_dict['auth_token']
    from_number = twilio_dict['from_number']

    # Start a Twilio client
    client = Client(account_sid, auth_token)

    # Send text
    message = client.messages.create(
        body=text_body,
        from_=from_number,
        to=to
    )

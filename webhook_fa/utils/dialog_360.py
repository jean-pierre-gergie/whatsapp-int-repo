import requests
from dotenv import load_dotenv
import os 
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a logger that dynamically takes the module's name

load_dotenv()


dialog_360_message_url = os.getenv("DIALOG_360_MESSAGE_URL")

def send_message_to_users_through_360(number,message,api_key_360,logger):

    try:
        # Prepare the 360dialog payload
        dialog_payload = {
            "recipient_type": "individual",
            "to": number,  # Assuming 'room' is the phone number or identifier for 360dialog
            "messaging_product": "whatsapp",
            "type": "text",
            "text": {
                "body": message  # The actual message content
            }
        }

        # Send the POST request to 360dialog's API
        logger.debug(f"Sending payload to 360dialog API: {dialog_payload}")
        dialog_response = requests.post(
            dialog_360_message_url,
            json=dialog_payload,
            headers={
                "Content-Type": "application/json",
                "D360-API-KEY": api_key_360 
            }
        )

        if dialog_response.status_code == 200:
            logger.info(f"Successfully sent message via 360dialog to {number}.")
        else:
            logger.error(f"Failed to send message via 360dialog. Status: {dialog_response.status_code}, Response: {dialog_response.text}")

    except Exception as e:
        logger.error(f"Error sending message to 360dialog: {e}")
        raise 
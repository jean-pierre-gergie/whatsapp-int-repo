import requests
from dotenv import load_dotenv
import os 
import logging
from utils.db_helper import get_mongo_client

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a logger that dynamically takes the module's name
logger = logging.getLogger(__name__)

load_dotenv()


dialog_360_message_url = os.getenv("DIALOG_360_MESSAGE_URL")


def get_api_key(foundation_name):
        """
        Fetches the API key for the foundation using the foundation name.
        """
        try:
            logger.debug(f"Fetching API key for foundation: {foundation_name}")
            mongo_client = get_mongo_client()
            foundations_collection = mongo_client['foundations_db']['foundations']
            # Find the document in the collection matching the foundation name
            foundation_doc = foundations_collection.find_one({"foundation": foundation_name})

            if not foundation_doc:
                logger.warning(f"No document found for foundation: {foundation_name}")
                return None

            # Extract the API key
            api_key = foundation_doc.get("api_key")
            if not api_key:
                logger.warning(f"No API key found for foundation: {foundation_name}")
                return None

            logger.info(f"API key for {foundation_name}: {api_key}")
            return api_key

        except Exception as e:
            logger.error(f"Error fetching API key for {foundation_name}: {e}", exc_info=True)
            raise

def send_message_to_users_through_360(number,message,foundation_name):

    try:

        api_key =get_api_key(foundation_name=foundation_name)
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
                "D360-API-KEY": api_key 
            }
        )

        if dialog_response.status_code == 200:
            logger.info(f"Successfully sent message via 360dialog to {number}.")
        else:
            logger.error(f"Failed to send message via 360dialog. Status: {dialog_response.status_code}, Response: {dialog_response.text}")

    except Exception as e:
        logger.error(f"Error sending message to 360dialog: {e}")
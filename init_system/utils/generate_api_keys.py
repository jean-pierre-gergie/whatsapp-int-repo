import requests
import json
import os
from dotenv import load_dotenv
from logger.set_logger import get_logger

logger  = get_logger()

def get_token():
    """
    Fetches an access token from the 360dialog API using environment variables for credentials.
    """
    load_dotenv()

    try:
        username = os.getenv("USERNAME_360_DIALOG")
        password = os.getenv("PASSWORD")

        if not username or not password:
            raise ValueError("Username or password environment variable is missing or empty.")

        url = "https://hub.360dialog.io/api/v2/token"
        payload = json.dumps({
            "username": username,
            "password": password
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.post(url, headers=headers, data=payload)

        if response.status_code != 200:
            logger.error(f"Failed to fetch token. HTTP Status: {response.status_code}, Response: {response.text}")
            response.raise_for_status()

        return response.json().get('access_token')
    except ValueError as ve:
        logger.error(f"ValueError occurred: {ve}")
        raise
    except requests.RequestException as re:
        logger.error(f"RequestException occurred: {re}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

    
def get_channelID():
    """
    Load environment variables and extract channel IDs for foundations.

    Reads environment variables ending with '_CHANNELID', maps them to their
    respective foundation names, and returns a dictionary of foundation names
    and their channel IDs.
    """
    load_dotenv()  

    foundations_channel_ids = {}  

    try:
        for key, value in os.environ.items():
            if key.endswith('_CHANNELID'):
                foundation_name = key.replace('_CHANNELID', '').lower()
                foundation_channel_id = value

                if not foundation_channel_id:
                    raise ValueError(f"Channel ID for {foundation_name} is missing or empty.")

                foundations_channel_ids[foundation_name] = foundation_channel_id
                logger.debug(f"Found foundation channel ID: {key} (Mapped as: {foundation_name})")
    except ValueError as ve:
        logger.error(f"ValueError occurred: {ve}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

    return foundations_channel_ids


def get_api_keys():
    """
    Generates API keys for all foundations using their respective channel IDs.
    """
    try:
        foundations_api_keys ={}
        token = get_token()  # Fetch the access token
        foundations_channel_ids = get_channelID()  # Fetch channel IDs

        for foundation, channel_id in foundations_channel_ids.items():

            # Construct the URL dynamically for each channel ID
            url = f"https://hub.360dialog.io/api/v2/partners/l2Wjy9PA/channels/{channel_id}/api_keys"

            payload = json.dumps({})  # Empty payload for the POST request
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'  # Use the fetched token for authorization
            }

            # Make the POST request to generate an API key
            response = requests.post(url, headers=headers, data=payload)

            if response.status_code == 201:
                logger.info(f"API key successfully generated for foundation: {foundation}")
                foundations_api_keys['foundation'] = response.json().get('api_key')
                
            else:
                logger.error(f"Failed to generate API key for foundation: {foundation}. "
                             f"HTTP Status: {response.status_code}, Response: {response.text}")
                

        return foundations_api_keys

    except Exception as e:
        logger.error(f"An error occurred while generating API keys: {e}")
        raise


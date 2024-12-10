import requests
import json
import os
from dotenv import load_dotenv
from urllib.parse import quote


def get_token(logger):
    
    load_dotenv()

    try:
        # Fetch credentials from environment variables
        username = os.getenv("USERNAME_360_DIALOG")
        password = os.getenv("PASSWORD_360_DIALOG")

        if not username or not password:
            logger.error("Username or password environment variable is missing or empty.")
            raise ValueError("Username or password environment variable is missing or empty.")

        # Log credentials (for debugging purposes only, do not use in production)
        logger.debug(f"Fetched credentials: username={username}, password={password}")

        # Prepare API request
        url = "https://hub.360dialog.io/api/v2/token"
        payload = json.dumps({
            "username": "rtenn@mymada.com",
            "password": "@cce$$-APP23"
            })
        headers = {
            'Content-Type': 'application/json'
            }

        logger.debug(f"Sending token request to {url} with payload: {payload}")
        
        # Send request
        response = requests.request("POST", url, headers=headers, data=payload)

        # logger.debug(f"{response}")

        # logger.debug(f"Token request response: {response.status_code}, {response.text}")
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch token. Response: {response.json()}")
            response.raise_for_status()
        
        # Extract token
        token = response.json().get('access_token')
        if not token:
            logger.error("Access token not found in the API response.")
            raise ValueError("Access token not found in the API response.")
        
        logger.info("Successfully fetched access token.")
        return token

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

def get_channelID(logger):
    """
    Load environment variables and extract channel IDs for foundations.

    Reads environment variables ending with '_CHANNELID', maps them to their
    respective foundation names, and returns a dictionary of foundation names
    and their channel IDs.
    """
    logger.info("Loading environment variables from .env file.")
    load_dotenv()  # Load variables from .env file into the environment

    foundations_channel_ids = {}

    try:
        logger.info("Extracting channel IDs from environment variables.")
        for key, value in os.environ.items():
            if key.endswith('_CHANNELID'):
                foundation_name = key.replace('_CHANNELID', '').lower()
                foundation_channel_id = value.strip()  # Ensure no leading/trailing spaces

                if not foundation_channel_id:
                    logger.warning(f"Channel ID for {foundation_name} is missing or empty.")
                    continue

                foundations_channel_ids[foundation_name] = foundation_channel_id
                logger.debug(f"Mapped channel ID: {key} to foundation: {foundation_name}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing channel IDs: {e}")
        raise

    if not foundations_channel_ids:
        logger.warning("No channel IDs were found in the environment variables.")
    else:
        logger.info(f"Successfully extracted channel IDs: {foundations_channel_ids}")

    return foundations_channel_ids


def get_api_keys(logger):
    """
    Generates API keys for all foundations using their respective channel IDs.
    """
    try:
        foundations_api_keys = {}
        token = get_token(logger)  # Fetch the access token
        foundations_channel_ids = get_channelID(logger)  # Fetch channel IDs

        logger.debug(f"Fetched token: {token[:10]}... (truncated for security)")
        logger.debug(f"Channel IDs retrieved: {foundations_channel_ids}")

        for foundation, channel_id in foundations_channel_ids.items():
            url = f"https://hub.360dialog.io/api/v2/partners/l2Wjy9PA/channels/{channel_id}/api_keys"

            payload = json.dumps({})
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }

            logger.debug(f"Generating API key for foundation: {foundation} with channel ID: {channel_id}. URL: {url}")

            response = requests.post(url, headers=headers, data=payload)

            logger.debug(f"Response from API for foundation {foundation}: HTTP {response.status_code}, Response: {response.text}")

            if response.status_code == 201:
                logger.info(f"API key successfully generated for foundation: {foundation}")
                foundations_api_keys[foundation] = response.json().get('api_key')
            else:
                logger.error(f"Failed to generate API key for foundation: {foundation}. "
                             f"HTTP Status: {response.status_code}, Response: {response.text}")

        return foundations_api_keys

    except Exception as e:
        logger.error(f"An error occurred while generating API keys: {e}")
        raise
import os
import requests
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse


# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to console handler
console_handler.setFormatter(formatter)

# Add console handler to logger
logger.addHandler(console_handler)

# Load environment variables
load_dotenv()

def set_webhook_config(foundation_name, api_key, webhook_base_url, max_attempts=2):
    try:
        url = 'http://waba.360dialog.io/v1/configs/webhook'
        headers = {
            'Content-Type': 'application/json',
            'D360-API-KEY': api_key
        }
        expected_url = f"{webhook_base_url}/webhook/{foundation_name}"
        data = {
            "url": expected_url
        }

        for attempt in range(1, max_attempts + 1):
            logger.debug(f"\n{'='*12}")
            logger.debug(f"Attempt {attempt}: Setting webhook for {foundation_name}")

            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            response_data = response.json()
            current_url = response_data.get("url", "")

            logger.debug(f"{foundation_name} webhook status: {response.status_code}")
            logger.debug(f"Response URL: {current_url}")
            logger.debug(response.text)
            logger.debug(f"\n{'='*12}")

            # Check if the current URL matches the expected URL
            if current_url == expected_url:
                logger.info(f"Webhook for {foundation_name} set successfully.")
                break
            elif attempt == max_attempts:
                logger.warning(f"Max attempts reached. Webhook URL for {foundation_name} might not match the expected URL.")
            else:
                logger.info(f"Retrying to set the webhook for {foundation_name}...")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error setting webhook for {foundation_name}: {e}", exc_info=True)


def load_environment_variables():
    """
    Load environment variables based on FLASK_ENV and validate them.
    """
    # Configure the logger
    logger = logging.getLogger("LOAD_ENV_VAR")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()  # Logs to the console
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)

    try:
        # Determine the environment
        flask_env = os.getenv('FLASK_ENV', 'development').lower()
        logger.debug(f"FLASK_ENV: {flask_env}")

        # Load and log the webhook setting
        set_webhook = os.getenv('SET_WEBHOOK_URL') == 'TRUE'
        logger.debug(f"SET_WEBHOOK_URL: {set_webhook}")

        # Load the appropriate base URL based on FLASK_ENV
        if flask_env == 'production':
            webhook_base_url = os.getenv('WEBHOOK_BASE_URL', '')
        else:  # Development or other environments
            webhook_base_url = os.getenv('NGROK_BASE_URL', '')

        if not webhook_base_url:
            raise ValueError(f"{'WEBHOOK_BASE_URL' if flask_env == 'production' else 'NGROK_BASE_URL'} is not set or empty.")

        # Validate URL format
        parsed_url = urlparse(webhook_base_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {webhook_base_url}")
        logger.debug(f"Validated webhook_base_url: {webhook_base_url}")

        # Extract foundation names and log API keys
        foundations_dep = []
        for key, value in os.environ.items():
            if key.endswith('_360_API_KEY'):
                foundation_name = key.replace('_360_API_KEY', '').lower()
                foundation_api_key = value

                if not foundation_api_key:
                    raise ValueError(f"API key for {foundation_name} is missing or empty.")

                foundation_dep = (foundation_name, foundation_api_key)
                foundations_dep.append(foundation_dep)

                logger.debug(f"Found foundation API key: {key} (Mapped as: {foundation_name})")

        # Return the gathered information in a dictionary
        result = {
            'flask_env': flask_env,
            'set_webhook': set_webhook,
            'webhook_base_url': webhook_base_url,
            'foundations_dep': foundations_dep
        }
        
        logger.debug(f"Environment variables loaded successfully: {result}")
        return result

    except Exception as e:
        logger.error(f"Error loading environment variables: {e}", exc_info=True)
        raise


def init_webhook_urls():
    try:
        env_variables = load_environment_variables()

        if env_variables.get('set_webhook'):
            logger.debug("INIT WEBHOOK --- Setting webhooks for all foundations...")

            foundations_dep = env_variables.get("foundations_dep")
            webhook_base_url = env_variables.get("webhook_base_url")

            for foundation_dep in foundations_dep:
                logger.debug(f"Setting webhook for {foundation_dep[0]}")

                set_webhook_config(foundation_name=foundation_dep[0],
                                   api_key=foundation_dep[1],
                                   webhook_base_url=webhook_base_url)
        else:
            logger.debug("SET_WEBHOOK_URL is not enabled. Skipping webhook setup.")

    except Exception as e:
        logger.error(f"Error during webhook initialization: {e}", exc_info=True)



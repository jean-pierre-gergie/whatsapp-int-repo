import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging 
import requests
import datetime
import jwt
from logger_setup.logger_setup import logger

# Load environment variables
load_dotenv()





def get_webhook_url():
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
        

        # Load the appropriate base URL based on FLASK_ENV
        if flask_env == 'production':
            webhook_base_url = os.getenv('WEBHOOK_BASE_URL', '')

        else:  # Development or other environments
            webhook_base_url = os.getenv('NGROK_BASE_URL', '')
        
        logger.debug(f"webhook_base_url: {webhook_base_url}")

        return webhook_base_url
    except Exception as e:
        logger.debug(f"Error loading environment variables: {e}", exc_info=True)
        logger.error(f"Error loading environment variables: ", exc_info=True)
        raise


def get_mongo_client():

    load_dotenv()

    username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
    password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
    host = os.getenv('MONGO_HOST')
    port = os.getenv('MONGO_PORT')

    client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")
    logger.debug(f"Loaded environment variables: MONGO_INITDB_ROOT_USERNAME={username}, MONGO_HOST={host}, MONGO_PORT={port}")
    pymongo_logger = logging.getLogger("pymongo")
    pymongo_logger.setLevel(logging.ERROR)

    return client

def get_all_foundation_names():
    try:
        # Establish connection to MongoDB client
        mongo_client = get_mongo_client()
        
        # Access the foundations collection in the foundations database
        foundations_collection = mongo_client['foundations_db']['foundations']

        # Retrieve all foundation names
        foundation_names = foundations_collection.distinct("foundation")
        logger.debug("======= Retrieved Foundation Names =======")
        logger.debug(f"{foundation_names}")
        logger.debug("=========================================")
        logger.debug("Successfully retrieved all foundation names.")
        return foundation_names
    except Exception as e:
        logger.error(f"Error retrieving foundation names: {e}")
        raise


def generate_jwt_token(secret_key, expiration_hours=12):
    """
    Generate a JWT token with an expiration time.
    """
    payload = {
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expiration_hours),
        'sub': 'webhook-auth'  # Subject can be customized as needed
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def set_webhook_config(foundation_name, api_key, webhook_base_url, jwt_token, max_attempts=2):
    try:
        #TODO update to new v2 url 
        url = 'http://waba.360dialog.io/v1/configs/webhook'
        secret_key = os.getenv('JWT_SECRET_KEY')
        

        


        headers = {
            'Content-Type': 'application/json',
            'D360-API-KEY': api_key
        }
        expected_url = f"{webhook_base_url}/webhook/{foundation_name}"
        data = {
            "url": expected_url,
                "headers": {
                "Authorization": f"Bearer {jwt_token}"
                }
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


def refresh_jwt(logger):
    try:
        secret_key = os.getenv("JWT_SECRET_KEY")
        webhook_url = get_webhook_url()
        logger.debug(f"webhook url : {webhook_url}")
        logger.info ("Refreshing JWT ...")
        if not secret_key:
            logger.error("JWT_SECRET_KEY is not set in environment variables.")
            return

        logger.info("Starting JWT refresh process.")

        foundations_names = get_all_foundation_names()
        logger.info(f"Foundations to process: {foundations_names}")

        mongo_client = get_mongo_client()

        foundations_collection = mongo_client['foundations_db']['foundations']
        revoked_tokens_collection = mongo_client['revoked_tokens_db']['revoked_tokens']

        for foundation_name in foundations_names:
            try:
                logger.debug(f"Processing foundation: {foundation_name}")
                foundation_doc = foundations_collection.find_one({"foundation": foundation_name})

                if not foundation_doc:
                    logger.warning(f"No document found for foundation: {foundation_name}")
                    continue

                old_jwt = foundation_doc.get('jwt')

                if old_jwt:
                    try:
                        # Add the old JWT to the revoked tokens collection
                        revoked_tokens_collection.insert_one({
                            "foundation": foundation_name,
                            "revoked_jwt": old_jwt,
                            "revoked_at": datetime.datetime.utcnow()
                        })
                        logger.info(f"Old JWT for {foundation_name} added to revoked tokens.")
                    except Exception as e:
                        logger.error(f"Failed to add old JWT to revoked tokens for {foundation_name}: {e}")

                # Generate a new JWT token
                new_jwt_token = generate_jwt_token(secret_key)

                # Update webhook configuration
                set_webhook_config(
                    foundation_name=foundation_name,
                    api_key=foundation_doc['api_key'],
                    webhook_base_url=webhook_url,
                    jwt_token=new_jwt_token
                )
                logger.debug(f"Webhook updated for foundation: {foundation_name}")

                # Update the foundations collection with the new JWT
                foundations_collection.update_one(
                    {"foundation": foundation_name},
                    {"$set": {"jwt": new_jwt_token}}
                )
                logger.debug(f"JWT token refreshed for foundation: {foundation_name}")
            except Exception as e:
                logger.error(f"Error processing foundation {foundation_name}: {e}")

        logger.info("JWT refresh process completed.")
    except Exception as e:
        logger.error(f"Critical error in refresh_jwt...")
        logger.debug(f"Critical error in refresh_jwt: {e}")
        
    











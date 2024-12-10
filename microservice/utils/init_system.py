
from utils.webhook_get_api_key_helper import get_api_keys
from utils.init_foundations_dbs import init_foundations_dbs
from utils.add_users_to_db import add_users_to_db
from utils.webhook_jwt_refresh_helper import refresh_jwt

def init_system(logger):
    """
    Initializes the system by performing the following steps:
    1. Generates API keys for all foundations.
    2. Initializes databases and collections for the foundations.
    3. Populates the user credentials database with initial user data.
    4. Refresh the JWT token for webhook urls

    This function handles errors gracefully, logging debug and error messages 
    to aid in troubleshooting.
    """

    try:
        logger.debug("Starting system initialization...")

    
        logger.debug("Generating API keys for foundations...")
        foundations_api_keys = get_api_keys(logger)
        logger.info("API keys generated successfully.")

        logger.debug("Initializing foundation databases...")
        init_foundations_dbs(foundations_api_keys,logger=logger)
        logger.info("Foundation databases initialized successfully.")


        logger.debug("Adding users to the database...")
        add_users_to_db(logger=logger)
        logger.info("Users added to the database successfully.")


        logger.debug("Setting JWT Token for webhook...")
        refresh_jwt(logger)
        logger.debug("JWT  refreshed  successfully")

        logger.info("System initialization completed successfully.")


    except Exception as e:
        logger.error(f"An error occurred during system initialization: {e}", exc_info=True)








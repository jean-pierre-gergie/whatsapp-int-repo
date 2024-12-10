
from utils.utils import get_mongo_client
from utils.generate_api_keys import get_api_keys
from utils.add_users_to_db import add_users_to_db
from utils.init_foundations_dbs import init_foundations_dbs
from logger.set_logger import get_logger

logger  = get_logger()

def init_system():
    """
    Initializes the system by performing the following steps:
    1. Generates API keys for all foundations.
    2. Initializes databases and collections for the foundations.
    3. Populates the user credentials database with initial user data.

    This function handles errors gracefully, logging debug and error messages 
    to aid in troubleshooting.
    """
    try:
        logger.debug("Starting system initialization...")

        # Generate API keys
        logger.debug("Generating API keys for foundations...")
        foundations_api_keys = get_api_keys()
        logger.info("API keys generated successfully.")

        # Initialize all foundations databases
        logger.debug("Initializing foundation databases...")
        init_foundations_dbs(foundations_api_keys)
        logger.info("Foundation databases initialized successfully.")

        # Add users to the database
        logger.debug("Adding users to the database...")
        add_users_to_db()
        logger.info("Users added to the database successfully.")

        logger.info("System initialization completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during system initialization: {e}", exc_info=True)

if __name__ =="__main__":
    init_system()

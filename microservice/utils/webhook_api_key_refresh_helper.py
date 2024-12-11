
from utils.webhook_get_api_key_helper import get_api_keys
from utils.mongo_db_helper import get_mongo_client


def update_foundations_api_keys(foundations_api_keys,logger):
    """
    Updates the API key for each foundation specified in the given dictionary.
    Parameters:
        foundations_api_keys (dict): A dictionary where keys are foundation names
                                     and values are the new API keys.
    """
    try:
        client = get_mongo_client()
        foundations_db = client['foundations_db']
        foundations_collection = foundations_db['foundations']

        for foundation_name, new_api_key in foundations_api_keys.items():
            result = foundations_collection.update_one(
                {"foundation": foundation_name},
                {"$set": {"api_key": new_api_key}}
            )

            if result.matched_count > 0:
                logger.info(f"Updated API key for foundation '{foundation_name}'.")
            else:
                logger.warning(f"No document found for foundation '{foundation_name}'. API key update skipped.")

        logger.info("API key updates completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred while updating API keys: {e}", exc_info=True)


def webhook_refresh_api_key(logger):
    """
    Refreshes the API keys for all foundations by retrieving updated API keys 
    and applying them to the database.
    
    Parameters:
        logger: The logger instance for logging messages.
        
    Workflow:
        1. Retrieves updated API keys from the `get_api_keys` function.
        2. Updates the foundations' API keys in the database by calling 
           `update_foundations_api_keys`.
    """
    try:
        logger.debug("Starting API key refresh process.")

        # Retrieve the updated API keys
        foundations_api_keys = get_api_keys(logger)
        logger.debug(f"Retrieved API keys: {foundations_api_keys}")

        # Update the API keys in the database
        update_foundations_api_keys(foundations_api_keys=foundations_api_keys, logger=logger)
        logger.info("API key refresh process completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred while refreshing API keys: {e}", exc_info=True)



from utils.mongo_db_helper import get_mongo_client ,create_collection_if_not_exists,populate_collection_from_json,create_index
from logger_setup.logger_setup import logger



def init_foundations_dbs(foundations_api_keys,logger):
    """
    Initializes databases and collections for multiple foundations.
    Creates or updates documents in the 'foundations' collection and sets up
    dynamic databases and collections for each foundation based on their API keys.
    """
    try:
        client = get_mongo_client()
        foundations_db = client['foundations_db']
        foundations_collection = foundations_db['foundations']

        for foundation_name, api_key in foundations_api_keys.items():
            auto_reply_message = f"Default auto-reply message for {foundation_name}"
            document = {
                "foundation": foundation_name,
                "api_key": api_key,
                "whatsapp_data_db": f"whatsapp_data_{foundation_name}",
                "agent_data_db": f"agent_data_{foundation_name}",
                "auto_reply_message": auto_reply_message
            }

            if not foundations_collection.find_one({"foundation": foundation_name}):
                foundations_collection.insert_one(document)
                # logger.info(f"Inserted document for foundation '{foundation_name}'.")
            else:
                foundations_collection.update_one(
                    {"foundation": foundation_name},
                    {"$set": {"auto_reply_message": auto_reply_message}}
                )
                # logger.info(f"Updated document for foundation '{foundation_name}'.")

        for prefix in foundations_api_keys:
            databases = {
                f"whatsapp_data_{prefix}": [
                    'campaign', 'campaign_responses', 'language', 'members',
                    'templates', 'webhook_latest_from_user',
                    'webhook_latest_to_user', 'webhook_responses'
                ],
                f"agent_data_{prefix}": ["rooms"]
            }

            for db_name, collections in databases.items():
                db = client[db_name]
                for collection_name in collections:
                    create_collection_if_not_exists(db, collection_name)

            agent_db = client[f'agent_data_{prefix}']
            rooms_collection = agent_db['rooms']
            create_index(rooms_collection, 'last_message_time', 'last_message_time_desc')

            main_db = client[f'whatsapp_data_{prefix}']
            language_collection = main_db['language']
            if language_collection.count_documents({}) == 0:
                populate_collection_from_json(language_collection, '/app/init_data/languages.json')

        logger.info("Foundations databases initialized successfully.")

    except Exception as e:
        logger.error(f"An error occurred during foundations DB initialization: {e}", exc_info=True)







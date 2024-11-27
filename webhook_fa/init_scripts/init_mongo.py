import logging
from utils_init.utils_init import *


# Configure the logger
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


def create_collections():
    """Initialize collections in dynamic databases based on available 360 API keys."""
    client = get_mongo_client()
    api_keys = get_360_api_keys()

    user_credentials_db = client['user_credentials_db'] ## newly created 
    user_credentials_collection = user_credentials_db['user_credentials']
    populate_collection_from_json(user_credentials_collection, '/app/init_data/users.json', unique_field='user_id')

    

    foundations_db = client['foundations_db']
    foundations_collection = foundations_db['foundations']


    with open("/app/init_data/foundation_default_auto_reply.json", "r", encoding="utf-8") as f:
        auto_reply_messages = json.load(f)

    for foundation_name, api_key in api_keys.items():

        auto_reply_message = auto_reply_messages.get(
                foundation_name, 
                f"Default auto-reply message for {foundation_name}"
            )
        

        document = {
            "foundation": foundation_name,
            "api_key": api_key,
            "whatsapp_data_db": f"whatsapp_data_{foundation_name}",
            "agent_data_db": f"agent_data_{foundation_name}",
            "auto_reply_message": auto_reply_message
        }
        
        # Insert document if not already present
        if not foundations_collection.find_one({"foundation": foundation_name}):
            foundations_collection.insert_one(document)
            logger.info(f"Inserted document for foundation '{foundation_name}' with API key.")
        else:

            foundations_collection.update_one(
                    {"foundation": foundation_name},
                    {"$set": {"auto_reply_message": auto_reply_message}}
                )
            logger.info(f"Updated document for foundation '{foundation_name}' with auto-reply message.")

    
    for prefix in api_keys:
        # Define dynamic database names for each API key
        databases = {
            f"whatsapp_data_{prefix}": [
                'campaign', 'campaign_responses', 'language', 'members',
                'templates', 'webhook_latest_from_user',
                'webhook_latest_to_user', 'webhook_responses'
            ],
            f"agent_data_{prefix}": ["rooms"]
        }
        
        # Initialize collections for each database
        for db_name, collections in databases.items():
            db = client[db_name]
            for collection_name in collections:
                create_collection_if_not_exists(db, collection_name)
        
        # Additional setup for collections that require indexes or initial data
        agent_db = client[f'agent_data_{prefix}']
        rooms_collection = agent_db['rooms']
        create_index(rooms_collection, 'last_message_time', 'last_message_time_desc')

        main_db = client[f'whatsapp_data_{prefix}']
        language_collection = main_db['language']
        if language_collection.count_documents({}) == 0:
            populate_collection_from_json(language_collection, '/app/init_data/languages.json')
        
        




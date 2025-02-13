
from utils.send_campaigns_helpers import get_mongo_client
from logger_setup.logger_setup import logger



def get_dependencies_by_foundation(foundation_name, mongo_url):
    try:
        # Connect to MongoDB
        logger.debug(f"Connecting to MongoDB at {mongo_url}")
        logger.info (f"Connecting to MongoDB...")
        
        mongo_client = get_mongo_client(mongo_url)
        
        # Access the 'foundations' collection in 'foundations_db'
        foundations_collection = mongo_client['foundations_db']['foundations']
        logger.info(f"Accessing foundations collection to find data for foundation '{foundation_name}'")
        
        # Query to find the foundation document by foundation_name
        foundation_doc = foundations_collection.find_one({'foundation': foundation_name})
        
        if not foundation_doc:
            error_message = f"Foundation '{foundation_name}' not found in the database."
            logger.error(error_message)
            raise ValueError(error_message)
        
        # Retrieve the necessary fields from the document
        api_key_360 = foundation_doc.get('api_key')
        whatsapp_data_db_name = foundation_doc.get('whatsapp_data_db')
        agent_data_db_name = foundation_doc.get('agent_data_db')
        
        if not api_key_360 or not whatsapp_data_db_name or not agent_data_db_name:
            error_message = "One or more required fields are missing from the foundation document."
            logger.error(error_message)
            raise ValueError(error_message)
        
        # Access the databases directly by their names
        logger.info(f"Accessing databases for foundation '{foundation_name}'")
        whatsapp_data_db = mongo_client[whatsapp_data_db_name]
        agent_data_db = mongo_client[agent_data_db_name]
        
        # Pretty debug logging
        logger.debug(f"""
        =================================================
        Retrieved Dependencies for Foundation: {foundation_name}
        =================================================
        WhatsApp Database:   '{whatsapp_data_db_name}'
        Agent Database:      '{agent_data_db_name}'
        API Key:             '{api_key_360}'
        =================================================
        """)
        
        logger.info(f"Successfully retrieved dependencies for foundation '{foundation_name}'")
        return whatsapp_data_db, agent_data_db, api_key_360
    
    except Exception as e:
        logger.exception(f"An error occurred while fetching dependencies for foundation '{foundation_name}': {e}")
        raise
        
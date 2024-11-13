
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging 

from utils.generate_long_lived_token import generate_forever_token
import socketio
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError
from utils.helper_functions import WhatsAppDataHandler
from utils.auto_reply_helper import AutoReplyHandler

logging.basicConfig(
    level=logging.DEBUG,
    format="- %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


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


def get_foundation_dependencies(foundation_name):
    
    try:
        # Establish connection to MongoDB client
        mongo_client = get_mongo_client()
        
        # Access the foundations collection in the foundations database
        foundations_collection = mongo_client['foundations_db']['foundations']
        foundation_doc = foundations_collection.find_one({"foundation": foundation_name})

        if not foundation_doc:
            raise ValueError(f"No foundation found with name: {foundation_name}")

        whatsapp_data_db = foundation_doc.get("whatsapp_data_db", "whatsapp_data")
        agent_data_db = foundation_doc.get("agent_data_db", "agent_data")

        # Define the collections
        RAW_COLLECTION = 'webhook_responses'
        BUSINESS_TO_USER_COLLECTION = 'webhook_latest_to_user'
        USER_TO_BUSINESS_COLLECTION = 'webhook_latest_from_user'
        ROOMS_COLLECTION = 'rooms'

        main_db = mongo_client[whatsapp_data_db]
        raw_collection = main_db[RAW_COLLECTION]
        business_to_user_collection = main_db[BUSINESS_TO_USER_COLLECTION]
        user_to_business_collection = main_db[USER_TO_BUSINESS_COLLECTION]

        agent_db = mongo_client[agent_data_db]
        chat_rooms_collection = agent_db[ROOMS_COLLECTION]

        api_key_360 = foundation_doc.get("api_key", "api_key")

        logger.debug(f"Successfully retrieved dependencies for foundation: {foundation_name}")
        return {
            "raw_collection": raw_collection,
            "business_to_user_collection": business_to_user_collection,
            "user_to_business_collection": user_to_business_collection,
            "chat_rooms_collection": chat_rooms_collection,
            "api_key_360":api_key_360
        }
    except ValueError as ve:
        logger.error(f"ValueError: {ve}")
        raise
    except Exception as e:
        logger.error(f"Error retrieving dependencies for foundation '{foundation_name}': {e}")
        raise

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

def create_handlers_for_all_foundations():
    logger.debug("Cretting all handlers for all foundations...")
    try:
        foundation_names = get_all_foundation_names()
        handlers = {}

        for foundation_name in foundation_names:
            try:
                # Retrieve dependencies
                dependencies = get_foundation_dependencies(foundation_name)
                
                token = generate_forever_token()
                logger.info(f"WEBHOOK --- --- Token generated for {foundation_name}.")
                
                sio = socketio.Client()

                @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5), reraise=True)
                def connect_to_agent_service():
                    # Connect using the foundation-specific namespace
                    namespace = f"/agent/agent_namespace/{foundation_name}"
                    sio.connect(f"http://agent:5001/?token={token}", namespaces=[namespace])
                    logger.info(f"Successfully connected to the agent service for {foundation_name} with JWT authentication.")

                connect_to_agent_service()

                

                auto_reply_handler = AutoReplyHandler(chat_rooms_collection=dependencies['chat_rooms_collection'],
                                                      api_key_360=dependencies['api_key_360'],
                                                      logger=logger)
                handler = WhatsAppDataHandler(
                    dependencies['raw_collection'],
                    dependencies['user_to_business_collection'],
                    dependencies['business_to_user_collection'],
                    dependencies['chat_rooms_collection'],
                    auto_reply_handler=auto_reply_handler,
                    name_space=f"/agent/agent_namespace/{foundation_name}",
                    sio=sio
                )

                handlers[foundation_name] = handler
                logger.debug(f"Handler created for foundation: {foundation_name}")

            except Exception as e:
                logger.error(f"Error creating handler for foundation '{foundation_name}': {e}")
        
        logger.debug("======= Handlers Dictionary =======")
        logger.debug(f"{handlers}")
        logger.debug("===================================")
        return handlers
    except Exception as e:
        logger.error(f"Error creating handlers for all foundations: {e}")
        raise

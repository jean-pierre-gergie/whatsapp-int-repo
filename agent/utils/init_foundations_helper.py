
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging 



logging.basicConfig(
    level=logging.DEBUG,
    format="- %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

pymongo_logger = logging.getLogger("pymongo")
pymongo_logger.setLevel(logging.ERROR)



def get_mongo_client():

    load_dotenv()

    username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
    password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
    host = os.getenv('MONGO_HOST')
    port = os.getenv('MONGO_PORT')

    client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")
    logger.debug(f"Loaded environment variables: MONGO_INITDB_ROOT_USERNAME={username} ,MONGO_HOST={host} MONGO_PORT={port}")
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
        logger.debug("======= Retrieved Foundation Names from agent  =======")
        logger.debug(f"{foundation_names}")
        logger.debug("======================================================")
        logger.debug("Successfully retrieved all foundation names.")
        return foundation_names
    except Exception as e:
        logger.error(f"Error retrieving foundation names: {e}")
        raise

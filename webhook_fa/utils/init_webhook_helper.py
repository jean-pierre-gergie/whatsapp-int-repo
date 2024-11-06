
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


def get_foundation_dependencies_names(foundation_name):
    mongo_db  = get_mongo_client()

    foundations = mongo_db['foundations_db']['foundations']

    whatsapp_data_db = mongo_db.foun









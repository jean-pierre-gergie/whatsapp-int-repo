from datetime import timedelta
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging
from .logger_setup.logger_setup import LoggerSetup

logger = LoggerSetup(__name__).get_logger()
load_dotenv()



class Config:
    
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 1)))
    
    API_KEY = os.getenv('DEFAULT_API_KEY')
    DEFAULT_DB = 'whatsapp_data_maronite'

    MICROSERVICE_BASE_URL = os.getenv("MICROSERVICE_BASE_URL")

    username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
    password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
    host = os.getenv('MONGO_HOST')
    port = os.getenv('MONGO_PORT')

    MONGODB_URI = f"mongodb://{username}:{password}@{host}:{port}/"

    @staticmethod
    def get_api_keys(MONGODB_URI):
        api_keys = {}
        try:
            client = MongoClient(MONGODB_URI)
            db = client["foundations_db"]
            collection = db["foundations"]

            for document in collection.find():
                foundation_name = document.get("foundation")
                api_key = document.get("api_key")
                if foundation_name and api_key:
                    api_keys[foundation_name] = {
                        "api_key": api_key,
                        "whatsapp_data_db": f"whatsapp_data_{foundation_name}",
                        "agent_data_db": f"agent_data_{foundation_name}"
                    }
                else:
                    logger.warning(f"Incomplete data for foundation '{foundation_name}': {document}")

            if not api_keys:
                logger.warning("No API keys found in 'foundations' collection.")
        except Exception as e:

            logger.error(f"An error occurred while fetching API keys:")

        return api_keys

    FOUNDATION_CONFIGS = get_api_keys(MONGODB_URI)

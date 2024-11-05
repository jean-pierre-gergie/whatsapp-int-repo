from datetime import timedelta
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging


# Load environment variables from .env file
load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class Config:
    # Load sensitive values from environment variables
    SECRET_KEY = os.getenv('SECRET_KEY')  
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')  
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 1)))
    
    API_KEY = os.getenv('DEFAULT_API_KEY')  
    DEFAULT_DB ='whatsapp_data_maronite'

    MICROSERVICE_BASE_URL= os.getenv("MICROSERVICE_BASE_URL")

    # MongoDB settings
    username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
    password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
    host = os.getenv('MONGO_HOST')
    port = os.getenv('MONGO_PORT')
    
   
    MONGODB_URI = f"mongodb://{username}:{password}@{host}:{port}/"


   
    def get_api_keys(MONGODB_URI):
        """Fetch all API keys and corresponding database names from the 'foundations' collection in MongoDB."""
        api_keys = {}
        try:
            # Connect to MongoDB
            client = MongoClient(MONGODB_URI)
            db = client["foundations_db"]
            collection = db["foundations"]
            
            # Query for all foundation documents
            for document in collection.find():
                foundation_name = document.get("foundation")
                api_key = document.get("api_key")
                if foundation_name and api_key:
                    # Assume corresponding database names follow a pattern
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
            logger.error(f"An error occurred while fetching API keys: {e}")
        
        return api_keys

    FOUNDATION_CONFIGS = get_api_keys(MONGODB_URI)
    
from datetime import timedelta
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Load sensitive values from environment variables
    SECRET_KEY = os.getenv('SECRET_KEY')  
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')  
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 1)))
    API_KEY = os.getenv('API_KEY')  
    
    # MongoDB settings
    username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
    password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
    host = os.getenv('MONGO_HOST')
    port = os.getenv('MONGO_PORT')
    
    database_name = 'whatsapp_data'
    MONGODB_URI = f"mongodb://{username}:{password}@{host}:{port}/"
    MONGODB_NAME = 'whatsapp_data'

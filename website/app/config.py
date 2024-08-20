from datetime import timedelta
import os

class Config:
    SECRET_KEY = '[Wfrs!HR7B<^NL>'
    JWT_SECRET_KEY = 'your_jwt_secret_key' 
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    API_KEY = 'iHB20OJavj7OcHzCmfIKyCHlAK'
    
    from dotenv import load_dotenv
    load_dotenv()
    username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
    password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
    host = os.getenv('MONGO_HOST') 
    port = os.getenv('MONGO_PORT')      
    
    MONGODB_URI = f"mongodb://{username}:{password}@{host}:{port}/"
    MONGODB_NAME = 'whatsapp_data'
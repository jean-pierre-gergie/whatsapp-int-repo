from datetime import timedelta
import os

class Config:
    SECRET_KEY = '[Wfrs!HR7B<^NL>'
    JWT_SECRET_KEY = 'your_jwt_secret_key' 
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    API_KEY = 'iHB20OJavj7OcHzCmfIKyCHlAK'
    
    from dotenv import load_dotenv
    load_dotenv()
    username = os.getenv('MONGO_INITDB_ROOT_USERNAME','rtenn')
    password = os.getenv('MONGO_INITDB_ROOT_PASSWORD','123456')
    host = os.getenv('MONGO_HOST','mongodb_container')
    port = os.getenv('MONGO_PORT',27017)
    database_name = 'whatsapp_data'
    MONGODB_URI = f"mongodb://{username}:{password}@{host}:{port}/"
    MONGODB_NAME = 'whatsapp_data'
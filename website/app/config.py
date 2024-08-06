from datetime import timedelta

class Config:
    SECRET_KEY = '[Wfrs!HR7B<^NL>'
    JWT_SECRET_KEY = 'your_jwt_secret_key' 
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=10)
    API_KEY = 'iHB20OJavj7OcHzCmfIKyCHlAK'
    MONGODB_URI = 'mongodb://mongodb_container:27017/'  
    MONGODB_NAME = 'whatsapp_data'
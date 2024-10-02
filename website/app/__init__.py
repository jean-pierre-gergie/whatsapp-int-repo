import logging
from flask import Flask
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from .config import Config

jwt = JWTManager()

# Initialize the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a stream handler to log messages to the console (stdout)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Define the log message format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)

def create_app():
    # Logging initialization
    logger.debug("Starting create_app()")

    # Specifically configure pymongo's logging level
    pymongo_logger = logging.getLogger("pymongo")
    pymongo_logger.setLevel(logging.WARNING)

    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize JWT
    jwt.init_app(app)
    logger.debug("JWT initialized.")

    # Initialize MongoDB
    try:
        client = get_mongo_client()
        logger.info("MongoDB client initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing MongoDB client: {e}")  

    app.mongo = client[app.config['MONGODB_NAME']]

    # Register blueprints
    with app.app_context():
        from .views import auth, templates, campaigns, upload_data
        app.register_blueprint(auth.bp)
        app.register_blueprint(templates.bp)
        app.register_blueprint(campaigns.bp)
        app.register_blueprint(upload_data.bp)  
        logger.debug("Blueprints registered.")

    return app

def get_mongo_client():
    logger.debug(f"Connecting to MongoDB with URI: {Config.MONGODB_URI}")
    return MongoClient(Config.MONGODB_URI)

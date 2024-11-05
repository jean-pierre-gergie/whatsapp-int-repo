import logging
from flask import Flask
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from .config import Config
from art import text2art ,art
from termcolor import colored


jwt = JWTManager()

# Initialize the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a stream handler to log messages to the console (stdout)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Define the log message format
formatter = logging.Formatter('- %(name)s - %(levelname)s - %(message)s')
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

    log_config()

    # Initialize JWT
    jwt.init_app(app)
    logger.debug("JWT initialized.")

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        token_in_db = app.mongo['DEFAULT_DB'].revoked_tokens.find_one({'jti': jti})
        return token_in_db is not None

    # # Initialize MongoDB
    try:
        client = get_mongo_client()
        logger.info("MongoDB client initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing MongoDB client: {e}")  
    

    app.mongo = client
    app.default_db = client[app.config['DEFAULT_DB']]
    

    # # Register blueprints
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


def log_config():
    """Logs the app configuration settings in a structured format, including a blue and grey ASCII logo."""
    
    # Generate the ASCII art logo
    ascii_logo = text2art("OC MYMADA", font='starwars')
    # ascii_logo = art("OCMYMADA", "random-medium")
    # 
    # Print the logo in blue and grey shades
    for line in ascii_logo.splitlines():
        print(line)
    
    logger.info("Application Configuration Settings:")
    logger.info("============================================")
    
    # Standard configurations
    logger.info(f"SECRET_KEY: {'[HIDDEN]' if Config.SECRET_KEY else '[NOT SET]'}")
    logger.info(f"JWT_SECRET_KEY: {'[HIDDEN]' if Config.JWT_SECRET_KEY else '[NOT SET]'}")
    logger.info(f"JWT_ACCESS_TOKEN_EXPIRES: {Config.JWT_ACCESS_TOKEN_EXPIRES}")
    logger.info(f"MONGODB_URI: {Config.MONGODB_URI}")
    logger.info(f"MICROSERVICE_BASE_URL: {Config.MICROSERVICE_BASE_URL}")

    # Foundation-specific configurations
    logger.info("Foundation Configurations:")
    for foundation, settings in Config.FOUNDATION_CONFIGS.items():
        logger.info(f"  Foundation: {foundation}")
        logger.info(f"    API Key: {'[HIDDEN]' if settings['api_key'] else '[NOT SET]'}")
        logger.info(f"    WhatsApp Database: {settings['whatsapp_data_db']}")
        logger.info(f"    Agent Database: {settings['agent_data_db']}")
        logger.info("  -----------------------------------")
    logger.info("============================================")
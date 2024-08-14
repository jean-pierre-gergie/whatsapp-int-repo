from flask import Flask
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from .config import Config
import os

jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    jwt.init_app(app)

    mongodb_username = os.getenv("MONGODB_USERNAME")
    mongodb_password = os.getenv("MONGODB_PASSWORD")

    client = MongoClient(f"mongodb://{mongodb_username}:{mongodb_password}@mongodb_container:27017/whatsapp_data")
    app.mongo = client[app.config['MONGODB_NAME']]

    with app.app_context():
        from .views import auth, templates, campaigns, upload_data
        app.register_blueprint(auth.bp)
        app.register_blueprint(templates.bp)
        app.register_blueprint(campaigns.bp)
        app.register_blueprint(upload_data.bp)

    return app

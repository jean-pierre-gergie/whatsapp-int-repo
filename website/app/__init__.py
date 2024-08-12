from flask import Flask
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from .config import Config

jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    jwt.init_app(app)

    client = MongoClient(app.config['MONGODB_URI'])
    app.mongo = client[app.config['MONGODB_NAME']]

    with app.app_context():
        from .views import auth, templates, campaigns, upload_data
        app.register_blueprint(auth.bp)
        app.register_blueprint(templates.bp)
        app.register_blueprint(campaigns.bp)
        app.register_blueprint(upload_data.bp)

    return app

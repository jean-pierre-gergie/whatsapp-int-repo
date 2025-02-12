from app import create_app
from flask import request
import os
import threading
from app.logger_setup.logger_setup import LoggerSetup


app = create_app()

@app.before_request
def before_request():
    token = request.cookies.get('access_token_cookie')
    if token:
        request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {token}'

if __name__ == '__main__':
    logger = LoggerSetup(__name__).get_logger()

    MODE = os.getenv('MODE', 'production').lower()
    DEBUG = True if MODE == 'developement' else False
    logger.info(f"MODE: {MODE.upper()}, DEBUG: {DEBUG}")
    if not DEBUG:
        FLASK_APP = os.getenv("FLASK_APP", "app.py")
        FLASK_ENV = os.getenv("FLASK_ENV", "production")
        WERKZEUG_RUN_MAIN = os.getenv("WERKZEUG_RUN_MAIN", "true")

    else:
        app.run(host="0.0.0.0",debug=DEBUG , port=1313)
import eventlet
eventlet.monkey_patch() 

import logging
from flask import Flask, render_template , request,jsonify
from flask_socketio import SocketIO, join_room, leave_room, send, emit,Namespace
import os 
from utils.logging_config import configure_logging
from utils.jwt_helper import verify_jwt
from utils.init_foundations_helper import get_all_foundation_names

from services.agent_namespace import create_dynamic_namespaces
from dotenv import load_dotenv



app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  
app.config['PRODUCTION'] = os.getenv('FLASK_ENV') == 'production'

logger = configure_logging()



# Initialize SocketIO with eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

founsation_names = get_all_foundation_names()
create_dynamic_namespaces(socketio=socketio,
                          foundation_names=founsation_names)


@app.route('/agent_server')
@verify_jwt
def index():
    # Get the foundation name from the query parameters
    foundation_name = request.args.get('foundation_name')
    logger.info(f"Received request with foundation_name: {foundation_name}")

    # Construct the namespace dynamically
    name_space = f"/agent/agent_namespace/{foundation_name}"
    logger.info(f"Constructed namespace: {name_space}")

    # Dynamically set the base path
    base_path = '/agent' if app.config.get('PRODUCTION', False) else ''
    logger.info(f"Determined base path: {base_path}")

    # Determine the environment
    flask_env = os.getenv('FLASK_ENV', 'development')  # Default to 'development' if not set
    logger.info(f"Environment detected: {flask_env}")

    # Dynamically select the socket URL based on the environment
    if flask_env == 'production':
        socket_url = os.getenv('SOCKET_URL_PRODUCTION', 'https://www.omnichanneltv.com/agent/socket.io/')
    else:
        socket_url = os.getenv('SOCKET_URL_DEVELOPMENT', 'http://localhost:5001/socket.io/')
    logger.info(f"Selected socket URL: {socket_url}")

    # Render the template and log the final configuration
    logger.info(f"Rendering template with base_path: {base_path}, socket_url: {socket_url}, name_space: {name_space}")
    logger.info(f"Foundation Name {foundation_name}")
    return render_template(
        'index.html',
        socket_url=socket_url,
        name_space=name_space,
        foundation_name=foundation_name,
        base_path=base_path
    )

if __name__ == '__main__':  
    logger.info("Starting Flask-SocketIO server")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
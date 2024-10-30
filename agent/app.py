import eventlet
eventlet.monkey_patch() 

import logging
from flask import Flask, render_template , request,jsonify
from flask_socketio import SocketIO, join_room, leave_room, send, emit,Namespace

import os 
from utils.db_helper import get_rooms_collection , handle_chat_room
from utils.logging_config import configure_logging
from utils.jwt_helper import verify_jwt

from services.socketio_events import register_socketio_events 
from services.agent_namespace import AgentNamespace
from dotenv import load_dotenv



app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  


logger = configure_logging()

load_dotenv()

# Initialize SocketIO with eventlet
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
socketio.on_namespace(AgentNamespace('/agent/agent_namespace'))

active_agent_namespace = '/agent/agent_namespace'
# socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/agent_server')
@verify_jwt
def index():
    token = request.args.get('token')  # Get the token that was passed during the redirect
    # Render the template with the token included as a context variable
    return render_template('index.html', socket_url='https://www.ocmymada.com/agent/socket.io/', token=token)

register_socketio_events(socketio)




if __name__ == '__main__':  
    logger.info("Starting Flask-SocketIO server")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
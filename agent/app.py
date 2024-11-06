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
    # token = request.args.get('token')  # Get the token that was passed during the redirect
    # Render the template with the token included as a context variable
    # return render_template('index.html', socket_url='https://www.ocmymada.com/agent/socket.io/', token=token)
    return render_template('index.html', socket_url='https://www.ocmymada.com/agent/socket.io/')




if __name__ == '__main__':  
    logger.info("Starting Flask-SocketIO server")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
import eventlet
eventlet.monkey_patch() 

import logging
from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, leave_room, send, emit,Namespace
import requests
import os 
from utils.db_helper import get_rooms_collection , handle_chat_room
from utils.dialog_360 import send_message_to_users_through_360
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime




logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')

pymongo_logger = logging.getLogger('pymongo')
pymongo_logger.setLevel(logging.WARNING)


chat_rooms_collection  = get_rooms_collection()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  

class AgentNamespace(Namespace):
    def on_connect(self):
        print('Client connected')

    def on_disconnect(self):
        print('Client disconnected')

# Initialize SocketIO with eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
socketio.on_namespace(AgentNamespace('/agent_namespace'))
socketIO_URL = os.getenv('CHAT_AGENT_URL')

@app.route('/agent_server')
def index():
    return render_template('index.html', socket_url='https://www.ocmymada.com/agent/socket.io/')

@socketio.on('connect', namespace='/agent_namespace')
def connect():
    logger.info(f"Client connected to '/agent_namespace'")

    try:
        # Fetch only the 'room_id' field from all documents
        chat_rooms = chat_rooms_collection.find({}, {'room_id': 1, '_id': 0})  
        room_ids = [chat['room_id'] for chat in chat_rooms]  # Extract room IDs
        logger.info(f"Available rooms: {room_ids}")
        emit('available_rooms', room_ids, namespace='/agent_namespace')
    except Exception as e:
        logger.error(f"Error fetching room IDs: {str(e)}")
        emit('error', {'message': 'Failed to fetch chat rooms'}, namespace='/agent_namespace')

@socketio.on('new_room', namespace='/agent_namespace')
def handle_new_room(data):
    """
    Event handler for 'new_room' events.
    """
    logger.info(f"EVENT---Received 'new_room' event with data: {data}")
    try:
    # Fetch only the 'room_id' field from all documents
        chat_rooms = chat_rooms_collection.find({}, {'room_id': 1, '_id': 0})  
        room_ids = [chat['room_id'] for chat in chat_rooms]  # Extract room IDs
        logger.info(f"EVENT---Added--Available rooms: {room_ids}")
        emit('available_rooms', room_ids, namespace='/agent_namespace')
    except Exception as e:
        logger.error(f"Error fetching room IDs: {str(e)}")
        emit('error', {'message': 'Failed to fetch chat rooms'}, namespace='/agent_namespace')

@socketio.on('message_from_user', namespace='/agent_namespace')
def handle_message(data):
    """
    Event handler for 'message_from_user' events.
    """
    logger.info(f"EVENT-message_from_user-Received event with data: {data}")
    
    room_id = data.get('room')
    message_body = data.get('message')
    sender = data.get('sender', 'system')
    
    try:
        # Emit the received message to the same room
        socketio.emit('message_from_user', data, room=room_id, namespace='/agent_namespace')
        logger.info(f"EVENT-message_from_user-Sent message to room {room_id}: {message_body}")
        
        # Fetch and reorder the rooms, moving the active room to the top
        chat_rooms = chat_rooms_collection.find({}, {'room_id': 1, '_id': 0})
        room_ids = [chat['room_id'] for chat in chat_rooms]
        
        # Move the active room to the top of the list
        if room_id in room_ids:
            room_ids.remove(room_id)
        room_ids.insert(0, room_id)
        
        # Emit the updated list of rooms
        socketio.emit('available_rooms', room_ids, namespace='/agent_namespace')
        logger.info(f"EVENT-message_from_user-Updated available rooms: {room_ids}")
    
    except Exception as e:
        logger.error(f"Error processing message or fetching room IDs: {str(e)}")
        emit('error', {'message': 'Failed to process message or fetch chat rooms'}, namespace='/agent_namespace')

   
@socketio.on('message_from_business', namespace='/agent_namespace')
def handle_message(data):
    """
    Event handler for 'message_from_business' events.
    """
    try:
        logger.info(f"EVENT-message_from_business-Received event with data: {data}")
        
        # Extracting information from the event data
        room_id = data.get('room')
        message_body = data.get('message')
        sender = data.get('sender', 'system')
        
        if not room_id or not message_body:
            logger.warning(f"EVENT-message_from_business-Missing required information: room_id={room_id}, message_body={message_body}")
            return

        try:
            # Emit the received message to the same room
            logger.debug(f"EVENT-message_from_business-Emitting message to room {room_id}")
            socketio.emit('message_from_business', data, room=room_id, namespace='/agent_namespace')
        except Exception as e:
            logger.error(f"EVENT-message_from_business-Error emitting message to room {room_id}: {e}")
            return

        try:
            # Sending message through 360dialog
            send_message_to_users_through_360(room_id, message=message_body)
        except Exception as e:
            logger.error(f"EVENT-message_from_business-Error sending message through 360dialog for room {room_id}: {e}")

        try:
            # Updating chat room collection
            handle_chat_room(chat_rooms_collection=chat_rooms_collection,
                             room=room_id,
                             message_body=message_body)
        except Exception as e:
            logger.error(f"EVENT-message_from_business-Error handling chat room for room_id {room_id}: {e}")

        logger.info(f"EVENT-message_from_business-Successfully sent message to room {room_id}: {message_body}")

    except Exception as e:
        logger.error(f"EVENT-message_from_business-Error processing event: {e}")


@socketio.on('join_room', namespace='/agent_namespace')
def on_join_room(data):
    """
    Event handler for 'join_room' event.
    """
    try:
        room = data.get('room')
        if not room:
            logger.warning("No room provided in join_room event")
            return
        
        logger.info(f"Client joined room: {room}")
        
        # Join the client to the specified room
        join_room(room, namespace='/agent_namespace')

        try:
            # Fetch chat history from the chat_rooms_collection
            chat_history = chat_rooms_collection.find_one({"room_id": room}, {"_id": 0, "messages": 1})
            if chat_history:
                # Convert datetime fields to ISO format strings
                for message in chat_history['messages']:
                    if isinstance(message.get('timestamp'), datetime):
                        message['timestamp'] = message['timestamp'].isoformat()
                
                # Emit the chat history to the client
                socketio.emit('chat_history', {"room": room, "messages": chat_history['messages']}, namespace='/agent_namespace')
                logger.info(f"Sent chat history for room: {room}")
            else:
                logger.info(f"No chat history found for room: {room}")
                socketio.emit('chat_history', {"room": room, "messages": []}, namespace='/agent_namespace')
        except Exception as e:
            logger.error(f"Error fetching chat history for room {room}: {e}")
    except Exception as e:
        logger.error(f"Error in join_room event: {e}")





if __name__ == '__main__':  
    logger.info("Starting Flask-SocketIO server")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
import logging
from flask_socketio import emit, join_room
from utils.db_helper import get_rooms_collection, handle_chat_room
from utils.dialog_360 import send_message_to_users_through_360
from datetime import datetime

logger = logging.getLogger('app')
chat_rooms_collection = get_rooms_collection()
active_agent_namespace = '/agent/agent_namespace'


def register_socketio_events(socketio):
    @socketio.on('connect', namespace=active_agent_namespace)
    def connect():
        logger.info(f"Client connected to {active_agent_namespace}")
        try:
            chat_rooms = chat_rooms_collection.find({}, {'room_id': 1, '_id': 0})
            room_ids = [chat['room_id'] for chat in chat_rooms]
            logger.info(f"Available rooms: {room_ids}")
            emit('available_rooms', room_ids, namespace=active_agent_namespace)
        except Exception as e:
            logger.error(f"Error fetching room IDs: {str(e)}")
            emit('error', {'message': 'Failed to fetch chat rooms'}, namespace=active_agent_namespace)

    @socketio.on('new_room', namespace=active_agent_namespace)
    def handle_new_room(data):
        logger.info(f"EVENT---Received 'new_room' event with data: {data}")
        try:
            chat_rooms = chat_rooms_collection.find({}, {'room_id': 1, '_id': 0})
            room_ids = [chat['room_id'] for chat in chat_rooms]
            logger.info(f"EVENT---Added--Available rooms: {room_ids}")
            emit('available_rooms', room_ids, namespace=active_agent_namespace)
        except Exception as e:
            logger.error(f"Error fetching room IDs: {str(e)}")
            emit('error', {'message': 'Failed to fetch chat rooms'}, namespace=active_agent_namespace)

    @socketio.on('message_from_user', namespace=active_agent_namespace)
    def handle_message(data):
        logger.info(f"EVENT-message_from_user-Received event with data: {data}")
        room_id = data.get('room')
        message_body = data.get('message')
        sender = data.get('sender', 'system')
        try:
            socketio.emit('message_from_user', data, room=room_id, namespace=active_agent_namespace)
            logger.info(f"EVENT-message_from_user-Sent message to room {room_id}: {message_body}")

            chat_rooms = chat_rooms_collection.find({}, {'room_id': 1, '_id': 0})
            room_ids = [chat['room_id'] for chat in chat_rooms]
            if room_id in room_ids:
                room_ids.remove(room_id)
            room_ids.insert(0, room_id)
            socketio.emit('available_rooms', room_ids, namespace=active_agent_namespace)
            logger.info(f"EVENT-message_from_user-Updated available rooms: {room_ids}")
        except Exception as e:
            logger.error(f"Error processing message or fetching room IDs: {str(e)}")
            emit('error', {'message': 'Failed to process message or fetch chat rooms'}, namespace=active_agent_namespace)

    @socketio.on('message_from_business', namespace=active_agent_namespace)
    def handle_message(data):
        try:
            logger.info(f"EVENT-message_from_business-Received event with data: {data}")
            room_id = data.get('room')
            message_body = data.get('message')
            sender = data.get('sender', 'system')
            if not room_id or not message_body:
                logger.warning(f"EVENT-message_from_business-Missing required information: room_id={room_id}, message_body={message_body}")
                return
            try:
                logger.debug(f"EVENT-message_from_business-Emitting message to room {room_id}")
                socketio.emit('message_from_business', data, room=room_id, namespace=active_agent_namespace)
            except Exception as e:
                logger.error(f"EVENT-message_from_business-Error emitting message to room {room_id}: {e}")
                return
            try:
                send_message_to_users_through_360(room_id, message=message_body)
            except Exception as e:
                logger.error(f"EVENT-message_from_business-Error sending message through 360dialog for room {room_id}: {e}")
            try:
                handle_chat_room(chat_rooms_collection, room=room_id, message_body=message_body)
            except Exception as e:
                logger.error(f"EVENT-message_from_business-Error handling chat room for room_id {room_id}: {e}")
            logger.info(f"EVENT-message_from_business-Successfully sent message to room {room_id}: {message_body}")
        except Exception as e:
            logger.error(f"EVENT-message_from_business-Error processing event: {e}")

    @socketio.on('join_room', namespace=active_agent_namespace)
    def on_join_room(data):
        try:
            room = data.get('room')
            if not room:
                logger.warning("No room provided in join_room event")
                return
            logger.info(f"Client joined room: {room}")
            join_room(room, namespace=active_agent_namespace)
            try:
                chat_history = chat_rooms_collection.find_one({"room_id": room}, {"_id": 0, "messages": 1})
                if chat_history:
                    for message in chat_history['messages']:
                        if isinstance(message.get('timestamp'), datetime):
                            message['timestamp'] = message['timestamp'].isoformat()
                    socketio.emit('chat_history', {"room": room, "messages": chat_history['messages']}, namespace=active_agent_namespace)
                    logger.info(f"Sent chat history for room: {room}")
                else:
                    logger.info(f"No chat history found for room: {room}")
                    socketio.emit('chat_history', {"room": room, "messages": []}, namespace=active_agent_namespace)
            except Exception as e:
                logger.error(f"Error fetching chat history for room {room}: {e}")
        except Exception as e:
            logger.error(f"Error in join_room event: {e}")

import logging
from flask_socketio import emit, join_room
from utils.db_helper import get_rooms_collection, handle_chat_room
from utils.dialog_360 import send_message_to_users_through_360
from utils.chat_room_helper import get_opened_closed_discussions
from utils.jwt_helper import socket_io_jwt
from datetime import datetime


logger = logging.getLogger('app')
chat_rooms_collection = get_rooms_collection()
active_agent_namespace = '/agent/agent_namespace'


def register_socketio_events(socketio):
    @socketio.on('connect', namespace=active_agent_namespace)
    @socket_io_jwt
    def connect():
        logger.info(f"Client connected to {active_agent_namespace}")
        try:
            open_rooms,closed_rooms=get_opened_closed_discussions(chat_rooms_collection)
            logger.info(f"BACKEND---Open rooms: {open_rooms}")
            logger.info(f"BACKEND---Closed rooms: {closed_rooms}")

            socketio.emit('available_rooms', {'openRooms': open_rooms, 'closedRooms': closed_rooms}, namespace=active_agent_namespace)
            
        except Exception as e:
            logger.error(f"Error fetching room IDs: {str(e)}")
            emit('error', {'message': 'Failed to fetch chat rooms'}, namespace=active_agent_namespace)

    @socketio.on('new_room', namespace=active_agent_namespace)
    @socket_io_jwt
    def handle_new_room(data):
        logger.info(f"EVENT---Received 'new_room' event with data: {data}")
        try:
            open_rooms,closed_rooms=get_opened_closed_discussions(chat_rooms_collection)
            logger.info(f"BACKEND---Open rooms: {open_rooms}")
            logger.info(f"BACKEND---Closed rooms: {closed_rooms}")

            emit('available_rooms', {'openRooms': open_rooms, 'closedRooms': closed_rooms}, namespace=active_agent_namespace)
        except Exception as e:
            logger.error(f"Error fetching room IDs: {str(e)}")
            emit('error', {'message': 'Failed to fetch chat rooms'}, namespace=active_agent_namespace)

    @socketio.on('message_from_user', namespace=active_agent_namespace)
    @socket_io_jwt
    def handle_message(data):
        logger.info(f"EVENT-message_from_user-Received event with data: {data}")
        room_id = data.get('room')
        message_body = data.get('message')
        sender = data.get('sender', 'system')
        try:
            socketio.emit('message_from_user', data, room=room_id, namespace=active_agent_namespace)
            logger.info(f"EVENT-message_from_user-Sent message to room {room_id}: {message_body}")

            open_rooms,closed_rooms=get_opened_closed_discussions(chat_rooms_collection)
            logger.info(f"BACKEND---Open rooms: {open_rooms}")
            logger.info(f"BACKEND---Closed rooms: {closed_rooms}")

            socketio.emit('available_rooms', {'openRooms': open_rooms, 'closedRooms': closed_rooms}, namespace=active_agent_namespace)
            logger.info(f"EVENT-message_from_user-Updated available rooms: open {open_rooms} closed {closed_rooms}")
        except Exception as e:
            logger.error(f"Error processing message or fetching room IDs: {str(e)}")
            socketio.emit('error', {'message': 'Failed to process message or fetch chat rooms'}, namespace=active_agent_namespace)

    @socketio.on('message_from_business', namespace=active_agent_namespace)
    @socket_io_jwt
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
    @socket_io_jwt
    def on_join_room(data):
        try:
            room = data.get('room')
            if not room:
                logger.warning("No room provided in join_room event")
                return
            
            logger.info(f"Client joined room: {room}")
            join_room(room, namespace=active_agent_namespace)
            
            # Check and set the open_discussion flag to true if not already true
            room_data = chat_rooms_collection.find_one({"room_id": room}, {"open_discussion": 1})
            if room_data and not room_data.get("open_discussion", False):
                chat_rooms_collection.update_one({"room_id": room}, {"$set": {"open_discussion": True}})
                logger.info(f"Set open_discussion to true for room: {room}")
            
            # Update unread messages to read
            try:
                update_result = chat_rooms_collection.update_many(
                    {"room_id": room, "messages.info": "unread", "messages.sender": "user"},
                    {"$set": {"messages.$[elem].info": "read"}},
                    array_filters=[{"elem.info": "unread", "elem.sender": "user"}]
                )
                logger.info(f"Updated {update_result.modified_count} unread messages to read in room: {room}")

                # Fetch updated chat history
                chat_history = chat_rooms_collection.find_one({"room_id": room}, {"_id": 0, "messages": 1})
                if chat_history:
                    # Convert timestamps to ISO format for frontend
                    for message in chat_history['messages']:
                        if isinstance(message.get('timestamp'), datetime):
                            message['timestamp'] = message['timestamp'].isoformat()
                    
                    socketio.emit('chat_history', {"room": room, "messages": chat_history['messages']}, namespace=active_agent_namespace)
                    logger.info(f"Sent chat history for room: {room}")
                else:
                    logger.info(f"No chat history found for room: {room}")
                    socketio.emit('chat_history', {"room": room, "messages": []}, namespace=active_agent_namespace)

                # Emit available rooms with updated open/closed status
                open_rooms, closed_rooms = get_opened_closed_discussions(chat_rooms_collection)
                logger.info(f"BACKEND---Open rooms: {open_rooms}")
                logger.info(f"BACKEND---Closed rooms: {closed_rooms}")
                socketio.emit('available_rooms', {'openRooms': open_rooms, 'closedRooms': closed_rooms}, namespace=active_agent_namespace)
            
            except Exception as e:
                logger.error(f"Error updating unread messages to read for room {room}: {e}")
                socketio.emit('error', {'message': 'Failed to update unread messages'}, namespace=active_agent_namespace)
        
        except Exception as e:
            logger.error(f"Error in join_room event for room {room}: {e}")


    @socketio.on('close_conversation', namespace=active_agent_namespace)
    @socket_io_jwt
    def close_conversation(data):
        room_id = data.get('room_id')
        try:
            # Check if the room is already closed
            room = chat_rooms_collection.find_one({'room_id': room_id})
            if room and not room.get('open_discussion', True):
                logger.info(f"Room {room_id} is already closed. No action taken.")
    
                return {'status': 'already_closed'}  

            # Update room status to closed in MongoDB
            chat_rooms_collection.update_one(
                {'room_id': room_id},
                {'$set': {'open_discussion': False}}
            )
            logger.info(f"Conversation closed for room {room_id}")

            # Emit updated available rooms to refresh client displays
            open_rooms, closed_rooms = get_opened_closed_discussions(chat_rooms_collection)
            emit('available_rooms', {'openRooms': open_rooms, 'closedRooms': closed_rooms}, broadcast=True, namespace=active_agent_namespace)
        except Exception as e:
            logger.error(f"Error closing conversation for room {room_id}: {str(e)}")

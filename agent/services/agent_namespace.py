from flask_socketio import Namespace, emit, disconnect
from flask import request
import jwt
import logging
import os
from utils.jwt_helper import socket_io_jwt
from utils.db_helper import get_chat_rooms_collection
from services.socketio_events import register_socketio_events

logger = logging.getLogger('app')
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_secret')

class DynamicNamespace(Namespace):
        @socket_io_jwt
        def on_connect(self):
            emit('connect_ack', {'message': 'Connected successfully'})
            logger.info(f"Client connected to {self.namespace} with valid JWT token.")

        @socket_io_jwt
        def on_disconnect(self):
            logger.info(f"Client disconnected from {self.namespace}.")

        @socket_io_jwt
        def on_new_room(self, data):
            emit('available_rooms', {'message': 'New room created'})
            logger.info(f"Handled 'new_room' event on {self.namespace} with valid JWT token.")

        @socket_io_jwt
        def on_message_from_user(self, data):
            emit('message', {'message': 'Message from user received'})
            logger.info(f"Handled 'message_from_user' event on {self.namespace} with valid JWT token.")


def create_dynamic_namespaces(socketio, foundation_names):
    for foundation_name in foundation_names:
        namespace_path = f"/agent/agent_namespace/{foundation_name}"
        logger.info(f"Creating namespace: {namespace_path}")
        chat_rooms_collection = get_chat_rooms_collection(foundation_name)
        socketio.on_namespace(DynamicNamespace(namespace_path))

        register_socketio_events(socketio=socketio,
                                 active_agent_namespace=namespace_path,
                                 chat_rooms_collection=chat_rooms_collection)

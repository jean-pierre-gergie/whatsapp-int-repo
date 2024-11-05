from flask_socketio import Namespace, emit, disconnect
from flask import request
import jwt
import logging
import os
from utils.jwt_helper import socket_io_jwt

logger = logging.getLogger('app')
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_secret')

active_agent_namespace = '/agent/agent_namespace'



class AgentNamespace(Namespace):
    @socket_io_jwt
    def on_connect(self):
        emit('connect_ack', {'message': 'Connected successfully'})
        logger.info("Client successfully connected with valid JWT token.")

    @socket_io_jwt
    def on_disconnect(self):
        logger.info("Client disconnected.")

    @socket_io_jwt
    def on_new_room(self, data):
        # Handle the 'new_room' event
        emit('available_rooms', {'message': 'New room created'})
        logger.info("Handled 'new_room' event with valid JWT token.")

    @socket_io_jwt
    def on_message_from_user(self, data):
        # Handle the 'message_from_user' event
        emit('message', {'message': 'Message from user received'})
        logger.info("Handled 'message_from_user' event with valid JWT token.")
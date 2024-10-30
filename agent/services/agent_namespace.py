from flask_socketio import Namespace, emit
from flask import request
import jwt
import logging
import os

logger = logging.getLogger('app')
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_secret')

active_agent_namespace = '/agent/agent_namespace'



class AgentNamespace(Namespace):
    def on_connect(self):
        try:
            # Fetch the JWT token from the headers
            token = request.headers.get('Authorization', '').replace('Bearer ', '')  # Assuming "Bearer" scheme

            # Validate the token
            if not token:
                logger.error("Authentication token is missing!")
                emit('connect_error', {'message': 'Authentication token is missing!'}, namespace=active_agent_namespace)
                return False

            try:
                # Decode and verify the token
                user_data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                logger.info(f"User authenticated: {user_data}")

                # Emit successful connection acknowledgment
                emit('connect_ack', {'message': 'Connected successfully'}, namespace=active_agent_namespace)

                # Log client information
                client_info = request.remote_addr or 'Unknown IP'
                user_agent = request.headers.get('User-Agent', 'Unknown User-Agent')
                logger.info(f'AgentNamespace---- Client attempting connection to {active_agent_namespace} from IP: {client_info}, User-Agent: {user_agent}')
                
            except jwt.ExpiredSignatureError:
                logger.error("Token has expired!")
                emit('connect_error', {'message': 'Token has expired!'}, namespace=active_agent_namespace)
                return False
            except jwt.InvalidTokenError:
                logger.error("Invalid token!")
                emit('connect_error', {'message': 'Invalid token!'}, namespace=active_agent_namespace)
                return False

        except Exception as e:
            logger.error(f'Connection error in {active_agent_namespace}: {str(e)}')
            emit('connect_error', {'message': 'Connection error occurred'}, namespace=active_agent_namespace)
            return False

    def on_disconnect(self):
        client_info = request.environ.get('REMOTE_ADDR', 'Unknown IP')
        logger.info(f'AgentNamespace---- Client disconnected from /agent_namespace, IP: {client_info}')
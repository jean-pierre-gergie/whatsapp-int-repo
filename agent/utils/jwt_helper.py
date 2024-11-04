from flask import request, jsonify
from functools import wraps
from flask_socketio import emit, disconnect
import logging
import jwt
import os

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_secret')

logger = logging.getLogger('wrapper_functions_jwt')
# for wbesite logger.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)


def verify_jwt(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('jwt_token')  # Get the token from the secure cookie

        if not token:
            return jsonify({"message": "Token is missing!"}), 403

        try:
            # Verify and decode the JWT using the same secret and algorithm as in the first app
            user_data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            # Attach user data to the request context if needed
            request.user = user_data
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token!"}), 403

        return f(*args, **kwargs)
    return decorated_function


active_agent_namespace = '/agent/agent_namespace'

def socket_io_jwt(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log the full request details for debugging purposes
        logger.info("--------------------------------------------------")
        # logger.info("Full Request Data:")
        # logger.info(f"Request method: {request.method}")
        # logger.info(f"Request path: {request.path}")
        # logger.info(f"Request headers: {dict(request.headers)}")
        # logger.info(f"Request args: {request.args}")
        # logger.info(f"Request cookies: {request.cookies}")
        # logger.info(f"Request data: {request.get_data()}")

        # Retrieve the token from args, headers, cookies, or auth parameter
        token = None
        if request.args.get('token'):
            token = request.args.get('token')
            logger.info("Token found in URL args.")
        elif 'Authorization' in request.headers:
            token = request.headers.get('Authorization').replace('Bearer ', '')
            logger.info("Token found in Authorization header.")
        elif 'jwt_token' in request.cookies:
            token = request.cookies.get('jwt_token')
            logger.info("Token found in cookies.")
        elif 'auth' in kwargs and isinstance(kwargs['auth'], dict) and 'token' in kwargs['auth']:
            token = kwargs['auth']['token']
            logger.info("Token found in auth parameter.")

        # Log the token extraction result
        logger.info(f"Extracted token: {token}")

        # If no token was found, emit an error and disconnect
        if not token:
            logger.error("Authentication token is missing!")
            emit('connect_error', {'message': 'Authentication token is missing!'}, namespace='/agent/agent_namespace')
            disconnect()
            return False

        # Attempt to decode the JWT token
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            logger.info("JWT token successfully decoded and verified.")
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired!")
            emit('connect_error', {'message': 'Token has expired!'}, namespace='/agent/agent_namespace')
            disconnect()
            return False
        except jwt.InvalidTokenError:
            logger.error("Invalid token!")
            emit('connect_error', {'message': 'Invalid token!'}, namespace='/agent/agent_namespace')
            disconnect()
            return False

        # Proceed with the wrapped function if token validation is successful
        return f(*args, **kwargs)

    return decorated_function
import logging
from functools import wraps
from flask import jsonify,current_app
from flask_jwt_extended import get_jwt_identity

# Set up logging
from ..logger_setup.logger_setup import LoggerSetup

logger = current_app.logger

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            current_user = get_jwt_identity()

            # Check if the JWT token is missing or invalid
            if not current_user:
                logger.warning("Missing or invalid token.")
                return jsonify({"msg": "Missing or invalid token"}), 401

            # Get the user's role from the JWT token
            user_role = current_user.get('role')

            # Log the current user's identity and role
            logger.debug(f"Current user: {current_user}, Role: {user_role}")

            # Check if the role is missing from the token
            if not user_role:
                logger.warning(f"Role not found for user: {current_user['username']}")
                return jsonify({"msg": "Role not found in token"}), 403

            # Check if the user's role is allowed
            if user_role not in roles:
                logger.warning(f"Access denied for user {current_user['username']} with role {user_role}. Insufficient permissions.")
                return jsonify({"msg": "Access denied: insufficient permissions"}), 403

            # If everything checks out, proceed with the request
            logger.debug(f"Access granted for user {current_user['username']} with role {user_role}.")
            return f(*args, **kwargs)
        return wrapper
    return decorator
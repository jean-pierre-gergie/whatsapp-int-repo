from flask import jsonify
from functools import wraps
from flask_jwt_extended import get_jwt_identity

def role_required(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user = get_jwt_identity()
            if not current_user:
                return jsonify({"msg": "Missing or invalid token"}), 401

            user_role = current_user.get('role')
            if not user_role:
                return jsonify({"msg": "Role not found in token"}), 403

            if user_role != required_role:
                return jsonify({"msg": "Access denied: insufficient permissions"}), 403

            return func(*args, **kwargs)
        return wrapper
    return decorator

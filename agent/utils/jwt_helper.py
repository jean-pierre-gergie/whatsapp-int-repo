from flask import request, jsonify
from functools import wraps
import jwt
import os

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_secret')

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
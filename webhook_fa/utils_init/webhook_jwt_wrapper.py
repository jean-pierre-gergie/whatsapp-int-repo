from functools import wraps
import jwt
from fastapi import Request, Header, HTTPException
import os 
import logging 

def verify_jwt(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        # Extract `Authorization` header
        authorization = kwargs.get("authorization", None)
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

        token = authorization.split(" ")[1]
        secret_key = os.getenv('JWT_SECRET_KEY')

        try:
            # Decode the JWT token
            decoded_token = jwt.decode(token, secret_key, algorithms=["HS256"])
            kwargs["decoded_token"] = decoded_token  # Pass decoded token to the route handler

            # Log success in debug mode
            logger = logging.getLogger("JWT Authentication")
            logger.debug(f"JWT authenticated successfully: {decoded_token}")
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="JWT token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid JWT token")

        return await f(*args, **kwargs)

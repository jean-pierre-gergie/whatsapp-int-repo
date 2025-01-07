from functools import wraps
import jwt
from fastapi import Request, Header, HTTPException
import os 
import logging 


from logger_setup.logger_setup import logger



def verify_jwt(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        # Extract `Authorization` header
        authorization = kwargs.get("authorization") or args[0].headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            logger.warning("Authorization header missing or invalid")
            raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

        token = authorization.split(" ")[1]
        secret_key = os.getenv("JWT_SECRET_KEY")

        if not secret_key:
            logger.error("JWT_SECRET_KEY is not set in environment variables")
            raise RuntimeError("JWT_SECRET_KEY is not set in environment variables")

        try:
            # Decode the JWT token
            decoded_token = jwt.decode(token, secret_key, algorithms=["HS256"])
            kwargs["decoded_token"] = decoded_token  # Pass decoded token to the route handler

            # Log success in debug mode
            logger.debug(f"JWT authenticated successfully: {decoded_token}")

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise HTTPException(status_code=401, detail="JWT token has expired")
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        except Exception as e:
            logger.error(f"Unexpected error during JWT authentication: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error during JWT authentication")

        # Call the wrapped function
        return await f(*args, **kwargs)

    return wrapper
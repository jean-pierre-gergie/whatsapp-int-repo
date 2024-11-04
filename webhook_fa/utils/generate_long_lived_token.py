import jwt
from dotenv import load_dotenv
import os 


load_dotenv()
SECRET_KEY = os.getenv('JWT_SECRET_KEY')


def generate_forever_token():
    # Generate a token without an expiration time
    token = jwt.encode({}, SECRET_KEY, algorithm="HS256")
    return token

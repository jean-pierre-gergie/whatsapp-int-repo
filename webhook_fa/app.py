import json
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from pymongo import MongoClient
from pydantic import BaseModel
from init_mongo import create_collections
from typing import Optional, Dict, Any
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import socketio
from datetime import datetime
from utils.helper_functions import WhatsAppDataHandler
from utils.generate_long_lived_token import generate_forever_token
from utils.auto_reply_helper import AutoReplyHandler
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError


# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Socket.IO client to connect to the Flask server
sio = socketio.Client()

# Load environment variables
load_dotenv()
username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
host = os.getenv('MONGO_HOST')
port = os.getenv('MONGO_PORT')


client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")

logger.debug(f"Loaded environment variables: MONGO_INITDB_ROOT_USERNAME={username}, MONGO_HOST={host}, MONGO_PORT={port}")

pymongo_logger = logging.getLogger("pymongo")
pymongo_logger.setLevel(logging.ERROR)

# MongoDB configuration
MAIN_WHTSPP_DB = 'whatsapp_data'
RAW_COLLECTION = 'webhook_responses'
BUSINESS_TO_USER_COLLECTION = 'webhook_latest_to_user'
USER_TO_BUSINESS_COLLECTION = 'webhook_latest_from_user'


AGENT_CHAT_DB = 'agent_data'
ROOMS_COLLECTION = 'rooms'

main_db = client[MAIN_WHTSPP_DB]
raw_collection = main_db[RAW_COLLECTION]
business_to_user_collection = main_db[BUSINESS_TO_USER_COLLECTION]
user_to_business_collection = main_db[USER_TO_BUSINESS_COLLECTION]

agent_db = client[AGENT_CHAT_DB]
chat_rooms_collection = agent_db[ROOMS_COLLECTION]


token = generate_forever_token()
logger.info(f"WEBHOOK --- --- Token {token}")
@retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5), reraise=True)
def connect_to_agent_service():
    # Pass the token in the `auth` parameter
    sio.connect(f"http://agent:5001/?token={token}", namespaces=['/agent/agent_namespace'])
    logger.info("Successfully connected to the agent service with JWT authentication.")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting the needed stuff")
    try:
        create_collections()
        logger.info("Collections created successfully on startup.")
    except Exception as e:
        logger.error(f"Error creating collections on startup: {e}")

    try:
        connect_to_agent_service()
    except RetryError as e:
        logger.error(f"Failed to connect to the agent service after multiple attempts: {e}")
    except socketio.exceptions.ConnectionError as e:
        logger.error(f"Connection error encountered: {e}")

class WebhookPayload(BaseModel):
    entry: Optional[list[Dict[str, Any]]]

auto_reply_handler = AutoReplyHandler(chat_rooms_collection,logger = logger) 


handler = WhatsAppDataHandler(raw_collection, 
                            user_to_business_collection,
                            business_to_user_collection,
                            chat_rooms_collection,
                            auto_reply_handler=auto_reply_handler,
                            sio=sio)



@app.post("/webhook")
async def webhook(request: Request, authorization: Optional[str] = Header(None)):
    try:
        # Get the request payload
        payload = await request.json()
        logger.info("Received webhook payload.")

        # Store raw data in the raw collection
        await handler.process_webhook_payload(payload)


        return JSONResponse(content={"status": "success"}, status_code=200)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received.")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing webhook data: {e}")
        raise HTTPException(status_code=500, detail="Processing error")

if __name__ == '__main__':
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="debug")

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

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Load environment variables
load_dotenv()
username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
host = os.getenv('MONGO_HOST')
port = os.getenv('MONGO_PORT')
database_name = 'whatsapp_data'
client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")

logger.debug(f"Loaded environment variables: MONGO_INITDB_ROOT_USERNAME={username}, MONGO_HOST={host}, MONGO_PORT={port}")


pymongo_logger = logging.getLogger("pymongo")
pymongo_logger.setLevel(logging.ERROR)

# MongoDB configuration
DATABASE_NAME = 'whatsapp_data'
RAW_COLLECTION = 'webhook_responses'
BUSINESS_TO_USER_COLLECTION = 'webhook_latest_to_user'
USER_TO_BUSINESS_COLLECTION = 'webhook_latest_from_user'

db = client[DATABASE_NAME]
raw_collection = db[RAW_COLLECTION]
business_to_user_collection = db[BUSINESS_TO_USER_COLLECTION]
user_to_business_collection = db[USER_TO_BUSINESS_COLLECTION]

# Call create_collections() during startup
@app.on_event("startup")
async def startup_event():
    try:
        create_collections()
        logger.info("Collections created successfully on startup.")
    except Exception as e:
        logger.error(f"Error creating collections on startup: {e}")

class WebhookPayload(BaseModel):
    entry: Optional[list[Dict[str, Any]]]

@app.get("/webhook_test")
def index():
    logger.debug("Webhook test endpoint called.")
    return {"message": "Webhook server is running"}

@app.post("/webhook")
async def webhook(request: Request, authorization: Optional[str] = Header(None)):
    try:
        # Get the request payload
        payload = await request.json()
        logger.info("Received webhook payload.")

        # Store raw data in the raw collection
        raw_result = raw_collection.insert_one(payload)
        logger.debug(f"Raw data inserted with id: {raw_result.inserted_id}")

        # Iterate through each entry in the payload
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})

                # Determine the direction of the message
                if 'messages' in value and 'statuses' not in value:
                    # Messages coming from users to the business
                    for message in value.get('messages', []):
                        wa_mid = message.get('id')
                        logger.debug(f"User to Business wa_mid: {wa_mid}")

                        if wa_mid:
                            # Check if wa_mid exists in the latest collection
                            existing_record = user_to_business_collection.find_one({'id': wa_mid})
                            if existing_record:
                                # Update existing record
                                update_result = user_to_business_collection.update_one(
                                    {'id': wa_mid},
                                    {'$set': message}
                                )
                                logger.info(f"Updated user-to-business record with id: {wa_mid}, modified count: {update_result.modified_count}")
                            else:
                                # Insert new record
                                latest_result = user_to_business_collection.insert_one(message)
                                logger.info(f"New user-to-business message inserted with id: {latest_result.inserted_id}")

                elif 'statuses' in value:
                    # Messages going from the business to users
                    for status in value.get('statuses', []):
                        wa_mid = status.get('id')
                        logger.debug(f"Business to User wa_mid: {wa_mid}")

                        if wa_mid:
                            # Check if wa_mid exists in the latest collection
                            existing_record = business_to_user_collection.find_one({'id': wa_mid})
                            if existing_record:
                                # Update existing record
                                update_result = business_to_user_collection.update_one(
                                    {'id': wa_mid},
                                    {'$set': status}
                                )
                                logger.info(f"Updated business-to-user record with id: {wa_mid}, modified count: {update_result.modified_count}")
                            else:
                                # Insert new record
                                latest_result = business_to_user_collection.insert_one(status)
                                logger.info(f"New business-to-user message inserted with id: {latest_result.inserted_id}")

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

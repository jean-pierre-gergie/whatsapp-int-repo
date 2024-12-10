import json
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from pymongo import MongoClient
from pydantic import BaseModel
from init_scripts.init_mongo import create_collections
from init_scripts.init_webhook_urls import init_webhook_urls
from typing import Optional, Dict, Any
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import socketio
from datetime import datetime
from utils.helper_functions import WhatsAppDataHandler
from utils.generate_long_lived_token import generate_forever_token
from utils.auto_reply_helper import AutoReplyHandler
from utils.init_webhook_helper import create_handlers_for_all_foundations
from utils_init.webhook_jwt_wrapper import verify_jwt
from utils_init.utils_init import get_mongo_client
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError,wait_fixed

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="- %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
pymongo_logger = logging.getLogger("pymongo")
pymongo_logger.setLevel(logging.ERROR)

app = FastAPI()


mongo_client = get_mongo_client()
foundations_collection = mongo_client['foundations_db']['foundations']

EXPECTED_DOCUMENT_COUNT = int(os.getenv('EXPECTED_DOCUMENT_COUNT',1))


foundation_handlers = {}


@retry(wait=wait_fixed(3), stop=stop_after_attempt(100))
def check_mongo_collection_ready():
    """Check if the MongoDB collection has the required number of documents."""
    attempt_number = check_mongo_collection_ready.retry.statistics.get('attempt_number', 0) + 1
    logger.info(f"Attempt {attempt_number}: Checking MongoDB collection...")
    document_count = foundations_collection.count_documents({})
    if document_count < EXPECTED_DOCUMENT_COUNT:
        raise Exception(f"Collection foundations has {document_count} documents. Waiting for {EXPECTED_DOCUMENT_COUNT}.")
    logger.info(f"Collection foundations is ready with {document_count} documents.")





# foundation_handlers = create_handlers_for_all_foundations()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI server and initializing collections.")

    logger.info("Starting up FastAPI server and initializing collections.")
    try:
        
        # Wait for MongoDB collection to be ready
        logger.info("Checking MongoDB collection readiness...")
        check_mongo_collection_ready()


        global foundation_handlers
        foundation_handlers = create_handlers_for_all_foundations()


        
        for foundation_name in foundation_handlers:
            logger.info(f"Handlers initialized for foundation: {foundation_name}")


    except RetryError:
        logger.error("MongoDB collection did not reach the required number of documents in time. Exiting...")
        raise HTTPException(status_code=500, detail="MongoDB initialization failed")

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise HTTPException(status_code=500, detail="Startup initialization error")

class WebhookPayload(BaseModel):
    entry: Optional[list[Dict[str, Any]]]


@app.post("/webhook/{foundation_name}")
@verify_jwt
async def webhook(request: Request, foundation_name: str, authorization: Optional[str] = Header(None), decoded_token=None):
    if foundation_name not in foundation_handlers:
        logger.error(f"Handler for foundation '{foundation_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Foundation '{foundation_name}' not found")

    handler = foundation_handlers[foundation_name]

    try:
        # Get the request payload
        payload = await request.json()
        logger.info(f"Received webhook payload for foundation '{foundation_name}'.")

       
        logger.debug(f"Decoded JWT token: {decoded_token}")

        # Process webhook payload using the specific handler
        await handler.process_webhook_payload(payload)

        return JSONResponse(content={"status": "success"}, status_code=200)

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON payload received for foundation '{foundation_name}'.")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing webhook data for foundation '{foundation_name}': {e}")
        raise HTTPException(status_code=500, detail="Processing error")




if __name__ == '__main__':
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="debug")

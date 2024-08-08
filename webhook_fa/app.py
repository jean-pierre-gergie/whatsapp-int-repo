import json
from fastapi import FastAPI, Request, HTTPException, Header
from pymongo import MongoClient
from pydantic import BaseModel
from init_mongo import create_collections
from typing import Optional, Dict, Any
from fastapi.responses import JSONResponse


create_collections()
app = FastAPI()

# MongoDB configuration
MONGO_URI = 'mongodb://mongodb_container:27017/'  # Update to container name
DATABASE_NAME = 'whatsapp_data'
RAW_COLLECTION = 'webhook_responses'
BUSINESS_TO_USER_COLLECTION = 'webhook_latest_to_user'
USER_TO_BUSINESS_COLLECTION = 'webhook_latest_from_user'

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
raw_collection = db[RAW_COLLECTION]
business_to_user_collection = db[BUSINESS_TO_USER_COLLECTION]
user_to_business_collection = db[USER_TO_BUSINESS_COLLECTION]

def verify_token(auth_header: Optional[str]) -> bool:
    """Verify the token from the Authorization header."""
    if not auth_header:
        return False
    try:
        token = auth_header.split(" ")[1]
        # Token verification logic here (e.g., check against a known token)
        return token == "your_secret_token"
    except IndexError:
        return False

class WebhookPayload(BaseModel):
    entry: Optional[list[Dict[str, Any]]]

@app.get("/webhook_test")
def index():
    return {"message": "Webhook server is running"}

@app.post("/webhook")
async def webhook(request: Request, authorization: Optional[str] = Header(None)):
    # Verify the token
    # if not verify_token(authorization):
    #     raise HTTPException(status_code=401, detail="Unauthorized access: Invalid token!")

    print("Token verified successfully.")

    try:
        # Get the request payload
        payload = await request.json()

        # Store raw data in the raw collection
        raw_result = raw_collection.insert_one(payload)
        print(f"Raw data inserted with id: {raw_result.inserted_id}")

        # Iterate through each entry in the payload
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                messages = value.get('messages', [])

                for message in messages:
                    if 'from' in message and 'id' in message:
                        user_id = message['from']
                        message_id = message['id']
                        message_data = {
                            'user_id': user_id,
                            'message_id': message_id,
                            'message': message,
                        }
                        status = business_to_user_collection.find_one_and_replace(
                            {"user_id": user_id, "message_id": message_id},
                            message_data,
                            upsert=True
                        )
                        if status:
                            print(f"Updated business-to-user message with id: {message_id}")
                        else:
                            latest_result = business_to_user_collection.insert_one(message_data)
                            print(f"New business-to-user message inserted with id: {latest_result.inserted_id}")

        return JSONResponse(content={"status": "success"}, status_code=200)

    except json.JSONDecodeError:
        print("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        print(f"Error processing data: {e}")
        raise HTTPException(status_code=500, detail="Processing error")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="debug")

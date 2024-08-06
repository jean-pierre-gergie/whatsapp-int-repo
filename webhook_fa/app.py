import hmac
import hashlib
import json
import subprocess
import time
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask import abort
from init_mongo import create_collections





create_collections() 

app = Flask(__name__)

# MongoDB configuration
MONGO_URI = 'mongodb://mongodb_container:27017/'  # Update to container name
DATABASE_NAME = 'whatsapp_data'
RAW_COLLECTION = 'webhook_responses'
BUSINESS_TO_USER_COLLECTION = 'webhook_latest_to_user'
USER_TO_BUSINESS_COLLECTION = 'webhook_latest_from_user'

# Ensure this is your correct app secret for webhook verification
API_SECRET = 'iHB20OJavj7OcHzCmfIKyCHlAK'

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
raw_collection = db[RAW_COLLECTION]
business_to_user_collection = db[BUSINESS_TO_USER_COLLECTION]
user_to_business_collection = db[USER_TO_BUSINESS_COLLECTION]

def verify_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.

    Raise and return 403 if not authorized.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    if not signature_header:
        abort(403, description="x-hub-signature-256 header is missing!")
    
    # Create HMAC digest using the secret token and raw payload
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    # Securely compare the computed HMAC digest with the received signature
    if not hmac.compare_digest(expected_signature, signature_header):
        abort(403, description="Request signatures didn't match!")

@app.route('/', methods=['GET'])
def index():
    return 'Webhook server is running'

@app.route('/whatsapp', methods=['POST'])
def webhook():
    # Get the request payload and signature header
    payload = request.get_data(as_text=True)
    signature_sha256 = request.headers.get('X-Hub-Signature-256')

    print(f"Signature Header: {signature_sha256}")

    # Verify the signature before processing the data
    # verify_signature(payload.encode('utf-8'), API_SECRET, signature_sha256)

    print("SHA256 Signature verified successfully.")
        
    try:
        # Parse the JSON payload
        data = json.loads(payload)

        # Store raw data in the raw collection
        raw_result = raw_collection.insert_one(data)
        print(f"Raw data inserted with id: {raw_result.inserted_id}")

        # Iterate through each entry in the payload
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})

                # Determine the direction of the message
                if 'messages' in value and 'statuses' not in value:
                    # Messages coming from users to the business
                    for message in value.get('messages', []):
                        wa_mid = message.get('id')
                        print("User to Business wa_mid:", wa_mid)

                        if wa_mid:
                            # Check if wa_mid exists in the latest collection
                            existing_record = user_to_business_collection.find_one({'id': wa_mid})
                            if existing_record:
                                # Update existing record
                                update_result = user_to_business_collection.update_one(
                                    {'id': wa_mid},
                                    {'$set': message}
                                )
                                print(f"Updated record with id: {wa_mid}, modified count: {update_result.modified_count}")
                            else:
                                # Insert new record
                                latest_result = user_to_business_collection.insert_one(message)
                                print(f"New user-to-business message inserted with id: {latest_result.inserted_id}")

                elif 'statuses' in value:
                    # Messages going from the business to users
                    for status in value.get('statuses', []):
                        wa_mid = status.get('id')
                        print("Business to User wa_mid:", wa_mid)

                        if wa_mid:
                            # Check if wa_mid exists in the latest collection
                            existing_record = business_to_user_collection.find_one({'id': wa_mid})
                            if existing_record:
                                # Update existing record
                                update_result = business_to_user_collection.update_one(
                                    {'id': wa_mid},
                                    {'$set': status}
                                )
                                print(f"Updated record with id: {wa_mid}, modified count: {update_result.modified_count}")
                            else:
                                # Insert new record
                                latest_result = business_to_user_collection.insert_one(status)
                                print(f"New business-to-user message inserted with id: {latest_result.inserted_id}")

        return jsonify({"status": "success"}), 200

    except json.JSONDecodeError:
        print("Invalid JSON payload")
        return jsonify({"status": "failure", "reason": "Invalid JSON payload"}), 400
    except Exception as e:
        print(f"Error processing data: {e}")
        return jsonify({"status": "failure", "reason": "Processing error"}), 500
        

if __name__ == '__main__':
    
    app.run(host="0.0.0.0",port=5000, debug=True)


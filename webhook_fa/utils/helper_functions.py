
import json
import logging
from datetime import datetime



class WhatsAppDataHandler:
    def __init__(self, raw_collection, user_to_business_collection, business_to_user_collection,chat_rooms_collection,sio):
        self.raw_collection = raw_collection
        self.user_to_business_collection = user_to_business_collection
        self.business_to_user_collection = business_to_user_collection
        self.chat_rooms_collection =chat_rooms_collection
        self.sio = sio 
        self.logger = logging.getLogger(__name__)

    async def process_webhook_payload(self, payload):
        self.logger.info("Received webhook payload.")
        
        # Store raw data in the raw collection
        raw_result = self.raw_collection.insert_one(payload)
        self.logger.debug(f"Raw data inserted with id: {raw_result.inserted_id}")
        
        # Process each entry in the payload
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                
                # Determine the direction of the message
                if 'messages' in value and 'statuses' not in value:
                    # Messages coming from users to the business
                    await self._handle_user_to_business_messages(value)
                elif 'statuses' in value:
                    # Messages going from the business to users
                    self._handle_business_to_user_statuses(value)
        
    def _handle_business_to_user_statuses(self, value):
        for status in value.get('statuses', []):
            wa_mid = status.get('id')
            if wa_mid:
                # Check if wa_mid exists in the business-to-user collection
                existing_record = self.business_to_user_collection.find_one({'id': wa_mid})
                if existing_record:
                    # Update existing record
                    update_result = self.business_to_user_collection.update_one(
                        {'id': wa_mid},
                        {'$set': status}
                    )
                    self.logger.info(f"Updated business-to-user record with id: {wa_mid}, modified count: {update_result.modified_count}")
                else:
                    # Insert new record
                    latest_result = self.business_to_user_collection.insert_one(status)
                    self.logger.info(f"New business-to-user message inserted with id: {latest_result.inserted_id}")

    async def _handle_user_to_business_messages(self, value):
        for message in value.get('messages', []):
            wa_mid = message.get('id')
            if wa_mid:
                self.insert_to_user_to_business_collection(wa_mid=wa_mid,message=message)
            
            sender_phone = message.get('from')
            message_body = message.get('text', {}).get('body', '')
            time_stamp = message.get('timestamp')

            self.logger.info("Handling Chat Room...")
            await self._handle_chat_room(sender_phone=sender_phone,
                                   wa_mid=wa_mid,
                                   message_body=message_body,
                                   timestamp=time_stamp)
            

    async def _handle_chat_room(self, sender_phone , wa_mid , message_body,timestamp):
        if sender_phone:

            existing_room = self.chat_rooms_collection.find_one({'room_id': sender_phone})

            message_data = {
                    "wa_mid": wa_mid,
                    "sender": "user",
                    "timestamp": timestamp,
                    "body": message_body
                }

            if not existing_room:
                room_data = {
                    "room_id": sender_phone,
                    "created_at": datetime.utcnow(),
                    "messages": [message_data]
                }
                self.chat_rooms_collection.insert_one(room_data)
                self.logger.info(f"Created new chat room with room_id: {sender_phone}")

                await self.emit_event(event_name='new_room',
                                data=  {'room': sender_phone}
                            )
            
            else:
                # Check if the wa_mid already exists in the room's messages
                wa_mid_exists = self.chat_rooms_collection.find_one(
                    {'room_id': sender_phone, 'messages.wa_mid': wa_mid},
                    {'_id': 1}  # Only fetch the _id field to optimize query speed
                )

                if wa_mid_exists:
                    self.logger.info(f"Message with wa_mid {wa_mid} already exists for room_id: {sender_phone}")
                    return 
                else:
                    # Update the existing room with the new message
                    self.chat_rooms_collection.update_one(
                        {'room_id': sender_phone},
                        {'$push': {'messages': message_data}}
                    )
                    self.logger.info(f"Updated chat room with new message for room_id: {sender_phone}")

            
            await self.emit_event(event_name='message_from_user',
                            data= {'room': sender_phone,'sender':'user', 'message': message_body},
                            )

    def extract_whatsapp_data(self, response_json):
        try:
            # Extract the first entry and first change
            entry = response_json.get('entry', [])[0]
            changes = entry.get('changes', [])[0]
            value = changes.get('value', {})
            
            # Determine message type and extract the fields
            if 'messages' in value:
                sender_phone = value.get('messages', [])[0].get('from')
                wa_message_id = value.get('messages', [])[0].get('id')
                message_text_body = value.get('messages', [])[0].get('text', {}).get('body')
                return "user_to_business", [{"sender_phone": sender_phone, "wa_message_id": wa_message_id, "text_body": message_text_body}]
            elif 'statuses' in value:
                status_list = []
                for status in value.get('statuses', []):
                    wa_message_id = status.get('id')
                    status_list.append({"wa_message_id": wa_message_id, "status": status})
                return "business_to_user", status_list
            else:
                return None, []
        except (IndexError, KeyError, TypeError):
            # Handle missing or malformed keys
            return None, []

    def insert_to_user_to_business_collection(self, wa_mid, message):
        """
        Handles the insertion or update of user-to-business messages in the MongoDB collection.
        """
        existing_record = self.user_to_business_collection.find_one({'id': wa_mid})
        if existing_record:
            # Update existing record
            update_result = self.user_to_business_collection.update_one(
                {'id': wa_mid},
                {'$set': message}
            )
            self.logger.info(f"Updated user-to-business record with id: {wa_mid}, modified count: {update_result.modified_count}")
        else:
            # Insert new record
            latest_result = self.user_to_business_collection.insert_one(message)
            self.logger.info(f"New user-to-business message inserted with id: {latest_result.inserted_id}")

    async def emit_event(self, event_name, data,room=None):
        """Emit an event using the connected Socket.IO client."""
        try:
            self.sio.emit(event_name, data, namespace='/agent_namespace')
            self.logger.info(f"Emitted event '{event_name}' with data: {data}")
        except Exception as e:
            self.logger.error(f"Failed to emit event '{event_name}': {e}")


















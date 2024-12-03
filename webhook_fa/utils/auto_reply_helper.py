import logging
from utils.dialog_360 import send_message_to_users_through_360
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio

class AutoReplyHandler:
    AUTO_REPLY_MESSAGE = "**Auto Reply**"

    def __init__(self, foundations_collection ,foundation_name ,chat_rooms_collection,api_key_360, logger=None):
        self.foundations_collection = foundations_collection
        self.foundation_name = foundation_name
        self.chat_rooms_collection = chat_rooms_collection
        self.api_key_360= api_key_360
        self.logger = logger or logging.getLogger(__name__)
        load_dotenv()

    async def auto_reply(self, room_id):
        try:
            existing_room = self.chat_rooms_collection.find_one({'room_id': room_id})
            if not existing_room:
                self.logger.debug(f"No existing room found for room_id: {room_id}")
                return

            last_auto_reply = existing_room.get('last_auto_reply')
            if last_auto_reply:
                if isinstance(last_auto_reply, str):
                    last_auto_reply = datetime.fromisoformat(last_auto_reply)
                
                if datetime.utcnow() - last_auto_reply < timedelta(hours=25):
                    self.logger.debug(f"Auto reply already sent in the last 12 hours for room_id: {room_id}")
                    return
                
            auto_reply_message = self.get_auto_reply_message()

            send_message_to_users_through_360(room_id, auto_reply_message,self.api_key_360,logger = self.logger)
            # Call `_handle_chat_room` and handle the chat room without updating `last_auto_reply`
            await self._handle_chat_room(room_id, auto_reply_message ,timestamp=datetime.utcnow())

            # Now, update `last_auto_reply` once in the room's document
            self.chat_rooms_collection.update_one(
                {'room_id': room_id},
                {'$set': {'last_auto_reply': datetime.utcnow()}}
            )
            self.logger.info(f"Auto reply sent to room_id: {room_id}")

        except Exception as e:
            self.logger.error(f"Error in auto_reply for room_id: {room_id}. Exception: {e}")

    async def _handle_chat_room(self, user_phone_number, auto_reply_message, timestamp):
        try:
            self.logger.debug(f"AUTOREPLY -- Handling chat room auto reply for user: {user_phone_number}")

            # Check if the chat room already exists
            existing_room = self.chat_rooms_collection.find_one({'room_id': user_phone_number})
            if existing_room:
                self.logger.debug(f"Existing chat room found for user: {user_phone_number}")
            else:
                self.logger.debug(f"No existing chat room found for user: {user_phone_number}")

            timestamp = timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp

            # Prepare the message data
            message_data = {
                "sender": "business",
                "timestamp": timestamp,
                "campaign": True,
                "body": f"**Auto Reply** {auto_reply_message}"
            }
            self.logger.debug(f"Prepared message data: {message_data}")

            if not existing_room:
                # Create a new room with the provided user phone number as the room ID
                room_data = {
                    "room_id": user_phone_number,
                    "created_at": datetime.utcnow(),
                    "open_discussion": False,
                    "last_message_time": timestamp,
                    "messages": [message_data]
                    
                }
                self.chat_rooms_collection.insert_one(room_data)
                self.logger.info(f"Created new chat room with room_id: {user_phone_number}")
                self.logger.debug(f"Inserted room data: {room_data}")
            else:
                # Update the existing room with the new message
                update_result = self.chat_rooms_collection.update_one(
                    {'room_id': user_phone_number},
                    {
                        '$push': {'messages': message_data},
                        '$set': {
                            'open_discussion': True,
                            'last_message_time': timestamp  # Update last_message_time
                        }
                    }
                )
                self.logger.info(f"Updated chat room with new message for room_id: {user_phone_number}")
                self.logger.debug(f"Update result: {update_result.raw_result}")

        except Exception as e:
            self.logger.error(f"Error handling chat room for user: {user_phone_number}. Exception: {e}")

    def get_auto_reply_message(self):
        try:
            self.logger.debug(f"Fetching auto-reply message for foundation: {self.foundation_name}")
            foundation_doc = self.foundations_collection.find_one({"foundation": self.foundation_name})
            
            if foundation_doc:
                self.logger.debug(f"Document retrieved successfully for foundation: {self.foundation_name}")
            else:
                self.logger.warning(f"No document found for foundation: {self.foundation_name}")
            
            auto_reply_message = foundation_doc.get("auto_reply_message", "default auto reply")
            self.logger.info(f"Auto-reply message for {self.foundation_name}: {auto_reply_message}")
            
            return auto_reply_message
        except Exception as e:
            self.logger.error(f"Error fetching auto-reply message for {self.foundation_name}: {e}", exc_info=True)
            raise
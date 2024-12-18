from datetime import datetime
import logging
from logger_setup.logger_setup import celery_logger


logger = celery_logger

logger.setLevel(logging.DEBUG)


class WhatsAppChatCampaignHandler:
    def __init__(self, chat_rooms_collection, logger):
        self.chat_rooms_collection = chat_rooms_collection
        self.logger = logger

    async def _handle_chat_room(self, user_phone_number, wa_mid, campaign_name, timestamp):
        self.logger.debug(f"Handling chat room for user: {user_phone_number}, wa_mid: {wa_mid}")

        try:
            # Check if the chat room already exists
            existing_room = self.chat_rooms_collection.find_one({'room_id': user_phone_number})
            if existing_room:
                self.logger.debug(f"Existing chat room found for user: {user_phone_number}")
            else:
                self.logger.debug(f"No existing chat room found for user: {user_phone_number}")

            # Prepare the message data
            message_data = {
                "wa_mid": wa_mid,
                "sender": "business",
                "timestamp": timestamp,
                "body": None,
                "campaign": True,
                "body":f"**CAMPAIGN** {campaign_name}"
                
            }
            self.logger.debug(f"Prepared message data: {message_data}")

            if not existing_room:
                # Create a new room with the provided user phone number as the room ID
                room_data = {
                    "room_id": user_phone_number,
                    "created_at": datetime.utcnow(),
                    "open_discussion":False,
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
                                'open_discussion': user_phone_number,
                                'last_message_time': timestamp  # Update last_message_time
                            }
                        }
                    )
                self.logger.info(f"Updated chat room with new message for room_id: {user_phone_number}")
                self.logger.debug(f"Update result: {update_result.raw_result}")
        except Exception as e:
            self.logger.error(f"Error handling chat room for user: {user_phone_number}, wa_mid: {wa_mid}. Exception: {e}")
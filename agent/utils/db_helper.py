from pymongo import MongoClient
from dotenv import load_dotenv
import os 
import logging 
from datetime import datetime 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')




load_dotenv()
username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
host = os.getenv('MONGO_HOST')
port = os.getenv('MONGO_PORT')


AGENT_CHAT_DB = 'agent_data'
ROOMS_COLLECTION = 'rooms'


try:
    client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

def get_rooms_collection():
    try:
        agent_db = client[AGENT_CHAT_DB]
        chat_rooms_collection = agent_db[ROOMS_COLLECTION]
        logger.debug("Rooms collection retrieved successfully")
        return chat_rooms_collection
    except Exception as e:
        logger.error(f"Error retrieving rooms collection: {e}")
        raise



def handle_chat_room(chat_rooms_collection, room, message_body, timestamp=None, wa_mid=None):
    try:
        logger.debug(f"Handling chat room with room_id: {room}, message_body: {message_body}, timestamp: {timestamp}, wa_mid: {wa_mid}")
        
        if room:
            try:
                existing_room = chat_rooms_collection.find_one({'room_id': room})
                logger.debug(f"Existing room found: {existing_room is not None}")
            except Exception as e:
                logger.error(f"Error finding room with room_id: {room}: {e}")
                return

            message_data = {
                "sender": "business",
                "timestamp": timestamp if timestamp else datetime.utcnow(),
                "body": message_body,
                "wa_mid": wa_mid
            }

            if not existing_room:
                try:
                    logger.debug(f"No existing room found, creating a new room with room_id: {room}")
                    room_data = {
                        "room_id": room,
                        "created_at": datetime.utcnow(),
                        "messages": [message_data]
                    }
                    chat_rooms_collection.insert_one(room_data)
                    logger.info(f"Created new chat room with room_id: {room}")
                except Exception as e:
                    logger.error(f"Error creating new room with room_id: {room}: {e}")
            else:
                try:
                    logger.debug(f"Updating existing room with room_id: {room} with a new message")
                    chat_rooms_collection.update_one(
                        {'room_id': room},
                        {'$push': {'messages': message_data}}
                    )
                    logger.info(f"Updated chat room with new message for room_id: {room}")
                except Exception as e:
                    logger.error(f"Error updating room with room_id: {room}: {e}")
    except Exception as e:
        logger.error(f"Error in handle_chat_room function: {e}")

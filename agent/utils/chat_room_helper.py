import logging

from  logger_setup.logger_setup import LoggerSetup

logger = LoggerSetup(__name__).get_logger()





def get_opened_closed_discussions(chat_rooms_collection):
    try:
        logger.debug("Getting all conversations from the database...")

        # Fetch chat rooms from the collection, sorted by last_message_time in descending order
        chat_rooms = chat_rooms_collection.find(
            {}, 
            {'room_id': 1, 'open_discussion': 1, 'messages': 1, '_id': 0}
        ).sort("last_message_time", -1)  # Sort by last_message_time descending

        chat_rooms = list(chat_rooms)  # Convert to a list for easier processing

        open_rooms = []
        closed_rooms = []

        for chat in chat_rooms:
            room_id = chat.get('room_id')
            open_discussion = chat.get('open_discussion')
            messages = chat.get('messages', [])

            # Count unread messages sent by the user
            unread_count = sum(1 for msg in messages if msg.get('sender') == 'user' and msg.get('info') == 'unread')

            # Log the room and unread count for debugging
            logger.debug(f"Room ID: {room_id}, open_discussion: {open_discussion}, unread_count: {unread_count}")

            room_data = {
                "room_id": room_id,
                "unread_count": unread_count
            }

            if open_discussion is True:
                open_rooms.append(room_data)
            elif open_discussion is False:
                closed_rooms.append(room_data)
            else:
                # Log unexpected values of 'open_discussion'
                logger.warning(f"Unexpected 'open_discussion' value for Room ID {room_id}: {open_discussion}")

        logger.debug("Successfully categorized open and closed discussions.")
        return open_rooms, closed_rooms

    except Exception as e:
        # Log the exception with an error level
        logger.error(f"An error occurred while fetching and processing chat rooms: {e}")


        


    



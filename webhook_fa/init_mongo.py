import json
import logging
from pymongo import MongoClient, errors,DESCENDING

# Configure the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to console handler
console_handler.setFormatter(formatter)

# Add console handler to logger
logger.addHandler(console_handler)


def create_collections():
    try:
        # Connect to MongoDB
        from dotenv import load_dotenv
        import os
        load_dotenv()
        username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
        password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        host = os.getenv('MONGO_HOST')
        port = os.getenv('MONGO_PORT')
        client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")

        # Access the database
        main_db = client.whatsapp_data
        agent_db = client.agent_data

        try:
        # Create the 'rooms' collection if it doesn't exist
            agent_db.create_collection("rooms")
            logger.info("Collection 'rooms' created successfully in 'agent_data' database.")
            
            # Reference the 'rooms' collection
            rooms_collection = agent_db["rooms"]
            
            # Set an index on 'last_message_time' field in descending order
            rooms_collection.create_index([("last_message_time", DESCENDING)], name="last_message_time_desc")
            logger.info("Index 'last_message_time_desc' created on 'last_message_time' in 'rooms' collection.")
            
        except Exception as e:
            # Log an error if collection creation or indexing fails
            logger.error(f"An error occurred while creating the 'rooms' collection or setting the index: {e}")

        collections = [
            'campaign', 'campaign_responses', 'language', 'members',
            'templates', 'user_credentials', 'webhook_latest_from_user',
            'webhook_latest_to_user', 'webhook_responses'
        ]

        existing_collections = main_db.list_collection_names()

        for collection_name in collections:
            if collection_name not in existing_collections:
                try:
                    main_db.create_collection(collection_name)
                    logger.info(f"Collection '{collection_name}' created successfully.")
                except errors.CollectionInvalid:
                    logger.warning(f"Collection '{collection_name}' could not be created.")
            else:
                logger.info(f"Collection '{collection_name}' already exists.")

        # Check if the language collection is empty and populate it with data from languages.json
        language_collection = main_db['language']
        if language_collection.count_documents({}) == 0:
            try:
                # Load the JSON data
                with open('/app/init_data/languages.json', 'r') as file:
                    language_data = json.load(file)

                # Insert the data into the language collection
                language_collection.insert_many(language_data)
                logger.info("Languages data inserted successfully into the 'language' collection.")
            except FileNotFoundError:
                logger.error("The file 'languages.json' was not found.")
            except json.JSONDecodeError:
                logger.error("Error decoding JSON from the file 'languages.json'.")
            except errors.BulkWriteError as bwe:
                logger.error(f"Bulk write error occurred: {bwe.details}")
            except Exception as e:
                logger.error(f"An error occurred while inserting data into 'language': {e}")
        else:
            logger.info("The 'language' collection already contains data.")

        # Insert new user data without deleting existing users in the user_credentials collection
        user_credentials_collection = main_db['user_credentials']

        try:
            # Load the JSON data
            with open('/app/init_data/users.json', 'r') as file:
                users_data = json.load(file)

            # Insert new users, skip if user_id already exists
            if users_data:
                for user in users_data:
                    user_id = user.get('user_id')  # Assuming 'user_id' is the key for user identification
                    if user_id:
                        existing_user = user_credentials_collection.find_one({'user_id': user_id})
                        if existing_user:
                            logger.info(f"User with user_id {user_id} already exists. Skipping insertion.")
                        else:
                            user_credentials_collection.insert_one(user)
                            logger.info(f"Inserted user with user_id {user_id} into the 'user_credentials' collection.")
                    else:
                        logger.warning(f"No 'user_id' found for user: {user}. Skipping this entry.")
            else:
                logger.warning("No user data found in 'users.json' to insert.")

        except FileNotFoundError:
            logger.error("The file 'users.json' was not found.")
        except json.JSONDecodeError:
            logger.error("Error decoding JSON from the file 'users.json'.")
        except errors.BulkWriteError as bwe:
            logger.error(f"Bulk write error occurred: {bwe.details}")
        except Exception as e:
            logger.error(f"An error occurred while updating 'user_credentials': {e}")

    except errors.ConnectionError as e:
        logger.error(f"Could not connect to MongoDB: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


import json
from pymongo import MongoClient, errors
from dotenv import load_dotenv
import os

def create_collections():
    try:
        # Load environment variables
        load_dotenv()
        username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
        password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        host = os.getenv('MONGO_HOST')
        port = os.getenv('MONGO_PORT')

        # Connect to MongoDB
        client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")

        # Access the database
        db = client.whatsapp_data

        # Define collections to create
        collections = [
            'campaign', 'campaign_responses', 'final_campaign_response','language', 'members',
            'templates', 'user_credentials', 'webhook_latest_from_user',
            'webhook_latest_to_user', 'webhook_responses'
        ]

        existing_collections = db.list_collection_names()

        # Create collections if they don't exist
        for collection_name in collections:
            if collection_name not in existing_collections:
                try:
                    db.create_collection(collection_name)
                    print(f"Collection '{collection_name}' created successfully.")
                except errors.CollectionInvalid:
                    print(f"Collection '{collection_name}' could not be created.")
            else:
                print(f"Collection '{collection_name}' already exists.")

        # Check if the 'language' collection is empty and populate it
        language_collection = db['language']
        if language_collection.count_documents({}) == 0:
            try:
                # Load languages.json
                with open('/app/init_data/languages.json', 'r') as file:
                    language_data = json.load(file)

                # Insert the data into the 'language' collection
                language_collection.insert_many(language_data)
                print("Languages data inserted successfully into the 'language' collection.")
            except FileNotFoundError:
                print("The file 'languages.json' was not found.")
            except json.JSONDecodeError:
                print("Error decoding JSON from 'languages.json'.")
            except errors.BulkWriteError as bwe:
                print(f"Bulk write error occurred: {bwe.details}")
            except Exception as e:
                print(f"An error occurred while inserting data into 'language': {e}")
        else:
            print("The 'language' collection already contains data.")

        # Insert new user data without deleting existing users
        user_credentials_collection = db['user_credentials']
        try:
            # Load users.json
            with open('/app/init_data/users.json', 'r') as file:
                users_data = json.load(file)

            # Insert users, skipping existing ones
            if users_data:
                for user in users_data:
                    user_id = user.get('user_id')  # Assuming 'user_id' is the key
                    if user_id:
                        existing_user = user_credentials_collection.find_one({'user_id': user_id})
                        if existing_user:
                            print(f"User with user_id {user_id} already exists. Skipping insertion.")
                        else:
                            user_credentials_collection.insert_one(user)
                            print(f"Inserted user with user_id {user_id} into 'user_credentials'.")
                    else:
                        print(f"User has no 'user_id': {user}. Skipping this entry.")
            else:
                print("No user data found in 'users.json' to insert.")

        except FileNotFoundError:
            print("The file 'users.json' was not found.")
        except json.JSONDecodeError:
            print("Error decoding JSON from 'users.json'.")
        except errors.BulkWriteError as bwe:
            print(f"Bulk write error occurred: {bwe.details}")
        except Exception as e:
            print(f"An error occurred while updating 'user_credentials': {e}")

    except errors.ConfigurationError as e:
        print(f"Could not connect to MongoDB due to configuration issues: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


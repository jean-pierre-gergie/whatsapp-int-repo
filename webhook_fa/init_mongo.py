import json
from pymongo import MongoClient, errors
import os

print("Init_mongo.py")

def create_collections():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
        password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        host = os.getenv('MONGO_HOST')
        port = os.getenv('MONGO_PORT',27017)
        database_name = 'whatsapp_data'
        client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")
        
        try:
            client.server_info()
            print("Connected to MongoDB successfully.")
        except errors.ServerSelectionTimeoutError as err:
            print(f"Could not connect to MongoDB: {err}")
            return  

        admin_db = client.admin
        database_names = client.list_database_names()

        if database_name not in database_names:
            db = client[database_name]

            collections = [
                'campaign', 'campaign_responses', 'language', 'members',
                'templates', 'user_credentials', 'webhook_latest_from_user',
                'webhook_latest_to_user', 'webhook_responses'
            ]

            existing_collections = db.list_collection_names()

            for collection_name in collections:
                if collection_name not in existing_collections:
                    try:
                        db.create_collection(collection_name)
                        # Force the creation by inserting a dummy document and then deleting it
                        db[collection_name].insert_one({"_init": True})
                        db[collection_name].delete_one({"_init": True})
                        print(f"Collection '{collection_name}' created successfully.")
                    except errors.CollectionInvalid:
                        print(f"Collection '{collection_name}' could not be created.")
                else:
                    print(f"Collection '{collection_name}' already exists.")

            # Check if the language collection is empty and populate it with data from languages.json
            language_collection = db['language']
            if language_collection.count_documents({}) == 0:
                try:
                    # Load the JSON data
                    with open('/app/init_data/languages.json', 'r') as file:
                        language_data = json.load(file)

                    # Insert the data into the language collection
                    language_collection.insert_many(language_data)
                    print("Languages data inserted successfully into the 'language' collection.")
                except FileNotFoundError:
                    print("The file 'languages.json' was not found.")
                except json.JSONDecodeError:
                    print("Error decoding JSON from the file 'languages.json'.")
                except errors.BulkWriteError as bwe:
                    print(f"Bulk write error occurred: {bwe.details}")
                except Exception as e:
                    print(f"An error occurred while inserting data into 'language': {e}")
            else:
                print("The 'language' collection already contains data.")

            # Delete all documents and insert new data in the user_credentials collection
            user_credentials_collection = db['user_credentials']
            
            try:
                # Load the JSON data
                with open('/app/init_data/users.json', 'r') as file:
                    users_data = json.load(file)

                # Delete all existing documents in the collection
                delete_result = user_credentials_collection.delete_many({})
                print(f"Deleted {delete_result.deleted_count} existing documents from 'user_credentials'.")

                # Insert the new data
                if users_data:
                    user_credentials_collection.insert_many(users_data)
                    print("New user data inserted successfully into the 'user_credentials' collection.")
                else:
                    print("No user data found in 'users.json' to insert.")

            except FileNotFoundError:
                print("The file 'users.json' was not found.")
            except json.JSONDecodeError:
                print("Error decoding JSON from the file 'users.json'.")
            except errors.BulkWriteError as bwe:
                print(f"Bulk write error occurred: {bwe.details}")
            except Exception as e:
                print(f"An error occurred while updating 'user_credentials': {e}")
        else:
            print("The 'whatsapp_data' database already exists. No action was taken.")

    except errors.ConnectionFailure as e:
        print(f"Could not connect to MongoDB: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

create_collections()
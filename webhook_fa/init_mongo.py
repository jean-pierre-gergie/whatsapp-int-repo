import json
from pymongo import MongoClient, errors

def create_collections():
    try:
        # Connect to MongoDB
        from dotenv import load_dotenv
        import os
        load_dotenv()
        username = os.getenv('MONGO_INITDB_ROOT_USERNAME','rtenn')
        password = os.getenv('MONGO_INITDB_ROOT_PASSWORD','123456')
        host = os.getenv('MONGO_HOST','mongodb_container')
        port = os.getenv('MONGO_PORT', 27017)
        client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")

        # Access the database
        db = client.whatsapp_data

        # Create collections
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

    except errors.ConnectionError as e:
        print(f"Could not connect to MongoDB: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
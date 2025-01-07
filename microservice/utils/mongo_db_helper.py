import json
import logging
from pymongo import MongoClient, errors, DESCENDING
from dotenv import load_dotenv
import os
from logger_setup.logger_setup import logger





load_dotenv()


def get_mongo_client():
    """Establish MongoDB client connection using environment variables."""
    try:
        username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
        password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        host = os.getenv('MONGO_HOST')
        port = os.getenv('MONGO_PORT')
        client = MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")
        return client
    except errors.ConnectionError as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise

def populate_collection_from_json(collection, json_path, unique_field=None):
    """Populate a MongoDB collection with data from a JSON file, optionally skipping documents if `unique_field` exists."""
    try:
        with open(json_path, 'r') as file:
            data = json.load(file)
        if data:
            for document in data:
                if unique_field and collection.find_one({unique_field: document.get(unique_field)}):
                    logger.info(f"Document with '{unique_field}'={document.get(unique_field)} already exists. Skipping insertion.")
                else:
                    collection.insert_one(document)
                    # logger.info(f"Inserted document into '{collection.name}' collection.")
    except FileNotFoundError:
        logger.error(f"The file '{json_path}' was not found.")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from the file '{json_path}'.")
    except errors.BulkWriteError as bwe:
        logger.error(f"Bulk write error occurred: {bwe.details}")
    except Exception as e:
        logger.error(f"An error occurred while populating '{collection.name}': {e}")


def create_collection_if_not_exists(db, collection_name):
    """Create a MongoDB collection if it doesn't already exist."""
    if collection_name not in db.list_collection_names():
        try:
            db.create_collection(collection_name)
            # logger.info(f"Collection '{collection_name}' created successfully.")
        except errors.CollectionInvalid:
            
            logger.warning(f"Collection '{collection_name}' could not be created.")
    else:
        pass
        # logger.info(f"Collection '{collection_name}' already exists.")

def create_index(collection, field_name, index_name, order=DESCENDING):
    """Create an index on a specified field in the collection."""
    try:
        collection.create_index([(field_name, order)], name=index_name)
        logger.info(f"Index '{index_name}' created on '{field_name}' in '{collection.name}' collection.")
    except Exception as e:
        logger.error(f"An error occurred while creating index '{index_name}': {e}")


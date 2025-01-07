from utils.mongo_db_helper import get_mongo_client,populate_collection_from_json
from utils.grant_user_access_helper import grant_user_access





def add_users_to_db(logger):
    """
    This function initializes a MongoDB collection with user credentials.
    It reads data from a JSON file and populates the collection, ensuring
    unique entries based on a specified field.

    The data is loaded from '/app/init_data/users.json', and the unique field is 'user_id'.
    """
    try:
        # Initialize MongoDB client
        client = get_mongo_client()

        # Access the database and collection
        user_credentials_db = client['user_credentials_db']
        user_credentials_collection = user_credentials_db['user_credentials']

        # Populate collection with data from JSON
        populate_collection_from_json(
            user_credentials_collection,
            '/app/init_data/users.json',
            unique_field='user_id'
        )
        

        # TODO SET  foundation per user and set default foundation (admin all foundations , user defined )

        grant_user_access(logger=logger)


        logger.info("Users successfully added to the database.")
    except Exception as e:
        # Log any exceptions that occur
        logger.error(f"An error occurred while adding users to the database: {e}", exc_info=True)


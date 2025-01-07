from utils.mongo_db_helper import get_mongo_client



def grant_user_access(logger):
    """
    Grants access to foundations for users based on their roles.
    
    - For users with role 'admin', grants access to all foundations and sets the first foundation
      in the list as the default foundation.
    - Users with role 'user' remain unchanged.

    Parameters:
        logger (logging.Logger): Logger instance for logging messages.

    Returns:
        None
    """
    try:
        # Get MongoDB client
        client = get_mongo_client()
        users_collection = client['user_credentials_db']['user_credentials']
        foundations_collection = client['foundations_db']['foundations']

        # Fetch the list of all foundations
        foundations_list = foundations_collection.distinct("foundation")
        
        if not foundations_list:
            logger.error("No foundations found in the foundations collection.")
            return
        
        # Iterate through all users and update based on role
        for user in users_collection.find():
            try:
                if user.get("role") == "admin":
                    # Update the user document for admin role
                    users_collection.update_one(
                        {"_id": user["_id"]},
                        {
                            "$set": {
                                "granted_foundations": foundations_list,
                                "default_foundation": foundations_list[0],
                            }
                        }
                    )
                    logger.info(f"Updated admin user: {user.get('username')} with foundations access.")
                elif user.get("role") == "user":
                    logger.info(f"User {user.get('username')} remains unchanged.")
                else:
                    logger.warning(f"Unknown role for user: {user.get('username')}")
            except Exception as e:
                logger.error(f"Failed to update user {user.get('username')} with error: {e}")

        logger.info("Completed processing all users.")
    except Exception as e:
        logger.critical(f"Failed to grant user access due to an error: {e}")








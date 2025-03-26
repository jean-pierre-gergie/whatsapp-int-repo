
def clear_revoked_tokens(revoked_tokens_collection,logger):
    try:
        count = revoked_tokens_collection.count_documents({})

        # If there are any documents, delete them all
        if count > 0:
            result = revoked_tokens_collection.delete_many({})
            print(f"Deleted {result.deleted_count} documents from 'revoked_tokens' collection.")
        else:
            print("No documents to delete in 'revoked_tokens' collection.")
    except Exception as e:
        logger.error(f"An error occurred while clearing the revoked token collection: {e}", exc_info=True)


def set_jwt_token (logger):
    try:
        secret_key = os.getenv("JWT_SECRET_KEY")
        webhook_url = get_webhook_url()
        logger.debug(f"webhook url : {webhook_url}")
        logger.info ("Refreshing JWT ...")
        if not secret_key:
            logger.error("JWT_SECRET_KEY is not set in environment variables.")
            return
        

        logger.info("Starting JWT INIT process.")
        foundations_names = get_all_foundation_names()
        mongo_client = get_mongo_client()

        foundations_collection = mongo_client['foundations_db']['foundations']
        revoked_tokens_collection = mongo_client['revoked_tokens_db']['revoked_tokens']
        clear_revoked_tokens(revoked_tokens_collection , logger)


        for foundation_name in foundations_names:
            try:
                logger.debug(f"Processing foundation: {foundation_name}")
                foundation_doc = foundations_collection.find_one({"foundation": foundation_name})


                if not foundation_doc:
                    logger.warning(f"No document found for foundation: {foundation_name}")
                    continue

                old_jwt = foundation_doc.get('jwt')
                if old_jwt:
                    try:
                        # Add the old JWT to the revoked tokens collection
                        revoked_tokens_collection.insert_one({
                            "foundation": foundation_name,
                            "revoked_jwt": old_jwt,
                            "revoked_at": datetime.datetime.utcnow()
                        })
                        logger.info(f"Old JWT for {foundation_name} added to revoked tokens.")
                    except Exception as e:
                        logger.error(f"Failed to add old JWT to revoked tokens for {foundation_name}: {e}")

                     # Generate a new JWT token
                new_jwt_token = generate_jwt_token(secret_key)

                logger.info(f"Setting webhook for {foundation_name}")
                set_webhook_config(
                    foundation_name=foundation_name,
                    api_key=foundation_doc['api_key'],
                    webhook_base_url=webhook_url,
                    jwt_token=new_jwt_token
                )
                logger.debug(f"Webhook SET for foundation: {foundation_name}")
                foundations_collection.update_one(
                    {"foundation": foundation_name},
                    {"$set": {"jwt": new_jwt_token}}
                )
                logger.debug(f"JWT token SET for foundation: {foundation_name}")

            except Exception as e:
                logger.error(f"Error processing foundation {foundation_name}: {e}")
        logger.info("JWT for WEBHOOK SETTING process completed.")
    except Exception as e:
        logger.error(f"Critical error in refresh_jwt...")
        logger.debug(f"Critical error in refresh_jwt: {e}")

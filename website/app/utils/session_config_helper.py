from flask import session, current_app, flash, redirect, url_for
import logging

logger = logging.getLogger(__name__)


def get_session_foundation_config():
    """
    Retrieve the foundation-specific configuration and user-specific details from the session.

    This function fetches the configuration stored in the session, including API keys, 
    database names, and other relevant details. It handles errors gracefully by logging 
    and flashing appropriate messages.

    Returns:
        dict: A dictionary containing user and foundation-specific details, such as:
              - user_name (str): Name of the logged-in user.
              - user_role (str): Role of the user (e.g., admin, user).
              - granted_foundations (list): List of foundations the user has access to.
              - foundation_name (str): Current foundation name.
              - api_key (str): API key for the foundation.
              - whatsapp_data_db (MongoDB Collection): Collection for WhatsApp data.
              - agent_data_db (MongoDB Collection): Collection for Agent data.
              
              Returns an empty dictionary if an error occurs.
    """
    try:
        # Retrieve foundation and user configurations from the session
        foundation_config = session.get('foundation_configs')
        user_configs = session.get('user_configs')
        
        logger.debug(f"GET SESSION CONFIG --- Current foundation configuration from session: {foundation_config}")
        logger.debug(f"GET SESSION CONFIG --- Current user configuration from session: {user_configs}")

        if foundation_config and user_configs:
            try:
                # Extract foundation configuration details
                foundation_name = foundation_config.get('foundation_name', 'Default Foundation')
                foundation_db_name = foundation_config.get('whatsapp_data_db')
                agent_db_name = foundation_config.get('agent_data_db')
                api_key = foundation_config.get('api_key')

                # Access MongoDB collections using the extracted database names
                whatsapp_data_db = current_app.mongo[foundation_db_name]
                agent_data_db = current_app.mongo[agent_db_name]

                logger.debug(f"GET SESSION CONFIG --- Successfully accessed databases: "
                             f"WhatsApp DB={foundation_db_name}, Agent DB={agent_db_name}")

                # Return the consolidated configuration
                return {
                    "user_name": user_configs.get("user_name"),
                    "user_role": user_configs.get("user_role"),
                    "granted_foundations": user_configs.get("granted_foundations"),
                    'default_foundation':user_configs.get("default_foundation"),
                    "foundation_name": foundation_name,
                    "api_key": api_key,
                    "whatsapp_data_db": whatsapp_data_db,
                    "agent_data_db": agent_data_db
                }
            except KeyError as e:
                logger.error(f"GET SESSION CONFIG --- Missing key in foundation configuration: {str(e)}")
                flash("Configuration error. Please log in again.", "error")
                return {}
            except Exception as e:
                logger.error(f"GET SESSION CONFIG --- Unexpected error accessing MongoDB: {str(e)}")
                flash("Database access error. Please log in again.", "error")
                return {}
        else:
            # Log and flash error if session configurations are missing
            logger.error("GET SESSION CONFIG --- Foundation or user configuration not found in session.")
            flash("Configuration error. Please log in again.", "error")
            return {}

    except Exception as e:
        # Handle unexpected errors during session retrieval
        logger.critical(f"GET SESSION CONFIG --- Critical error retrieving session configuration: {str(e)}")
        flash("An unexpected error occurred. Please log in again.", "error")
        return {}
    


def set_session_foundation_config(user_name,
                                  user_role,
                                  granted_foundations,
                                  default_foundation,
                                  foundation_name,
                                  api_key,
                                  whatsapp_data_db,
                                  agent_data_db
                                  ):
    """
    Set session configurations for foundation and user-specific details.

    Parameters:
        user_name (str): Name of the user.
        user_role (str): Role of the user (e.g., admin, user).
        granted_foundations (list): List of foundations the user has access to.
        default_foundation (str): Default foundation for the user.
        foundation_name (str): Current foundation name.
        api_key (str): API key for the current foundation.
        whatsapp_data_db (str): WhatsApp data database for the current foundation.
        agent_data_db (str): Agent data database for the current foundation.

    Returns:
        None
    """

    logger.debug(f"SETTING SESSION CONFIGS --- Starting session setup for user: {user_name}, role: {user_role}")

    # Logging details of granted foundations and default foundation
    logger.debug(f"SETTING SESSION CONFIGS --- Granted foundations for user {user_name}: {granted_foundations}")
    logger.debug(f"SETTING SESSION CONFIGS --- Default foundation for user {user_name}: {default_foundation}")

    # Logging the foundation-specific configuration
    logger.debug(f"SETTING SESSION CONFIGS --- Foundation configuration being set: "
                 f"foundation_name={foundation_name}, api_key={api_key}, "
                 f"whatsapp_data_db={whatsapp_data_db}, agent_data_db={agent_data_db}")

    # Set foundation configurations in session
    session['foundation_configs'] = {
        'foundation_name': foundation_name,
        'api_key': api_key,
        'whatsapp_data_db': whatsapp_data_db,
        'agent_data_db': agent_data_db
    }
    logger.info(f"Foundation session configurations set for foundation: {foundation_name}")

    # Set user configurations in session
    session['user_configs'] = {
        "user_name": user_name,
        "user_role": user_role,
        "default_foundation": default_foundation,
        "granted_foundations": granted_foundations
    }
    logger.info(f"User session configurations set for user: {user_name}, role: {user_role}")

    # Log the final session state for foundation and user configs
    logger.debug(f"SETTING SESSION CONFIGS --- Final session state for foundation_configs: {session['foundation_configs']}")
    logger.debug(f"SETTING SESSION CONFIGS --- Final session state for user_configs: {session['user_configs']}")







def get_all_foundations():
    foundations_collection = current_app.mongo['foundations_db']['foundations']
    all_foundations = list(foundations_collection.find({}, {'_id': 0, 'foundation': 1}))
    all_foundations=[f['foundation'] for f in all_foundations]
    logger.debug(f"Retrieved available foundations: {all_foundations}")
    return all_foundations
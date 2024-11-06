from flask import session, current_app, flash, redirect, url_for
import logging

logger = logging.getLogger(__name__)


def get_session_foundation_config():
    """Retrieve the foundation-specific configuration from the session.
    
    Returns:
        dict: Foundation-specific configuration, including API key, database, and collection references.
    """
    # Retrieve the foundation config from the session
    foundation_config = session.get('foundation')
    logger.debug(f"Current foundation configuration from session: {foundation_config}")

    if foundation_config:
        try:
            # Extract foundation-specific details
            foundation_name = foundation_config.get('foundation_name', 'Default Foundation')
            foundation_db_name = foundation_config.get('whatsapp_data_db')
            agent_db_name = foundation_config.get('agent_data_db')
            api_key = foundation_config.get('api_key')

            # Access specific databases
            whatsapp_data_db = current_app.mongo[foundation_db_name]
            agent_data_db = current_app.mongo[agent_db_name]

            return {
                "foundation_name": foundation_name,
                "api_key": api_key,
                "whatsapp_data_db": whatsapp_data_db,
                "agent_data_db": agent_data_db
            }
        
        except KeyError as e:
            logger.error(f"Configuration error: Missing {str(e)} in foundation config.")
            flash("Configuration error. Please log in again.", "error")
            return redirect(url_for('auth.login'))

    else:
        logger.error("Foundation configuration not found in session.")
        flash("Configuration error. Please log in again.", "error")
        return redirect(url_for('auth.login'))
    
def get_all_foundations():
    foundations_collection = current_app.mongo['foundations_db']['foundations']
    all_foundations = list(foundations_collection.find({}, {'_id': 0, 'foundation': 1}))
    logger.debug(f"Retrieved available foundations: {[f['foundation'] for f in all_foundations]}")
    return all_foundations
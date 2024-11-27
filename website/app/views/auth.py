import logging
from flask import Blueprint, request, jsonify, make_response, render_template, redirect, url_for, session, current_app, flash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity , get_jwt
import bcrypt
from bson.objectid import ObjectId
from ..utils.decorators import  role_required
from ..utils.session_config_helper import get_session_foundation_config,get_all_foundations
import uuid

bp = Blueprint('auth', __name__)


# Initialize logger for this module
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG, 
                    format='- %(name)s - %(levelname)s - %(message)s')


# @bp.app_context_processor
# def inject_foundation_data():
#     session_configs = get_session_foundation_config()
#     foundation_name = session_configs.get('foundation_name')
#     all_foundations = get_all_foundations()
#     return dict(foundation_name=foundation_name, foundations=all_foundations)



# TODO : add a function in session_config_helper to set the session configs
@bp.route('/', methods=['GET', 'POST'])
def login():
    user_credentials_collection = current_app.mongo['user_credentials_db']['user_credentials']

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        logger.debug(f"Attempting login for username: {username}")

        try:
            # Fetch user from the database
            user = user_credentials_collection.find_one({'username': username})

            if user:
                logger.debug(f"User {username} found in the database.")
                stored_password = user.get('user_password')

                # Convert the stored password to bytes if it's a string
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')

                # Verify the password
                if bcrypt.checkpw(password, stored_password):
                    logger.debug(f"Password for user {username} is correct.")

                    # Fetch the role and foundation from the user document
                    role = user.get('role', 'user')  # Default to 'user' role if not specified
                    foundation_name = user.get('foundation')

                    logger.debug(f"User {username} has role: {role}, foundation: {foundation_name}")

                    # Fetch foundation-specific details from the database
                    foundations_collection = current_app.mongo['foundations_db']['foundations']
                    foundation_config = foundations_collection.find_one({"foundation": foundation_name})

                    
                    if foundation_config:
                        logger.debug(f"Foundation configuration found for {foundation_name}: {foundation_config}")

                        # Clear existing session and set new foundation-specific details
                        session.clear()
                        session['foundation'] = {
                            'foundation_name': foundation_name,
                            'api_key': foundation_config['api_key'],
                            'whatsapp_data_db': foundation_config['whatsapp_data_db'],
                            'agent_data_db': foundation_config['agent_data_db']
                        }
                        logger.debug(f"Session updated for foundation {foundation_name}.")
                    else:
                        logger.error(f"Foundation configuration not found for {foundation_name}.")
                        flash("Foundation configuration not found. Please contact support.", "error")
                        return render_template('login.html')

                    # Create JWT token with username and role
                    access_token = create_access_token(identity={'username': user['username'], 'role': role})
                    logger.debug(f"JWT created for user {username} with role {role}.")

                    # Set the JWT in the cookie
                    response = make_response(redirect(url_for('auth.index')))
                    response.set_cookie(
                        'access_token_cookie', 
                        access_token, 
                        httponly=True, 
                        secure=True, 
                        samesite='None'
                    )

                    logger.info(f"Login successful for user {username}. Redirecting to /index.")
                    return response
                else:
                    logger.warning(f"Incorrect password attempt for user {username}.")
            else:
                logger.warning(f"Login attempt for non-existent user: {username}.")

        except Exception as e:
            logger.error(f"Error during login process: {str(e)}")
            flash("An error occurred during login. Please try again.", "error")
            return render_template('login.html')

        # If login fails
        flash("Invalid username or password", "error")
        logger.debug(f"Rendering login page due to invalid login for user {username}.")
        return render_template('login.html')

    # GET request, render the login page
    logger.debug("Rendering login page (GET request).")
    return render_template('login.html')


@bp.route('/index')
@jwt_required()
@role_required(['admin', 'user'])  
def index():
    current_user = get_jwt_identity()  # Get the current user's identity from the JWT token
    logger.debug(f"Current user JWT identity: {current_user}")
    
    role = current_user.get('role', 'user')  # Default to 'user' role if not specified
    logger.debug(f"User {current_user['username']} has role: {role}")
    
    
    session_configs =get_session_foundation_config()

    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get('foundation_name')
    # Fetch campaigns from the database
    campaigns_collection = whatsapp_data_db.campaign
    campaigns = list(campaigns_collection.find())
    campaigns_data = [{"id": campaign.get('campaign_id'), "name": campaign.get('campaign_name')} for campaign in campaigns]
    logger.debug(f"Retrieved {len(campaigns_data)} campaigns from the database.")
    
    # Fetch templates from the database
    templates_collection = whatsapp_data_db.templates
    templates = list(templates_collection.find())
    templates_data = [{"id": template.get('template_id'), "name": template.get('template_name')} for template in templates]
    logger.debug(f"Retrieved {len(templates_data)} templates from the database.")


    # Fetch all available foundations for the sidebar
    foundations_collection = current_app.mongo['foundations_db']['foundations']
    all_foundations = list(foundations_collection.find({}, {'_id': 0, 'foundation': 1}))
    logger.debug(f"Retrieved available foundations: {[f['foundation'] for f in all_foundations]}")
    
    # Render the index page with user, campaigns, and templates data
    if role == 'admin':
        logger.info(f"Rendering index page for admin {current_user['username']}.")
        return render_template('index.html', 
                                current_user=current_user,
                                campaigns=campaigns_data,
                                templates=templates_data,
                                is_admin=True,
                                foundation_name=foundation_name,
                                foundations=all_foundations)
    else:
        logger.info(f"Rendering index page for user {current_user['username']}.")
        return render_template('index.html',
                               current_user=current_user,
                               campaigns=campaigns_data,
                               templates=templates_data,
                               is_admin=False,
                               foundation_name=foundation_name,
                               foundations=all_foundations)



@bp.route('/switch_foundation/<foundation_name>')
def switch_foundation(foundation_name):
    logging.debug(f"Switching foundation to: {foundation_name}")
    
    foundations_collection = current_app.mongo['foundations_db']['foundations']
    foundation_config = foundations_collection.find_one({"foundation": foundation_name})
    
    if foundation_config:
        logging.debug(f"Foundation config found: {foundation_config}")
        
        session['foundation'] = {
            'foundation_name': foundation_name,
            'api_key': foundation_config['api_key'],
            'whatsapp_data_db': foundation_config['whatsapp_data_db'],
            'agent_data_db': foundation_config['agent_data_db']
        }
        
        logging.debug(f"Session updated with foundation: {session['foundation']}")
    else:
        logging.warning(f"Foundation {foundation_name} not found in the database.")

    return redirect(url_for('auth.index'))


# TODO :
@bp.route('/change_password', methods=['GET', 'POST'])
@jwt_required()
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not old_password or not new_password or not confirm_password:
            flash('Please fill out all fields', 'error')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('auth.change_password'))

        current_user = get_jwt_identity()
        username = current_user['username']

        session_configs =get_session_foundation_config()

        whatsapp_data_db = session_configs.get('whatsapp_data_db')
        foundation_name = session_configs.get('foundation_name')
        user_credentials_collection  = current_app.mongo['user_credentials_db']['user_credentials']

        user = user_credentials_collection.find_one({'username': username})

        if user is None or not bcrypt.checkpw(old_password.encode('utf-8'), user['user_password'].encode('utf-8') if isinstance(user['user_password'], str) else user['user_password']):
            flash('Old password is incorrect', 'error')
            return redirect(url_for('auth.change_password'))

        if bcrypt.checkpw(new_password.encode('utf-8'), user['user_password'].encode('utf-8') if isinstance(user['user_password'], str) else user['user_password']):
            flash('New password cannot be the same as the old password', 'error')
            return redirect(url_for('auth.change_password'))

        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        result = user_credentials_collection.update_one(
            {'username': username},
            {'$set': {'user_password': hashed_password}}
        )

        if result.matched_count > 0:
            # Revoke current JWT token
            jti = get_jwt()["jti"]  # Get the JWT ID from the current token
            whatsapp_data_db.revoked_tokens.insert_one({"jti": jti})
            flash('Password updated successfully. Please log in again.', 'success')

            # Optionally, you can clear the JWT cookie to force re-login
            response = make_response(redirect(url_for('auth.login')))
            response.delete_cookie('access_token_cookie')
            return response
        else:
            flash('Error updating password', 'error')

    return render_template('change_password.html')



# TODO :
@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        session_configs =get_session_foundation_config()

        whatsapp_data_db = session_configs.get('whatsapp_data_db')
        
        user_credentials_collection  = current_app.mongo['user_credentials_db']['user_credentials']

        if user_credentials_collection.find_one({'username': username}):
            flash('Username already exists', 'error')
            return render_template('signup.html', message='Username already exists')

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        new_user = {
            '_id': ObjectId(),
            'user_id': str(uuid.uuid4()),  
            'username': username,
            'role': role,
            'user_password': hashed_password.decode('utf-8')  
        }

        user_credentials_collection.insert_one(new_user)
        flash('User created successfully', 'success')
        return render_template('signup.html', message='User created successfully', success=True)

    return render_template('signup.html', message='')



# TODO :
@bp.route('/logout')
def logout():
    session.clear() 
    response = make_response(redirect(url_for('auth.login')))
    response.set_cookie('access_token_cookie', '', expires=0)  
    return redirect(url_for('auth.login'))


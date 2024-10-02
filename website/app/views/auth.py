import logging
from flask import Blueprint, request, jsonify, make_response, render_template, redirect, url_for, session, current_app, flash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt
from bson.objectid import ObjectId
from ..utils.decorators import  role_required
import uuid

bp = Blueprint('auth', __name__)

# Initialize logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@bp.route('/', methods=['GET', 'POST'])
def login():
    mongo_db = current_app.mongo
    collection = mongo_db.user_credentials

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        logger.debug(f"Attempting login for username: {username}")
        
        # Fetch user from the database
        user = collection.find_one({'username': username})
        
        if user:
            logger.debug(f"User {username} found in the database.")
            stored_password = user.get('user_password')

            # Convert the stored password to bytes if it's a string
            if isinstance(stored_password, str):
                stored_password = stored_password.encode('utf-8')
            
            # Verify the password
            if bcrypt.checkpw(password, stored_password):
                logger.debug(f"Password for user {username} is correct.")

                # Fetch the role from the user document
                role = user.get('role', 'user')  # Default to 'user' role if not specified
                logger.debug(f"User {username} has role: {role}")

                # Create JWT token with username and role
                access_token = create_access_token(identity={'username': user['username'], 'role': role})
                logger.debug(f"JWT created for user {username} with role {role}.")

                # Set the JWT in the cookie
                response = make_response(redirect(url_for('auth.index')))
                response.set_cookie('access_token_cookie', access_token, httponly=True, secure=True, samesite='None')
                
                logger.info(f"Login successful for user {username} with role {role}. Redirecting to /index.")
                return response
            else:
                logger.warning(f"Incorrect password attempt for user {username}.")
        else:
            logger.warning(f"Login attempt for non-existent user: {username}.")
        
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
    
    mongo_db = current_app.mongo
    
    # Fetch campaigns from the database
    campaigns_collection = mongo_db.campaign
    campaigns = list(campaigns_collection.find())
    campaigns_data = [{"id": campaign.get('campaign_id'), "name": campaign.get('campaign_name')} for campaign in campaigns]
    logger.debug(f"Retrieved {len(campaigns_data)} campaigns from the database.")
    
    # Fetch templates from the database
    templates_collection = mongo_db.templates
    templates = list(templates_collection.find())
    templates_data = [{"id": template.get('template_id'), "name": template.get('template_name')} for template in templates]
    logger.debug(f"Retrieved {len(templates_data)} templates from the database.")
    
    # Render the index page with user, campaigns, and templates data
    if role == 'admin':
        logger.info(f"Rendering index page for admin {current_user['username']}.")
        return render_template('index.html', current_user=current_user, campaigns=campaigns_data, templates=templates_data, is_admin=True)
    else:
        logger.info(f"Rendering index page for user {current_user['username']}.")
        return render_template('index.html', current_user=current_user, campaigns=campaigns_data, templates=templates_data, is_admin=False)

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

        mongo_db = current_app.mongo
        user_credentials_collection = mongo_db.user_credentials

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
            flash('Password updated successfully', 'success')
        else:
            flash('Error updating password', 'error')

    return render_template('change_password.html')

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        mongo_db = current_app.mongo
        user_credentials_collection = mongo_db.user_credentials

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

@bp.route('/logout')
def logout():
    session.clear() 
    response = make_response(redirect(url_for('auth.login')))
    response.set_cookie('access_token_cookie', '', expires=0)  
    return redirect(url_for('auth.login'))

# @bp.before_request
# def before_request():
#     token = request.cookies.get('access_token_cookie')
#     if token:
#         request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {token}'
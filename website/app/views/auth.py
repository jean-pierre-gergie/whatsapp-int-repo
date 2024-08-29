from flask import Blueprint, request, jsonify, make_response, render_template, redirect, url_for, session , current_app,flash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET', 'POST'])
def login():
    mongo_db = current_app.mongo
    collection = mongo_db.user_credentials
    
    if request.method == 'POST':
        username = request.form['username']
        print(username)
        password = request.form['password'].encode('utf-8') 
        print(password)
        
        user = collection.find_one({'username': username})
        
        if user:
            stored_password = user.get('user_password')
            if isinstance(stored_password, str):
                stored_password = stored_password.encode('utf-8')  
            if bcrypt.checkpw(password, stored_password):
                access_token = create_access_token(identity={'username': user['username'], 'role': user['role']})
                response = make_response(jsonify({"msg": "Login successful"}), 200)
                response.set_cookie('access_token_cookie', access_token, httponly=True, secure=True, samesite='None')
                return response
        return jsonify({"msg": "Invalid username or password"}), 401
    
    return render_template('login.html')
 
@bp.route('/logout')
def logout():
    session.clear() 
    response = make_response(redirect(url_for('auth.login')))
    response.set_cookie('access_token_cookie', '', expires=0)  
    return redirect(url_for('auth.login'))

@bp.before_request
def before_request():
    token = request.cookies.get('access_token_cookie')
    if token:
        request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {token}'

@bp.route('/index')
@jwt_required()
def index():
    current_user = get_jwt_identity()
    print(current_user)
    
    mongo_db = current_app.mongo
    
    campaigns_collection = mongo_db.campaign
    campaigns = list(campaigns_collection.find())
    campaigns_data = [{"id": campaign.get('campaign_id'), "name": campaign.get('campaign_name')} for campaign in campaigns]
    
    templates_collection = mongo_db.templates
    templates = list(templates_collection.find())
    templates_data = [{"id": template.get('template_id'), "name": template.get('template_name')} for template in templates]
    
    return render_template('index.html', current_user=current_user, campaigns=campaigns_data, templates=templates_data)


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

        # Get the current user identity from JWT
        current_user = get_jwt_identity()
        username = current_user['username']

        # Fetch the user's current hashed password from the database
        mongo_db = current_app.mongo
        user_credentials_collection = mongo_db.user_credentials

        user = user_credentials_collection.find_one({'username': username})

        # Check if user exists and the passwords are correctly formatted
        if user is None or not bcrypt.checkpw(old_password.encode('utf-8'), user['user_password'].encode('utf-8') if isinstance(user['user_password'], str) else user['user_password']):
            flash('Old password is incorrect', 'error')
            return redirect(url_for('auth.change_password'))

        # Ensure the new password is different from the old one
        if bcrypt.checkpw(new_password.encode('utf-8'), user['user_password'].encode('utf-8') if isinstance(user['user_password'], str) else user['user_password']):
            flash('New password cannot be the same as the old password', 'error')
            return redirect(url_for('auth.change_password'))

        # Hash the new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        # Update the password in the database
        result = user_credentials_collection.update_one(
            {'username': username},
            {'$set': {'user_password': hashed_password}}
        )

        if result.matched_count > 0:
            flash('Password updated successfully', 'success')
        else:
            flash('Error updating password', 'error')

    return render_template('change_password.html')


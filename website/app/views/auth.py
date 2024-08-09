from flask import Blueprint, request, jsonify, make_response, render_template, redirect, url_for, session , current_app
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
    
    # Access MongoDB
    mongo_db = current_app.mongo
    
    # Fetch campaigns from MongoDB
    campaigns_collection = mongo_db.campaign
    campaigns = list(campaigns_collection.find())
    campaigns_data = [{"id": campaign.get('campaign_id'), "name": campaign.get('campaign_name')} for campaign in campaigns]
    
    # Fetch templates from MongoDB
    templates_collection = mongo_db.templates
    templates = list(templates_collection.find())
    templates_data = [{"id": template.get('template_id'), "name": template.get('template_name')} for template in templates]
    
    return render_template('index.html', current_user=current_user, campaigns=campaigns_data, templates=templates_data)

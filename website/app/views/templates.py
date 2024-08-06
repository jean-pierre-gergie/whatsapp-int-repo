from flask import Blueprint, render_template, request, jsonify,current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.decorators import role_required
from ..utils.helper_functions import get_template_texts
import requests
import json
from app.config import Config  

api_key_360 =Config.API_KEY

bp = Blueprint('templates', __name__)

@bp.route('/templates')
@jwt_required()
@role_required('admin')
def templates_list():
    current_user = get_jwt_identity()
    mongo_db = current_app.mongo
    collection = mongo_db.templates 
    
    templates = list(collection.find())

    for template in templates:
        template['_id'] = str(template['_id'])  

    return render_template('templates.html', templates=templates)


@bp.route('/create_template_html')
@jwt_required()
@role_required('admin')
def create_template_page():
    current_user = get_jwt_identity()
    mongo_db = current_app.mongo
    collection = mongo_db.language  
    languages = list(collection.find())
    for language in languages:
        language['_id'] = str(language['_id'])
        print(language)

    return render_template('create_template.html', languages=languages)

@bp.route('/get_template_text', methods=['POST'])
@jwt_required()
@role_required('admin')
def get_template_text():
    current_user = get_jwt_identity()
    data = request.get_json()
    template_name = data.get('template_name')

    texts = get_template_texts(template_name)
    if texts:
        return jsonify({'success': True, 'texts': texts['text_fields'], 'variable_count': texts['variable_count'], 'has_image': texts['has_image']})
    else:
        return jsonify({'success': False, 'error': 'Template not found or error retrieving template.'})


@bp.route('/create_template', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_template():
    current_user = get_jwt_identity()
    print(current_user)
    
    template_name = request.form['template_name']
    category = request.form['category']
    language_code = request.form['language']
    
    header_type = request.form.get('header_type')
    header_text = request.form.get('header_text')
    header_example = request.form.get('header_example')
    body_text = request.form['body_text']
    body_examples = request.form.getlist('body_example')
    footer_text = request.form.get('footer_text')
    
    allow_category_change = request.form.get('allow_category_change') == 'on'
    
    buttons = []
    button_types = request.form.getlist('button_type')
    button_texts = request.form.getlist('button_text')
    phone_numbers = request.form.getlist('phone_number')
    urls = request.form.getlist('url')
    
    for i in range(len(button_types)):
        if button_types[i]:
            button_data = {"type": button_types[i]}
            if button_types[i] == "COPY_CODE":
                button_data["text"] = "Copy offer code"
            else:
                button_data["text"] = button_texts[i]
                
            if button_types[i] == "PHONE_NUMBER" and i < len(phone_numbers) and phone_numbers[i]:
                button_data["phone_number"] = phone_numbers[i]
            elif button_types[i] == "URL" and i < len(urls) and urls[i]:
                button_data["url"] = urls[i]
            buttons.append(button_data)
    
    components = []
    
    if header_type == 'TEXT' and header_text:
        header_component = {
            "type": "HEADER",
            "format": "TEXT",
            "text": header_text
        }
        if header_example:
            header_component["example"] = {"header_text": [header_example]}
        components.append(header_component)
    elif header_type == 'IMAGE':
        header_component = {
            "type": "HEADER",
            "format": "IMAGE",
            "example": {
                "header_handle": [
                    'https://scontent.fpfo1-1.fna.fbcdn.net/v/t39.30808-6/452897352_876576197844165_4529346611977142382_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=cc71e4&_nc_ohc=1P8oWlpoBvkQ7kNvgFD1WJP&_nc_ht=scontent.fpfo1-1.fna&gid=AeycThSsBSem_su8TMgQHP2&oh=00_AYDIxxYUkfGMdaJnYk-nMaAczP5VtBYn5R1Pxnrm9BA28Q&oe=66AFAB4D'
                ]
            }
        }
        components.append(header_component)
    
    if body_text:
        variables = [part for part in body_text.split() if part.startswith('{{') and part.endswith('}}')]
        num_variables = len(variables)
        examples = []
        if num_variables > 0:
            examples = [body_examples[i:i + num_variables] for i in range(0, len(body_examples), num_variables)]
            examples = [example for example in examples if len(example) == num_variables]
        
        body_component = {
            "type": "BODY",
            "text": body_text
        }
        if examples:
            body_component["example"] = {"body_text": examples}
        components.append(body_component)
    
    if footer_text:
        components.append({"type": "FOOTER", "text": footer_text})
    
    if buttons:
        components.append({"type": "BUTTONS", "buttons": buttons})
    
    template_data = {
        "name": template_name,
        "category": category,
        "language": language_code,
        "components": components,
        "allow_category_change": allow_category_change
    }
    
    print(json.dumps(template_data, indent=4))
    
    headers = {
        "Content-Type": "application/json",
        "D360-API-KEY": api_key_360
    }
    
    response = requests.post("https://waba-v2.360dialog.io/v1/configs/templates", headers=headers, data=json.dumps(template_data))
    
    if response.status_code == 200:
        return jsonify(message="Template created successfully"), 200
    else:
        print(f"Error: {response.json()}")
        return jsonify(status_code=response.status_code, response=response.json()), 400
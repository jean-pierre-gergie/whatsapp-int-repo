from flask import Blueprint, render_template, request, jsonify, send_file, url_for, current_app, make_response
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.decorators import role_required
from ..utils.helper_functions import send_message, upload_image,get_report,transform_template_json, get_template_details, send_message_campaign,get_all_collections_content
import os
import csv
from io import StringIO

bp = Blueprint('campaigns', __name__)

@bp.route('/whatsapp')
@jwt_required()
@role_required('admin')
def whatsapp():
    current_user = get_jwt_identity()

    mongo_db = current_app.mongo
    campaigns_collection = mongo_db.campaign  
    templates_collection = mongo_db.templates  

    campaigns = list(campaigns_collection.find())
    templates = list(templates_collection.find())

    for campaign in campaigns:
        campaign['_id'] = str(campaign['_id'])
    
    for template in templates:
        template['_id'] = str(template['_id'])

    return render_template('whatsapp.html', campaigns=campaigns, templates=templates)


@bp.route('/send_single_message', methods=['POST'])
@jwt_required()
@role_required('admin')
def send_single_message():
    current_user = get_jwt_identity()
    phone_number = request.form['phone_number']
    variables = request.form.getlist('variables[]')
    print(variables)

    selected_template = request.form['single_template']
    template_details = get_template_details(selected_template)
    template_json = transform_template_json(template_details)

    file = request.files.get('file')
    media_id = None
    if file:
        file_path = f"./{file.filename}"
        file.save(file_path)
        media_id = upload_image(file_path)
        print('The media ID is:', media_id)

    response = send_message(
        [{'phone': phone_number, 'variables': variables}],
        template_json,
        media_id,
        single=True
    )
    return response



@bp.route('/send_campaign')
@jwt_required()
@role_required('admin')
def send_campaign():
    current_user = get_jwt_identity()
    
    mongo_db = current_app.mongo
    campaigns_collection = mongo_db.campaign  
    templates_collection = mongo_db.templates  

    campaigns = list(campaigns_collection.find())
    templates = list(templates_collection.find())

    for campaign in campaigns:
        campaign['_id'] = str(campaign['_id'])
    
    for template in templates:
        template['_id'] = str(template['_id'])

    print("Campaigns: ", campaigns)  # Debug print

    return render_template('send_campaign.html', campaigns=campaigns, templates=templates)


@bp.route('/send_campaign', methods=['POST'])
@jwt_required()
def send_campaign_messages():
    current_user = get_jwt_identity()
    selected_campaign = request.form['campaign']
    selected_template = request.form['campaign_template']
    campaign_name = request.form['campaign_name']

    # MongoDB connection
    mongo_db = current_app.mongo
    campaign_name_collection = mongo_db.campaign_name
    
    # Check if the campaign_name already exists
    if campaign_name_collection.find_one({"name": campaign_name}):
        return jsonify({"success": False, "error": "Campaign name already exists. Please choose a different name."}), 400

    # Proceed with the rest of the process if campaign_name does not exist
    template_details = get_template_details(selected_template)
    template_json = transform_template_json(template_details)

    file = request.files.get('file')
    media_id = None
    if file:
        file_path = f"./{file.filename}"
        file.save(file_path)
        media_id = upload_image(file_path)
        print('The media ID is:', media_id)

    members_collection = mongo_db.members
    members = list(members_collection.find({"tag": selected_campaign}))
    
    variables = request.form.getlist('variables[]')
    
    response = send_message_campaign(members, template_json, variables, media_id, selected_campaign, campaign_name)
    return response

@bp.route('/download/<filename>')
def download_file(filename):
    path = os.path.join(os.getcwd(), 'output_files', filename)
    print(f"Attempting to send file: {path}")
    if not os.path.exists(path):
        print(f"Error: File not found: {path}")
        return jsonify(error="File not found"), 404
    return send_file(path, as_attachment=True)

@bp.route('/generate_report_page')
@jwt_required()
@role_required('admin')
def generate_report_page():
    current_user = get_jwt_identity()
    mongo_db = current_app.mongo
    campaign_name_collection = mongo_db.campaign_name
    campaign_names = list(campaign_name_collection.find())
    for cn in campaign_names:
        cn['_id'] = str(cn['_id'])
    return render_template('generate_report.html', campaign_names=campaign_names)

@bp.route('/generate_report', methods=['POST'])
@jwt_required()
def generate_report():
    try:
        data = request.get_json()
        campaign_name = data.get('campaign_name')
        print("Campaign Name:", campaign_name)
        
        if not campaign_name:
            return jsonify({'success': False, 'message': 'Missing campaign name parameter'}), 400

        current_user = get_jwt_identity()

        report_data = get_report(campaign_name)

        if report_data:
            return jsonify({'success': True, 'status_counts': report_data['status_counts']}), 200
        else:
            return jsonify({'success': False, 'message': 'No data found for the given campaign name'}), 404

    except Exception as e:
        current_app.logger.error(f"Error generating report: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while generating the report'}), 500

@bp.route('/download_csv/<status>', methods=['GET'])
@jwt_required()
def download_csv(status):
    campaign_name = request.args.get('campaign_name')
    report_data = get_report(campaign_name)
    
    if not report_data:
        return jsonify({'success': False, 'message': f'No data found for campaign {campaign_name}'}), 404

    data = report_data['data_by_status'].get(status, [])

    if not data:
        return jsonify({'success': False, 'message': f'No data found for status {status}'}), 404

    si = StringIO()
    cw = csv.writer(si)
    
    # Write headers
    cw.writerow(['Campaign Name', 'Phone Number', 'Message ID', 'Status'])
    
    # Write data rows
    for item in data:
        cw.writerow([
            item['campaign_name'],
            item['number'],
            item['response']['messages'][0]['id'],
            status
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={status}_messages.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@bp.route('/show_all_collections_html', methods=['GET'])
def show_all_collections_html():
    collections_content = get_all_collections_content()
    collection_names = collections_content.keys()
    return render_template('show_collections.html', collections=collection_names)

from bson import json_util

@bp.route('/view_collection_content', methods=['POST'])
def view_collection_content():
    try:
        collection_name = request.json.get('collection_name')
        if not collection_name:
            return jsonify({"success": False, "message": "No collection name provided."}), 400

        mongo_db = current_app.mongo
        collection = mongo_db[collection_name]
        documents = list(collection.find())

        # Use json_util to serialize ObjectId and other BSON types
        return json_util.dumps({"success": True, "content": documents})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

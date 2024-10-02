from flask import Blueprint, render_template, request, jsonify, send_file, url_for, current_app, make_response
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.decorators import role_required
from ..utils.helper_functions import send_message, upload_image,get_report,transform_template_json, get_template_details, send_message_campaign,get_all_collections_content
from ..utils.template_updater import fetch_and_update_templates

import os
import csv
from io import StringIO
from bson import ObjectId

import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('campaign_status_logger')


bp = Blueprint('campaigns', __name__)


@bp.route('/audience', methods=['GET'])
@jwt_required()
@role_required(['admin', 'user']) 
def audience():
    current_user = get_jwt_identity()
    mongo_db = current_app.mongo
    audience_collection = mongo_db.members
    
    page = int(request.args.get('page', 1))  
    per_page = 15  
    offset = (page - 1) * per_page

    selected_tag = request.args.get('tag', None)

    if selected_tag:
        audience_list = list(audience_collection.find({'tag': selected_tag}).skip(offset).limit(per_page))
        total_audience = audience_collection.count_documents({'tag': selected_tag})
    else:
        audience_list = list(audience_collection.find().skip(offset).limit(per_page))
        total_audience = audience_collection.count_documents({})

    for audience in audience_list:
        audience['_id'] = str(audience['_id'])

    tags = audience_collection.distinct('tag')

    total_pages = (total_audience + per_page - 1) // per_page  

    return render_template('audience.html', audience_list=audience_list, tags=tags, selected_tag=selected_tag, page=page, total_pages=total_pages)



@bp.route('/audience/<member_id>', methods=['DELETE'])
@jwt_required()
@role_required(['admin', 'user']) 
def remove_member(member_id):
    mongo_db = current_app.mongo
    audience_collection = mongo_db.members

    result = audience_collection.delete_one({'_id': ObjectId(member_id)})

    if result.deleted_count > 0:
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': 'Member not found'}), 404


@bp.route('/audience/tag/<tag>', methods=['DELETE'])
@jwt_required()
@role_required(['admin', 'user']) 
def remove_members_by_tag(tag):
    mongo_db = current_app.mongo
    audience_collection = mongo_db.members
    campaign_collection = mongo_db.campaign

    result = audience_collection.delete_many({'tag': tag})
    campaign_collection.delete_one({'tag': tag})


    if result.deleted_count > 0:
        return jsonify({'success': True, 'deleted_count': result.deleted_count}), 200
    else:
        return jsonify({'success': False, 'error': 'No members found with this tag'}), 404


@bp.route('/whatsapp')
@jwt_required()
@role_required(['admin']) 
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
@role_required(['admin', 'user']) 
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
@role_required(['admin', 'user']) 
def send_campaign():
    current_user = get_jwt_identity()
    

    fetch_and_update_templates()

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
@role_required(['admin', 'user']) 
def send_campaign_messages():
    current_user = get_jwt_identity()

    selected_campaign = request.form['campaign']
    selected_template = request.form['campaign_template']
    campaign_name = request.form['campaign_name']

    # MongoDB connection
    mongo_db = current_app.mongo
    campaign_name_collection = mongo_db.campaign_name

    if campaign_name_collection.find_one({"name": campaign_name}):
        return jsonify({"success": False, "error": "Campaign name already exists. Please choose a different name."}), 400

    template_details = get_template_details(selected_template)
    template_json = transform_template_json(template_details)

    file = request.files.get('file')
    media_id = None
    if file:
        file_path = f"./{file.filename}"
        file.save(file_path)
        media_id = upload_image(file_path)

    members_collection = mongo_db.members
    members = list(members_collection.find({"tag": selected_campaign}))

    variables = request.form.getlist('variables[]')

    # Send campaign messages asynchronously (not waiting for completion)
    send_message_campaign(members, template_json, variables, media_id, selected_campaign, campaign_name)

    # Immediately return success response without counts (campaign is still processing)
    return jsonify({
        "success": True,
        "message": "Campaign is being processed.",
        "campaign_name": campaign_name  # Include this in the response
    })

@bp.route('/campaign_status/<campaign_name>', methods=['GET'])
@jwt_required()
@role_required(['admin', 'user']) 
def get_campaign_status(campaign_name):
    mongo_db = current_app.mongo
    campaign_responses_collection = mongo_db.campaign_responses
    logger.debug("Pulling status ")
    # Fetch all documents with the campaign_name
    all_documents = list(campaign_responses_collection.find({"campaign_name": campaign_name}))
    logger.debug(f"All documents for campaign {campaign_name}: {all_documents}")  # Debugging all documents

    # Correctly query documents with status_code == 200 (at the top level)
    sent_documents = list(campaign_responses_collection.find({
        "campaign_name": campaign_name,
        "status_code": 200
    }))
    sent_count = len(sent_documents)
    logger.debug(f"Sent documents: {sent_documents}")  # Log documents marked as sent

    # Correctly query documents with status_code != 200 (at the top level)
    failed_documents = list(campaign_responses_collection.find({
        "campaign_name": campaign_name,
        "status_code": {"$ne": 200}
    }))
    failed_count = len(failed_documents)
    logger.debug(f"Failed documents: {failed_documents}")  # Log documents marked as failed

    # Log final counts
    logger.debug(f"Sent: {sent_count}, Failed: {failed_count}")

    return jsonify({
        "sent_count": sent_count,
        "failed_count": failed_count
    })

@bp.route('/download/<filename>')
@jwt_required()
@role_required(['admin', 'user']) 
def download_file(filename):
    path = os.path.join(os.getcwd(), 'output_files', filename)
    print(f"Attempting to send file: {path}")
    if not os.path.exists(path):
        print(f"Error: File not found: {path}")
        return jsonify(error="File not found"), 404
    return send_file(path, as_attachment=True)

@bp.route('/generate_report_page') 
@jwt_required()
@role_required(['admin', 'user']) 
def generate_report_page():
    current_user = get_jwt_identity()
    mongo_db = current_app.mongo

    # Collections
    campaign_name_collection = mongo_db.campaign_name

    # Sort by 'created_at' in descending order (-1)
    campaign_names = list(campaign_name_collection.find().sort("created_at", -1))

    # Convert ObjectId to string
    for cn in campaign_names:
        cn['_id'] = str(cn['_id'])

    return render_template('generate_report.html', campaign_names=campaign_names)


@bp.route('/generate_report', methods=['POST'])
@jwt_required()
@role_required(['admin', 'user']) 
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
@role_required(['admin', 'user']) 
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
@jwt_required()
@role_required(['admin']) 
def show_all_collections_html():
    collections_content = get_all_collections_content()
    collection_names = collections_content.keys()
    return render_template('show_collections.html', collections=collection_names)

from bson import json_util

@bp.route('/view_collection_content', methods=['POST'])
@jwt_required()
@role_required(['admin']) 
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

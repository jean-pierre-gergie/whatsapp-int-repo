from flask import Blueprint, render_template, request, jsonify, send_file, url_for, current_app, make_response
from datetime import datetime, timedelta
from dateutil import parser
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.decorators import role_required
from ..utils.helper_functions import send_message, upload_image,get_report,transform_template_json, get_template_details, send_message_campaign,get_all_collections_content
from ..utils.template_updater import fetch_and_update_templates

import os
import csv
from io import StringIO
from bson import ObjectId
import requests

import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


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




@bp.route('/campaigns')
@jwt_required()
@role_required(['admin', 'user'])
def campaigns():

    # Get the MongoDB collection
    mongo_db = current_app.mongo
    final_campaign_response_collection = mongo_db.final_campaign_response

    # Fetch campaigns from the collection
    campaigns = list(final_campaign_response_collection.find().sort('campaign_submitted_at', -1))

    # Define the date fields that need formatting
    date_fields = [
        'campaign_submitted_at',
        'campaign_scheduled_at',  # This is stored as a string in ISO format
        'campaign_started_at',
        'campaign_finished_at'
    ]

    # Loop through campaigns and reformat applicable date fields
    for campaign in campaigns:
        campaign['_id'] = str(campaign['_id'])

        for field in date_fields:
            if field in campaign:
                # Check if the field is a datetime object or a string in ISO format
                if isinstance(campaign[field], datetime):
                    # Convert datetime objects to a readable format
                    campaign[field] = campaign[field].strftime('%Y-%m-%d %I:%M %p')
                elif isinstance(campaign[field], str):
                    try:
                        # Convert the ISO 8601 string to a datetime object
                        campaign[field] = parser.parse(campaign[field]).strftime('%Y-%m-%d %I:%M %p')
                    except Exception as e:
                        # Handle parsing errors if necessary
                        current_app.logger.error(f"Error parsing date field {field}: {e}")

    # Render the template with the formatted campaigns
    return render_template('campaigns_page.html', campaigns=campaigns)


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
    campaign_timing = request.form['campaign_timing']  
    scheduled_date_local = request.form['scheduled_date_local']
    scheduled_date = request.form['scheduled_date_utc']
    logger.debug(f"----UTC Time {scheduled_date}")
    logger.debug(f"----Local Time {scheduled_date_local}")
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
        # Define the upload directory
        upload_dir = './uploaded_assets'

        # Check if the directory exists, if not, create it
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        # Save the file in the 'uploaded_assets' directory
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)

        # Upload the file and get the media_id (assuming upload_image is a function to upload to a remote service)
        media_id = upload_image(file_path)

    variables = request.form.getlist('variables[]')

    payload = {
        "campaign_timing": campaign_timing,  
        "scheduled_date": scheduled_date,
        "scheduled_date_local":scheduled_date_local,  
        "selected_campaign": selected_campaign,
        "template_json": template_json,
        "variables": variables,
        "campaign_name": campaign_name,
        "media_id": media_id if media_id else 0 
    }

    microservice_base_url = current_app.config['MICROSERVICE_BASE_URL']

    logger.info(f"BE LEVEL Payload details at BE LEVEL: {payload}")
    logger.info(f"BE LEVEL Micro Service Base url {microservice_base_url}")

    try:
        # Send the request to submit the job
        response = requests.post(f"{microservice_base_url}/start_campaign_task", json=payload)

        if response.status_code == 200:
            # Extract the task_id from the response
            task_id = response.json().get("task_id")
            logger.info(f"Task started with ID: {task_id}")

            # Add campaign name and task_id to the campaign_name collection
            campaign_name_collection.insert_one({
                "name": campaign_name,
                "task_id": task_id,
                "created_by": current_user,  
                "created_at": datetime.utcnow()  
            })

            return jsonify({
                "success": True,
                "message": "Campaign is being processed. Task started",
                "campaign_name": campaign_name,
                "task_id": task_id
            }), 200
        else:
            return jsonify({"success": False, "error": "Failed to start campaign task."}), response.status_code

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred while processing the campaign."}), 500

  

@bp.route('/campaign_task_status_polling/<campaign_name>', methods=['GET'])
@jwt_required()
@role_required(['admin', 'user']) 
def get_campaign_status(campaign_name):
    mongo_db = current_app.mongo

    logger.debug("Polling for campaign status.")
    logger.debug(f"Polling status for campaign: {campaign_name}")

    try:
        campaign_collection = mongo_db.campaign_name  # MongoDB collection name is campaign_name
        campaign_doc = campaign_collection.find_one({"name": campaign_name})

        if not campaign_doc:
            logger.warning(f"Campaign {campaign_name} not found in the database.")
            return jsonify({"error": "Campaign not found"}), 404

        task_id = campaign_doc.get('task_id')

        if not task_id:
            logger.warning(f"No task ID found for campaign {campaign_name}.")
            return jsonify({"error": "Task ID not found for this campaign"}), 404

        microservice_base_url = current_app.config['MICROSERVICE_BASE_URL']
        logger.debug(f"Requesting status from microservice for task ID: {task_id}")

        try:
            response = requests.get(f"{microservice_base_url}/microservice_get_campaign_status/{task_id}")
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx and 5xx)
            logger.debug(f"Received response from microservice for task ID: {task_id}")
        except requests.RequestException as e:
            logger.error(f"Error contacting FastAPI for task {task_id}: {e}")
            return jsonify({"error": "Could not fetch campaign status"}), 500

        microservice_data = response.json()

        if microservice_data.get('status') == 'Task in progress...':
            total_members = microservice_data.get('total_members', 0)
            processed = microservice_data.get('processed', 0)
            curr_succ = microservice_data.get('success_count', 0)
            curr_failed = microservice_data.get('failed_count', 0)

            logger.debug(f"Task {task_id} is in progress: {processed}/{total_members} processed, "
                         f"{curr_succ} successes, {curr_failed} failures.")
            
            return jsonify({
                "task_id": task_id,
                "status": "Task in progress...",
                "total_members": total_members,
                "processed": processed,
                "current_success": curr_succ,
                "current_failed": curr_failed
            })

        elif microservice_data.get('status') == 'Task completed!':
            # Fetch the final results from the campaign_responses collection
            final_campaign_response_collection = mongo_db.final_campaign_response
            response_data = final_campaign_response_collection.find_one({"campaign_name": campaign_name})

            if not response_data:
                logger.warning(f"Final results for campaign {campaign_name} not found in the database.")
                return jsonify({"error": "Final results not found"}), 404

            # Retrieve total members, successes, and failures from the response data
            total_members = response_data.get('total_members', 0)
            success_count = response_data.get('total_success', 0)
            failed_count = response_data.get('total_failed', 0)

            logger.debug(f"Task {task_id} completed successfully with {success_count} successes and {failed_count} failures.")

            return jsonify({
                "task_id": task_id,
                "status": "Task completed!",
                "total_members": total_members,
                "processed": total_members,  # All members should be processed by now
                "current_success": success_count,
                "current_failed": failed_count
            })

        else:
            logger.warning(f"Task {task_id} status returned from microservice: {microservice_data.get('status')}")
            return jsonify({"error": microservice_data.get('status')}), 400

    except Exception as e:
        logger.error(f"An unexpected error occurred while polling campaign status for {campaign_name}: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500




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
        # Extract message ID safely, with a fallback in case it's missing
        message_id = (
            item['response']['messages'][0]['id']
            if 'response' in item and 'messages' in item['response'] and isinstance(item['response']['messages'], list) and item['response']['messages']
            else 'N/A'  # Fallback in case the message ID is not available
        )

        cw.writerow([
            item['campaign_name'],
            item['number'],
            message_id,
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

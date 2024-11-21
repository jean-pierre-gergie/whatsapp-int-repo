from flask import Blueprint, redirect, render_template, request, jsonify, send_file, url_for, current_app, make_response
from datetime import datetime, timedelta
from dateutil import parser
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt ,create_access_token
from ..utils.decorators import role_required
from ..utils.helper_functions import send_message, upload_image,get_report,transform_template_json, get_template_details, send_message_campaign,get_all_collections_content
from ..utils.template_updater import fetch_and_update_templates
from ..utils.session_config_helper import get_session_foundation_config, get_all_foundations


import os
import csv
from io import StringIO
from bson import ObjectId
import requests

import logging

logging.basicConfig(level=logging.DEBUG, 
                    format='- %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


bp = Blueprint('campaigns', __name__)


@bp.app_context_processor
def inject_foundation_data():
    session_configs = get_session_foundation_config()
    if not session_configs:
        return {}  # Or handle it gracefully if the data is missing
    foundation_name = session_configs.get('foundation_name')
    all_foundations = get_all_foundations()
    return dict(foundation_name=foundation_name, foundations=all_foundations)



# FIXME : no need to do anything start with th enext url 
@bp.route('/audience', methods=['GET'])
@jwt_required()
@role_required(['admin', 'user']) 
def audience():
    session_configs =get_session_foundation_config()
    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get("foundation_name")
    audience_collection = whatsapp_data_db.members
    
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

    return render_template('audience.html',
                           audience_list=audience_list,
                           tags=tags,
                           selected_tag=selected_tag,
                           page=page,
                           total_pages=total_pages,
                           foundation_name =foundation_name)


# FIXME 
@bp.route('/audience/<member_id>', methods=['DELETE'])
@jwt_required()
@role_required(['admin', 'user']) 
def remove_member(member_id):


    session_configs =get_session_foundation_config()
    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    
    audience_collection = whatsapp_data_db.members

    result = audience_collection.delete_one({'_id': ObjectId(member_id)})

    if result.deleted_count > 0:
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': 'Member not found'}), 404

# FIXME
@bp.route('/audience/tag/<tag>', methods=['DELETE'])
@jwt_required()
@role_required(['admin', 'user']) 
def remove_members_by_tag(tag):
    
    
    session_configs =get_session_foundation_config()
    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    audience_collection = whatsapp_data_db.members
    campaign_collection = whatsapp_data_db.campaign

    result = audience_collection.delete_many({'tag': tag})
    campaign_collection.delete_one({'tag': tag})


    if result.deleted_count > 0:
        return jsonify({'success': True, 'deleted_count': result.deleted_count}), 200
    else:
        return jsonify({'success': False, 'error': 'No members found with this tag'}), 404

# FIXME
@bp.route('/whatsapp')
@jwt_required()
@role_required(['admin']) 
def whatsapp():

    session_configs =get_session_foundation_config()
    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get("foundation_name")

    campaigns_collection = whatsapp_data_db.campaign  
    templates_collection = whatsapp_data_db.templates  

    campaigns = list(campaigns_collection.find())
    templates = list(templates_collection.find())

    for campaign in campaigns:
        campaign['_id'] = str(campaign['_id'])
    
    for template in templates:
        template['_id'] = str(template['_id'])

    return render_template('whatsapp.html',
                           campaigns=campaigns,
                           templates=templates,
                           foundation_name = foundation_name)

# FIXME
@bp.route('/send_single_message', methods=['POST'])
@jwt_required()
@role_required(['admin', 'user']) 
def send_single_message():
    
    session_configs =get_session_foundation_config()
    api_key_360 = session_configs.get('api_key')

    phone_number = request.form['phone_number']
    variables = request.form.getlist('variables[]')
    print(variables)

    selected_template = request.form['single_template']
    template_details = get_template_details(selected_template,api_key_360=api_key_360)
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
        api_key_360=api_key_360,
        single=True
    )
    return response




@bp.route('/campaigns')
@jwt_required()
@role_required(['admin', 'user'])
def campaigns():

    session_configs =get_session_foundation_config()

    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get('foundation_name')
    final_campaign_response_collection = whatsapp_data_db.final_campaign_response

    # TODO  MAKE THE INDEXING FOR THIS 
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
                # Convert all datetime fields to ISO format for consistency
                if isinstance(campaign[field], datetime):
                    campaign[field] = campaign[field].isoformat() + "Z"  # Ensure UTC
                elif isinstance(campaign[field], str):
                    try:
                        # Convert string to datetime and format as ISO UTC
                        campaign[field] = parser.parse(campaign[field]).isoformat() + "Z"
                    except Exception as e:
                        current_app.logger.error(f"Error parsing date field {field}: {e}")

    # Render the template with the formatted campaigns
    return render_template('campaigns_page.html', campaigns=campaigns,foundation_name=foundation_name)


# FIXME 
@bp.route('/campaign_details/<campaign_name>')
@jwt_required()
@role_required(['admin', 'user'])
def campaign_details(campaign_name):
    # Get the MongoDB collection

    if not campaign_name:
        return jsonify({'success': False, 'message': 'Missing campaign name parameter'}), 400
    
    session_configs =get_session_foundation_config()

    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get('foundation_name')
    final_campaign_response_collection = whatsapp_data_db.final_campaign_response


    campaign = final_campaign_response_collection.find_one({'campaign_name': campaign_name})

    report_data = get_report(campaign_name,whatsapp_data_db)

    data = []
    for stat in ['sent', 'delivered', 'read', 'failed']:
        data.extend(report_data['data_by_status'].get(stat, []))

    table_data = []
    for item in data:
        # Extract message ID safely, with a fallback in case it's missing
        message_id = item.get('wamid', 'N/A')  # Using 'wamid' from the combined data

        # Extract error details from the item (assumed structure from webhook)
        errors = item.get('errors', [])
        error_code = errors[0]['code'] if errors else 'N/A'
        error_message = errors[0]['message'] if errors else 'N/A'

        # Extract billable status from 'pricing'
        billable = 'Yes' if item.get('billable', False) else 'No'

        table_data.append({
            'campaign_name': item['campaign_name'],
            'number': item['number'],
            'message_id': message_id,
            'status': item.get('status', 'unknown'),  # Extracting status from the combined data
            'error_code': error_code,
            'error_message': error_message,
            'billable': billable
        })


    # Check if the campaign exists
    if not campaign:
        # If no campaign is found, return an error message
        return f"No campaign found with the name '{campaign_name}'", 404

    # Convert the MongoDB ObjectId to a string for easier handling
    
    campaign['_id'] = str(campaign['_id'])


    # Return the campaign details (for now, just a basic response)
    return render_template('campaigns_details_page.html', campaign=campaign,table_data =  table_data,foundation_name=foundation_name)


# FIXME
@bp.route('/send_campaign')
@jwt_required()
@role_required(['admin', 'user']) 
def send_campaign():
    session_configs =get_session_foundation_config()

    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get('foundation_name')
    api_key_360 = session_configs.get('api_key')
    

    fetch_and_update_templates(api_key_360=api_key_360,whatsapp_data_db=whatsapp_data_db)

   
    campaigns_collection = whatsapp_data_db.campaign  
    templates_collection = whatsapp_data_db.templates  

    campaigns = list(campaigns_collection.find())
    templates = list(templates_collection.find())

    for campaign in campaigns:
        campaign['_id'] = str(campaign['_id'])
    
    for template in templates:
        template['_id'] = str(template['_id'])

    print("Campaigns: ", campaigns)  # Debug print

    return render_template('send_campaign.html', campaigns=campaigns, templates=templates , foundation_name=foundation_name)

# BUG : NEED TO FIX FOR MICROSERVICE PAYLOAD 
@bp.route('/send_campaign', methods=['POST'])
@jwt_required()
@role_required(['admin', 'user']) 
def send_campaign_messages():
    current_user = get_jwt_identity()

    selected_campaign = request.form['campaign']
    selected_template = request.form['campaign_template']
    campaign_name = request.form['campaign_name'].strip()
    campaign_timing = request.form['campaign_timing']  
    scheduled_date_local = request.form['scheduled_date_local']
    scheduled_date = request.form['scheduled_date_utc']
    logger.debug(f"----UTC Time {scheduled_date}")
    logger.debug(f"----Local Time {scheduled_date_local}")


    # MongoDB connection
    session_configs =get_session_foundation_config()

    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get('foundation_name')
    api_key_360 = session_configs.get('api_key')



    campaign_name_collection = whatsapp_data_db.campaign_name

    if campaign_name_collection.find_one({"name": campaign_name}):
        return jsonify({"success": False, "error": "Campaign name already exists. Please choose a different name."}), 400

    template_details = get_template_details(selected_template,api_key_360=api_key_360)
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
        media_id = upload_image(file_path,api_key_360=api_key_360)

    variables = request.form.getlist('variables[]')

    payload = {

        "foundation_name":foundation_name,
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
                "foundation_name":foundation_name,
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

  
# FIXME BUG THIS IS POLLING FROM THE MICROSERVICE 
@bp.route('/campaign_task_status_polling/<campaign_name>', methods=['GET'])
@jwt_required()
@role_required(['admin', 'user']) 
def get_campaign_status(campaign_name):
    session_configs =get_session_foundation_config()

    whatsapp_data_db = session_configs.get('whatsapp_data_db')

    logger.debug("Polling for campaign status.")
    logger.debug(f"Polling status for campaign: {campaign_name}")

    try:
        campaign_collection = whatsapp_data_db.campaign_name  # MongoDB collection name is campaign_name
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
            final_campaign_response_collection = whatsapp_data_db.final_campaign_response
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
                "processed": total_members,  
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

# FIXME
@bp.route('/generate_report_page') 
@jwt_required()
@role_required(['admin', 'user']) 
def generate_report_page():


    session_configs =get_session_foundation_config()

    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get('foundation_name')

    # Collections
    campaign_name_collection = whatsapp_data_db.campaign_name

    # Sort by 'created_at' in descending order (-1)
    campaign_names = list(campaign_name_collection.find().sort("created_at", -1))

    # Convert ObjectId to string
    for cn in campaign_names:
        cn['_id'] = str(cn['_id'])

    return render_template('generate_report.html', campaign_names=campaign_names,foundation_name = foundation_name)

# FIXME 
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

        session_configs =get_session_foundation_config()

        whatsapp_data_db = session_configs.get('whatsapp_data_db')

        report_data = get_report(campaign_name,whatsapp_data_db)

        if report_data:
            return jsonify({'success': True, 'status_counts': report_data['status_counts']}), 200
        else:
            return jsonify({'success': False, 'message': 'No data found for the given campaign name'}), 404

    except Exception as e:
        current_app.logger.error(f"Error generating report: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while generating the report'}), 500


# FIXME
@bp.route('/download_csv/<status>', methods=['GET'])
@jwt_required()
@role_required(['admin', 'user']) 
def download_csv(status):
    campaign_name = request.args.get('campaign_name')
    
    if not campaign_name:
        current_app.logger.error("Campaign name is missing in request args.")
        return jsonify({'success': False, 'message': 'Missing campaign name parameter'}), 400

    session_configs =get_session_foundation_config()
    whatsapp_data_db = session_configs.get('whatsapp_data_db')

    logger.debug(f"Session configs: {session_configs}")
    logger.debug(f"Using database: {whatsapp_data_db}")

    report_data = get_report(campaign_name,whatsapp_data_db=whatsapp_data_db)

    if not report_data:
        current_app.logger.error(f"No report data found for campaign {campaign_name}.")
        return jsonify({'success': False, 'message': f'No report data found for campaign {campaign_name}'}), 404
    
    if status == 'all':
        # Combine all message statuses into a single list
        data = []
        for stat in ['sent', 'delivered', 'read', 'failed']:
            data.extend(report_data['data_by_status'].get(stat, []))
    else:
        # Get data for a specific status
        data = report_data['data_by_status'].get(status, [])

    if not data:
        return jsonify({'success': False, 'message': f'No data found for status {status}'}), 404

    si = StringIO()
    cw = csv.writer(si)
    
    # Write headers including the new fields
    cw.writerow([
        'Campaign Name', 
        'Phone Number', 
        'Message ID', 
        'Status', 
        'Error Code', 
        'Error Message', 
        'Billable'
    ])
    
    # Write data rows
    for item in data:
        # Extract message ID safely, with a fallback in case it's missing
        message_id = (
            item.get('wamid', 'N/A')  # Using 'wamid' from the combined data
        )

        # Extract error details from the item (assumed structure from webhook)
        errors = item.get('errors', [])
        error_code = errors[0]['code'] if errors else 'N/A'
        error_message = errors[0]['message'] if errors else 'N/A'

        # Extract billable status from 'pricing'
        billable = item.get('billable', 'False')

        cw.writerow([
            item['campaign_name'],
            item['number'],
            message_id,
            item.get('status', 'unknown'),  # Extracting status from the combined data
            error_code,
            error_message,
            billable
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={status}_messages.csv"
    output.headers["Content-type"] = "text/csv"
    return output



# FIXME
@bp.route('/show_all_collections_html', methods=['GET'])
@jwt_required()
@role_required(['admin']) 
def show_all_collections_html():

    session_configs =get_session_foundation_config()

    whatsapp_data_db = session_configs.get('whatsapp_data_db')
    foundation_name = session_configs.get('foundation_name')
    collections_content = get_all_collections_content(whatsapp_data_db)
    collection_names = collections_content.keys()
    return render_template('show_collections.html', collections=collection_names,foundation_name=foundation_name)

from bson import json_util


# FIXME
@bp.route('/view_collection_content', methods=['POST'])
@jwt_required()
@role_required(['admin']) 
def view_collection_content():
    try:
        collection_name = request.json.get('collection_name')
        if not collection_name:
            return jsonify({"success": False, "message": "No collection name provided."}), 400

        session_configs =get_session_foundation_config()

        whatsapp_data_db = session_configs.get('whatsapp_data_db')
        
        collection = whatsapp_data_db[collection_name]
        documents = list(collection.find())

        # Use json_util to serialize ObjectId and other BSON types
        return json_util.dumps({"success": True, "content": documents})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# TODO for deployment


@bp.route('/dynamic_redirect', methods=['GET'])
@jwt_required()
@role_required(['admin', 'user'])
def dynamic_redirect():
    # Get the current user's identity
    current_identity = get_jwt_identity()

    # Create a new JWT token
    token = create_access_token(identity=current_identity, expires_delta=timedelta(hours=1))

    # Check the environment and select the appropriate URL
    flask_env = os.getenv('FLASK_ENV', 'development')  # Default to 'development' if not set
    if flask_env == 'production':
        agent_server_url = os.getenv('CHAT_AGENT_SERVER_URL_PRODUCTION')  # Production URL
    else:
        agent_server_url = os.getenv('CHAT_AGENT_SERVER_URL_DEVELOPMENT')  # Development URL

    # Get foundation-specific session configs
    session_configs = get_session_foundation_config()
    foundation_name = session_configs.get('foundation_name', 'default')

    # Construct the redirect URL
    redirect_url = f"{agent_server_url}?foundation_name={foundation_name}"
    logger.info(f"Redirecting to {redirect_url}")

    # Prepare the response
    response = make_response(redirect(redirect_url))
    response.set_cookie(
        'jwt_token',
        token,
        httponly=False,
        secure=(flask_env == 'production'),  # Use secure cookies only in production
        samesite='None' if flask_env == 'production' else 'Strict',  # Adjust SameSite attribute based on environment
        domain='.omnichanneltv.com' if flask_env == 'production' else None  # Domain only for production
    )
    return response
# @bp.route('/dynamic_redirect', methods=['GET'])
# @jwt_required()
# @role_required(['admin', 'user'])
# def dynamic_redirect():
# #     # Create a new token or get the existing one
#     current_identity = get_jwt_identity()  # Get the current user's identity
#     token = create_access_token(identity=current_identity,expires_delta=timedelta(hours=1))    # Create a new token with the same identity
#     agent_server_url = os.getenv('CHAT_AGENT_SERVER_URL')

#     session_configs = get_session_foundation_config()
#     foundation_name = session_configs.get('foundation_name')

#     agent_server_url = os.getenv('CHAT_AGENT_SERVER_URL')
#     redirect_url = f"{agent_server_url}?foundation_name={foundation_name}"
#     logger.info(f"redirecting to {redirect_url}")


# #     logger.info(f"redirecting to {agent_server_url}")
#     response = make_response(redirect(redirect_url))
#     response.set_cookie(
#         'jwt_token', 
#         token, 
#         httponly=False, 
#         secure=True, 
#         samesite='None', 
#         domain='.omnichanneltv.com'
#     )
#     return response


# @bp.route('/dynamic_redirect', methods=['GET'])
# @jwt_required()
# @role_required(['admin', 'user'])
# def dynamic_redirect():
#     # Create a new token or get the existing one
#     current_identity = get_jwt_identity()  
#     token = create_access_token(identity=current_identity,expires_delta=timedelta(hours=1))  

#     agent_server_url = os.getenv('CHAT_AGENT_SERVER_URL')

#     session_configs = get_session_foundation_config()
#     foundation_name = session_configs.get('foundation_name')

#     agent_server_url = os.getenv('CHAT_AGENT_SERVER_URL')
#     redirect_url = f"{agent_server_url}?foundation_name={foundation_name}"
#     logger.info(f"redirecting to {redirect_url}")


#     response = make_response(redirect(redirect_url))
#     response.set_cookie('jwt_token',token, httponly=False, secure=True, samesite='Strict')

    
#     return response
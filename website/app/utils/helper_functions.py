import requests
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file, url_for,current_app
import time
import json
import re
import phonenumbers
import os
from app.config import Config
from datetime import datetime
from collections import Counter
import logging
from datetime import datetime
from .country_number_cleaning import is_valid_phone_number




logger = current_app.logger

# pymongo_logger = logging.getLogger("pymongo")
# pymongo_logger.setLevel(logging.ERROR) 



def get_template_texts(template_name,api_key_360):
    url = "https://waba-v2.360dialog.io/v1/configs/templates"
    headers = {
        "D360-API-KEY": api_key_360,
        "Content-Type": "application/json"
    }
    params = {
        "limit": 1000,
        "offset": 0,
        "sort": "id",
        "filters": json.dumps({"business_templates.name": template_name})
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        templates = response.json().get('waba_templates', [])
        if templates:
            template = templates[0]
            text_fields = []
            variable_count = 0
            buttons = []
            has_image = False
            for component in template['components']:
                if component['type'] == 'HEADER' and component.get('format') == 'IMAGE':
                    text_fields.append('Image Header')
                    has_image = True
                if component['type'] == 'BODY' and 'text' in component:
                    text_fields.append(component['text'])
                    variable_count = max(variable_count, component['text'].count('{{'))
                if component['type'] == 'FOOTER' and 'text' in component:
                    text_fields.append(component['text'])
                if component['type'] == 'BUTTONS' and 'buttons' in component:
                    buttons.extend([f"{button['type']}: {button['text']}" for button in component['buttons']])
            if buttons:
                text_fields.append(f"Buttons: {', '.join(buttons)}")
            return {'text_fields': text_fields, 'variable_count': variable_count, 'has_image': has_image}
    return None


def upload_image(file_path,api_key_360):
    api_url = "https://waba-v2.360dialog.io/media"
    headers = {"D360-API-KEY": api_key_360}
    files = {
        "messaging_product": (None, "whatsapp"),
        "file": (file_path, open(file_path, 'rb'), 'image/jpeg')
    }
    response = requests.post(api_url, headers=headers, files=files)
    return response.json().get('id') if response.status_code == 200 else None


def get_template_details(template_name,api_key_360):
    url = "https://waba-v2.360dialog.io/v1/configs/templates"
    headers = {
        "D360-API-KEY": api_key_360,
        "Content-Type": "application/json"
    }
    params = {
        "limit": 1000,
        "offset": 0,
        "sort": "id",
        "filters": json.dumps({"business_templates.name": template_name})
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        templates = response.json().get('waba_templates', [])
        if templates:
            return templates[0]
    else:
        print(f"Failed to retrieve templates: {response.status_code}")
        print(response.text)
    return None


def send_message(users, template_json, media_id, api_key_360,single = False):
    success_rows = []
    failed_rows = []
    start_time = time.time()
    try:
        template_dict = json.loads(template_json)
    except json.JSONDecodeError as e:
        return jsonify(success=[], failed=[{'Number': 'N/A', 'Title': 'Error', 'Details': str(e), 'Code': 'N/A', 'TimeTaken': time.time() - start_time}])
    for user in users:
        number = user['phone'] if single else user.get('mobile')
        template_dict['to'] = number
        variables = user['variables']
        for component in template_dict.get('template', {}).get('components', []):
            if component['type'] == 'body':
                for i, parameter in enumerate(component.get('parameters', [])):
                    if parameter['type'] == 'text' and i < len(variables):
                        parameter['text'] = variables[i] if variables[i] else f'Variable_{i+1}'
            elif component['type'] == 'header' and component.get('parameters', []):
                if component['parameters'][0].get('type') == 'image' and media_id:
                    component['parameters'][0]['image'] = {'id': media_id}
        url = "https://waba-v2.360dialog.io/messages"
        headers = {"Content-Type": "application/json", "D360-API-KEY": api_key_360}
        response = requests.post(url, headers=headers, json=template_dict)
        response_time = time.time() - start_time
        if response.status_code in [200, 201]:
            response_json = response.json()
            for contact, message in zip(response_json.get('contacts', []), response_json.get('messages', [])):
                success_rows.append({
                    'Number': contact.get('input', 'N/A'),
                    'MessageID': message.get('id', 'N/A'),
                    'MessageStatus': message.get('message_status', 'N/A'),
                    'TimeTaken': response_time
                })
        else:
            try:
                response_json = response.json()
                error = response_json['errors'][0] if 'errors' in response_json else response_json['error']
                failed_rows.append({
                    'Number': number,
                    'Code': error.get('code', 'N/A'),
                    'Title': error.get('title', 'N/A'),
                    'Details': error.get('details', response.text),
                    'TimeTaken': response_time
                })
            except (ValueError, KeyError, IndexError):
                failed_rows.append({
                    'Number': number,
                    'Code': 'N/A',
                    'Title': 'N/A',
                    'Details': 'N/A',
                    'TimeTaken': response_time
                })
    success_df = pd.DataFrame(success_rows)
    failed_df = pd.DataFrame(failed_rows)
    return jsonify(success=success_df.to_dict(orient="records"), failed=failed_df.to_dict(orient="records"))


def transform_template_json(input_json):
    try:
        data = json.loads(input_json) if not isinstance(input_json, dict) else input_json
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return None
    namespace = data.get("namespace")
    language_code = data.get("language")
    name = data.get("name")
    components = data.get("components", [])
    payload = {
        "to": "PLACEHOLDER_NUMBER",
        "messaging_product": "whatsapp",
        "type": "template",
        "template": {
            "namespace": namespace,
            "language": {"policy": "deterministic", "code": language_code},
            "name": name,
        }
    }
    template_components = []
    for component in components:
        if component.get("type") == "HEADER" and component.get("format") == "IMAGE":
            header = {
                "type": "header",
                "parameters": [{"type": "image", "image": {"id": "PLACEHOLDER_IMAGE_ID"}}]
            }
            template_components.append(header)
        elif component.get("type") == "BODY":
            body_text = component.get("text")
            if body_text:
                variables = re.findall(r'\{\{(\d+)\}\}', body_text)
                if variables:
                    body = {"type": "body", "parameters": [{"type": "text", "text": f'PLACEHOLDER_VAR_{var}'} for var in variables]}
                    template_components.append(body)
    if template_components:
        payload["template"]["components"] = template_components
    payload_json = json.dumps(payload, indent=4)
    payload_json = payload_json.replace('"PLACEHOLDER_NUMBER"', '"number"')
    for var in re.findall(r'PLACEHOLDER_VAR_(\d+)', payload_json):
        payload_json = payload_json.replace(f'"PLACEHOLDER_VAR_{var}"', f'"Variable_{var}"')
    return payload_json

# TODO : DELETE THIS FUNCTION IT IS DEPRICATED 
def send_message_campaign(members, template_json, variables, api_key_360 , media_id=None, campaign=None, campaign_name=None):
    success_rows = []
    failed_rows = []
    start_time = time.time()
    
    logger.debug("Starting send_message_campaign")
    logger.debug(f"Received members: {members}")
    logger.debug(f"Template JSON: {template_json}")
    logger.debug(f"Variables: {variables}")
    logger.debug(f"Media ID: {media_id}, Campaign: {campaign}, Campaign Name: {campaign_name}")
    
    try:
        template_dict = json.loads(template_json)
        logger.debug("Template JSON successfully parsed into a dictionary")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse template JSON: {e}")
        return jsonify(success=[], failed=[{'Number': 'N/A', 'Title': 'Error', 'Details': str(e), 'Code': 'N/A'}])
    
    for member in members:
        number = member['mobile']
        template_dict['to'] = number
        logger.debug(f"Processing member with number: {number}")
        
        member_data = {column: member.get(column, '') for column in variables}
        logger.debug(f"Member data: {member_data}")
        
        for component in template_dict.get('template', {}).get('components', []):
            if component['type'] == 'body':
                for i, parameter in enumerate(component.get('parameters', [])):
                    if parameter['type'] == 'text' and i < len(variables):
                        parameter['text'] = str(member_data[variables[i]]) if variables[i] in member_data else f'Variable_{i+1}'
            elif component['type'] == 'header' and component.get('parameters', []):
                if component['parameters'][0].get('type') == 'image' and media_id:
                    component['parameters'][0]['image'] = {'id': media_id}
        
        url = "https://waba-v2.360dialog.io/messages"
        headers = {"Content-Type": "application/json", "D360-API-KEY": api_key_360}
        # logger.debug(f"Sending request to URL: {url} with headers: {headers} and template: {template_dict}")
        logger.debug(f"Sending request to URL: ...")
        try:
            response = requests.post(url, headers=headers, json=template_dict)
            response_time = time.time() - start_time
            logger.debug(f"Response received in {response_time:.2f} seconds with status code {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            failed_rows.append({
                'Number': number,
                'Title': 'Request Error',
                'Details': str(e),
                'Code': 'N/A',
                'TimeTaken': time.time() - start_time
            })
            continue
        
        mongo_db = current_app.mongo
        collection = mongo_db.campaign_responses
        campaign_name_collection = mongo_db.campaign_name

        if campaign_name and not campaign_name_collection.find_one({"name": campaign_name}):
            logger.debug(f"Inserting campaign name {campaign_name} into MongoDB")
            
            # Prepare the document with the current date and time
            campaign_data = {
                "name": campaign_name,
                "created_at": datetime.utcnow()  # Use UTC time for consistency
            }
            
            # Insert the document into the collection
            campaign_name_collection.insert_one(campaign_data)

        data_to_insert = {
            'campaign': campaign,
            'campaign_name': campaign_name,
            'campaign_date': datetime.now(),
            'number': number,
            'template': template_dict,
            'response': response.json() if response.status_code == 200 else response.text,
            'status_code': response.status_code,
            'time_taken': response_time
        }
        logger.debug(f"Data to be inserted into MongoDB: ...")

        try:
            collection.insert_one(data_to_insert)
            logger.debug("Data inserted successfully into MongoDB")
        except Exception as e:
            logger.error(f"Error inserting data into MongoDB: {e}")

        if response.status_code == 200:
            try:
                response_json = response.json()
                logger.debug(f"Successful response JSON: {response_json}")
                for contact, message in zip(response_json.get('contacts', []), response_json.get('messages', [])):
                    success_rows.append({
                        'Number': contact.get('input', 'N/A'),
                        'MessageID': message.get('id', 'N/A'),
                        'MessageStatus': message.get('message_status', 'N/A'),
                        'TimeTaken': response_time
                    })
            except json.JSONDecodeError:
                logger.error("Invalid JSON response")
                failed_rows.append({
                    'Number': number,
                    'Title': 'Error',
                    'Details': 'Invalid JSON response',
                    'Code': response.status_code,
                    'TimeTaken': response_time
                })
        else:
            try:
                error_message = response.json().get("error", {}).get("message", "N/A")
                error_code = response.json().get("error", {}).get("code", "N/A")
                logger.debug(f"Error message from response: {error_message}, Error code: {error_code}")
            except (json.JSONDecodeError, KeyError):
                error_message = response.text
                error_code = response.status_code
            failed_rows.append({
                'Number': number,
                'Title': 'Error',
                'Details': error_message,
                'Code': error_code,
                'TimeTaken': response_time
            })
    
    logger.debug(f"Campaign completed. Success: {len(success_rows)}, Failed: {len(failed_rows)}")
    return jsonify(
        success=success_rows,
        failed=failed_rows,
        summary={
            'total': len(members),
            'successful': len(success_rows),
            'failed': len(failed_rows),
            'success_percentage': f'{(len(success_rows) / len(members)) * 100:.2f}%',
            'failed_percentage': f'{(len(failed_rows) / len(members)) * 100:.2f}%'
        }
    )



def get_report(campaign_name,whatsapp_data_db):
    logger.info(f"Fetching report for campaign: {campaign_name}")
    
    
    webhook_latest_to_user_collection = whatsapp_data_db.webhook_latest_to_user
    campaign_responses_collection = whatsapp_data_db.campaign_responses

    # Fetch campaign responses from the database
    logger.info(f"Querying campaign_responses_collection with campaign_name: {campaign_name}")
    try:
        campaign_responses = list(campaign_responses_collection.find({
            'campaign_name': campaign_name.strip()
        }))
    except Exception as e:
        logger.error(f"Error querying campaign_responses_collection: {e}")
        return None
    logger.info(f"Campaign responses fetched: {campaign_responses}")

    if not campaign_responses:
        logger.warning(f"No campaign responses found for campaign: {campaign_name}")
        return None

    logger.info(f"Found {len(campaign_responses)} responses for campaign: {campaign_name}")

    message_ids = [
        response['response']['messages'][0]['id']
        for response in campaign_responses
        if 'response' in response and 'messages' in response['response'] and isinstance(response['response']['messages'], list) and response['response']['messages']
    ]

    logger.info(f"Collected {len(message_ids)} message IDs from campaign responses")
    logger.info (message_ids)

    # Fetch webhook data for the collected message IDs
    logger.info(f"Fetching webhook data for message IDs from the database")
    webhook_latest_to_user = list(webhook_latest_to_user_collection.find({
        'id': {'$in': message_ids}
    }))

    logger.info(f"Fetched {len(webhook_latest_to_user)} webhook records")

    # Create a dictionary to map message IDs to webhook data
    webhook_dict = {doc['id']: doc for doc in webhook_latest_to_user}

    # Initialize variables for joined data and status counting
    joined_data = []
    status_counter = Counter()

    data_by_status = {
        'sent': [],
        'delivered': [],
        'read': [],
        'failed': []
    }

    logger.info("Starting to join campaign responses with webhook data")

    # Iterate over the campaign responses and join them with webhook data
    for response in campaign_responses:
        if 'response' in response and 'messages' in response['response'] and isinstance(response['response']['messages'], list) and response['response']['messages']:
            message_id = response['response']['messages'][0]['id']

            if message_id in webhook_dict:
                webhook_data = webhook_dict[message_id]
                
                # Extract relevant fields from campaign response
                combined_data = {
                    'campaign': response.get('campaign'),
                    'campaign_name': response.get('campaign_name'),
                    'number': response.get('number'),
                    'status_code': response.get('status_code'),
                    'wa_id': response['response']['contacts'][0].get('wa_id') if response['response'].get('contacts') else None,
                    'wamid': message_id,  # Message ID from the response
                }

                # Extract relevant fields from webhook data
                combined_data.update({
                    'status': webhook_data.get('status', 'unknown'),  # Status from webhook
                    'billable': webhook_data.get('pricing', {}).get('billable', False),  # If available
                    'errors': webhook_data.get('errors', [])  # Error details from webhook
                })

                # Join response and webhook data
                joined_data.append(combined_data)

                # Update status counter and categorize by status
                status = webhook_data.get('status', 'unknown')  # Use 'unknown' as a fallback status
                status_counter[status] += 1

                if status in data_by_status:
                    data_by_status[status].append(combined_data)
                else:
                    data_by_status[status] = [combined_data]

                logger.debug(f"Message ID {message_id} - Status: {status}")
    
        # Check if the message has a failed status due to error in response
        if response.get('status_code') == 400 and 'error' in response.get('response', {}):
            # Extract relevant fields from campaign response for the failed status
            failed_data = {
                'campaign': response.get('campaign'),
                'campaign_name': response.get('campaign_name'),
                'number': response.get('number'),
                'status_code': response.get('status_code'),
                'wa_id': response['response']['contacts'][0].get('wa_id') if response['response'].get('contacts') else None,
                'wamid': response['response']['messages'][0]['id'],  # Message ID from the response
                'status': 'failed',  # Explicitly mark as failed due to error
                'errors': response.get('response', {}).get('error', 'Unknown error')  # Extract error from response
            }

            # Append to the failed status category
            status_counter['failed'] += 1
            data_by_status['failed'].append(failed_data)

            # logger.warning(f"Message ID {failed_data['wamid']} - Status: failed due to error: {failed_data['errors']}")

    # Prepare the status counts dictionary
    message_statuses = {
        'sent': status_counter.get('sent', 0),
        'delivered': status_counter.get('delivered', 0),
        'read': status_counter.get('read', 0),
        'failed': status_counter.get('failed', 0)
    }

    logger.info(f"Status counts for campaign {campaign_name}: {message_statuses}")
    logger.info(f"Data by status {campaign_name}:\n{json.dumps(data_by_status, indent=4, default=str)}")

    # Return the status counts and the data categorized by status
    return {'status_counts': message_statuses, 'data_by_status': data_by_status}


def get_all_collections_content(whatsapp_data_db):
    
    all_collections = whatsapp_data_db.list_collection_names()
    collections_content = {}

    for collection_name in all_collections:
        collection = whatsapp_data_db[collection_name]
        documents = list(collection.find())
        collections_content[collection_name] = documents

    return collections_content

def check_df_validity(df):
    # Specify which columns to check for duplicates and phone numbers
    duplicate_check_columns = ['formatted_mobile']  # Adjust as needed
    phone_number_column = 'mobile'  # Adjust if needed

    df[phone_number_column] = df[phone_number_column].astype(str)
    # Apply phone number validation
    df['formatted_mobile'] = df[phone_number_column].apply(is_valid_phone_number)

    # Count invalid phone numbers
    num_invalid_numbers = df['formatted_mobile'].isna().sum()

    # Filter out rows with invalid phone numbers
    df_valid = df[df['formatted_mobile'].notna()]

    duplicates = df_valid[df_valid.duplicated(subset=duplicate_check_columns, keep=False)]
    num_duplicates = len(duplicates)

    df_cleaned = df_valid.drop_duplicates(subset=duplicate_check_columns, keep='first')

    df_cleaned.loc[:, phone_number_column] = df_cleaned['formatted_mobile']
    df_cleaned = df_cleaned.drop(columns=['formatted_mobile'])

    total_rows = len(df)
    num_proper_rows = len(df_cleaned)
    num_valid_numbers = num_proper_rows

    # Prepare statistics summary
    stats_summary = {
        'total_rows': total_rows,
        'num_duplicates': num_duplicates,
        'num_valid_numbers': num_valid_numbers,
        'num_invalid_numbers': num_invalid_numbers,
        'num_proper_rows': num_proper_rows
    }

    return stats_summary, duplicates, df_cleaned



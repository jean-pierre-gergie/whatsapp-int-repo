from celery import Celery
from celery import states
import time
from dotenv import load_dotenv
import os
import logging
import json
import requests
from flask import jsonify
from datetime import datetime
from pymongo import MongoClient
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

logger.setLevel(logging.DEBUG)



# Load environment variables from .env
load_dotenv()

rabbitmq_user = os.getenv("RABBITMQ_DEFAULT_USER")
rabbitmq_pwd  = os.getenv("RABBITMQ_DEFAULT_PASS")

mongo_username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
mongo_password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
mongo_host = os.getenv('MONGO_HOST')
mongo_port = os.getenv('MONGO_PORT')

dialog_360_message_url = os.getenv("DIALOG_360_MESSAGE_URL")
api_key_360 = os.getenv('API_KEY')

rabbit_url = f'amqp://{rabbitmq_user}:{rabbitmq_pwd}@rabbitmq:5672//'
mongo_url = f'mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}'



celery_app = Celery(
    'microservice',
    broker= rabbit_url ,# RabbitMQ as broker
    backend= f"{mongo_url}/celery_backend"  # MongoDB as result backend
)



# run the stask with status 

@celery_app.task(bind=True)
def send_message_campaign(self, selected_campaign, template_json, variables, campaign, campaign_name, media_id=None):
    success_rows = []
    failed_rows = []
    start_time = time.time()

    mongo_client = get_mongo_client()
    mongo_db = mongo_client.whatsapp_data
    members_collection = mongo_db.members
    members = list(members_collection.find({"tag": selected_campaign}))

    # Remove the _id field from members
    members = [{key: value for key, value in member.items() if key != '_id'} for member in members]
    total_members = len(members)

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
        return {
            'success': [],
            'failed': [{'Number': 'N/A', 'Title': 'Error', 'Details': str(e), 'Code': 'N/A'}],
            'summary': {
                'total': 0,
                'successful': 0,
                'failed': 1,
                'success_percentage': '0.00%',
                'failed_percentage': '100.00%'
            }
        }

    # Set up the MongoDB collections
    campaign_responses_collection = mongo_db.campaign_responses
    final_campaign_response_collection = mongo_db.final_campaign_response

    for prog_idx, member in enumerate(members, start=1):
        time.sleep(5)
        number = member['mobile']
        template_dict['to'] = number
        logger.debug(f"Processing member with number: {number}")

        member_data = {column: member.get(column, '') for column in variables}
        logger.debug(f"Member data: {member_data}")

        # Update template with member-specific data
        for component in template_dict.get('template', {}).get('components', []):
            if component['type'] == 'body':
                for i, parameter in enumerate(component.get('parameters', [])):
                    if parameter['type'] == 'text' and i < len(variables):
                        parameter['text'] = str(member_data.get(variables[i], f'Variable_{i+1}'))
            elif component['type'] == 'header' and component.get('parameters', []):
                if component['parameters'][0].get('type') == 'image' and media_id:
                    component['parameters'][0]['image'] = {'id': media_id}

        headers = {"Content-Type": "application/json", "D360-API-KEY": api_key_360}
        try:
            response = requests.post(dialog_360_message_url, headers=headers, json=template_dict)
            response_time = time.time() - start_time
            logger.debug(f"Response received in {response_time:.2f} seconds with status code {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            failed_rows.append({
                'Number': number,
                'Title': 'Request Error',
                'Details': str(e),
                'Code': 'N/A',
                'TimeTaken': response_time
            })
            continue

        # Save individual message response
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

        try:
            campaign_responses_collection.insert_one(data_to_insert)
            logger.debug("Individual message response inserted successfully into MongoDB")
        except Exception as e:
            logger.error(f"Error inserting individual message response into MongoDB: {e}")

        # Handle response based on status code
        if response.status_code == 200:
            try:
                response_json = response.json()
                for contact, message in zip(response_json.get('contacts', []), response_json.get('messages', [])):
                    success_rows.append({
                        'Number': contact.get('input', 'N/A'),
                        'MessageID': message.get('id', 'N/A'),
                        'MessageStatus': message.get('message_status', 'N/A'),
                        'TimeTaken': response_time
                    })
            except json.JSONDecodeError:
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

        # Update task state to show progress
        self.update_state(state='PROGRESS', meta={
            'Total_members': total_members,
            'processed': prog_idx,
            'curr_succ': len(success_rows),
            'curr_failed': len(failed_rows)
        })

    # Save aggregated results to final_campaign_response_collection
    aggregated_data_to_insert = {
        'campaign': campaign,
        'campaign_name': campaign_name,
        'campaign_date': datetime.now(),
        'total_members': total_members,
        'total_success': len(success_rows),
        'total_failed': len(failed_rows),
        'success_rows': success_rows,
        'failed_rows': failed_rows
    }

    try:
        final_campaign_response_collection.insert_one(aggregated_data_to_insert)
        logger.debug("Aggregated campaign data inserted successfully into MongoDB")
    except Exception as e:
        logger.error(f"Error inserting aggregated campaign data into MongoDB: {e}")

    # Return the final results
    logger.debug(f"Campaign completed. Success: {len(success_rows)}, Failed: {len(failed_rows)}")
    return {
        'success': success_rows,
        'failed': failed_rows,
        'summary': {
            'total': total_members,
            'successful': len(success_rows),
            'failed': len(failed_rows),
            'success_percentage': f'{(len(success_rows) / total_members) * 100:.2f}%' if total_members > 0 else '0.00%',
            'failed_percentage': f'{(len(failed_rows) / total_members) * 100:.2f}%' if total_members > 0 else '0.00%'
        }
    }


def get_mongo_client():
    logger.debug(f"Connecting to MongoDB with URI: {mongo_url}")
    return MongoClient(mongo_url) 
    



### only for testing 

# todo rmove this in production 


@celery_app.task(bind=True)
def looping_task(self, n):
    result_list = []
    for i in range(1, n + 1):
        # Simulate a delay
        time.sleep(1)
        result = i * 2  
        result_list.append(result)

        # Update task state with current iteration's result, using a custom 'PROGRESS' state
        self.update_state(state='PROGRESS', meta={'current': i, 'total': n, 'result': result})

    # Final return after completing the loop
    return {'status': 'Task completed', 'final_result': result_list}


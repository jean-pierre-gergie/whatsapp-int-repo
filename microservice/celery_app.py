from celery import Celery
from celery import states
import time
from dotenv import load_dotenv
import os
import logging
import json
import requests
from flask import jsonify
from datetime import datetime, timezone
from pymongo import MongoClient
from celery.utils.log import get_task_logger
from utils import *
from dateutil import parser

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
def send_message_campaign(self, campaign_timing, scheduled_date,scheduled_date_local, selected_campaign, template_json, variables, campaign_name, media_id=None):

    logger.debug(f"Task started with: campaign_timing={campaign_timing}, scheduled_datetime={scheduled_date},scheduled_datetime_local={scheduled_date_local}, "
                 f"selected_campaign={selected_campaign}, template_json={template_json}, variables={variables}, "
                 f"campaign_name={campaign_name}, media_id={media_id}")
    

    success_rows = []
    failed_rows = []
    start_time = time.time()

    mongo_client = get_mongo_client(mongo_url)
    mongo_db = mongo_client.whatsapp_data

    members = get_member_list(mongo_db, selected_campaign=selected_campaign)
    total_members = len(members)

    template_dict = get_template_json(template_json)

    logger.debug("Submitted campaign")
    logger.debug(f"Campaign Timing: {campaign_timing}")
    logger.debug(f"Scheduled Datetime: {scheduled_date}")
    logger.debug(f"Received members: {members}")
    logger.debug(f"Template JSON: {template_json}")
    logger.debug(f"Variables: {variables}")
    logger.debug(f"Media ID: {media_id}, Campaign: {selected_campaign}, Campaign Name: {campaign_name}")

    campaign_responses_collection = mongo_db.campaign_responses
    final_campaign_response_collection = mongo_db.final_campaign_response

    self.update_state(state='PENDING', meta={
        'Total_members': 0,
        'processed': 0,
        'curr_succ': 0,
        'curr_failed': 0
    })
    scheduled_date_compare = parser.parse(scheduled_date)
    if campaign_timing == "scheduled" and datetime.now(timezone.utc) < scheduled_date_compare:
        campaign_scheduled = True
        initial_campaign_data = {
            'status': "Pending Start Time",
            'campaign': selected_campaign,
            'campaign_name': campaign_name,
            'campaign_submitted_at': datetime.now(),
            'campaign_scheduled': campaign_scheduled,
            'campaign_scheduled_at': scheduled_date,
            'total_members': total_members
        }

        campaign_id = manage_campaign_data(
            initial_campaign_data, final_campaign_response_collection, campaign_id=None, action='insert')
        
        self.apply_async(
                kwargs = {
                    'campaign_timing': campaign_timing,  # Same
                    'scheduled_date': scheduled_date,  # Rename scheduled_datetime to scheduled_date
                    'scheduled_date_local':scheduled_date_local,
                    'selected_campaign': selected_campaign,  # Same
                    'template_json': template_json,  # Same
                    'variables': variables,  # Same
                    'campaign_name': campaign_name,  # Same
                    'media_id': media_id if media_id else 0  # Use media_id with default value 0 if not provided
                },
                eta=scheduled_date
                )
        return 

    else:
        initial_campaign_data = {
            'status': "Starting Now",
            'campaign': selected_campaign,
            'campaign_name': campaign_name,
            'campaign_submitted_at': datetime.now(),
            'campaign_scheduled': False,
            'total_members': total_members
        }

        campaign_id = manage_campaign_data(
            initial_campaign_data, final_campaign_response_collection, campaign_id=None, action='insert')

        for prog_idx, member in enumerate(members, start=1):
            time.sleep(5)

            progress_update = {
                'status': "Sending Messages",
                'campaign_started_at': datetime.now()
            }
   
            manage_campaign_data(progress_update, final_campaign_response_collection, campaign_id=campaign_id, action="update")

            number = member['mobile']
            template_dict['to'] = number
            logger.debug(f"Processing member with number: {number}")

            member_data = get_member_data(member, variables)
            template_dict = update_template_components(template_dict, member_data=member_data, variables=variables, media_id=media_id)

            response, response_time = send_post_request(
                dialog_360_message_url=dialog_360_message_url,
                api_key_360=api_key_360,
                template_dict=template_dict,
                number=number,
                failed_rows=failed_rows,
                start_time=start_time)
            
            if response:
                data_to_insert = {
                    'campaign': selected_campaign,
                    'campaign_name': campaign_name,
                    'campaign_date': datetime.now(),
                    'number': number,
                    'template': template_dict,
                    'response': response.json() if response.status_code == 200 else response.text,
                    'status_code': response.status_code,
                    'time_taken': response_time
                }

                insert_message_response(campaign_responses_collection=campaign_responses_collection, data_to_insert=data_to_insert)

                process_response(response=response, number=number, response_time=response_time, success_rows=success_rows, failed_rows=failed_rows)
            else:
                logger.error(f"No response received for member {number}. Skipping this member.")
                failed_rows.append({
                    'Number': number,
                    'Title': 'No Response',
                    'Details': 'No response received from API',
                    'Code': 'N/A',
                    'TimeTaken': time.time() - start_time
                })        

            self.update_state(state='PROGRESS', meta={
                'Total_members': total_members,
                'processed': prog_idx,
                'curr_succ': len(success_rows),
                'curr_failed': len(failed_rows)
            })

        final_update = {
            'status': "finished",
            'campaign_finished_at': datetime.now(),
            'total_success': len(success_rows),
            'total_failed': len(failed_rows),
            'success_percentage': f'{(len(success_rows) / total_members) * 100:.2f}%' if total_members > 0 else '0.00%',
            'failed_percentage': f'{(len(failed_rows) / total_members) * 100:.2f}%' if total_members > 0 else '0.00%'
        }

        update_final_campaign_data(campaign_id=campaign_id,
                                    final_campaign_response_collection=final_campaign_response_collection, 
                                    final_update=final_update,
                                    success_rows_len=len(success_rows),
                                    failed_rows_len=len(success_rows))

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

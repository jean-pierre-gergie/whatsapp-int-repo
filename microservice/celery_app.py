from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready 
import time
from dotenv import load_dotenv
from datetime import datetime
import os
import logging
import json
import requests
from flask import jsonify
from datetime import datetime, timezone
from pymongo import MongoClient
from celery.utils.log import get_task_logger
from utils.send_campaigns_helpers import *
from utils.chat_rooms_helper import WhatsAppChatCampaignHandler
from utils.manage_founadtion_session import get_dependencies_by_foundation
from utils.webhook_jwt_refresh_helper import refresh_jwt
from utils.init_system import init_system
from utils.webhook_api_key_refresh_helper import refresh_api_key
from dateutil import parser
import asyncio



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


rabbit_url = f'amqp://{rabbitmq_user}:{rabbitmq_pwd}@rabbitmq:5672//'
mongo_url = f'mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}'



celery_app = Celery(
    'microservice',
    broker= rabbit_url ,# RabbitMQ as broker
    backend= f"{mongo_url}/celery_backend"  # MongoDB as result backend
)

celery_app.conf.beat_schedule = {
    'refresh-webhook-jwt-token': {
        'task': 'tasks.refresh_webhook_jwt_token',
        'schedule': crontab(hour='*/10'),  # Every 6 hours
    },
    'refresh-api-key-weekly': {
        'task': 'tasks.refresh_api_key',
        'schedule': crontab(hour='*/20'),  # Every Sunday at 12:00 AM
    },
}

@celery_app.task(bind=True)
def send_message_campaign(self, foundation_name, campaign_timing, scheduled_date,scheduled_date_local, selected_campaign, template_json, variables, campaign_name, media_id=None,campaign_id_db =None):

    logger = get_task_logger(__name__)

    logger.debug(f"Foundation: {foundation_name}")

    logger.debug(f"Task started with: campaign_timing={campaign_timing}, scheduled_datetime={scheduled_date},scheduled_datetime_local={scheduled_date_local}, "
                 f"selected_campaign={selected_campaign}, template_json={template_json}, variables={variables}, "
                 f"campaign_name={campaign_name}, media_id={media_id}")
    
    logger.debug(f"campaign_id_db: {campaign_id_db}")

    

    success_rows = []
    failed_rows = []
    start_time = time.time()

    whatsapp_data_db , agent_data_db , api_key_360 = get_dependencies_by_foundation(foundation_name=foundation_name,mongo_url=mongo_url)

    chat_room_collection = agent_data_db.rooms


    chat_room_handler = WhatsAppChatCampaignHandler(chat_room_collection,logger=logger)


    members = get_member_list(whatsapp_data_db, selected_campaign=selected_campaign)
    total_members = len(members)

    template_dict = get_template_json(template_json)

    logger.debug("Submitted campaign")
    logger.debug(f"Campaign Timing: {campaign_timing}")
    logger.debug(f"Scheduled Datetime: {scheduled_date}")
    logger.debug(f"Received members: {members}")
    logger.debug(f"Template JSON: {template_json}")
    logger.debug(f"Variables: {variables}")
    logger.debug(f"Media ID: {media_id}, Campaign: {selected_campaign}, Campaign Name: {campaign_name}")

    campaign_responses_collection = whatsapp_data_db.campaign_responses
    final_campaign_response_collection = whatsapp_data_db.final_campaign_response


    self.update_state(state='PENDING', meta={
        'Total_members': 0,
        'processed': 0,
        'curr_succ': 0,
        'curr_failed': 0
    })
  
    

    logger.debug(f"immediate or Second run campaign_id_db: {campaign_id_db}")



    for prog_idx, member in enumerate(members, start=1):

        

        # time.sleep(10)

        progress_update = {
            'status': "Sending Messages",
            'campaign_started_at': datetime.now()
        }

        logger.debug(f"updating record campaign_id_db: {campaign_id_db}")

        logger.debug(f"progress updating : {progress_update}")
    
        manage_campaign_data(progress_update, final_campaign_response_collection, campaign_id=campaign_id_db, action="update")

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

            logger.debug("Inserts an individual message response into MongoDB.")
            insert_message_response(campaign_responses_collection=campaign_responses_collection, data_to_insert=data_to_insert)

            


            process_response(response=response, number=number, response_time=response_time, success_rows=success_rows, failed_rows=failed_rows)


            logger.info (f"handeling chat data for {member}")
            asyncio.run(chat_room_handler._handle_chat_room(
                user_phone_number=number,
                wa_mid=None,  # or actual wa_mid value if available
                campaign_name=campaign_name,
                timestamp=datetime.utcnow()
            ))


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

        # Final update after processing all members
    final_update = {
        'status': "Finished",
        'campaign_finished_at': datetime.now(),
        'total_success': len(success_rows),
        'total_failed': len(failed_rows),
        'success_percentage': f'{(len(success_rows) / total_members) * 100:.2f}%' if total_members > 0 else '0.00%',
        'failed_percentage': f'{(len(failed_rows) / total_members) * 100:.2f}%' if total_members > 0 else '0.00%'
    }

    # Update the final campaign data using the same campaign_id_db
    update_final_campaign_data(
            campaign_id=campaign_id_db,
            final_campaign_response_collection=final_campaign_response_collection,
            final_update=final_update,
            success_rows_len=len(success_rows),
            failed_rows_len=len(failed_rows)
        )


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




@celery_app.task(name='tasks.refresh_webhook_jwt_token' ,bind = True)
def refresh_webhook_jwt_token(self):
    logger = get_task_logger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.info(f"BEAT --- Refreshing JWT Token")
    refresh_jwt(logger)
    logger.info(f"BEAT --- Done updating JWT Token")
    


@celery_app.task(name="task.refresh_api_key",bind = True)
def refresh_api_key(self):
    logger = get_task_logger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.info(f"BEAT --- Refreshing API KEY")
    refresh_api_key(logger)
    logger.info(f"BEAT --- Done  updating API KEY")






@celery_app.task(name='tasks.init_system_task',bind = True)
def init_system_task(self):
    logger = get_task_logger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.info(f"INIT_SYSTEM --- initializing the system")
    init_system(logger)
    logger.info(f"INIT_SYSTEM --- init Done")
                

            







@worker_ready.connect
def call_refresh_token_on_startup(sender, **kwargs):
    logger.info("Worker started, calling refresh_webhook_jwt_token immediately...")
    celery_app.send_task('tasks.init_system_task')





def submit_task(task_args=None, start_immediately=True, scheduled_time=None):
    logger = get_task_logger(__name__)
    logger.info("Submitting task...")

    whatsapp_data_db , _ , _ = get_dependencies_by_foundation(foundation_name=task_args['foundation_name'],mongo_url=mongo_url)
    members = get_member_list(whatsapp_data_db, selected_campaign=task_args['selected_campaign'])
    total_members = len(members)
    final_campaign_response_collection = whatsapp_data_db.final_campaign_response

    
    if not task_args:
        raise ValueError("task_args must be provided and contain the required arguments.")

    if start_immediately:
        logger.info("Starting job immediately...")
        initial_campaign_data = {
                'status': "Pending Start Time",
                'campaign': task_args['selected_campaign'],
                'campaign_name': task_args['campaign_name'],
                'campaign_submitted_at': datetime.now(),
                'campaign_scheduled': False,  # Immediate campaign, so not scheduled
                'total_members': total_members
            }
        campaign_id_db = manage_campaign_data(
                initial_campaign_data, final_campaign_response_collection, campaign_id=None, action='insert'
            )
        task_args['campaign_id_db'] = str(campaign_id_db) 
        result = send_message_campaign.apply_async(kwargs=task_args)
        

    elif scheduled_time:
        logger.info(f"Scheduling job for: {scheduled_time}")
        # Handle 'Z' suffix in ISO 8601 string
        if scheduled_time.endswith('Z'):
            scheduled_time = scheduled_time.replace('Z', '+00:00')  # Replace 'Z' with UTC offset
        eta = datetime.fromisoformat(scheduled_time)
        initial_campaign_data = {
                'status': "Pending Start Time",
                'campaign': task_args['selected_campaign'],
                'campaign_name': task_args['campaign_name'],
                'campaign_submitted_at': datetime.now(),
                'campaign_scheduled': True,
                'campaign_scheduled_at': task_args['scheduled_date'],
                'total_members': total_members
            }

        

        campaign_id_db = manage_campaign_data(
                initial_campaign_data, final_campaign_response_collection, campaign_id=None, action='insert'
            )
        
        task_args['campaign_id_db'] = str(campaign_id_db)

        result = send_message_campaign.apply_async(kwargs=task_args, eta=eta)
        
        
    else:
        raise ValueError("Either 'start_immediately' must be True or 'scheduled_time' must be provided.")

    logger.info(f"Task submitted with ID: {result.id}")
    return result.id





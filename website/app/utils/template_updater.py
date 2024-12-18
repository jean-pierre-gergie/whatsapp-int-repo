import time
import requests
import pandas as pd
from app.config import Config  
from flask import current_app
from pymongo.errors import BulkWriteError
from pymongo import UpdateOne
import copy
from flask import Flask, current_app
from pymongo import MongoClient
import threading
from ..logger_setup.logger_setup import LoggerSetup

logger = current_app.logger



# pymongo_logger = logging.getLogger("pymongo")
# pymongo_logger.setLevel(logging.ERROR) 


def fetch_and_update_templates(api_key_360, whatsapp_data_db):

    logger.debug(f" API Key: {api_key_360}")
   
    logger.debug(f"x3nZhZTVLqT2egKf81lfCsW3AK ")
    url = "https://waba-v2.360dialog.io/v1/configs/templates"
    headers = {
        "D360-API-KEY": api_key_360,
        "Content-Type": "application/json"
    }
    params = {
        "limit": 1000,
        "offset": 0,
        "sort": "id"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        logger.debug(f"Fetching templates: Status {response.status_code}")
        
        if response.status_code == 200:
            templates = response.json().get('waba_templates', [])
            api_template_ids = set(template['id'] for template in templates)
            collection = whatsapp_data_db.templates 

            for template in templates:
                created_at = pd.to_datetime(template.get('created_at')).to_pydatetime() if template.get('created_at') else None
                existing_template = collection.find_one({'template_id': template['id']})
                
                template_data = {
                    'template_name': template.get('name'),
                    'service_category': template.get('category'),
                    'status': template.get('status'),
                    'language': template.get('language'),
                    'created_day': created_at
                }
                
                if existing_template:
                    collection.update_one(
                        {'template_id': template['id']},
                        {'$set': template_data}
                    )
                    logger.info(f"Updated template: {template['id']}")
                else:
                    template_data['template_id'] = template['id']
                    collection.insert_one(template_data)
                    logger.info(f"Inserted new template: {template['id']}")

            db_templates = collection.find()
            for db_template in db_templates:
                if db_template['template_id'] not in api_template_ids:
                    collection.delete_one({'template_id': db_template['template_id']})
                    logger.info(f"Deleted outdated template: {db_template['template_id']}")
                    
            logger.debug("Template synchronization completed successfully.")
        else:
            logger.error(f"Failed to retrieve templates. Status: {response.status_code}, Response: {response.text}")

    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
    except Exception as e:
        logger.exception(f"An error occurred while fetching and updating templates: {e}")


# def start_template_updater(app):
#     while True:
#         with app.app_context():
#             fetch_and_update_templates()
#         time.sleep(120)
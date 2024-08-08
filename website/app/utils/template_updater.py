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


api_key_360 =Config.API_KEY

def fetch_and_update_templates():
    url = "https://waba-v2.360dialog.io/v1/configs/templates"
    api_key = api_key_360

    headers = {
        "D360-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    params = {
        "limit": 1000,
        "offset": 0,
        "sort": "id"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        templates = response.json().get('waba_templates', [])
        api_template_ids = set(template['id'] for template in templates)

        mongo_db = current_app.mongo
        collection = mongo_db.templates 

        for template in templates:
            created_at = pd.to_datetime(template['created_at']).to_pydatetime() if template.get('created_at') else None
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
            else:
                template_data['template_id'] = template['id']
                collection.insert_one(template_data)

        db_templates = collection.find()
        for db_template in db_templates:
            if db_template['template_id'] not in api_template_ids:
                collection.delete_one({'template_id': db_template['template_id']})
    else:
        print(f"Failed to retrieve templates: {response.status_code}")
        print(response.text)


def start_template_updater(app):
    while True:
        with app.app_context():
            fetch_and_update_templates()
        time.sleep(10000)

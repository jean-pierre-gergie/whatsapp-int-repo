from celery import Celery
from celery.schedules import crontab
from pymongo import MongoClient
import os
from celery.utils.log import get_task_logger
import logging
from utils import get_mongo_client





# Logger for Celery Beat
logger = get_task_logger(__name__)
logger.setLevel(logging.DEBUG)

# MongoDB connection setup
mongo_username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
mongo_password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
mongo_host = os.getenv('MONGO_HOST')
mongo_port = os.getenv('MONGO_PORT')
mongo_url = f'mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}'

mongo_client = get_mongo_client(mongo_url)
mongo_db = mongo_client.whatsapp_data

# Celery Beat app configuration
celery_beat_app = Celery(
    'celery_beat_service',
    broker=f"amqp://{os.getenv('RABBITMQ_DEFAULT_USER')}:{os.getenv('RABBITMQ_DEFAULT_PASS')}@rabbitmq:5672//",
    backend=f"{mongo_url}/celery_backend"
)

# Task to clear revoked tokens directly in the beat app
@celery_beat_app.task
def clear_revoked_tokens():
    result = mongo_db.revoked_tokens.delete_many({})
    logger.info(f"Cleared {result.deleted_count} revoked tokens from the collection.")

# Schedule for the task to run every hour
celery_beat_app.conf.beat_schedule = {
    'clear-revoked-tokens-every-hour': {
        'task': 'celery_beat_service.clear_revoked_tokens',  # Task in the same beat app
        # 'schedule': crontab(minute=0, hour='*')  # Runs every hour on the hour
        'schedule': crontab(minute='*')  # This will run every minute
    }
}

celery_beat_app.conf.timezone = 'UTC'

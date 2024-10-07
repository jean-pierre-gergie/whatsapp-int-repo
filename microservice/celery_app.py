from celery import Celery
from celery import states
import time
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

rabbitmq_user = os.getenv("RABBITMQ_DEFAULT_USER")
rabbitmq_pwd  = os.getenv("RABBITMQ_DEFAULT_PASS")

mongo_username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
mongo_password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
mongo_host = os.getenv('MONGO_HOST')
mongo_port = os.getenv('MONGO_PORT')


rabbit_url = f'amqp://{rabbitmq_user}:{rabbitmq_pwd}@rabbitmq:5672//'
mongo_url = f'mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/celery_backend'



celery_app = Celery(
    'microservice',
    broker= rabbit_url ,# RabbitMQ as broker
    backend= mongo_url   # MongoDB as result backend
)



# run the stask with status 

@celery_app.task(bind=True)
def Send_campaign(self, n):
    pass



### only for testing 

# todo rmove this in production 


@celery_app.task(bind=True)
def looping_task(self, n):
    result_list = []
    for i in range(1, n + 1):
        # Simulate a delay
        time.sleep(1)
        result = i * 2  # Simulated computation for each iteration
        result_list.append(result)

        # Update task state with current iteration's result, using a custom 'PROGRESS' state
        self.update_state(state='PROGRESS', meta={'current': i, 'total': n, 'result': result})

    # Final return after completing the loop
    return {'status': 'Task completed', 'final_result': result_list}


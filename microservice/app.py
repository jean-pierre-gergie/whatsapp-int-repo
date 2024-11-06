from fastapi import FastAPI ,Request
from celery_app import celery_app ,send_message_campaign
import time 
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # Set the logging level


pymongo_logger = logging.getLogger("pymongo")
pymongo_logger.setLevel(logging.WARNING)

app = FastAPI()


@app.post("/start_campaign_task/")
async def start_campaign_task(request: Request):

    logger.debug(f"Microservice received start request, sending request  to celery worker: ...")

    payload = await request.json()

    logger.debug(f"Received payload: {payload}")

    # logger.debug(f"Final kwargs /for task: {kwargs}")
    task = send_message_campaign.apply_async(
            kwargs={
                'foundation_name':payload['foundation_name'],
                'campaign_timing': payload['campaign_timing'],
                'scheduled_date': payload['scheduled_date'],
                'scheduled_date_local':payload['scheduled_date_local'],
                'selected_campaign': payload['selected_campaign'],
                'template_json': payload['template_json'],
                'variables': payload['variables'],
                'campaign_name': payload['campaign_name'],
                'media_id': payload.get('media_id', 0),
                'campaign_id_db': None
            }
        )
   
    return {"task_id":task.id, "message": "Campaign processing started"}






@app.get("/microservice_get_campaign_status/{task_id}")
async def send_campaign_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)
    
    logger.debug(f"Received request for task status with task_id: {task_id}")

    if task_result.state == 'PENDING':
        logger.debug(f"Task {task_id} is still pending...")
        return {"status": "Task is still pending...", "task_id": task_id}
    
    elif task_result.state == 'PROGRESS':
        total_members = task_result.info.get('Total_members', 0)
        processed = task_result.info.get('processed', 0)
        success_count = task_result.info.get('curr_succ', 0)
        failed_count = task_result.info.get('curr_failed', 0)
        
        logger.debug(f"Task {task_id} is in progress: {processed}/{total_members} processed, "
                     f"{success_count} successes, {failed_count} failures.")
        
        return {
            "status": "Task in progress...",
            "total_members": total_members,  # Total members
            "processed": processed,  # Processed members so far
            "success_count": success_count,  # Number of successful sends
            "failed_count": failed_count,  # Number of failed sends
            "task_id": task_id
        }
    
    elif task_result.state == 'SUCCESS':
        logger.debug(f"Task {task_id} completed successfully.")
        # Extract the final result from task_result.result
        final_result = task_result.result or {}
        total_members = final_result.get('summary', {}).get('total', 0)
        final_success_count = final_result.get('summary', {}).get('successful', 0)
        final_failed_count = final_result.get('summary', {}).get('failed', 0)

        # In the completed state, all members should be processed
        logger.debug(f"Task {task_id} completed: {total_members} total, "
                     f"{final_success_count} successes, {final_failed_count} failures.")
        
        return {
            "status": "Task completed!",
            "total_members": total_members,  # Total members
            "processed": total_members,  # All members have been processed
            "success_count": final_success_count,  # Final number of successful sends
            "failed_count": final_failed_count,  # Final number of failed sends
            "task_id": task_id
        }
    
    elif task_result.state == 'FAILURE':
        logger.debug(f"Task {task_id} failed with error: {str(task_result.result)}")
        return {
            "status": "Task failed.",
            "error": str(task_result.result),
            "task_id": task_id
        }
    
    else:
        logger.debug(f"Task {task_id} is in state: {task_result.state}")
        return {"status": task_result.state, "task_id": task_id}



# ### only for testing 

# # todo rmove this in production 

# @app.get("/start-task/")
# async def start_task(n: int):
#     task = looping_task.delay(n)  # Start the looping task asynchronously
#     return {"task_id": task.id}


# @app.get("/task-status/{task_id}")
# async def task_status(task_id: str):
#     task_result = celery_app.AsyncResult(task_id)

#     if task_result.state == 'PENDING':
#         return {"status": "Task is still pending..."}
#     elif task_result.state == 'PROGRESS':
#         return {
#             "status": "Task in progress...",
#             "current": task_result.info.get('current', 0),
#             "total": task_result.info.get('total', 1),
#             "result": task_result.info.get('result', None)
#         }
#     elif task_result.state == 'SUCCESS':
#         return {"status": "Task completed!", "final_result": task_result.result}
#     elif task_result.state == 'FAILURE':
#         return {"status": "Task failed.", "error": str(task_result.result)}
#     else:
#         return {"status": task_result.state}
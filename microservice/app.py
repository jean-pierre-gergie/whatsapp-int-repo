from fastapi import FastAPI
from celery_app import celery_app , looping_task
import time 
app = FastAPI()


@app.get("/send_campaign/")
async def send_campaign(x: int, y: int):
    # return task id 
    pass



@app.get("/send_campaign_status/{task_id}")
async def send_campaign_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)
    # return current results
    pass



### only for testing 

# todo rmove this in production 

@app.get("/start-task/")
async def start_task(n: int):
    task = looping_task.delay(n)  # Start the looping task asynchronously
    return {"task_id": task.id}


@app.get("/task-status/{task_id}")
async def task_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)

    if task_result.state == 'PENDING':
        return {"status": "Task is still pending..."}
    elif task_result.state == 'PROGRESS':
        return {
            "status": "Task in progress...",
            "current": task_result.info.get('current', 0),
            "total": task_result.info.get('total', 1),
            "result": task_result.info.get('result', None)
        }
    elif task_result.state == 'SUCCESS':
        return {"status": "Task completed!", "final_result": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"status": "Task failed.", "error": str(task_result.result)}
    else:
        return {"status": task_result.state}
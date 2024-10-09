import requests
import time

# API endpoints
BASE_URL = "http://localhost:1616"
START_TASK_URL = f"{BASE_URL}/start-task/"
TASK_STATUS_URL = f"{BASE_URL}/task-status/"

# Start a new task by sending a request to the FastAPI API
def start_task(n):
    response = requests.get(START_TASK_URL, params={'n': n})
    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"Task started with ID: {task_id}")
        return task_id
    else:
        print("Failed to start the task")
        return None

# Check the status of the task by polling the task-status API
def check_task_status(task_id):
    response = requests.get(f"{TASK_STATUS_URL}{task_id}")
    if response.status_code == 200:
        task_info = response.json()
        if task_info["status"] == "Task in progress...":
            print(f"Task Progress: {task_info['current']} out of {task_info['total']}, Latest result: {task_info['result']}")
        elif task_info["status"] == "Task completed!":
            print(f"Task Completed! Final result: {task_info['final_result']}")
            return True
        else:
            print(f"Task Status: {task_info['status']}")
    else:
        print("Failed to get the task status")
    
    return False

# Main function to start the task and poll the status
def main():
    n = 100  # Number of iterations for the task
    task_id = start_task(n)
    
    if task_id:
        task_completed = False
        while not task_completed:
            time.sleep(5)  # Wait for 5 seconds before checking the status again
            task_completed = check_task_status(task_id)

if __name__ == "__main__":
    main()

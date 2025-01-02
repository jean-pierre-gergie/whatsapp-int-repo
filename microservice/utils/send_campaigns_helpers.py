from pymongo import MongoClient
import logging 
from celery.utils.log import get_task_logger
import json 
from datetime import datetime
import requests
import time 
from bson import ObjectId
from logger_setup.logger_setup import celery_logger


logger = celery_logger

logger.setLevel(logging.DEBUG)


def get_mongo_client(mongo_url):
    """
    Establish a connection to MongoDB using the provided MongoDB URI.
    
    Args:
        mongo_url (str): The MongoDB URI/URL for connecting to the MongoDB instance.
    
    Returns:
        MongoClient: A MongoClient instance that can be used to interact with the MongoDB database.
    
    Raises:
        Exception: Logs and raises an exception if the connection fails.
    """
    logger.debug(f"Connecting to MongoDB with URI: {mongo_url}")
    return MongoClient(mongo_url)

def get_member_list(mongo_db,selected_campaign):
    members_collection = mongo_db.members
    members = list(members_collection.find({"tag": selected_campaign}))
    members = [{key: value for key, value in member.items() if key != '_id'} for member in members]
    return members


def get_template_json(template_json):
    """
    Parse a JSON string into a dictionary, and handle any JSONDecodeError.
    
    Args:
        template_json (str): The JSON string to parse.
    
    Returns:
        dict: A dictionary containing parsing results.
    """
    try:
        template_dict = json.loads(template_json)
        logger.debug("Template JSON successfully parsed into a dictionary")
        return template_dict  # You can adjust what to return on success based on your needs.
    
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
    

def manage_campaign_data(campaign_data_progess, final_campaign_response_collection,campaign_id=None, action="insert"):
    """
    Manages MongoDB operations for inserting or updating campaign data.

    Parameters:
    - campaign_data: The initial or update data to be inserted/updated.
    - final_campaign_response_collection: MongoDB collection object.
    - action: Either 'insert' for inserting new data or 'update' for updating existing data.
    - campaign_id: The campaign ID for updating (only required for 'update' action).
    - number: Member number (for logging purposes, required for 'update').
    - success_rows: List of successful rows (for counting in the 'update' action).
    - failed_rows: List of failed rows (for counting in the 'update' action).
    """
    logger.debug(f"progress updating function campaign id   : {campaign_id}")
    logger.debug(f"progress updating function  action : {action}")
    logger.debug(f"progress updating function  payload : {campaign_data_progess}")

    try:
        campaign_id = ObjectId(campaign_id)
        logger.debug("reformated  the ID to object")
    except Exception as e:
        logging.error(f"Invalid campaign_id format: {e}")
        return


    if action == "insert":
        try:
            # Insert the initial campaign data
            campaign_id = final_campaign_response_collection.insert_one(campaign_data_progess).inserted_id
            logging.debug(f"Initial campaign data inserted with ID: {campaign_id}")
            return campaign_id
        except Exception as e:
            logging.error(f"Error inserting initial campaign data into MongoDB: {e}")
            return None

    elif action == "update":

        doc = final_campaign_response_collection.find_one({'_id': campaign_id})

        if not doc:
            logging.error(f"No document found with campaign_id: {campaign_id}")
            return
        

        if campaign_id is None:
            logging.error("Campaign ID must be provided for the update action.")
            return

        try:
            # Update the campaign progress
            final_campaign_response_collection.update_one(
                {'_id': campaign_id},
                {'$set': campaign_data_progess}
            )
            logging.debug(f"Campaign progress updated for campaign {campaign_id} with {campaign_data_progess} ")
        except Exception as e:
            logging.error(f"Error updating campaign progress in MongoDB: {e}")

def get_member_data(member, variables):
    """
    Generates a dictionary of member data based on the given variables.

    Parameters:
    - member: A dictionary containing member information.
    - variables: A list of variables (keys) to extract from the member dictionary.

    Returns:
    - A dictionary containing the member data.
    """
    member_data = {column: member.get(column, '') for column in variables}
    logging.debug(f"Member data: {member_data}")
    return member_data


def update_template_components(template_dict, member_data, variables, media_id=None, media_type=None, logger=None):
    """
    Updates the components of the template based on member data, variables, and media type/ID.

    Parameters:
    - template_dict: The dictionary containing the template information.
    - member_data: A dictionary containing member-specific data.
    - variables: A list of variable names to map to the template parameters.
    - media_id: The media ID to be used for updating header components (optional).
    - media_type: The type of media ('image', 'video', etc.) for the header (optional).
    - logger: Logger for debugging (optional).

    Returns:
    - The updated template dictionary.
    """
    # Ensure components array exists
    if "components" not in template_dict.get("template", {}):
        template_dict["template"]["components"] = []

    for component in template_dict["template"]["components"]:
        if component["type"].lower() == "body":
            # Update body text parameters
            for i, parameter in enumerate(component.get("parameters", [])):
                if parameter["type"] == "text" and i < len(variables):
                    parameter["text"] = str(member_data.get(variables[i], f"Variable_{i+1}"))

        elif component["type"].lower() == "header":
            if media_id and media_type == "video":
                # Update header component for video with media_id
                component["parameters"] = [
                    {
                        "type": "video",
                        "video": {"id": media_id}
                    }
                ]
            elif media_id and media_type == "image":
                # Update header component for image with media_id
                component["parameters"] = [
                    {
                        "type": "image",
                        "image": {"id": media_id}
                    }
                ]
            else:
                raise ValueError("Invalid or missing media_id and media_type for header component.")

    # Add header component if not present
    if not any(c["type"].lower() == "header" for c in template_dict["template"]["components"]):
        if media_type == "video" and media_id:
            template_dict["template"]["components"].append({
                "type": "header",
                "parameters": [
                    {
                        "type": "video",
                        "video": {"id": media_id}
                    }
                ]
            })
        elif media_type == "image" and media_id:
            template_dict["template"]["components"].append({
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {"id": media_id}
                    }
                ]
            })

    logger.debug(f"UPDATE FUNCTION : {template_dict}")
    return template_dict


def send_post_request(dialog_360_message_url, api_key_360, template_dict, number, failed_rows, start_time, logger):
    """
    Sends a POST request to the 360 Dialog API and handles response or errors.

    Parameters:
    - dialog_360_message_url: The URL for the 360 Dialog API.
    - api_key_360: The API key for authentication.
    - template_dict: The JSON payload to send in the POST request.
    - number: The phone number associated with the request (used for logging or error tracking).
    - failed_rows: A list to store information about failed requests.
    - start_time: The time when the request process started (for calculating response time).

    Returns:
    - response: The response object if the request was successful, None otherwise.
    - response_time: The time taken to receive the response.
    """
    headers = {"Content-Type": "application/json", "D360-API-KEY": api_key_360}
    response = None
    response_time = None

    try:
        # Send the POST request
        response = requests.post(dialog_360_message_url, headers=headers, json=template_dict)
        response_time = time.time() - start_time
        logger.debug(f"MICROSERVICE HELPER raw response {response}")
        logger.debug(f"MICROSERVICE HELPER Response received in {response_time:.2f} seconds with status code {response.status_code}")

        # Log the response content for debugging
        try:
            response_json = response.json()  # Attempt to parse JSON
            logger.debug(f"MICROSERVICE HELPER Response Content: {response_json}")
        except ValueError:
            logger.debug(f"MICROSERVICE HELPER Response Content (non-JSON): {response.text}")

        # If the response indicates an error, log it
        if response.status_code != 200:
            logger.error(f"MICROSERVICE HELPER API Error - Status Code: {response.status_code}, Content: {response.text}")
            failed_rows.append({
                'Number': number,
                'Title': f'HTTP {response.status_code}',
                'Details': response.text,
                'Code': response.status_code,
                'TimeTaken': response_time
            })
    except requests.RequestException as e:
        # Log the error and append to failed rows
        response_time = time.time() - start_time
        logger.error(f"MICROSERVICE HELPER Request failed: {e}")
        failed_rows.append({
            'Number': number,
            'Title': 'Request Error',
            'Details': str(e),
            'Code': 'N/A',
            'TimeTaken': response_time
        })

    return response, response_time

def insert_message_response(campaign_responses_collection, data_to_insert):
    """
    Inserts an individual message response into MongoDB.

    Parameters:
    - campaign_responses_collection: MongoDB collection where responses are stored.
    - campaign: The campaign identifier.
    - campaign_name: Name of the campaign.
    - number: The member's number.
    - template_dict: The template data used for the message.
    - response: The response object from the request.
    - response_time: The time taken for the request to complete.
    """


    try:
        # Insert the response into MongoDB
        campaign_responses_collection.insert_one(data_to_insert)
        logging.debug("Individual message response inserted successfully into MongoDB")
    except Exception as e:
        logging.error(f"Error inserting individual message response into MongoDB: {e}")



def process_response(response, number, response_time, success_rows, failed_rows):
    """
    Processes the API response and appends results to success or failed rows.

    Parameters:
    - response: The HTTP response object from the API request.
    - number: The phone number associated with the response.
    - response_time: The time taken to get the response.
    - success_rows: A list to store information for successful requests.
    - failed_rows: A list to store information for failed requests.
    """
    if response.status_code == 200:
        try:
            # Try to parse the successful JSON response
            response_json = response.json()
            for contact, message in zip(response_json.get('contacts', []), response_json.get('messages', [])):
                success_rows.append({
                    'Number': contact.get('input', 'N/A'),
                    'MessageID': message.get('id', 'N/A'),
                    'MessageStatus': message.get('message_status', 'N/A'),
                    'TimeTaken': response_time
                })
        except json.JSONDecodeError:
            # Handle case when the response is not valid JSON
            failed_rows.append({
                'Number': number,
                'Title': 'Error',
                'Details': 'Invalid JSON response',
                'Code': response.status_code,
                'TimeTaken': response_time
            })
    else:
        try:
            # Try to parse the error message from the response
            error_message = response.json().get("error", {}).get("message", "N/A")
            error_code = response.json().get("error", {}).get("code", "N/A")
        except (json.JSONDecodeError, KeyError):
            # If the response body cannot be parsed, fallback to plain text
            error_message = response.text
            error_code = response.status_code
        
        # Append the error details to failed_rows
        failed_rows.append({
            'Number': number,
            'Title': 'Error',
            'Details': error_message,
            'Code': error_code,
            'TimeTaken': response_time
        })

    logging.debug(f"Processed response for number {number}. Success rows: {len(success_rows)}, Failed rows: {len(failed_rows)}")

def update_final_campaign_data(campaign_id, final_campaign_response_collection, final_update,success_rows_len,failed_rows_len):
    """
    Updates the final campaign data in MongoDB once the campaign is finished.

    Parameters:
    - campaign_id: The ID of the campaign to update.
    - final_campaign_response_collection: The MongoDB collection where the final campaign response is stored.
    - success_rows: List of successful message records.
    - failed_rows: List of failed message records.
    - total_members: Total number of members involved in the campaign.
    """
    # Prepare the final update data
    
    try:
        campaign_id = ObjectId(campaign_id)
        logger.debug("reformated  the ID to object")
    except Exception as e:
        logging.error(f"Invalid campaign_id format: {e}")
        return

    try:
        # Update the final campaign data in MongoDB
        final_campaign_response_collection.update_one(
            {'_id': campaign_id},
            {'$set': final_update}
        )
        logging.debug(f"Final campaign data updated successfully. Status: Finished. Success: {success_rows_len}, Failed: {failed_rows_len}")
    except Exception as e:
        logging.error(f"Error updating final campaign data in MongoDB: {e}")
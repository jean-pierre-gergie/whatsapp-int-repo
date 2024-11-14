import os
from google.cloud import dialogflowcx_v3beta1 as dialogflowcx
import uuid



class dialogflowHandler():
    def __init__(self,project_id,location_id,agent_id) :
        self.project_id =project_id
        self.location_id = location_id
        self.agent_id = agent_id

    
    def detect_intent_texts(self,text, session_id=str(uuid.uuid4())):
        # Specify the regional endpoint for us-central1
        client_options = {"api_endpoint": f"{self.location_id}-dialogflow.googleapis.com"}
        
        # Initialize the session client with the correct endpoint
        session_client = dialogflowcx.SessionsClient(client_options=client_options)
        session_path = session_client.session_path(self.project_id, self.location_id, self.agent_id, session_id)

        # Prepare the text input and query
        text_input = dialogflowcx.TextInput(text=text)
        query_input = dialogflowcx.QueryInput(text=text_input, language_code="en")

        # Send the query to Dialogflow CX
        response = session_client.detect_intent(request={"session": session_path, "query_input": query_input})
        return response.query_result.response_messages[0].text.text
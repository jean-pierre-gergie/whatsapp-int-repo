import socketio
import logging

# Set up logging to see debug outputs
logging.basicConfig(level=logging.DEBUG)

# Initialize the Socket.IO client without any authentication
sio = socketio.Client()

# Define event handlers
@sio.event
def connect():
    print("Connected to the server (unexpected success without token).")

@sio.event
def connect_error(data):
    print("Connection failed:", data)

@sio.event
def connect_ack(data):
    print("Acknowledged connection:", data)

@sio.event
def disconnect():
    print("Disconnected from the server.")


# token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTczMDcwODQyNiwianRpIjoiOWVjMWRhMmEtMjg4Ni00YzM4LWJmZDgtMDA5YjU3MWY1ZTFiIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6eyJ1c2VybmFtZSI6ImpwZ2VyZ2llIiwicm9sZSI6ImFkbWluIn0sIm5iZiI6MTczMDcwODQyNiwiY3NyZiI6IjAyODk1MmZkLTBmMWUtNGUzYS04MGRkLTFkY2I0MWNiNDRiYSIsImV4cCI6MTczMDcxMjAyNn0.Ju732cu67RvaYF5AKq-Zz5L66-F1jqmZ3gKq4QrW8Jg"

token ="ioi"

# Attempt to connect to the namespace without a token
try:
    sio.connect(
        'http://localhost:5001/agent/agent_namespace', 
        namespaces=['/agent/agent_namespace'],
        transports=['websocket', 'polling'],
        auth={'token': token}  # Pass the token here
    )
    sio.wait()  # Wait to keep the connection open and listen for events
except Exception as e:
    print("Exception occurred during connection attempt:", e)
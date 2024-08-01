import requests

def call_webhook_server():
    # Define the IP address and route
    ip_address = "34.133.93.255"
    route = "/"

    # Construct the URL
    url = f"http://{ip_address}{route}"

    try:
        # Make a GET request to the server
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            print("Server Response:", response.text)
        else:
            print("Failed to reach the server. Status code:", response.status_code)
    except requests.RequestException as e:
        print("Error occurred while making the request:", str(e))

if __name__ == "__main__":
    call_webhook_server()
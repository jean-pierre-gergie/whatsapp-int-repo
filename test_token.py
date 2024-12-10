import requests
import json

url = "https://hub.360dialog.io/api/v2/token"

payload = json.dumps({
  "username": "rtenn@mymada.com",
  "password": "@cce$$-APP23"
})
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
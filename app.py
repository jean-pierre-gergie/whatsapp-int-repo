import os
from flask import Flask, request, jsonify
import requests
import pandas as pd
from datetime import datetime
import json




from dotenv import load_dotenv

load_dotenv()



apiKey = "Pz1wL6a3xzRiJy3UjYMLjEIXAK"

autoReplyMessage = "صباح الخير. للاستفسار يرجى الاتصال من الإثنين حتى الجمعة من الساعة التاسعة صباحا حتى الساعة الخامسة بعد الظهر على الرقم التالي 453444-05 أو ارسال رسالة خطية (WhatsApp) على الرقم 077082-03. شكراً لتواصلكم معنا."

app = Flask(__name__)



# def get_today_iso_format():
#     return datetime.now().strftime('%Y-%m-%d')

# current_date = get_today_iso_format()
# csv_primary_file = f'webhook_logs_{current_date}.csv'

# def create_csv_writer_for_date(date):
#     return pd.DataFrame(columns=[
#         'Status ID', 'Status', 'Timestamp', 'Recipient ID',
#         'Conversation ID', 'Origin Type', 'Phone Number',
#         'Message Type', 'Message Body', 'Contact Name'
#     ])

# csv_writer = create_csv_writer_for_date(current_date)


# def rotate_log_file():
#     global current_date, csv_writer
#     new_date = get_today_iso_format()
#     if new_date != current_date:
#         current_date = new_date
#         csv_writer = create_csv_writer_for_date(current_date)
#         print(f"Log file rotated to webhook_logs_{current_date}.csv")


# write_queue = []


# def process_queue():
#     global csv_writer
#     if not write_queue:
#         return
    
#     record = write_queue.pop(0)
#     csv_writer = pd.concat([csv_writer, pd.DataFrame([record])])
#     csv_writer.to_csv(csv_primary_file, mode='a', index=False, header=False)
#     print('Record appended to primary CSV log')


# def contains_arabic(text):
#     return any('\u0600' <= c <= '\u06FF' for c in text)


# def fetch_media_url(media_id):
#     url = f'https://waba-v2.360dialog.io/{media_id}'
#     headers = {
#         "Content-Type": "application/json",
#         "D360-API-KEY": apiKey
#     }
    
#     try:
#         response = requests.get(url, headers=headers)
#         response.raise_for_status()
#         return response.json()
#     except requests.RequestException as error:
#         print(f'Error fetching media URL: {error}')
#         return None


# def download_media_file(media_url, filename):
#     download_dir = 'C:\\Users\\admn-rtenn\\Desktop\\webhook\\media'
#     os.makedirs(download_dir, exist_ok=True)
#     file_path = os.path.join(download_dir, filename)
    
#     headers = {
#         "D360-API-KEY": apiKey
#     }
    
#     try:
#         response = requests.get(media_url, headers=headers, stream=True)
#         response.raise_for_status()
        
#         with open(file_path, 'wb') as file:
#             for chunk in response.iter_content(1024):
#                 file.write(chunk)
        
#         print(f'Downloaded media file: {filename}')
#     except requests.RequestException as error:
#         print(f'Error downloading media file: {error}')


# def send_auto_reply(recipient_id, message_text):
#     url = 'https://waba-v2.360dialog.io/messages'
#     headers = {
#         "Content-Type": "application/json",
#         "D360-API-KEY": apiKey
#     }
    
#     data = {
#         "recipient_type": "individual",
#         "to": recipient_id,
#         "messaging_product": "whatsapp",
#         "type": "text",
#         "text": {
#             "body": message_text
#         }
#     }
    
#     try:
#         response = requests.post(url, headers=headers, json=data)
#         response.raise_for_status()
#         print('Auto-reply sent:', response.json())
#     except requests.RequestException as error:
#         print(f'Error sending auto-reply: {error}')


@app.route('/', methods=['GET'])
def index():
    return 'Webhook server is running'

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     print('Received webhook data:', json.dumps(request.json, indent=2, ensure_ascii=False))
    
#     try:
#         # Process the message and add to queue
#         if 'entry' in request.json and request.json['entry']:
#             for entry in request.json['entry']:
#                 if 'changes' in entry and entry['changes']:
#                     for change in entry['changes']:
#                         if change['field'] == 'messages':
#                             if 'messages' in change['value'] and change['value']['messages']:
#                                 for message in change['value']['messages']:
#                                     message_type = message.get('type', 'unknown')

#                                     if message_type in ['audio', 'image']:
#                                         media_id = message.get('audio', {}).get('id') if message_type == 'audio' else message.get('image', {}).get('id')
#                                         media_info = fetch_media_url(media_id)
#                                         if media_info and 'url' in media_info:
#                                             media_url = media_info['url'].replace('https://lookaside.fbsbx.com', 'https://waba-v2.360dialog.io')
#                                             contact_name = change['value'].get('contacts', [{}])[0].get('profile', {}).get('name', 'unknown')

#                                             record = {
#                                                 'Status ID': message['id'],
#                                                 'Status': 'received',
#                                                 'Timestamp': datetime.fromtimestamp(int(message['timestamp'])).strftime('%Y-%m-%d %H:%M:%S'),
#                                                 'Recipient ID': message['from'],
#                                                 'Conversation ID': entry['id'],
#                                                 'Origin Type': change['value'].get('metadata', {}).get('origin', {}).get('type', 'unknown'),
#                                                 'Phone Number': change['value']['metadata']['display_phone_number'],
#                                                 'Message Type': message_type,
#                                                 'Message Body': media_url,
#                                                 'Contact Name': contact_name
#                                             }

#                                             write_queue.append(record)
#                                             process_queue()  # Process the queue

#                                             # Download the media file
#                                             file_extension = 'ogg' if message_type == 'audio' else 'jpg'
#                                             filename = f'{media_id}.{file_extension}'
#                                             download_media_file(media_url, filename)

#                                             # Send auto-reply
#                                             print('Sending auto-reply to:', message['from'])
#                                             send_auto_reply(message['from'], autoReplyMessage)
#                                     else:
#                                         message_body = message['text']['body'] if message_type == 'text' else json.dumps(message)
#                                         contact_name = change['value'].get('contacts', [{}])[0].get('profile', {}).get('name', 'unknown')

#                                         record = {
#                                             'Status ID': message['id'],
#                                             'Status': 'received',
#                                             'Timestamp': datetime.fromtimestamp(int(message['timestamp'])).strftime('%Y-%m-%d %H:%M:%S'),
#                                             'Recipient ID': message['from'],
#                                             'Conversation ID': entry['id'],
#                                             'Origin Type': change['value'].get('metadata', {}).get('origin', {}).get('type', 'unknown'),
#                                             'Phone Number': change['value']['metadata']['display_phone_number'],
#                                             'Message Type': message_type,
#                                             'Message Body': message_body if contains_arabic(message_body) else json.dumps(message_body),
#                                             'Contact Name': contact_name
#                                         }

#                                         write_queue.append(record)
#                                         process_queue()  # Process the queue

#                                         # Send auto-reply
#                                         print('Sending auto-reply to:', message['from'])
#                                         send_auto_reply(message['from'], autoReplyMessage)

#                             if 'statuses' in change['value'] and change['value']['statuses']:
#                                 for status in change['value']['statuses']:
#                                     record = {
#                                         'Status ID': status['id'],
#                                         'Status': status['status'],
#                                         'Timestamp': datetime.fromtimestamp(int(status['timestamp'])).strftime('%Y-%m-%d %H:%M:%S'),
#                                         'Recipient ID': status['recipient_id'],
#                                         'Conversation ID': status.get('conversation', {}).get('id', 'unknown'),
#                                         'Origin Type': status.get('conversation', {}).get('origin', {}).get('type', 'unknown'),
#                                         'Phone Number': change['value']['metadata']['display_phone_number'],
#                                         'Message Type': 'status',
#                                         'Message Body': json.dumps(status),
#                                         'Contact Name': 'N/A'
#                                     }

#                                     write_queue.append(record)
#                                     process_queue()  # Process the queue
#         else:
#             print('No valid entries found in webhook data:', request.json)
        
#         return 'Message received', 200
#     except Exception as error:
#         print(f'Error processing webhook data: {error}')
#         return 'Error processing webhook data', 500
    
if __name__ == '__main__':
    app.run (host='0.0.0.0',port=3000)
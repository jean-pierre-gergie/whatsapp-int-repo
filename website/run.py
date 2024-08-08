from app import create_app
from flask import request
import threading
from app.utils.template_updater import start_template_updater
app = create_app()

@app.before_request
def before_request():
    token = request.cookies.get('access_token_cookie')
    if token:
        request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {token}'

if __name__ == '__main__':
    template_updater_thread = threading.Thread(target=start_template_updater ,  args=(app,))
    template_updater_thread.daemon = True 
    template_updater_thread.start()
    app.run(host="0.0.0.0",debug=True, port=1313)
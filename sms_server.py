import os
import json
import datetime
import psycopg2
import redis
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_FILE = os.path.expanduser('~/sms_gateway_config.json')

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    LOG_FILE = config.get('log_file', 'sms_log.txt')
except FileNotFoundError:
    LOG_FILE = 'sms_log.txt'
except json.JSONDecodeError:
    LOG_FILE = 'sms_log.txt'

# Load secrets from environment with fallback to config.json
CF_BACKEND_URL = os.getenv('CF_BACKEND_URL', config.get('cf_endpoint', 'https://default-url-if-not-set'))
API_KEY = os.getenv('CF_API_KEY', config.get('cf_api_key', ''))
if not API_KEY:
    print("Warning: API key not set.")

POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'sms_gateway'),
    'user': os.getenv('POSTGRES_USER', 'sms_user'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
}

REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'password': os.getenv('REDIS_PASSWORD', None),
    'db': 0,
}

pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
pg_conn.autocommit = True

redis_client = redis.StrictRedis(
    host=REDIS_CONFIG['host'],
    port=REDIS_CONFIG['port'],
    password=REDIS_CONFIG['password'],
    db=REDIS_CONFIG['db'],
)

class SMSHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        sms_raw = self.rfile.read(content_length).decode('utf-8')

        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] {sms_raw}\n")

        try:
            if sms_raw.strip().startswith('{'):
                sms_data = json.loads(sms_raw)
            else:
                sender, message = (sms_raw.split(':', 1) + [""])[:2]
                sms_data = {
                    'sender': sender.strip() or "Unknown",
                    'message': message.strip(),
                    'timestamp': datetime.datetime.now().isoformat(),
                }
        except Exception as e:
            print(f"[Error] Parsing SMS failed: {e}")
            self.send_response(400)
            self.end_headers()
            return

        sender = sms_data['sender']
        cursor = pg_conn.cursor()

        try:
            sender_exists = redis_client.exists(sender)
            if not sender_exists:
                cursor.execute("SELECT 1 FROM sms_senders WHERE sender = %s LIMIT 1;", (sender,))
                if cursor.fetchone() is None:
                    cursor.execute("INSERT INTO sms_senders (sender) VALUES (%s);", (sender,))
                redis_client.set(sender, 1)

            forwarded = not sender_exists

            cursor.execute("""
                INSERT INTO sms_messages (sender, message, forwarded)
                VALUES (%s, %s, %s);
            """, (sender, sms_data.get('message', ''), forwarded))
        except Exception as e:
            print(f"[Error] DB operation failed: {e}")
            self.send_response(500)
            self.end_headers()
            cursor.close()
            return
        cursor.close()

        if forwarded:
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {API_KEY}'
                }
                response = requests.post(CF_BACKEND_URL, json=sms_data, headers=headers, timeout=5)
                print(f"Forwarded SMS from {sender}, status: {response.status_code}")
            except Exception as e:
                print(f"[Warning] Forwarding to CF backend failed: {e}")

        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    PORT = int(os.getenv('PYTHON_RECEIVER_PORT', 8080))
    print(f"Starting SMS receiver on port {PORT}...")
    print(f"Forwarding to CF backend: {CF_BACKEND_URL}")
    print(f"Logging SMS to: {LOG_FILE}")
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, SMSHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped by user.")

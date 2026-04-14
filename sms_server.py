from flask import Flask, request, jsonify
import sys
import os
import time

# Ensure we can import modules from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from modem_client import ModemClient

app = Flask(__name__)


def parse_bool(value, default=False):
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"1", "true", "yes", "on", "sim"}


def parse_int(value, default):
    if value in (None, ""):
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default

@app.route('/send_sms', methods=['POST'])
def send_sms():
    data = request.json
    
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400
        
    number = data.get('number')
    message = data.get('message')
    
    if not number or not message:
        return jsonify({"error": "Missing 'number' or 'message' field"}), 400
        
    try:
        # Initialize client (uses config.py for credentials)
        client = ModemClient()
        
        # Attempt login
        if not client.login():
             return jsonify({"error": "Failed to login to modem"}), 500
        
        # Wait a bit to ensure session is active
        time.sleep(1)
        
        # Send SMS
        if client.send_sms(number, message):
            return jsonify({"status": "success", "message": "SMS sent successfully"}), 200
        else:
            return jsonify({"error": "Failed to send SMS via modem"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/inbox_sms', methods=['GET', 'POST'])
def inbox_sms():
    data = request.json if request.method == 'POST' else request.args
    data = data or {}

    limit = parse_int(data.get('limit'), 10)
    unread_only = parse_bool(data.get('unread_only'), default=False)
    mark_read = parse_bool(data.get('mark_read'), default=False)

    try:
        client = ModemClient()

        if not client.login():
            return jsonify({"error": "Failed to login to modem"}), 500

        status = client.get_sms_device_status()
        if not status:
            return jsonify({"error": "Failed to read SMS device status"}), 500

        messages = client.list_sms_inbox(
            limit=limit,
            unread_only=unread_only,
            mark_read=mark_read,
            full_content=True,
        )
        if messages is None:
            return jsonify({"error": "Failed to read inbox SMS"}), 500

        return jsonify({
            "status": "success",
            "total_inbox_messages": status.get("inbox_used_count", 0),
            "returned_messages": len(messages),
            "messages": messages,
        }), 200
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    # Listen on all interfaces using the configured port.
    app.run(host='0.0.0.0', port=config.SMS_SERVER_PORT)

from flask import Flask, request, jsonify
import sys
import os
import time

# Ensure we can import modules from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modem_client import ModemClient

app = Flask(__name__)

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

if __name__ == '__main__':
    # Listen on all interfaces on port 5000 (or regular Flask default)
    # Debug mode disabled for production-like usage, but helpful for dev
    app.run(host='0.0.0.0', port=5001)

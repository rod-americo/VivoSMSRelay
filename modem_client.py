import requests
import json
import time
import argparse
import sys
if __name__ == "__main__" and __package__ is None:
    # Hack to allow relative import if run as script
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from modem_crypto import ModemCrypto
    import config
else:
    from .modem_crypto import ModemCrypto
    from . import config

class ModemClient:
    def __init__(self, username=None, password=None, password_hash=None):
        self.BASE_URL = config.MODEM_URL
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'json',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        # Use args if provided, else config defaults
        self.username = username if username else config.MODEM_USER
        
        # Priority: explicit hash -> explicit password -> config hash -> config password
        if password_hash:
            self.password_hash = password_hash
        elif password:
            self.password_hash = ModemCrypto.encode_pw(password)
        elif config.MODEM_HASH:
            self.password_hash = config.MODEM_HASH
        elif config.MODEM_PASS:
            self.password_hash = ModemCrypto.encode_pw(config.MODEM_PASS)
        else:
            raise ValueError("No password provided in args or config")

    def login(self):
        url = f"{self.BASE_URL}/cgi-bin/login.cgi"
        
        # 1. Check if login valid (optional but good practice as observed in flow)
        payload_check = {"action": "get_web_user_login_valid", "args": {}}
        try:
            r = self.session.post(url, json=payload_check, timeout=5)
        except Exception as e:
            print(f"Warning: Initial check failed: {e}")

        # 2. Perform Login
        payload_login = {
            "action": "set_web_user_login",
            "args": {
                "user": self.username,
                "password": self.password_hash
            }
        }
        
        print(f"Logando como {self.username}...")
        r = self.session.post(url, json=payload_login, timeout=10)
        
        if r.status_code == 200:
            return True
        else:
            print(f"Falha no Login via HTTP {r.status_code}: {r.text}")
            return False

    def send_sms(self, number, content):
        url = f"{self.BASE_URL}/cgi-bin/gui.cgi"
        
        payload = {
            "action": "set_sms_send",
            "args": {
                "sendto": [{"number": number}],
                "content": content
            }
        }
        
        print(f"Enviando SMS para {number}...")
        r = self.session.post(url, json=payload, timeout=10)
        
        if r.status_code == 200:
            try:
                resp = r.json()
                # Check for success in send_report
                # Structure: { "set_sms_send": { "send_report": [ { "send_success": true } ] } }
                if resp.get("set_sms_send", {}).get("send_report", [{}])[0].get("send_success"):
                    print("SMS enviado com sucesso!")
                    return True
                else:
                    print(f"Erro ao enviar SMS: {r.text}")
                    return False
            except:
                print(f"Erro ao analisar resposta: {r.text}")
                return False
        else:
            print(f"Falha no envio via HTTP {r.status_code}: {r.text}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send SMS via Vivo Modem")
    parser.add_argument("number", help="Phone number to send to")
    parser.add_argument("message", help="Message content")
    parser.add_argument("--user", default="admin", help="Modem username (default: admin)")
    parser.add_argument("--password", help="Modem password (raw)")
    parser.add_argument("--hash", help="Modem password hash (optional overflow)")
    
    args = parser.parse_args()
    
    # Default stored password if nothing provided
    DEFAULT_PASS = "Q7fR9xL2M6ZKp8dS"
    
    pwd = args.password
    pwd_hash = args.hash
    
    if not pwd and not pwd_hash:
        pwd = DEFAULT_PASS
        # print(f"Using default password: {DEFAULT_PASS}")
    
    client = ModemClient(username=args.user, password=pwd, password_hash=pwd_hash)
    if client.login():
        time.sleep(1) 
        client.send_sms(args.number, args.message)
    else:
        print("Could not log in.")
        sys.exit(1)

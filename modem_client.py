import requests
import json
import time
import argparse
import sys

# Tenta importar ModemCrypto e config.
# O bloco if/else permite que o script seja executado tanto como módulo quanto como script standalone.
if __name__ == "__main__" and __package__ is None:
    # Hack para permitir importação relativa se rodado diretamente como script
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from modem_crypto import ModemCrypto
    import config
else:
    from .modem_crypto import ModemCrypto
    from . import config

class ModemClient:
    """
    Cliente para interação com a API web do Modem Vivo (ZTE).
    Gerencia autenticação (login) e envio de comandos (SMS).
    """

    def __init__(self, username=None, password=None, password_hash=None):
        self.BASE_URL = config.MODEM_URL
        
        self.session = requests.Session()
        # Headers simulando um navegador real, necessários para que o modem aceite as requisições
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'json',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        # Usa argumentos se fornecidos, senão usa os defaults do config
        self.username = username if username else config.MODEM_USER
        
        # Lógica de prioridade para a senha/hash:
        # 1. Hash explícito via argumento
        # 2. Senha explícita via argumento (será calculado o hash)
        # 3. Hash do config (.env)
        # 4. Senha do config (.env)
        if password_hash:
            self.password_hash = password_hash
        elif password:
            self.password_hash = ModemCrypto.encode_pw(password)
        elif config.MODEM_HASH:
            self.password_hash = config.MODEM_HASH
        elif config.MODEM_PASS:
            self.password_hash = ModemCrypto.encode_pw(config.MODEM_PASS)
        else:
            raise ValueError("Nenhuma senha ou hash fornecido nos argumentos ou configuração")

    def login(self):
        """Realiza o login no modem usando o hash da senha."""
        url = f"{self.BASE_URL}/cgi-bin/login.cgi"
        
        # 1. Verifica se o login já é válido ou inicializa sessão (opcional, mas recomendado)
        payload_check = {"action": "get_web_user_login_valid", "args": {}}
        try:
            r = self.session.post(url, json=payload_check, timeout=5)
        except Exception as e:
            print(f"Aviso: Verificação inicial falhou: {e}")

        # 2. Executa o Login
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
        """Envia um SMS para o número especificado."""
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
                # Verifica sucesso no relatório de envio dentro da resposta JSON
                # Estrutura esperada: { "set_sms_send": { "send_report": [ { "send_success": true } ] } }
                if resp.get("set_sms_send", {}).get("send_report", [{}])[0].get("send_success"):
                    print("SMS enviado com sucesso!")
                    return True
                else:
                    print(f"Erro ao enviar SMS (resposta negativa do modem): {r.text}")
                    return False
            except:
                print(f"Erro ao analisar resposta do modem: {r.text}")
                return False
        else:
            print(f"Falha no envio via HTTP {r.status_code}: {r.text}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enviar SMS via Modem Vivo (ZTE)")
    parser.add_argument("number", help="Número de telefone destinatário")
    parser.add_argument("message", help="Conteúdo da mensagem")
    parser.add_argument("--user", help="Usuário do modem (sobrescreve config)")
    parser.add_argument("--password", help="Senha do modem (texto plano)")
    parser.add_argument("--hash", help="Hash da senha do modem (opcional)")
    
    args = parser.parse_args()
    
    # Defaults de senha tratados na classe ModemClient baseados em config
    
    client = ModemClient(username=args.user, password=args.password, password_hash=args.hash)
    if client.login():
        time.sleep(1) # Pequena pausa para garantir que a sessão foi estabelecida
        client.send_sms(args.number, args.message)
    else:
        print("Não foi possível logar.")
        sys.exit(1)

import requests
import json
import time
import argparse
import sys

# Tenta importar ModemCrypto e config.
# O bloco if/else permite que o script seja executado tanto como módulo quanto como script standalone.
if __name__ == "__main__" or not __package__:
    # Hack para permitir importação relativa se rodado diretamente como script ou modulo top-level
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

    def _post_json(self, path, payload, timeout=10):
        """Executa um POST JSON e retorna a resposta decodificada."""
        url = f"{self.BASE_URL}{path}"
        r = self.session.post(url, json=payload, timeout=timeout)

        if r.status_code != 200:
            raise RuntimeError(f"Falha HTTP {r.status_code}: {r.text}")

        try:
            return r.json()
        except ValueError as exc:
            raise RuntimeError(f"Resposta JSON inválida: {r.text}") from exc

    def _gui_action(self, action, args=None, timeout=10):
        """Dispara uma ação em gui.cgi."""
        payload = {
            "action": action,
            "args": args or {},
        }
        return self._post_json("/cgi-bin/gui.cgi", payload, timeout=timeout)

    @staticmethod
    def normalize_sms_record(record):
        """Normaliza o formato das mensagens para uso externo."""
        return {
            "idx": record.get("idx"),
            "number": record.get("number", ""),
            "time": record.get("time", ""),
            "content": record.get("content", ""),
            "unread": bool(record.get("new_sms")),
        }

    def send_sms(self, number, content):
        """Envia um SMS para o número especificado."""
        print(f"Enviando SMS para {number}...")
        try:
            resp = self._gui_action(
                "set_sms_send",
                {
                    "sendto": [{"number": number}],
                    "content": content,
                },
            )
            # Estrutura esperada: { "set_sms_send": { "send_report": [ { "send_success": true } ] } }
            if resp.get("set_sms_send", {}).get("send_report", [{}])[0].get("send_success"):
                print("SMS enviado com sucesso!")
                return True

            print(f"Erro ao enviar SMS (resposta negativa do modem): {json.dumps(resp)}")
            return False
        except Exception as e:
            print(f"Falha no envio: {e}")
            return False

    def get_sms_device_status(self):
        """Obtém a ocupação atual das caixas de SMS do modem."""
        try:
            resp = self._gui_action("get_sms_device_status")
            status = resp.get("get_sms_device_status")
            if status and status.get("errno") == 0:
                return status

            print(f"Resposta inesperada da API (get_sms_device_status): {resp}")
            return None
        except Exception as e:
            print(f"Erro ao obter o status de SMS: {e}")
            return None

    def get_sms_inbox_records(self, start=1, end=None, full_content=True):
        """Lê registros da inbox entre os índices informados."""
        if end is None:
            status = self.get_sms_device_status()
            if not status:
                return None
            end = status.get("inbox_used_count", 0)

        if end <= 0:
            return []

        start = max(1, int(start))
        end = int(end)
        if start > end:
            return []

        if end - start + 1 > 30:
            records = []
            chunk_start = start

            while chunk_start <= end:
                chunk_end = min(chunk_start + 29, end)
                chunk_records = self.get_sms_inbox_records(
                    start=chunk_start,
                    end=chunk_end,
                    full_content=False,
                )
                if chunk_records is None:
                    return None
                records.extend(chunk_records)
                chunk_start = chunk_end + 1

            records.sort(key=lambda record: int(record.get("idx") or 0), reverse=True)
            if full_content:
                return self._expand_inbox_records(records)
            return records

        request_full_content = bool(full_content and start == end)

        try:
            resp = self._gui_action(
                "get_sms_inbox_records",
                {
                    "full_content": request_full_content,
                    "start": start,
                    "end": end,
                },
            )
            inbox = resp.get("get_sms_inbox_records")
            if inbox and inbox.get("errno") == 0:
                records = inbox.get("records", [])
                if full_content and start != end:
                    return self._expand_inbox_records(records)
                return records

            print(f"Resposta inesperada da API (get_sms_inbox_records): {resp}")
            return None
        except Exception as e:
            print(f"Erro ao obter mensagens da inbox: {e}")
            return None

    def _expand_inbox_records(self, records):
        """Complementa uma lista da inbox buscando cada conteúdo completo pelo índice."""
        expanded_records = []

        for record in records:
            idx = record.get("idx")
            if idx is None:
                expanded_records.append(record)
                continue

            detailed_records = self.get_sms_inbox_records(start=idx, end=idx, full_content=True)
            if detailed_records:
                detailed_record = detailed_records[0]
                merged_record = dict(record)
                merged_record.update(detailed_record)
                expanded_records.append(merged_record)
            else:
                expanded_records.append(record)

        return expanded_records

    def get_sms_inbox_record(self, idx):
        """Obtém uma única mensagem da inbox pelo índice interno do modem."""
        records = self.get_sms_inbox_records(start=idx, end=idx, full_content=True)
        if records:
            return records[0]
        return None

    def set_sms_inbox_read(self, idx):
        """Marca uma mensagem da inbox como lida."""
        try:
            resp = self._gui_action("set_sms_inbox_read", {"idx": int(idx)})
            result = resp.get("set_sms_inbox_read")
            if result and result.get("errno") == 0:
                return True

            print(f"Resposta inesperada da API (set_sms_inbox_read): {resp}")
            return False
        except Exception as e:
            print(f"Erro ao marcar SMS como lido: {e}")
            return False

    def list_sms_inbox(self, limit=None, unread_only=False, mark_read=False, full_content=True):
        """Lista mensagens da inbox com filtros simples."""
        status = self.get_sms_device_status()
        if not status:
            return None

        total = status.get("inbox_used_count", 0)
        if total <= 0:
            return []

        if limit is None:
            limit = total
        else:
            limit = max(0, int(limit))

        if limit == 0:
            return []

        limit = min(limit, total)
        start = total - limit + 1
        records = self.get_sms_inbox_records(start=start, end=total, full_content=full_content)
        if records is None:
            return None

        if unread_only:
            records = [record for record in records if record.get("new_sms")]

        if mark_read:
            for record in records:
                if record.get("new_sms") and self.set_sms_inbox_read(record["idx"]):
                    record["new_sms"] = 0

        return [self.normalize_sms_record(record) for record in records]

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

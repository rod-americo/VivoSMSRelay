import argparse
import hashlib
import hmac
import html
import json
import os
import secrets
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

if __name__ == "__main__" or not __package__:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from modem_crypto import ModemCrypto
    import config
else:
    from .modem_crypto import ModemCrypto
    from . import config


class ModemApiError(RuntimeError):
    def __init__(self, code, message=""):
        self.code = str(code)
        self.message = message or ""
        super().__init__(f"Erro da API do modem {self.code}: {self.message}")


def _coerce_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _xml_text(value):
    if value is None:
        return ""
    return str(value)


def _dict_to_xml(root_name, data):
    root = ET.Element(root_name)
    _append_xml_children(root, data)
    return '<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(
        root, encoding="unicode"
    )


def _append_xml_children(parent, data):
    for key, value in data.items():
        if isinstance(value, list):
            container = ET.SubElement(parent, key)
            singular = key[:-1] if key.endswith("s") else "Item"
            for item in value:
                child = ET.SubElement(container, singular)
                if isinstance(item, dict):
                    _append_xml_children(child, item)
                else:
                    child.text = _xml_text(item)
        elif isinstance(value, dict):
            child = ET.SubElement(parent, key)
            _append_xml_children(child, value)
        else:
            child = ET.SubElement(parent, key)
            child.text = _xml_text(value)


def _element_to_value(element):
    children = list(element)
    if not children:
        return html.unescape(element.text or "")

    result = {}
    for child in children:
        value = _element_to_value(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(value)
        else:
            result[child.tag] = value
    return result


def _parse_xml_response(text):
    root = ET.fromstring(text)
    data = _element_to_value(root)
    if root.tag == "error":
        raise ModemApiError(data.get("code", "unknown"), data.get("message", ""))
    if root.tag == "response":
        return data
    return {root.tag: data}


def _is_ok_response(response):
    return response == "OK" or (
        isinstance(response, dict) and response.get("response") == "OK"
    )


class BaseModemClient:
    driver = "base"

    def login(self):
        return True

    def send_sms(self, number, content):
        raise NotImplementedError

    def get_sms_device_status(self):
        raise NotImplementedError

    def get_sms_inbox_records(self, start=1, end=None, full_content=True):
        raise NotImplementedError

    def get_sms_inbox_record(self, idx):
        records = self.get_sms_inbox_records(start=1, end=100, full_content=True)
        if not records:
            return None
        for record in records:
            if str(record.get("idx")) == str(idx):
                return record
        return None

    def set_sms_inbox_read(self, idx):
        raise NotImplementedError

    def list_sms_inbox(self, limit=None, unread_only=False, mark_read=False, full_content=True):
        status = self.get_sms_device_status()
        if not status:
            return None

        total = _coerce_int(status.get("inbox_used_count"), 0)
        if total <= 0:
            return []

        if limit is None:
            limit = total
        else:
            limit = max(0, int(limit))

        if limit == 0:
            return []

        limit = min(limit, total)
        start = max(1, total - limit + 1)
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

    @staticmethod
    def normalize_sms_record(record):
        return {
            "idx": record.get("idx"),
            "number": record.get("number", ""),
            "time": record.get("time", ""),
            "content": record.get("content", ""),
            "unread": bool(record.get("new_sms")),
        }

    def get_stats(self):
        raise NotImplementedError

    def clear_stats(self):
        raise NotImplementedError


class ZteModemClient(BaseModemClient):
    """
    Cliente para modems Vivo/ZTE legados que expoem login.cgi/gui.cgi.
    """

    driver = "zte"

    def __init__(self, username=None, password=None, password_hash=None):
        self.BASE_URL = config.MODEM_URL
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Content-Type": "json",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        self.username = username if username else config.MODEM_USER

        if password_hash:
            self.password_hash = password_hash
        elif password:
            self.password_hash = ModemCrypto.encode_pw(password)
        elif config.MODEM_HASH:
            self.password_hash = config.MODEM_HASH
        elif config.MODEM_PASS:
            self.password_hash = ModemCrypto.encode_pw(config.MODEM_PASS)
        else:
            raise ValueError("Nenhuma senha ou hash fornecido nos argumentos ou configuracao")

    def login(self):
        url = f"{self.BASE_URL}/cgi-bin/login.cgi"
        payload_check = {"action": "get_web_user_login_valid", "args": {}}
        try:
            self.session.post(url, json=payload_check, timeout=5)
        except Exception as exc:
            print(f"Aviso: verificacao inicial falhou: {exc}")

        payload_login = {
            "action": "set_web_user_login",
            "args": {"user": self.username, "password": self.password_hash},
        }

        print(f"Logando como {self.username} no modem ZTE...")
        r = self.session.post(url, json=payload_login, timeout=10)

        if r.status_code == 200:
            return True

        print(f"Falha no login via HTTP {r.status_code}: {r.text}")
        return False

    def _post_json(self, path, payload, timeout=10):
        url = f"{self.BASE_URL}{path}"
        r = self.session.post(url, json=payload, timeout=timeout)

        if r.status_code != 200:
            raise RuntimeError(f"Falha HTTP {r.status_code}: {r.text}")

        try:
            return r.json()
        except ValueError as exc:
            raise RuntimeError(f"Resposta JSON invalida: {r.text}") from exc

    def _gui_action(self, action, args=None, timeout=10):
        return self._post_json(
            "/cgi-bin/gui.cgi",
            {
                "action": action,
                "args": args or {},
            },
            timeout=timeout,
        )

    def send_sms(self, number, content):
        print(f"Enviando SMS para {number}...")
        try:
            resp = self._gui_action(
                "set_sms_send",
                {"sendto": [{"number": number}], "content": content},
            )
            if resp.get("set_sms_send", {}).get("send_report", [{}])[0].get("send_success"):
                print("SMS enviado com sucesso.")
                return True

            print(f"Erro ao enviar SMS: {json.dumps(resp)}")
            return False
        except Exception as exc:
            print(f"Falha no envio: {exc}")
            return False

    def get_sms_device_status(self):
        try:
            resp = self._gui_action("get_sms_device_status")
            status = resp.get("get_sms_device_status")
            if status and status.get("errno") == 0:
                return status

            print(f"Resposta inesperada da API (get_sms_device_status): {resp}")
            return None
        except Exception as exc:
            print(f"Erro ao obter o status de SMS: {exc}")
            return None

    def get_sms_inbox_records(self, start=1, end=None, full_content=True):
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
        except Exception as exc:
            print(f"Erro ao obter mensagens da inbox: {exc}")
            return None

    def _expand_inbox_records(self, records):
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

    def set_sms_inbox_read(self, idx):
        try:
            resp = self._gui_action("set_sms_inbox_read", {"idx": int(idx)})
            result = resp.get("set_sms_inbox_read")
            if result and result.get("errno") == 0:
                return True

            print(f"Resposta inesperada da API (set_sms_inbox_read): {resp}")
            return False
        except Exception as exc:
            print(f"Erro ao marcar SMS como lido: {exc}")
            return False

    def get_stats(self):
        try:
            resp = self._gui_action("get_wwan_total_network_stats")
            stats = resp.get("get_wwan_total_network_stats")
            if stats:
                return stats
            print("Resposta inesperada da API (get_stats):", resp)
            return None
        except Exception as exc:
            print(f"Erro ao buscar estatisticas: {exc}")
            return None

    def clear_stats(self):
        try:
            resp = self._gui_action("set_wwan_reset_network_stats")
            if resp.get("set_wwan_reset_network_stats", {}).get("errno") == 0:
                print("Historico limpo com sucesso.")
                return True
            print("Erro ao limpar historico:", resp)
            return False
        except Exception as exc:
            print(f"Erro ao limpar historico: {exc}")
            return False


class HuaweiModemClient(BaseModemClient):
    """
    Cliente para roteadores Huawei/ZOWEE HiLink, incluindo H153-381 / 5G CPE 5s.
    """

    driver = "huawei"

    def __init__(self, username=None, password=None, password_hash=None):
        self.BASE_URL = config.MODEM_URL
        self.username = username if username else config.MODEM_USER
        self.password = password if password else config.MODEM_PASS
        self.password_hash = password_hash
        self.tokens = []
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

    def _remember_response_tokens(self, response):
        for name in (
            "__RequestVerificationTokenone",
            "__RequestVerificationTokentwo",
            "__RequestVerificationToken",
            "__requestverificationtokenone",
            "__requestverificationtokentwo",
            "__requestverificationtoken",
        ):
            token = response.headers.get(name)
            if token:
                self.tokens.append(token)

    def _refresh_token(self):
        response = self.session.get(f"{self.BASE_URL}/api/webserver/token", timeout=10)
        response.raise_for_status()
        data = _parse_xml_response(response.text)
        token = data.get("token")
        if not token:
            raise RuntimeError("Token CSRF nao retornado pelo roteador.")

        # A UI oficial usa apenas a metade final do token retornado por este firmware.
        self.tokens.append(token[32:] if len(token) > 32 else token)
        self._remember_response_tokens(response)

    def _next_token(self):
        if not self.tokens:
            self._refresh_token()
        return self.tokens.pop(0)

    def _get_xml(self, path, auth=False, params=None, timeout=10):
        headers = {"_ResponseSource": "Broswer"}
        if auth:
            headers["__RequestVerificationToken"] = self._next_token()

        response = self.session.get(
            f"{self.BASE_URL}{path}",
            params=params,
            headers=headers,
            timeout=timeout,
        )
        self._remember_response_tokens(response)
        response.raise_for_status()
        return _parse_xml_response(response.text)

    def _post_xml(self, path, data, auth=True, timeout=10):
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "_ResponseSource": "Broswer",
        }
        if auth:
            headers["__RequestVerificationToken"] = self._next_token()

        body = _dict_to_xml("request", data)
        response = self.session.post(
            f"{self.BASE_URL}{path}",
            data=body.encode("utf-8"),
            headers=headers,
            timeout=timeout,
        )
        self._remember_response_tokens(response)
        response.raise_for_status()
        return _parse_xml_response(response.text)

    def _scram_client_proof(self, password, salt_hex, iterations, first_nonce, server_nonce):
        salt = bytes.fromhex(salt_hex)
        auth_message = f"{first_nonce},{server_nonce},{server_nonce}".encode("utf-8")
        salted_password = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        # The router's emui-crypto.js calls CryptoJS.HmacSHA256(message, key) with
        # the SCRAM arguments reversed compared with the RFC wording.
        client_key = hmac.new(b"Client Key", salted_password, hashlib.sha256).digest()
        stored_key = hashlib.sha256(client_key).digest()
        client_signature = hmac.new(auth_message, stored_key, hashlib.sha256).digest()
        client_proof = bytes(a ^ b for a, b in zip(client_key, client_signature)).hex()
        server_key = hmac.new(b"Server Key", salted_password, hashlib.sha256).digest()
        server_signature = hmac.new(auth_message, server_key, hashlib.sha256).hexdigest()
        return client_proof, server_signature

    def login(self):
        if self.password_hash and not self.password:
            raise ValueError("MODEM_HASH nao e suportado pelo driver Huawei; use MODEM_PASS.")
        if not self.password:
            print("Senha do roteador Huawei/ZOWEE nao configurada.")
            return False

        print(f"Logando como {self.username} no roteador Huawei/ZOWEE...")
        # A UI web pode invalidar o token CSRF entre challenge e auth.
        for attempt in range(2):
            first_nonce = secrets.token_hex(32)
            self.tokens.clear()
            try:
                challenge = self._post_xml(
                    "/api/user/challenge_login",
                    {"username": self.username, "firstnonce": first_nonce, "mode": 1},
                    auth=True,
                )
            except ModemApiError as exc:
                if exc.code == "125003" and attempt == 0:
                    continue
                print(f"Falha no challenge_login: {exc}")
                return False

            server_nonce = challenge.get("servernonce")
            salt = challenge.get("salt")
            iterations = challenge.get("iterations")
            if not server_nonce or not salt or not iterations:
                print(f"Resposta inesperada do challenge_login: {challenge}")
                return False

            client_proof, server_signature = self._scram_client_proof(
                self.password, salt, iterations, first_nonce, server_nonce
            )
            try:
                auth_response = self._post_xml(
                    "/api/user/authentication_login",
                    {"clientproof": client_proof, "finalnonce": server_nonce},
                    auth=True,
                )
            except ModemApiError as exc:
                if exc.code == "125003" and attempt == 0:
                    continue
                print(f"Falha no authentication_login: {exc}")
                return False

            returned_signature = auth_response.get("serversignature")
            if returned_signature and returned_signature != server_signature:
                print("Assinatura SCRAM do servidor nao confere.")
                return False

            return True

        return False

    @staticmethod
    def _normalize_huawei_sms(message):
        idx = message.get("Index")
        smstat = str(message.get("Smstat", "1"))
        return {
            "idx": idx,
            "number": message.get("Phone", ""),
            "time": message.get("Date", ""),
            "content": message.get("Content", ""),
            # Em HiLink, Smstat=0 costuma indicar mensagem nao lida.
            "new_sms": 1 if smstat == "0" else 0,
        }

    def send_sms(self, number, content):
        print(f"Enviando SMS para {number}...")
        try:
            response = self._post_xml(
                "/api/sms/send-sms",
                {
                    "Index": -1,
                    "Phones": [number],
                    "Sca": "",
                    "Content": content,
                    "Length": len(content),
                    "Reserved": 1,
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                auth=True,
                timeout=20,
            )
            if _is_ok_response(response):
                print("SMS enviado com sucesso.")
                return True
            print(f"Resposta inesperada ao enviar SMS: {response}")
            return False
        except Exception as exc:
            print(f"Falha no envio: {exc}")
            return False

    def get_sms_device_status(self):
        try:
            data = self._get_xml("/api/sms/sms-count", auth=True)
            total = (
                _coerce_int(data.get("LocalInbox"), 0)
                + _coerce_int(data.get("LocalOutbox"), 0)
                + _coerce_int(data.get("LocalDraft"), 0)
            )
            inbox_count = _coerce_int(data.get("LocalInbox"), total)
            return {
                "inbox_used_count": inbox_count,
                "inbox_unread_count": _coerce_int(data.get("LocalUnread"), 0),
                "raw": data,
            }
        except Exception as exc:
            print(f"Erro ao obter o status de SMS: {exc}")
            return None

    def get_sms_inbox_records(self, start=1, end=None, full_content=True):
        if end is None:
            status = self.get_sms_device_status()
            if not status:
                return None
            end = status.get("inbox_used_count", 0)

        count = max(0, int(end) - max(1, int(start)) + 1)
        if count <= 0:
            return []

        try:
            data = self._post_xml(
                "/api/sms/sms-list",
                {
                    "PageIndex": 1,
                    "ReadCount": count,
                    "BoxType": 1,
                    "SortType": 0,
                    "Ascending": 0,
                    "UnreadPreferred": 0,
                },
                auth=True,
                timeout=15,
            )
            messages = data.get("Messages", {}).get("Message", [])
            if isinstance(messages, dict):
                messages = [messages]
            return [self._normalize_huawei_sms(message) for message in messages]
        except Exception as exc:
            print(f"Erro ao obter mensagens da inbox: {exc}")
            return None

    def set_sms_inbox_read(self, idx):
        try:
            response = self._post_xml("/api/sms/set-read", {"Index": idx}, auth=True)
            return _is_ok_response(response)
        except Exception as exc:
            print(f"Erro ao marcar SMS como lido: {exc}")
            return False

    def get_stats(self):
        try:
            data = self._get_xml("/api/monitoring/traffic-statistics", auth=False)
            month = {}
            try:
                month = self._get_xml("/api/monitoring/month_statistics", auth=False)
            except Exception:
                month = {}

            total_upload_bytes = float(data.get("TotalUpload", 0) or 0)
            total_download_bytes = float(data.get("TotalDownload", 0) or 0)
            stats = {
                "tx": total_upload_bytes / 1024,
                "rx": total_download_bytes / 1024,
                "CurrentUpload": data.get("CurrentUpload"),
                "CurrentDownload": data.get("CurrentDownload"),
                "CurrentUploadRate": data.get("CurrentUploadRate"),
                "CurrentDownloadRate": data.get("CurrentDownloadRate"),
                "TotalConnectTime": data.get("TotalConnectTime"),
                "raw": data,
            }
            if month.get("MonthLastClearTime"):
                stats["modem_last_clear_date"] = month["MonthLastClearTime"]
            return stats
        except Exception as exc:
            print(f"Erro ao buscar estatisticas: {exc}")
            return None

    def clear_stats(self):
        try:
            response = self._post_xml(
                "/api/monitoring/clear-traffic",
                {"ClearTraffic": 1},
                auth=True,
            )
            if _is_ok_response(response):
                print("Historico limpo com sucesso.")
                return True
            print("Resposta inesperada ao limpar historico:", response)
            return False
        except Exception as exc:
            print(f"Erro ao limpar historico: {exc}")
            return False


class ModemClient:
    """
    Fabrica compatível com a API antiga. Retorna o cliente do driver configurado.
    """

    def __new__(cls, username=None, password=None, password_hash=None, driver=None):
        selected_driver = (driver or config.MODEM_DRIVER or "zte").strip().lower()
        if selected_driver in {"zte", "vivo", "mf79u"}:
            return ZteModemClient(username=username, password=password, password_hash=password_hash)
        if selected_driver in {"huawei", "zowee", "hilink", "h153", "h153-381", "5gcpe"}:
            return HuaweiModemClient(username=username, password=password, password_hash=password_hash)
        raise ValueError(f"Driver de modem nao suportado: {selected_driver}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enviar SMS via modem/roteador CPE")
    parser.add_argument("number", help="Numero de telefone destinatario")
    parser.add_argument("message", help="Conteudo da mensagem")
    parser.add_argument("--driver", help="Driver do modem: zte ou huawei")
    parser.add_argument("--user", help="Usuario do modem (sobrescreve config)")
    parser.add_argument("--password", help="Senha do modem (texto plano)")
    parser.add_argument("--hash", help="Hash da senha do modem ZTE (opcional)")

    args = parser.parse_args()

    client = ModemClient(
        username=args.user,
        password=args.password,
        password_hash=args.hash,
        driver=args.driver,
    )
    if client.login():
        time.sleep(1)
        if not client.send_sms(args.number, args.message):
            sys.exit(1)
    else:
        print("Nao foi possivel logar.")
        sys.exit(1)

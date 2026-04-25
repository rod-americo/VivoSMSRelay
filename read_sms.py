import argparse
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modem_client import ModemClient


def print_text_messages(messages):
    if not messages:
        print("Nenhum SMS encontrado.")
        return

    for message in messages:
        status = "novo" if message.get("unread") else "lido"
        print(f"[{message.get('idx')}] {message.get('time')} | {status} | {message.get('number')}")
        print(message.get("content", ""))
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ler SMS recebidos do modem/roteador CPE")
    parser.add_argument("--limit", type=int, default=10, help="Quantidade máxima de mensagens retornadas")
    parser.add_argument("--unread-only", action="store_true", help="Retornar apenas mensagens não lidas")
    parser.add_argument("--mark-read", action="store_true", help="Marcar mensagens retornadas como lidas")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    parser.add_argument("--driver", help="Driver do modem: zte ou huawei")
    parser.add_argument("--user", help="Usuário do modem (sobrescreve config)")
    parser.add_argument("--password", help="Senha do modem (texto plano)")
    parser.add_argument("--hash", help="Hash da senha do modem (opcional)")

    args = parser.parse_args()

    client = ModemClient(
        username=args.user,
        password=args.password,
        password_hash=args.hash,
        driver=args.driver,
    )
    if not client.login():
        print("Não foi possível logar.")
        sys.exit(1)

    messages = client.list_sms_inbox(
        limit=args.limit,
        unread_only=args.unread_only,
        mark_read=args.mark_read,
        full_content=True,
    )
    if messages is None:
        print("Não foi possível obter as mensagens.")
        sys.exit(1)

    if args.json:
        print(json.dumps(messages, indent=2, ensure_ascii=False))
    else:
        print_text_messages(messages)

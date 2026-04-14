import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from modem_client import ModemClient


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_state(state_file):
    if not os.path.exists(state_file):
        return None

    with open(state_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state_file, state):
    directory = os.path.dirname(state_file)
    if directory:
        os.makedirs(directory, exist_ok=True)

    temp_file = f"{state_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, state_file)


def send_webhook(webhook_url, message, timeout):
    payload = {
        "event": "sms_received",
        "source": "vivosmsrelay",
        "message": message,
        "forwarded_at": utc_now_iso(),
    }
    response = requests.post(webhook_url, json=payload, timeout=timeout)
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"Webhook respondeu com HTTP {response.status_code}: {response.text[:500]}"
        )


def fetch_inbox_summaries(client):
    status = client.get_sms_device_status()
    if not status:
        raise RuntimeError("Não foi possível ler o status da inbox.")

    total = status.get("inbox_used_count", 0)
    if total <= 0:
        return []

    records = client.get_sms_inbox_records(start=1, end=total, full_content=False)
    if records is None:
        raise RuntimeError("Não foi possível ler o sumário da inbox.")

    return [client.normalize_sms_record(record) for record in records]


def build_initial_state(current_max_idx):
    return {
        "last_seen_idx": current_max_idx,
        "initialized_at": utc_now_iso(),
        "last_checked_at": utc_now_iso(),
        "last_forwarded_at": None,
    }


def run_poll_cycle(args):
    client = ModemClient(username=args.user, password=args.password, password_hash=args.hash)
    if not client.login():
        raise RuntimeError("Falha no login no modem.")

    summaries = fetch_inbox_summaries(client)
    current_max_idx = max((int(message.get("idx") or 0) for message in summaries), default=0)

    state = load_state(args.state_file)
    if state is None:
        initial_idx = 0 if args.replay_existing else current_max_idx
        state = build_initial_state(initial_idx)
        save_state(args.state_file, state)

        if not args.replay_existing:
            print(
                f"Estado inicializado em idx={initial_idx}. "
                "Nenhum SMS antigo foi encaminhado."
            )
            return 0

    last_seen_idx = int(state.get("last_seen_idx", 0))
    if current_max_idx < last_seen_idx:
        state = build_initial_state(current_max_idx)
        save_state(args.state_file, state)
        print(
            f"Aviso: inbox reinicializada ou limpa. "
            f"Reajustando last_seen_idx para {current_max_idx}."
        )
        return 0

    new_summaries = [
        message
        for message in summaries
        if int(message.get("idx") or 0) > last_seen_idx
    ]
    if args.unread_only:
        new_summaries = [message for message in new_summaries if message.get("unread")]

    new_summaries.sort(key=lambda message: int(message["idx"]))

    forwarded_count = 0
    for summary in new_summaries:
        idx = int(summary["idx"])
        detailed_record = client.get_sms_inbox_record(idx)
        if detailed_record:
            message = client.normalize_sms_record(detailed_record)
        else:
            message = summary

        send_webhook(args.webhook_url, message, timeout=args.request_timeout)

        if args.mark_read and message.get("unread"):
            client.set_sms_inbox_read(idx)

        state["last_seen_idx"] = idx
        state["last_checked_at"] = utc_now_iso()
        state["last_forwarded_at"] = state["last_checked_at"]
        save_state(args.state_file, state)
        forwarded_count += 1
        print(f"SMS idx={idx} encaminhado para o webhook.")

    if forwarded_count == 0:
        state["last_checked_at"] = utc_now_iso()
        save_state(args.state_file, state)
        print("Nenhum SMS novo para encaminhar.")

    return forwarded_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Encaminha SMS novos da inbox do modem para um webhook HTTP"
    )
    parser.add_argument("--webhook-url", default=config.SMS_WEBHOOK_URL, help="URL do webhook HTTP")
    parser.add_argument(
        "--state-file",
        default=config.SMS_POLL_STATE_FILE,
        help="Arquivo JSON local usado para persistir o último SMS processado",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=config.SMS_POLL_INTERVAL,
        help="Intervalo entre leituras quando executado em loop",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=config.SMS_POLL_REQUEST_TIMEOUT,
        help="Timeout do POST para o webhook",
    )
    parser.add_argument("--once", action="store_true", help="Executa um único ciclo e encerra")
    parser.add_argument(
        "--replay-existing",
        action="store_true",
        help="No primeiro ciclo, também encaminha SMS já existentes na inbox",
    )
    parser.add_argument(
        "--unread-only",
        action="store_true",
        help="Encaminha apenas mensagens ainda marcadas como não lidas no modem",
    )
    parser.add_argument(
        "--mark-read",
        action="store_true",
        help="Marca como lidas as mensagens encaminhadas com sucesso",
    )
    parser.add_argument("--user", help="Usuário do modem (sobrescreve config)")
    parser.add_argument("--password", help="Senha do modem (texto plano)")
    parser.add_argument("--hash", help="Hash da senha do modem (opcional)")

    args = parser.parse_args()

    if not args.webhook_url:
        parser.error("Informe --webhook-url ou defina SMS_WEBHOOK_URL no ambiente/.env")

    exit_code = 0
    while True:
        try:
            run_poll_cycle(args)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Erro no poller: {e}", file=sys.stderr)
            exit_code = 1

        if args.once:
            break

        time.sleep(max(1, args.poll_interval))

    sys.exit(exit_code)

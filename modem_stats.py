import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modem_client import ModemClient

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modem_stats_state.json")


def save_state():
    try:
        state = {"last_clear_timestamp": datetime.now().isoformat()}
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as exc:
        print(f"Aviso: Nao foi possivel salvar o estado local: {exc}")


def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                return state.get("last_clear_timestamp")
    except Exception as exc:
        print(f"Aviso: Nao foi possivel carregar o estado local: {exc}")
    return None


def format_bytes(size):
    # Entrada em KiB para preservar compatibilidade com o modem ZTE antigo.
    power = 2**10
    n = 0
    power_labels = {0: "K", 1: "M", 2: "G", 3: "T"}
    while size >= power and n < len(power_labels) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerenciar estatisticas do modem/roteador CPE")
    parser.add_argument("--clear", action="store_true", help="Limpar historico de conexoes")
    parser.add_argument("--json", action="store_true", help="Saida em JSON")
    parser.add_argument("--driver", help="Driver do modem: zte ou huawei")
    parser.add_argument("--user", help="Usuario do modem")
    parser.add_argument("--password", help="Senha do modem")
    parser.add_argument("--hash", help="Hash da senha do modem ZTE")

    args = parser.parse_args()

    client = ModemClient(
        username=args.user,
        password=args.password,
        password_hash=args.hash,
        driver=args.driver,
    )

    if args.clear or getattr(client, "driver", "") != "huawei":
        if not client.login():
            print("Falha no login.")
            sys.exit(1)

    if args.clear:
        print("Limpando estatisticas...")
        if client.clear_stats():
            save_state()
        time.sleep(2)

    stats = client.get_stats()
    if stats:
        last_clear = load_state()
        if last_clear:
            stats["last_clear_timestamp"] = last_clear
        elif stats.get("modem_last_clear_date"):
            stats["last_clear_timestamp"] = stats["modem_last_clear_date"]

        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("\n=== Estatisticas de Rede ===")
            if "last_clear_timestamp" in stats:
                try:
                    dt = datetime.fromisoformat(stats["last_clear_timestamp"])
                    print(f"Ciclo iniciado em: {dt.strftime('%d/%m/%Y %H:%M:%S')}")
                except Exception:
                    print(f"Ciclo iniciado em: {stats['last_clear_timestamp']}")

            print(f"Download (RX)    : {format_bytes(float(stats.get('rx', 0)))}")
            print(f"Upload   (TX)    : {format_bytes(float(stats.get('tx', 0)))}")
            total = float(stats.get("rx", 0)) + float(stats.get("tx", 0))
            print(f"Total            : {format_bytes(total)}")
    else:
        print("Nao foi possivel obter as estatisticas.")
        sys.exit(1)

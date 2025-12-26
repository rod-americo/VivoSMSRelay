import argparse
import sys
import os
import json
import time
from datetime import datetime

# Ensure we can import the existing modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modem_client import ModemClient

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modem_stats_state.json")

class ModemStats(ModemClient):
    def get_stats(self):
        """Fetches network statistics."""
        url = f"{self.BASE_URL}/cgi-bin/gui.cgi"
        payload = {
            "action": "get_wwan_total_network_stats",
            "args": {}
        }
        
        try:
            r = self.session.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if "get_wwan_total_network_stats" in data:
                    stats = data["get_wwan_total_network_stats"]
                    
                    # Add last clear timestamp if available
                    last_clear = self._load_state()
                    if last_clear:
                        stats["last_clear_timestamp"] = last_clear

                    return stats
                else:
                    print("Resposta inesperada da API (get_stats):", data)
                    return None
            else:
                print(f"Erro HTTP ao buscar estatísticas: {r.status_code}")
                return None
        except Exception as e:
            print(f"Erro ao buscar estatísticas: {e}")
            return None

    def clear_stats(self):
        """Clears the network history."""
        url = f"{self.BASE_URL}/cgi-bin/gui.cgi"
        payload = {
            "action": "set_wwan_reset_network_stats",
            "args": {}
        }
        
        try:
            r = self.session.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("set_wwan_reset_network_stats", {}).get("errno") == 0:
                    print("Histórico limpo com sucesso.")
                    self._save_state()
                    return True
                else:
                    print("Erro ao limpar histórico (API):", data)
                    return False
            else:
                print(f"Erro HTTP ao limpar histórico: {r.status_code}")
                return False
        except Exception as e:
            print(f"Erro ao limpar histórico: {e}")
            return False

    def _save_state(self):
        """Saves the current timestamp as the last clear time."""
        try:
            state = {"last_clear_timestamp": datetime.now().isoformat()}
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Aviso: Não foi possível salvar o estado local: {e}")

    def _load_state(self):
        """Loads the last clear timestamp."""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    return state.get("last_clear_timestamp")
        except Exception as e:
            print(f"Aviso: Não foi possível carregar o estado local: {e}")
        return None

def format_bytes(size):
    # Helper to print human readable units (Input is in KB)
    power = 2**10
    n = 0
    power_labels = {0 : 'K', 1: 'M', 2: 'G', 3: 'T'}
    while size >= power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerenciar estatísticas do Modem Vivo (ZTE)")
    parser.add_argument("--clear", action="store_true", help="Limpar histórico de conexões")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    
    # Optional auth overrides
    parser.add_argument("--user", help="Usuário do modem")
    parser.add_argument("--password", help="Senha do modem")
    parser.add_argument("--hash", help="Hash da senha")

    args = parser.parse_args()

    client = ModemStats(username=args.user, password=args.password, password_hash=args.hash)
    
    if not client.login():
        print("Falha no login.")
        sys.exit(1)

    if args.clear:
        print("Limpando estatísticas...")
        client.clear_stats()
        # Optionally wait a bit before fetching new stats
        time.sleep(2)

    stats = client.get_stats()
    if stats:
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("\n=== Estatísticas de Rede ===")
            if "last_clear_timestamp" in stats:
                try:
                    dt = datetime.fromisoformat(stats["last_clear_timestamp"])
                    print(f"Ciclo iniciado em: {dt.strftime('%d/%m/%Y %H:%M:%S')}")
                except:
                   print(f"Ciclo iniciado em: {stats['last_clear_timestamp']}")

            print(f"Download (RX)    : {format_bytes(stats.get('rx', 0))}")
            print(f"Upload   (TX)    : {format_bytes(stats.get('tx', 0))}")
            total = stats.get('rx', 0) + stats.get('tx', 0)
            print(f"Total            : {format_bytes(total)}")
    else:
        print("Não foi possível obter as estatísticas.")

import sys
import os
import getpass
try:
    from modem_crypto import ModemCrypto
except ImportError:
    # Handle if run from outside the directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from modem_crypto import ModemCrypto

def setup():
    print("=== Configuração do Vivo SMS Relay ===")
    print("Este script vai gerar o arquivo .env com suas configurações.")
    print("Pressione Enter para usar os valores padrão [entre colchetes].\n")

    # URL
    url = input("URL do Modem [http://192.168.1.1]: ").strip()
    if not url:
        url = "http://192.168.1.1"

    # User
    user = input("Usuário [admin]: ").strip()
    if not user:
        user = "admin"

    # Password
    password = getpass.getpass("Senha do Modem [vivo]: ").strip()
    if not password:
        password = "vivo"
    
    print("\nCalculando hash da senha...")
    pwd_hash = ModemCrypto.encode_pw(password)
    print(f"Hash gerado: {pwd_hash[:10]}...{pwd_hash[-10:]}")

    # Write .env
    env_content = f"""MODEM_URL={url}
MODEM_USER={user}
# MODEM_PASS não é necessário se tivermos o hash, mas deixamos comentado para referência ou fallback
# MODEM_PASS={password}
MODEM_HASH={pwd_hash}
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\nArquivo .env criado com sucesso!")
    print("Configuração salva.")

if __name__ == "__main__":
    setup()

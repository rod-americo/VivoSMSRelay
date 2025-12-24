import sys
import os
import getpass

# Importa as classes necessárias do projeto
try:
    from modem_crypto import ModemCrypto
except ImportError:
    # Ajuste de path caso rodado de fora do diretório
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from modem_crypto import ModemCrypto

def setup():
    """Guiado interativo para configurar o ambiente."""
    print("=== Configuração do Vivo SMS Relay ===")
    print("Este script vai gerar o arquivo .env com suas configurações.")
    print("Pressione Enter para usar os valores padrão [entre colchetes].\n")

    # Coleta URL
    url = input("URL do Modem [http://192.168.1.1]: ").strip()
    if not url:
        url = "http://192.168.1.1"

    # Coleta Usuário
    user = input("Usuário [admin]: ").strip()
    if not user:
        user = "admin"

    # Coleta Senha (oculta digitação)
    password = getpass.getpass("Senha do Modem [vivo]: ").strip()
    if not password:
        password = "vivo"
    
    print("\nCalculando hash da senha...")
    pwd_hash = ModemCrypto.encode_pw(password)
    print(f"Hash gerado: {pwd_hash[:10]}...{pwd_hash[-10:]}")

    # Monta o conteúdo do arquivo .env
    env_content = f"""MODEM_URL={url}
MODEM_USER={user}
# MODEM_PASS não é estritamente necessário se tivermos o hash (MODEM_HASH), 
# mas deixamos comentado para referência ou caso queira alterar manualmente depois.
# MODEM_PASS={password}
MODEM_HASH={pwd_hash}
"""
    
    # Grava o arquivo
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\nArquivo .env criado com sucesso!")
    print("Configuração salva. Agora você pode executar o modem_client.py.")

if __name__ == "__main__":
    setup()

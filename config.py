import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()


def get_int_env(name, default):
    """Lê uma variável de ambiente inteira com fallback seguro."""
    value = os.getenv(name)
    if value in (None, ""):
        return default

    try:
        return int(value)
    except ValueError:
        print(f"Aviso: {name} inválida ({value!r}); usando {default}.")
        return default

# Detalhes de Conexão do Modem
MODEM_URL = os.getenv("MODEM_URL", "http://192.168.1.1")

# Configuração do servidor HTTP opcional
SMS_SERVER_PORT = get_int_env("SMS_SERVER_PORT", 5001)

# Credenciais
MODEM_USER = os.getenv("MODEM_USER", "admin")
MODEM_PASS = os.getenv("MODEM_PASS", "vivo")

# Hash pré-calculado
# O script tenta ler um hash já pronto do ambiente para evitar recalcular a cada execução.
MODEM_HASH = os.getenv("MODEM_HASH", None)

# Hash padrão para admin/vivo otimizado
# Isso evita rodar a lógica de criptografia se o usuário estiver usando as credenciais de fábrica.
DEFAULT_VIVO_HASH = "93636363636363316363046363b76363206363636363638363635a63633b6363206363636363638363635a63633b6363206363636363638363635a63633b6363"

# Se nenhum hash foi fornecido e as credenciais são as padrão, usa o hash otimizado
if not MODEM_HASH and MODEM_USER == "admin" and MODEM_PASS == "vivo":
    MODEM_HASH = DEFAULT_VIVO_HASH

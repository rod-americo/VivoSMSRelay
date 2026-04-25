import os

from dotenv import load_dotenv

load_dotenv()


def get_int_env(name, default):
    """Le uma variavel de ambiente inteira com fallback seguro."""
    value = os.getenv(name)
    if value in (None, ""):
        return default

    try:
        return int(value)
    except ValueError:
        print(f"Aviso: {name} invalida ({value!r}); usando {default}.")
        return default


def get_modem_driver():
    """Retorna o driver do modem/roteador normalizado."""
    value = (
        os.getenv("MODEM_DRIVER")
        or os.getenv("MODEM_TYPE")
        or os.getenv("MODEM_VENDOR")
        or "zte"
    )
    return value.strip().lower()


# Driver suportado: zte, huawei.
# Aliases historicos MODEM_TYPE e MODEM_VENDOR ainda sao aceitos.
MODEM_DRIVER = get_modem_driver()

# Detalhes de conexao do modem/roteador.
MODEM_URL = os.getenv("MODEM_URL", "http://192.168.1.1").rstrip("/")

# Configuracao do servidor HTTP opcional.
SMS_SERVER_PORT = get_int_env("SMS_SERVER_PORT", 5001)
SMS_POLL_INTERVAL = get_int_env("SMS_POLL_INTERVAL", 30)
SMS_POLL_REQUEST_TIMEOUT = get_int_env("SMS_POLL_REQUEST_TIMEOUT", 15)

# Credenciais.
MODEM_USER = os.getenv("MODEM_USER", "admin")

# O modem ZTE antigo aceitava o default admin/vivo. Para Huawei/ZOWEE, senha
# deve ser fornecida explicitamente no .env ou por argumento.
MODEM_PASS = os.getenv("MODEM_PASS")
if MODEM_DRIVER in {"zte", "vivo", "mf79u"} and not MODEM_PASS:
    MODEM_PASS = "vivo"

SMS_WEBHOOK_URL = os.getenv("SMS_WEBHOOK_URL", None)
SMS_POLL_STATE_FILE = os.getenv(
    "SMS_POLL_STATE_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "sms_poller_state.json"),
)

# Hash pre-calculado usado apenas pelo driver ZTE legado.
MODEM_HASH = os.getenv("MODEM_HASH", None)

# Hash padrao para admin/vivo no ZTE antigo.
DEFAULT_VIVO_HASH = "93636363636363316363046363b76363206363636363638363635a63633b6363206363636363638363635a63633b6363206363636363638363635a63633b6363"

if (
    MODEM_DRIVER in {"zte", "vivo", "mf79u"}
    and not MODEM_HASH
    and MODEM_USER == "admin"
    and MODEM_PASS == "vivo"
):
    MODEM_HASH = DEFAULT_VIVO_HASH

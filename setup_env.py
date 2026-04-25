import getpass
import os
import sys

try:
    from modem_crypto import ModemCrypto
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from modem_crypto import ModemCrypto


def choose_driver():
    driver = input("Driver do modem [zte/huawei] (zte): ").strip().lower()
    if not driver:
        driver = "zte"
    if driver in {"vivo", "mf79u"}:
        return "zte"
    if driver in {"zowee", "hilink", "h153", "h153-381"}:
        return "huawei"
    if driver not in {"zte", "huawei"}:
        raise SystemExit(f"Driver nao suportado: {driver}")
    return driver


def setup():
    """Assistente interativo para gerar .env."""
    print("=== Configuracao do CPE SMS Relay ===")
    print("Este script gera o arquivo .env local, que nao deve ser versionado.")
    print("Pressione Enter para usar os valores padrao entre colchetes.\n")

    driver = choose_driver()
    default_url = "http://192.168.8.1" if driver == "huawei" else "http://192.168.1.1"
    url = input(f"URL do modem [{default_url}]: ").strip() or default_url

    user = input("Usuario [admin]: ").strip() or "admin"
    password = getpass.getpass("Senha do modem: ").strip()
    if not password:
        if driver == "zte":
            password = "vivo"
        else:
            raise SystemExit("Senha obrigatoria para o driver huawei.")

    lines = [
        f"MODEM_DRIVER={driver}",
        f"MODEM_URL={url}",
        f"MODEM_USER={user}",
    ]

    if driver == "zte":
        print("\nCalculando hash da senha ZTE...")
        pwd_hash = ModemCrypto.encode_pw(password)
        print(f"Hash gerado: {pwd_hash[:10]}...{pwd_hash[-10:]}")
        lines.extend(
            [
                "# MODEM_PASS pode ser usado no ZTE, mas MODEM_HASH evita guardar a senha em texto.",
                f"# MODEM_PASS={password}",
                f"MODEM_HASH={pwd_hash}",
            ]
        )
    else:
        lines.extend(
            [
                "# Huawei/ZOWEE usa SCRAM; MODEM_HASH nao se aplica.",
                f"MODEM_PASS={password}",
            ]
        )

    lines.extend(
        [
            "SMS_SERVER_PORT=5001",
            "",
        ]
    )

    with open(".env", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\nArquivo .env criado com sucesso.")


if __name__ == "__main__":
    setup()

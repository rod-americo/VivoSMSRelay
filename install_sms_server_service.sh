#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="vivosmsrelay"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
RUN_AS_USER="${SUDO_USER:-}"
RUN_AS_GROUP=""

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo ./install_sms_server_service.sh" >&2
  exit 1
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Este script exige Linux com systemd." >&2
  echo "No seu caso, rode no host remoto: ssh -t scraper 'cd /home/mezo/VivoSMSRelay && sudo ./install_sms_server_service.sh'" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl não encontrado. Este host não parece usar systemd." >&2
  exit 1
fi

if [[ ! -d "/etc/systemd/system" ]]; then
  echo "Diretório /etc/systemd/system não encontrado. Este host não parece usar systemd." >&2
  exit 1
fi

if [[ -z "${RUN_AS_USER}" ]]; then
  echo "SUDO_USER não definido. Execute o script com sudo a partir do usuário dono do projeto." >&2
  exit 1
fi

RUN_AS_GROUP="$(id -gn "${RUN_AS_USER}")"

if [[ -x "${REPO_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_DIR}/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "${PYTHON_BIN}" || ! -x "${PYTHON_BIN}" ]]; then
  echo "Python não encontrado." >&2
  exit 1
fi

if [[ ! -f "${REPO_DIR}/sms_server.py" ]]; then
  echo "sms_server.py não encontrado em ${REPO_DIR}" >&2
  exit 1
fi

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Vivo SMS Relay HTTP server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_AS_USER}
Group=${RUN_AS_GROUP}
WorkingDirectory=${REPO_DIR}
ExecStart=${PYTHON_BIN} ${REPO_DIR}/sms_server.py
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
  systemctl restart "${SERVICE_NAME}.service"
else
  systemctl start "${SERVICE_NAME}.service"
fi

echo
echo "Serviço instalado: ${SERVICE_NAME}.service"
systemctl --no-pager --full status "${SERVICE_NAME}.service" || true
echo
echo "Logs:"
echo "  sudo journalctl -u ${SERVICE_NAME}.service -f"

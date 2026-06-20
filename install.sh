#!/usr/bin/env bash
# install.sh -- Install pia-web as a systemd service on Debian/Ubuntu
set -e

SERVICE_USER="${SUDO_USER:-$USER}"
INSTALL_DIR="/opt/pia-web"
SERVICE_FILE="/etc/systemd/system/pia-web.service"
SCRIPT_URL="https://raw.githubusercontent.com/pcartwright81/pia-web-python/main/pia-web.py"
PORT="${PORT:-8042}"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash install.sh"
  exit 1
fi

echo "[pia-web] Installing to ${INSTALL_DIR} ..."
mkdir -p "${INSTALL_DIR}"
curl -fsSL "${SCRIPT_URL}" -o "${INSTALL_DIR}/pia-web.py"
chmod +x "${INSTALL_DIR}/pia-web.py"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}"

echo "[pia-web] Writing systemd unit to ${SERVICE_FILE} ..."
cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=PIA Remote Web UI
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/pia-web.py --port ${PORT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[pia-web] Enabling and starting service ..."
systemctl daemon-reload
systemctl enable pia-web
systemctl restart pia-web

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "✔ pia-web installed and running!"
echo "  Open http://${IP}:${PORT} in your browser."
echo ""
echo "  Manage with:"
echo "    sudo systemctl status pia-web"
echo "    sudo systemctl restart pia-web"
echo "    sudo systemctl stop pia-web"
echo ""
echo "  To change the port: sudo PORT=9090 bash install.sh"

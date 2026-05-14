#!/usr/bin/env bash
set -euo pipefail

# Run this script ON the Raspberry Pi.
# Installs:
#   1. momir-netswitch.service  — reads GPIO14 switch at boot, activates WiFi mode,
#                                 drives GPIO15 LED (on = home LAN, off = hotspot)
#   2. momir.service            — Flask app (starts after network is up)
#
# One-time hardware setup required before running this script:
#   GPIO14 (pin 8)  → switch middle; other leg → GND (active-low, uses pull-up)
#   GPIO15 (pin 10) → LED anode via 330Ω resistor → GND
#
# GPIO14/15 are the UART TX/RX pins. The script disables UART in /boot/firmware/config.txt
# (or /boot/config.txt) so those pins are available as plain GPIO.
#
# NetworkManager profiles needed (created automatically below if missing):
#   momir-ap   — hotspot (MomirPrinter / prompted at install time), autoconnect=no
#   momir-home — rename of your existing home WiFi connection

PROJECT_DIR="${PROJECT_DIR:-$HOME/MomirPrinter}"
SERVICE_NAME="${SERVICE_NAME:-momir}"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

# Prompt for hotspot password if not set via environment
if [[ -z "${HOTSPOT_PASSWORD:-}" ]]; then
  read -rsp "Enter hotspot password for MomirPrinter AP: " HOTSPOT_PASSWORD
  echo
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -x "$PROJECT_DIR/momir_env/bin/python3" ]]; then
  echo "Virtualenv missing at $PROJECT_DIR/momir_env/bin/python3" >&2
  echo "Create it first:"
  echo "  cd $PROJECT_DIR"
  echo "  python3 -m venv momir_env"
  echo "  source momir_env/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

cat > /tmp/${SERVICE_NAME}.service <<EOF
[Unit]
Description=MomirPrinter Flask App
After=network-online.target momir-netswitch.service
Wants=network-online.target momir-netswitch.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_DIR/momir_env/bin/python3 -m flask --app app run --host 0.0.0.0 --port 8000
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/${SERVICE_NAME}.service "$SERVICE_PATH"

# ── Add user to lp group for USB printer access (/dev/usb/lp0) ───────────────
sudo usermod -aG lp "$USER"
echo "User $USER added to lp group (USB printer access)"

# ── Disable UART on GPIO14/15 so they can be used as plain GPIO ───────────────
BOOT_CONFIG=""
for candidate in /boot/firmware/config.txt /boot/config.txt; do
  if [[ -f "$candidate" ]]; then
    BOOT_CONFIG="$candidate"
    break
  fi
done

if [[ -n "$BOOT_CONFIG" ]]; then
  if grep -q "enable_uart" "$BOOT_CONFIG"; then
    sudo sed -i 's/^enable_uart=.*/enable_uart=0/' "$BOOT_CONFIG"
  else
    echo "enable_uart=0" | sudo tee -a "$BOOT_CONFIG" > /dev/null
  fi
  echo "UART disabled in $BOOT_CONFIG (GPIO14/15 now available as plain GPIO)"
fi

# ── Create momir-ap hotspot profile (autoconnect=no — netswitch handles it) ───
if ! nmcli connection show momir-ap &>/dev/null; then
  echo "Creating momir-ap hotspot profile..."
  sudo nmcli connection add \
    type wifi ifname wlan0 con-name momir-ap ssid MomirPrinter \
    mode ap ipv4.method shared \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$HOTSPOT_PASSWORD" \
    connection.autoconnect no
  echo "momir-ap profile created (autoconnect=no)"
else
  # Ensure existing profile has autoconnect disabled
  sudo nmcli connection modify momir-ap autoconnect no
  echo "momir-ap profile already exists — autoconnect=no enforced"
fi

# ── Install netswitch service (runs after NetworkManager, sets WiFi mode via switch) ─
NETSWITCH_SERVICE="/etc/systemd/system/momir-netswitch.service"

cat > /tmp/momir-netswitch.service <<EOF
[Unit]
Description=MomirPrinter network mode switch (GPIO14 → WiFi AP or LAN)
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $PROJECT_DIR/app/netswitch.py
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/momir-netswitch.service "$NETSWITCH_SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable momir-netswitch
echo "netswitch service installed"

# ── Install and start main momir service ──────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# ── Set hostname to mo (→ mo.local via mDNS) ────────────────────────────────
sudo sed -i 's/preserve_hostname: false/preserve_hostname: true/' /etc/cloud/cloud.cfg 2>/dev/null || true
echo 'mo' | sudo tee /etc/hostname > /dev/null
sudo sed -i "s/$(hostname)/mo/g" /etc/hosts 2>/dev/null || true
sudo hostnamectl set-hostname mo
echo "Hostname set to mo (will be mo.local after reboot)"

# ── Install nginx reverse proxy (port 80 → Flask 8000) ───────────────────────
sudo apt-get install -y nginx 2>&1 | tail -3
sudo tee /etc/nginx/sites-available/momir > /dev/null << 'NGINXEOF'
server {
    listen 80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
NGINXEOF
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/momir /etc/nginx/sites-enabled/momir
sudo nginx -t && sudo systemctl enable nginx && sudo systemctl restart nginx
echo "nginx configured (http://mo.local after reboot)"

sudo systemctl --no-pager --full status "$SERVICE_NAME" | sed -n '1,20p'

echo "Service installed: $SERVICE_NAME"
echo "Logs: sudo journalctl -u $SERVICE_NAME -f"
echo "Reboot for mo.local to take effect"

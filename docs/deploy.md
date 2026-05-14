# Deploying to Raspberry Pi

The Pi is the **runtime machine**. All build steps happen on Mac first. See [update.md](update.md) for the build pipeline.

## Pi Details

| Item | Value |
|---|---|
| SSH hostname | `mo.local` |
| App URL | `http://mo.local` (via nginx on port 80) |
| User | `<your-pi-user>` |
| Flask service | `momir` (systemd) |
| Printer | `/dev/usb/lp0` |

---

## One-time Pi Setup

### 1. Install the systemd service (run on Pi)

```bash
cd ~/Mo
./scripts/deploy/install_momir_service.sh
```

This installs:
- `momir-netswitch.service` — reads GPIO14 switch at boot, selects WiFi mode, drives GPIO15 LED
- `momir.service` — Flask app, starts after network is up, auto-restarts on crash

### 2. nginx reverse proxy

nginx proxies port 80 → Flask port 5000. Config at `/etc/nginx/sites-available/momir`.

---

## Deploying Updates from Mac

Copy `config.example.sh` to `config.sh` and fill in your Pi username and path (it's gitignored):

```bash
cp config.example.sh config.sh
# edit config.sh: set PI_USER to your Pi username
```

Then deploy:

```bash
source config.sh && scripts/deploy/deploy_pi.sh
```

What it does:
1. Rsyncs project files to Pi over SSH (excludes `momir_env`, the entire `images/` folder, `cards_json`, `.git`). The Pi gets `images_dithered/` only.
2. Restarts the `momir` systemd service

### Options

```bash
source config.sh && scripts/deploy/deploy_pi.sh --dry-run      # preview only
source config.sh && scripts/deploy/deploy_pi.sh --target mo.local
```

The script auto-tries multiple targets: `mo.local`, `10.42.0.1`, `192.168.4.1`.

You can set up a shell alias for convenience:
```bash
alias deploy-momir='bash /path/to/Mo/scripts/deploy/deploy_pi.sh'
```

---

## Network Modes

The Pi supports two WiFi modes, selected by a physical GPIO14 switch at boot:

| Switch | Mode | LED (GPIO15) |
|---|---|---|
| Open | Hotspot (SSID: `MomirPrinter`) | Off |
| Closed → GND | Home WiFi (`momir-home` profile) | On |

### Manual network switch (run on Pi)

```bash
./scripts/deploy/switch_pi_network_mode.sh home
./scripts/deploy/switch_pi_network_mode.sh ap
```

Requires NetworkManager profiles `momir-home` and `momir-ap` to be configured.

### Auto switch at boot

`momir-netswitch.service` calls `app/netswitch.py` on boot.
GPIO wiring:
- GPIO14 (pin 8) → switch middle; other leg → GND
- GPIO15 (pin 10) → LED anode via 330Ω → GND

---

## Service Management (on Pi)

```bash
sudo systemctl status momir
sudo systemctl restart momir
sudo systemctl stop momir
journalctl -u momir -f       # live logs
```

---

## Troubleshooting

### Pi becomes unreachable after idle (WiFi power management)

**Symptom:** App works fine during active use but stops responding after sitting idle for a while. SSH also times out.

**Cause:** The Pi's WiFi chip enters power-save mode when traffic drops, causing the router to consider it disconnected.

**Fix:** A cron job on the Pi pings the router every minute to keep the radio awake:

```bash
# Check current cron (on Pi)
crontab -l

# Add keepalive if missing
(crontab -l 2>/dev/null; echo '* * * * * ping -c 1 192.168.1.1 > /dev/null 2>&1') | crontab -
```

In **hotspot mode** the Pi is the AP so its radio never sleeps — the ping simply fails silently and is harmless.
#!/usr/bin/env bash
set -euo pipefail

# Optional helper: switch between preconfigured NetworkManager connections.
# Requires nmcli and existing connection profiles.
# Example profiles:
#   home wifi:  momir-home
#   hotspot AP: momir-ap

MODE="${1:-}"
HOME_CONN="${HOME_CONN:-momir-home}"
AP_CONN="${AP_CONN:-momir-ap}"

usage() {
  echo "Usage: $0 home|ap"
  echo "Env overrides: HOME_CONN=<name> AP_CONN=<name>"
}

if [[ -z "$MODE" ]]; then
  usage
  exit 1
fi

if ! command -v nmcli >/dev/null 2>&1; then
  echo "nmcli not available on this Pi image."
  echo "Use your existing network config method manually."
  exit 2
fi

case "$MODE" in
  home)
    sudo nmcli connection up "$HOME_CONN"
    ;;
  ap)
    sudo nmcli connection up "$AP_CONN"
    ;;
  *)
    usage
    exit 1
    ;;
esac

echo "Switched to mode: $MODE"
echo "Current IPs:"
hostname -I || true

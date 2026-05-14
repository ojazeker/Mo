#!/usr/bin/env bash
# Copy this file to config.sh and fill in your values.
# config.sh is gitignored — never commit it.
#
# Usage:
#   source config.sh && scripts/deploy/deploy_pi.sh

# SSH username on your Raspberry Pi (default Pi OS user is 'pi', newer installs may differ)
export PI_USER="pi"

# Hostname or IP of your Pi — change if you used a different hostname
export PI_TARGETS=("mo.local" "10.42.0.1" "192.168.4.1")

# Remote path where the project lives on the Pi
export PI_DEST="~/MomirPrinter"

# Hotspot password — must match what install_momir_service.sh used for the momir-ap profile
# (set during one-time Pi setup, not used at deploy time)
export HOTSPOT_PASSWORD="your-hotspot-password-here"

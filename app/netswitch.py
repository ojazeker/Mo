#!/usr/bin/env python3
"""
Network mode switch for MomirPrinter.
Reads GPIO14 at boot to choose between hotspot (AP) and home LAN mode.
Controls GPIO15 LED: ON = home LAN, OFF = hotspot.

Wiring:
  GPIO14 (pin 8)  — switch middle (common)
  Any GND pin     — switch leg (other leg unconnected)
  GPIO15 (pin 10) — LED anode via ~330Ω resistor → GND

  Switch OPEN  (GPIO14 pulled HIGH via internal pull-up) → hotspot mode, LED off
  Switch CLOSED (GPIO14 pulled to GND)                   → home LAN mode, LED on

NetworkManager connection names:
  Hotspot : momir-ap
  Home LAN: detected dynamically (any wifi profile that isn't momir-ap)
"""

import glob
import subprocess
import sys
import time

GPIO_SWITCH = 14
GPIO_LED    = 15


def _gpio_base() -> int:
    """Return the sysfs base offset for the main GPIO chip (e.g. 512 on Pi OS Bookworm)."""
    chips = glob.glob('/sys/class/gpio/gpiochip*')
    if not chips:
        return 0
    best, best_ngpio = chips[0], 0
    for chip in chips:
        try:
            ngpio = int(open(chip + '/ngpio').read())
            if ngpio > best_ngpio:
                best, best_ngpio = chip, ngpio
        except OSError:
            pass
    try:
        return int(open(best + '/base').read())
    except OSError:
        return 0


GPIO_BASE = _gpio_base()

AP_CONN = 'momir-ap'


def find_home_conn() -> str:
    """Return the name of the home WiFi connection (any wifi profile that isn't momir-ap)."""
    result = subprocess.run(
        ['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show'],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        name, _, conn_type = line.partition(':')
        if conn_type.strip() in ('wifi', '802-11-wireless') and name.strip() != AP_CONN:
            return name.strip()
    return None


def _sysfs_pin(bcm_pin: int) -> int:
    """Translate BCM GPIO number to sysfs pin number (adds chip base offset)."""
    return GPIO_BASE + bcm_pin


def gpio_export(bcm_pin, direction):
    pin = _sysfs_pin(bcm_pin)
    with open('/sys/class/gpio/export', 'w') as f:
        f.write(str(pin))
    # wait a moment for the sysfs entry to appear
    time.sleep(0.05)
    with open(f'/sys/class/gpio/gpio{pin}/direction', 'w') as f:
        f.write(direction)


def gpio_unexport(bcm_pin):
    pin = _sysfs_pin(bcm_pin)
    try:
        with open('/sys/class/gpio/unexport', 'w') as f:
            f.write(str(pin))
    except OSError:
        pass


def gpio_read(bcm_pin) -> int:
    pin = _sysfs_pin(bcm_pin)
    with open(f'/sys/class/gpio/gpio{pin}/value') as f:
        return int(f.read().strip())


def gpio_write(bcm_pin, value: int):
    pin = _sysfs_pin(bcm_pin)
    with open(f'/sys/class/gpio/gpio{pin}/value', 'w') as f:
        f.write(str(value))


def nmcli_up(conn_name):
    result = subprocess.run(
        ['nmcli', 'connection', 'up', conn_name],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f'[netswitch] nmcli error: {result.stderr.strip()}', file=sys.stderr)
        return False
    return True


def enable_pull_up(bcm_pin):
    """Use pinctrl to enable the internal pull-up resistor on a GPIO input pin."""
    result = subprocess.run(
        ['pinctrl', 'set', str(bcm_pin), 'ip', 'pu'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f'[netswitch] pinctrl failed: {result.stderr.strip()}', file=sys.stderr)
    else:
        print(f'[netswitch] Pull-up enabled on GPIO{bcm_pin}')


def main():
    # Export switch pin as input
    try:
        gpio_export(GPIO_SWITCH, 'in')
    except OSError:
        pass

    # Export LED pin as output
    try:
        gpio_export(GPIO_LED, 'out')
    except OSError:
        pass

    # Enable internal pull-up — sysfs 'in' direction doesn't do this automatically
    enable_pull_up(GPIO_SWITCH)

    # Brief settle time for pull-up to stabilise
    time.sleep(0.1)

    try:
        switch_value = gpio_read(GPIO_SWITCH)
    except OSError as e:
        print(f'[netswitch] Cannot read GPIO{GPIO_SWITCH}: {e} — defaulting to hotspot mode', file=sys.stderr)
        nmcli_up(AP_CONN)
        return

    # Switch closed (to GND) → LOW → home LAN
    if switch_value == 0:
        home = find_home_conn()
        if not home:
            print('[netswitch] No home WiFi profile found — staying in hotspot mode', file=sys.stderr)
            try:
                gpio_write(GPIO_LED, 0)
            except OSError:
                pass
            nmcli_up(AP_CONN)
        else:
            print(f'[netswitch] Switch CLOSED → home LAN mode ({home})')
            try:
                gpio_write(GPIO_LED, 1)  # LED on
            except OSError:
                pass
            nmcli_up(home)
    else:
        print('[netswitch] Switch OPEN → hotspot mode')
        try:
            gpio_write(GPIO_LED, 0)  # LED off
        except OSError:
            pass
        nmcli_up(AP_CONN)

    # Leave LED state set; clean up switch pin
    gpio_unexport(GPIO_SWITCH)


if __name__ == '__main__':
    main()

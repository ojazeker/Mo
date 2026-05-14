# Hardware

See [bom.md](bom.md) for the full parts list. I'm still trying out different parts so feel free to try your own.

---

## Power

The printer and Pi are both powered from a USB-C power bank via a **PD trigger** that negotiates a fixed voltage (9V). The output feeds into a **buck down converter** set to 5V, which powers the Pi. The printer is wired to the 9v.

```
Power Bank (USB-C PD)
    └── PD Trigger (locks voltage at 9V)
            ├── Buck Converter (steps down to 5V)
            │       └── Raspberry Pi Zero W2 (5V via GPIO pins 2 & 6)
            └── Thermal Printer (9V direct via power terminals)
```

The printer draws a significant current spike when printing — make sure your PD trigger and power bank can handle it.

---

## Thermal Printer

The printer connects to the Pi via USB (Mini USB → Micro USB). USB is much faster than serial — serial tops out at 9600 baud. The printer shows up as `/dev/usb/lp0`.

---

## GPIO Wiring

| GPIO | Pin | Connected to |
|---|---|---|
| GPIO14 | Pin 8 | Switch middle leg; other leg → GND (Pin 6) |
| GPIO15 | Pin 10 | LED anode → 330Ω resistor → GND |

**Switch:** a 2-state switch selects the network mode at boot.
- Switch **open** (HIGH, internal pull-up) → hotspot mode
- Switch **closed to GND** (LOW) → home WiFi mode

**LED:** lights up when connected to home WiFi, off in hotspot mode.

---

## Schematic

> TODO — a wiring schematic will be added here at some point.

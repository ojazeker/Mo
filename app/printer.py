"""ESC/POS thermal printer driver for QR204 (58mm / 384-dot)."""

import os
import struct
import importlib
from pathlib import Path

from PIL import Image

PRINTER_WIDTH_DOTS = 384
DEFAULT_PRINTER_BAUD = int(os.environ.get('MOMIR_PRINTER_BAUD', '9600'))
PRINTER_DEVICE = os.environ.get('MOMIR_PRINTER_DEVICE')
PRINTER_DEVICE_CANDIDATES = (
    '/dev/usb/lp0',
    '/dev/serial0',
    '/dev/ttyAMA0',
    '/dev/ttyS0',
)


def _image_to_raster_data(img):
    """Convert a 1-bit PIL Image to ESC/POS raster bytes.

    Each row becomes PRINTER_WIDTH_DOTS / 8 = 48 bytes.
    In ESC/POS raster mode, a 1-bit means *black* ink, but BMP mode '1'
    stores white=1, black=0. We invert so that dark pixels print.
    """
    img = img.convert('1')

    # Resize width to printer width if needed, keeping aspect ratio
    if img.width != PRINTER_WIDTH_DOTS:
        ratio = PRINTER_WIDTH_DOTS / img.width
        new_height = int(img.height * ratio)
        img = img.resize((PRINTER_WIDTH_DOTS, new_height), Image.NEAREST)

    pixels = img.load()
    width_bytes = PRINTER_WIDTH_DOTS // 8
    rows = []

    for y in range(img.height):
        row = bytearray(width_bytes)
        for x in range(PRINTER_WIDTH_DOTS):
            if pixels[x, y] == 0:  # black pixel
                row[x // 8] |= (0x80 >> (x % 8))
        rows.append(bytes(row))

    return rows, img.height


def print_image(image_path, device=PRINTER_DEVICE, card_text=None):
    """Print a BMP/image file to the thermal printer, optionally followed by text.

    Uses ESC/POS GS v 0 (raster bit-image) command.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f'Image not found: {image_path}')

    img = Image.open(image_path)
    rows, height = _image_to_raster_data(img)
    width_bytes = PRINTER_WIDTH_DOTS // 8

    # GS v 0  –  raster bit image
    # Format: 1D 76 30 m xL xH yL yH [data]
    # m=0 (normal), xL/xH = width in bytes, yL/yH = height in dots
    cmd = b'\x1d\x76\x30\x00'
    cmd += struct.pack('<HH', width_bytes, height)

    data = cmd + b''.join(rows)

    if card_text:
        # Small gap after image, then print text
        data += b'\n'
        data += card_text.encode('utf-8', errors='replace')

    # Feed
    data += b'\n\n\n\n'

    _send_raw(data, device)


def print_text(text, device=PRINTER_DEVICE):
    """Print a simple text string to the thermal printer."""
    # ESC @ (initialize) + text + feed
    data = b'\x1b\x40'
    data += text.encode('utf-8', errors='replace')
    data += b'\n\n\n\n'
    _send_raw(data, device)


def _send_raw(data, device=PRINTER_DEVICE):
    """Write raw bytes to the printer device."""
    resolved_device = _resolve_printer_device(device)
    if _is_serial_device(resolved_device):
        serial_module = importlib.import_module('serial')
        with serial_module.Serial(
            resolved_device,
            DEFAULT_PRINTER_BAUD,
            timeout=5,
            write_timeout=30,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        ) as printer:
            printer.write(data)
            printer.flush()
        return

    with open(resolved_device, 'wb') as printer:
        printer.write(data)


def _resolve_printer_device(device=None):
    """Pick an explicit printer device or the first available candidate."""
    if device:
        return device

    for candidate in PRINTER_DEVICE_CANDIDATES:
        if Path(candidate).exists():
            return candidate

    searched = ', '.join(PRINTER_DEVICE_CANDIDATES)
    raise FileNotFoundError(f'No printer device found. Checked: {searched}')


def _is_serial_device(device):
    """Return True when the target device should be opened via pyserial."""
    return Path(device).name.startswith('tty') or device == '/dev/serial0'

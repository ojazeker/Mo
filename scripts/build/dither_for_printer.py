#!/usr/bin/env python3
"""
Convert card images to dithered monochrome for thermal printing.
Uses Floyd-Steinberg dithering (Pillow built-in) with optional brightness pre-lift.

Dark images are automatically brightened before dithering so detail isn't
lost in solid black areas. Use --brightness to tune the lift amount.

Usage:
  python3 dither_for_printer.py                         # default settings
  python3 dither_for_printer.py --brightness 30         # stronger lift
  python3 dither_for_printer.py --brightness 0          # no lift
  python3 dither_for_printer.py --force                 # re-dither all (skip cache)
  python3 dither_for_printer.py card_images/ card_images_dithered/  # legacy
  python3 dither_for_printer.py images/card_images/ images/card_images_dithered/
"""

import sys
import os
import argparse
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageStat

PRINTER_WIDTH = 384


def _mean_luminance(gray_img):
    """Return mean luminance 0-255 of a grayscale PIL image."""
    return ImageStat.Stat(gray_img).mean[0]


def _auto_brightness_factor(mean_lum, dark_threshold=100, target_lum=140):
    """
    If the image mean luminance is below dark_threshold, return a multiplicative
    factor that would push the mean toward target_lum.
    Returns 1.0 for images that aren't dark.
    """
    if mean_lum >= dark_threshold or mean_lum < 1:
        return 1.0
    return target_lum / mean_lum


def dither_image(input_path, output_path, brightness_boost=15):
    """
    Convert a colour card image to a dithered 1-bit BMP for thermal printing.

    Steps:
    1. Resize to 384 px wide, keep aspect ratio
    2. Convert to grayscale
    3. Auto-brighten dark images (+ optional fixed boost)
    4. Floyd-Steinberg error-diffusion dither (Pillow built-in C implementation)
    5. Save as BMP
    """
    try:
        img = Image.open(input_path).convert('RGB')

        # Resize to printer width
        aspect = img.height / img.width
        new_h = int(PRINTER_WIDTH * aspect)
        img = img.resize((PRINTER_WIDTH, new_h), Image.Resampling.LANCZOS)

        # Grayscale
        gray = ImageOps.grayscale(img)

        # Auto-brighten dark images
        mean_lum = _mean_luminance(gray)
        auto_factor = _auto_brightness_factor(mean_lum)
        total_factor = auto_factor + (brightness_boost / 100.0)
        if total_factor > 1.0:
            gray = ImageEnhance.Brightness(gray).enhance(total_factor)

        # Floyd-Steinberg dither (Pillow's built-in C implementation)
        bmp = gray.convert('1', dither=Image.Dither.FLOYDSTEINBERG)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        bmp.save(output_path, 'BMP')
        return True

    except Exception as e:
        print(f"   Error dithering {os.path.basename(input_path)}: {e}")
        return False


def dither_directory(input_dir, output_dir, brightness_boost=20, force=False):
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        print(f"{input_dir} not found!")
        return False

    print(f"Floyd-Steinberg dithering  (brightness boost +{brightness_boost}%)")
    print(f"   Source : {input_dir}/")
    print(f"   Output : {output_dir}/")
    if force:
        print("   Mode   : force re-dither all\n")
    else:
        print("   Mode   : skip already-dithered\n")

    processed = failed = 0

    for cmc_folder in sorted(input_path.iterdir()):
        if not cmc_folder.is_dir():
            continue

        cmc = cmc_folder.name
        out_cmc = output_path / cmc
        out_cmc.mkdir(parents=True, exist_ok=True)

        images = list(cmc_folder.glob('*.jpg'))
        if not images:
            continue

        print(f"CMC {cmc}: {len(images)} images...", end=' ', flush=True)
        ok = fail = 0

        for img_file in images:
            out_file = out_cmc / (img_file.stem + '.bmp')
            if out_file.exists() and not force:
                ok += 1
                continue
            if dither_image(str(img_file), str(out_file), brightness_boost):
                ok += 1
            else:
                fail += 1

        processed += ok
        failed += fail
        print("ok" if fail == 0 else f"({fail} failed)")

    print(f"\nDone — {processed} processed, {failed} failed")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dither card images for thermal printing (Floyd-Steinberg)')
    parser.add_argument('input_dir', nargs='?', default='images/creature')
    parser.add_argument('output_dir', nargs='?', default='images_dithered/creature')
    parser.add_argument('--brightness', type=int, default=15,
                        help='Extra brightness boost %% applied AFTER auto-lift (default: 15)')
    parser.add_argument('--force', action='store_true',
                        help='Re-dither even if output file already exists')
    args = parser.parse_args()

    if dither_directory(args.input_dir, args.output_dir, args.brightness, args.force):
        sys.exit(0)
    else:
        sys.exit(1)


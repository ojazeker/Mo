#!/usr/bin/env python3
"""
Dither all avatar images in images/avatars/ to images_dithered/avatar/.

Usage:
  python3 scripts/build/dither_avatars.py
  python3 scripts/build/dither_avatars.py --force   # re-dither even if output exists
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageStat

PRINTER_WIDTH = 384
BRIGHTNESS_BOOST = 15
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

BASE_DIR = Path(__file__).parent.parent.parent
SRC_DIR  = BASE_DIR / 'images' / 'avatars'
DST_DIR  = BASE_DIR / 'images_dithered' / 'avatar'


def _mean_luminance(gray_img):
    return ImageStat.Stat(gray_img).mean[0]


def _auto_brightness_factor(mean_lum, dark_threshold=100, target_lum=140):
    if mean_lum >= dark_threshold or mean_lum < 1:
        return 1.0
    return target_lum / mean_lum


def dither_image(input_path: Path, output_path: Path) -> bool:
    try:
        img = Image.open(input_path).convert('RGB')
        aspect = img.height / img.width
        new_h = int(PRINTER_WIDTH * aspect)
        img = img.resize((PRINTER_WIDTH, new_h), Image.Resampling.LANCZOS)

        gray = ImageOps.grayscale(img)
        mean_lum = _mean_luminance(gray)
        auto_factor = _auto_brightness_factor(mean_lum)
        total_factor = auto_factor + (BRIGHTNESS_BOOST / 100.0)
        if total_factor > 1.0:
            gray = ImageEnhance.Brightness(gray).enhance(total_factor)

        bmp = gray.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bmp.save(str(output_path), 'BMP')
        return True
    except Exception as e:
        print(f"  Error dithering {input_path.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Dither avatar images for thermal printing.')
    parser.add_argument('--force', action='store_true', help='Re-dither even if output already exists')
    args = parser.parse_args()

    if not SRC_DIR.exists():
        print(f"Source folder not found: {SRC_DIR}")
        sys.exit(1)

    sources = [p for p in sorted(SRC_DIR.iterdir()) if p.suffix.lower() in IMAGE_EXTENSIONS]
    if not sources:
        print(f"No images found in {SRC_DIR}")
        sys.exit(0)

    print(f"Dithering {len(sources)} avatar(s): {SRC_DIR} → {DST_DIR}")

    ok = skip = fail = 0
    for src in sources:
        dst = DST_DIR / (src.stem + '.bmp')
        if dst.exists() and not args.force:
            print(f"  skip  {src.name}")
            skip += 1
            continue
        success = dither_image(src, dst)
        if success:
            print(f"  ok    {src.name} → {dst.name}")
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} dithered, {skip} skipped, {fail} failed.")


if __name__ == '__main__':
    main()

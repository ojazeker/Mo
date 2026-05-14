#!/usr/bin/env python3
"""Convert token images to dithered monochrome for thermal printing."""

from pathlib import Path

from dither_for_printer import dither_image


def dither_tokens(input_dir='images/token', output_dir='images_dithered/token'):
    """Dither flat token image files into BMP output."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        print(f"❌ Error: {input_dir} not found!")
        return False

    output_path.mkdir(parents=True, exist_ok=True)

    images = sorted(input_path.glob('*.jpg'))
    if not images:
        print(f"❌ Error: no JPG images found in {input_dir}!")
        return False

    print('🎨 Dithering token images for thermal printing...')
    print(f'   Source: {input_dir}/')
    print(f'   Output: {output_dir}/\n')

    processed = 0
    failed = 0

    for image_file in images:
        output_file = output_path / f"{image_file.stem}.bmp"
        if output_file.exists():
            processed += 1
            continue

        if dither_image(str(image_file), str(output_file)):
            processed += 1
        else:
            failed += 1

    print('\n✅ Dithering complete!')
    print(f'   Processed: {processed}')
    print(f'   Failed:    {failed}')
    return failed == 0


if __name__ == '__main__':
    raise SystemExit(0 if dither_tokens() else 1)
#!/usr/bin/env python3
"""
Remove card images that are no longer in creatures_for_download.json.
Safe to run after re-running extract_creatures.py — deletes images for cards
that were filtered out (alchemy, digital-only, funny, etc.).

Usage: python3 scripts/build/cleanup_images.py [--dry-run]
"""

import argparse
import json
from pathlib import Path


def safe_filename(name: str) -> str:
    return name.replace('/', '').replace('"', '').replace("'", '')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without deleting anything')
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent.parent
    creatures_file = root / 'cards_json' / 'creatures_for_download.json'
    card_images_dir = root / 'images' / 'creature'

    if not creatures_file.exists():
        print(f'Error: {creatures_file} not found. Run extract_creatures.py first.')
        return

    with open(creatures_file, 'r', encoding='utf-8') as f:
        creatures = json.load(f)

    # Build set of expected filenames: card_images/<cmc>/<name>.jpg
    expected = set()
    for c in creatures:
        cmc = int(c['cmc'])
        filename = safe_filename(c['name']) + '.jpg'
        expected.add(card_images_dir / str(cmc) / filename)

    # Find all jpg files on disk and delete those not in expected
    deleted = 0
    kept = 0
    for jpg in sorted(card_images_dir.rglob('*.jpg')):
        if jpg in expected:
            kept += 1
        else:
            if args.dry_run:
                print(f'  would delete: {jpg.relative_to(root)}')
            else:
                jpg.unlink()
            deleted += 1

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done.")
    print(f"  {'Would delete' if args.dry_run else 'Deleted'}: {deleted}")
    print(f"  Kept:    {kept}")


if __name__ == '__main__':
    main()

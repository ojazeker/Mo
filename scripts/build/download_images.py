#!/usr/bin/env python3
"""
Download card images from Scryfall API in batches.
Scryfall allows 70 items per request with a small delay between requests.

Usage:
  python3 download_images.py                               # creatures (default)
  python3 download_images.py --type instant                # instants
  python3 download_images.py --type artifact --cmc 3       # artifacts at CMC 3
  python3 download_images.py --type all                    # all types
  python3 download_images.py instants_for_download.json --type instant

Output: images/{type}_images/<cmc>/<name>.jpg files
"""

import json
import requests
import time
import io
import os
import sys
import argparse
from pathlib import Path

# Scryfall API settings
SCRYFALL_COLLECTION_URL = 'https://api.scryfall.com/cards/collection'
BATCH_SIZE = 70  # Scryfall's limit per request
DELAY_BETWEEN_BATCHES = 0.5  # seconds

# Default input files per card type (relative to project root)
TYPE_INPUT_FILES = {
    'creature':     'cards_json/creatures_for_download.json',
    'instant':      'cards_json/instants_for_download.json',
    'sorcery':      'cards_json/sorceries_for_download.json',
    'artifact':     'cards_json/artifacts_for_download.json',
    'enchantment':  'cards_json/enchantments_for_download.json',
    'land':         'cards_json/lands_for_download.json',
    'planeswalker': 'cards_json/planeswalkers_for_download.json',
    'battle':       'cards_json/battles_for_download.json',
}

def download_images(creatures_file=None, filter_cmc=None, card_type='creature'):
    """
    Download images from Scryfall for cards of the given type.
    Organizes into folders by CMC: images/{type}_images/0/, images/{type}_images/1/, etc.

    Args:
        creatures_file: Path to input JSON (defaults to type-based filename)
        filter_cmc: List of CMC values to download (e.g., [0, 1, 2])
        card_type: Card type slug (creature/instant/sorcery/artifact/enchantment/land/planeswalker)
    """
    OUTPUT_DIR = f'images/{card_type}'
    if creatures_file is None:
        creatures_file = TYPE_INPUT_FILES.get(card_type, f'cards_json/{card_type}s_for_download.json')
    
    # Load card data
    print(f"Loading {card_type} data from {creatures_file}...")
    try:
        with open(creatures_file, 'r', encoding='utf-8') as f:
            all_creatures = json.load(f)
    except FileNotFoundError:
        print(f"Error: {creatures_file} not found!")
        print(f"   Run: python3 scripts/build/extract_cards.py --type {card_type}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False

    # Filter by CMC if specified
    if filter_cmc:
        creatures = [c for c in all_creatures if int(c['cmc']) in filter_cmc]
        print(f"   Loaded {len(creatures)} {card_type}s (filtered to CMC {filter_cmc})")
        print(f"   (Total available: {len(all_creatures)})\n")
    else:
        creatures = all_creatures
        print(f"   Loaded {len(creatures)} {card_type}s\n")

    if not creatures:
        print(f"No {card_type}s found for specified CMC!")
        return False
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cmc_dirs = {}
    for cmc in range(21):  # CMC 0-20
        cmc_dir = Path(OUTPUT_DIR) / str(cmc)
        cmc_dir.mkdir(exist_ok=True)
        cmc_dirs[cmc] = cmc_dir

    # Pre-filter to only creatures that don't have an image yet — avoids
    # hitting Scryfall for cards we already have on disk.
    def _image_exists(creature):
        cmc = int(creature['cmc'])
        filename = creature['name'].replace('/', '').replace('"', '').replace("'", '')
        return (cmc_dirs[cmc] / f"{filename}.jpg").exists()

    total_before = len(creatures)
    creatures = [c for c in creatures if not _image_exists(c)]
    already_existed = total_before - len(creatures)
    print(f"   {already_existed} already on disk, {len(creatures)} to download\n")

    if not creatures:
        print("All images already downloaded.")
        return True

    # Batch process creatures
    downloaded = 0
    failed = 0
    skipped = 0

    print("Downloading from Scryfall API...\n")
    
    for batch_num in range(0, len(creatures), BATCH_SIZE):
        batch = creatures[batch_num:batch_num + BATCH_SIZE]
        batch_end = min(batch_num + BATCH_SIZE, len(creatures))
        
        # Build request payload.
        # Use name+set when we have a set code (pins to the oldest original printing).
        # Fall back to oracle_id for DFCs (names with //) or cards without a set code.
        payload = {
            'identifiers': [
                {'oracle_id': creature['oracle_id']}
                if '//' in creature['name'] or not creature.get('setCode')
                else {'name': creature['name'], 'set': creature['setCode'].lower()}
                for creature in batch
            ]
        }
        
        # Make API request
        try:
            print(f"Batch {batch_num // BATCH_SIZE + 1} ({batch_num + 1}-{batch_end} of {len(creatures)})...", end=' ', flush=True)
            response = requests.post(
                SCRYFALL_COLLECTION_URL,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Process response
            if 'data' in data:
                for card_data in data['data']:
                    # Match by oracle_id (works for both identifier types)
                    matching_creature = next(
                        (c for c in batch if c['oracle_id'] == card_data.get('oracle_id')),
                        None
                    )
                    
                    if not matching_creature:
                        continue
                    
                    # Collect image URLs — stitch vertically if card has two faces
                    faces = card_data.get('card_faces', [])
                    face_urls = []
                    if faces and all(f.get('image_uris', {}).get('large') for f in faces):
                        face_urls = [f['image_uris']['large'] for f in faces]
                    else:
                        single = card_data.get('image_uris', {}).get('large')
                        if single:
                            face_urls = [single]
                    if not face_urls:
                        skipped += 1
                        continue

                    # Download image
                    try:
                        from PIL import Image
                        cmc = int(matching_creature['cmc'])
                        filename = matching_creature['name'].replace('/', '').replace('"', '').replace("'", '')
                        filepath = cmc_dirs[cmc] / f"{filename}.jpg"

                        # Skip if already exists (shouldn't happen after pre-filter, but safe)
                        if filepath.exists():
                            continue

                        face_images = []
                        for url in face_urls:
                            r = requests.get(url, timeout=10)
                            r.raise_for_status()
                            face_images.append(Image.open(io.BytesIO(r.content)).convert('RGB'))

                        if len(face_images) == 1:
                            face_images[0].save(filepath, 'JPEG', quality=90)
                        else:
                            # Stitch faces vertically
                            w = face_images[0].width
                            total_h = sum(img.height for img in face_images)
                            stitched = Image.new('RGB', (w, total_h))
                            y = 0
                            for img in face_images:
                                stitched.paste(img, (0, y))
                                y += img.height
                            stitched.save(filepath, 'JPEG', quality=90)

                        downloaded += 1
                    
                    except Exception as e:
                        failed += 1
                        print(f"\n   Failed to download {matching_creature['name']}: {e}", flush=True)
            
            print(f"ok {len(data.get('data', []))} cards", flush=True)
            
            # Respect rate limits
            time.sleep(DELAY_BETWEEN_BATCHES)
        
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            failed += len(batch)
    
    print(f"\nDownload complete!")
    print(f"   Downloaded:      {downloaded}")
    print(f"   Already existed: {already_existed}")
    print(f"   Failed:          {failed}")
    print(f"   Skipped:         {skipped} (no image URL)")
    print(f"   Total:           {downloaded + already_existed}")
    print(f"   Directory:       {OUTPUT_DIR}/\n")

    return True

if __name__ == '__main__':
    VALID_TYPES = ['creature', 'instant', 'sorcery', 'artifact', 'enchantment', 'land', 'planeswalker', 'battle', 'all']

    parser = argparse.ArgumentParser(
        description='Download card images from Scryfall API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 download_images.py                          # All creatures
  python3 download_images.py --type instant           # Instants
  python3 download_images.py --type artifact --cmc 0  # Artifact at CMC 0
  python3 download_images.py --type all               # All types
  python3 download_images.py --cmc 1,2,3              # Creatures CMC 1-3
        """
    )

    parser.add_argument('cards_file', nargs='?', default=None,
                       help='Path to cards JSON file (default: auto based on --type)')
    parser.add_argument('--type', default='creature', choices=VALID_TYPES,
                       help='Card type to download (default: creature)')
    parser.add_argument('--cmc', type=str, help='CMC values to download (e.g., "0" or "0,1,2")')
    
    args = parser.parse_args()

    # Parse CMC filter
    filter_cmc = None
    if args.cmc:
        try:
            filter_cmc = [int(x.strip()) for x in args.cmc.split(',')]
        except ValueError:
            print(f"Error: Invalid CMC values '{args.cmc}'")
            exit(1)

    types_to_run = list(TYPE_INPUT_FILES) if args.type == 'all' else [args.type]
    success = True
    for t in types_to_run:
        input_file = args.cards_file if (len(types_to_run) == 1 and args.cards_file) else None
        if not download_images(input_file, filter_cmc, t):
            success = False

    exit(0 if success else 1)

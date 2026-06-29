#!/usr/bin/env python3
"""
Quick start: Extract and preprocess creatures directly.
Skips the intermediate JSON file, downloads directly.
"""

import ijson
import json
import requests
import time
import os
from io import BytesIO
from pathlib import Path
from PIL import Image

# Scryfall API settings
SCRYFALL_COLLECTION_URL = 'https://api.scryfall.com/cards/collection'
BATCH_SIZE = 70
DELAY_BETWEEN_BATCHES = 0.5
OUTPUT_DIR = 'images/creature'
# Scryfall rejects requests without a descriptive User-Agent/Accept header (HTTP 400).
SCRYFALL_HEADERS = {'User-Agent': 'MomirPrinter/1.0', 'Accept': '*/*'}


def sanitize_filename(name):
    """Make a card name safe for filesystem use."""
    return name.replace('/', '').replace('"', '').replace("'", '')


def download_image_bytes(url):
    """Download raw bytes for an image URL."""
    response = requests.get(url, timeout=10, headers=SCRYFALL_HEADERS)
    response.raise_for_status()
    return response.content


def save_single_face_image(image_url, output_path):
    """Download and save a single-face card image."""
    img_bytes = download_image_bytes(image_url)
    with open(output_path, 'wb') as f:
        f.write(img_bytes)


def pick_image_uri(image_uris):
    """Pick preferred Scryfall image size for thermal workflow."""
    if not isinstance(image_uris, dict):
        return None
    # 384px target print width: normal is usually sufficient and much smaller than large.
    return image_uris.get('normal') or image_uris.get('small') or image_uris.get('large')


def save_dual_face_stacked_image(face_urls, output_path):
    """Download two face images and stack them vertically into one JPG."""
    top_bytes = download_image_bytes(face_urls[0])
    bottom_bytes = download_image_bytes(face_urls[1])

    top_img = Image.open(BytesIO(top_bytes)).convert('RGB')
    bottom_img = Image.open(BytesIO(bottom_bytes)).convert('RGB')

    target_width = max(top_img.width, bottom_img.width)

    if top_img.width != target_width:
        top_height = int(top_img.height * (target_width / top_img.width))
        top_img = top_img.resize((target_width, top_height), Image.Resampling.LANCZOS)

    if bottom_img.width != target_width:
        bottom_height = int(bottom_img.height * (target_width / bottom_img.width))
        bottom_img = bottom_img.resize((target_width, bottom_height), Image.Resampling.LANCZOS)

    merged = Image.new('RGB', (target_width, top_img.height + bottom_img.height), 'white')
    merged.paste(top_img, (0, 0))
    merged.paste(bottom_img, (0, top_img.height))
    merged.save(output_path, format='JPEG', quality=92)

def run_pipeline(filter_cmc=None):
    """
    Extract creatures from AtomicCards.json and immediately download images.
    """
    
    print("📖 Reading AtomicCards.json...")
    print("This may take a minute (~147MB file)...\n")
    
    creatures = []
    processed = 0
    skipped = 0
    
    try:
        with open('AtomicCards.json', 'r', encoding='utf-8') as file:
            parser = ijson.kvitems(file, 'data')
            
            for card_name, card_printings in parser:
                if not isinstance(card_printings, list):
                    card_printings = [card_printings]
                
                card = card_printings[0]
                
                if 'Creature' not in card.get('type', ''):
                    skipped += 1
                    continue
                
                if card.get('name', '').startswith('A-'):
                    skipped += 1
                    continue
                
                if card.get('layout') in ['meld', 'scheme']:
                    skipped += 1
                    continue
                
                oracle_id = card.get('identifiers', {}).get('scryfallOracleId')
                if not oracle_id:
                    skipped += 1
                    continue
                
                creature = {
                    'name': card.get('name'),
                    'oracle_id': oracle_id,
                    'cmc': float(card.get('manaValue', 0)),
                    'type': card.get('type'),
                    'power': card.get('power', '?'),
                    'toughness': card.get('toughness', '?'),
                    'manaCost': card.get('manaCost', ''),
                    'setCode': card.get('setCode', ''),
                }
                
                creatures.append(creature)
                processed += 1
                
                if processed % 1000 == 0:
                    print(f"  Processed {processed} creatures...")
    
    except FileNotFoundError:
        print(f"❌ Error: AtomicCards.json not found!")
        return False
    except Exception as e:
        print(f"❌ Error parsing JSON: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n✅ Extraction complete!")
    print(f"   Found: {processed} creatures")
    print(f"   Skipped: {skipped}\n")
    
    # Count by CMC
    cmc_counts = {}
    for c in creatures:
        cmc = int(c['cmc'])
        cmc_counts[cmc] = cmc_counts.get(cmc, 0) + 1
    
    print("Creatures by CMC:")
    for cmc in sorted(cmc_counts.keys()):
        print(f"  CMC {cmc:2d}: {cmc_counts[cmc]:5d}")
    print()
    
    # Filter by CMC if specified
    if filter_cmc:
        creatures = [c for c in creatures if int(c['cmc']) in filter_cmc]
        print(f"\n🎯 Filtered to CMC {filter_cmc}: {len(creatures)} creatures\n")
    
    if not creatures:
        print("❌ No creatures to download!")
        return False
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for cmc in range(21):
        (Path(OUTPUT_DIR) / str(cmc)).mkdir(exist_ok=True)
    
    # Download images
    print("🌐 Downloading from Scryfall API...\n")
    
    downloaded = 0
    failed = 0
    skipped = 0
    already_existed = 0
    dual_faced_stacked = 0
    
    for batch_num in range(0, len(creatures), BATCH_SIZE):
        batch = creatures[batch_num:batch_num + BATCH_SIZE]
        batch_end = min(batch_num + BATCH_SIZE, len(creatures))
        
        payload = {
            'identifiers': [
                {'oracle_id': c['oracle_id']}
                for c in batch
            ]
        }
        
        try:
            print(f"Batch {batch_num // BATCH_SIZE + 1} ({batch_num + 1}-{batch_end})...", end=' ', flush=True)
            response = requests.post(
                SCRYFALL_COLLECTION_URL,
                json=payload,
                timeout=10,
                headers=SCRYFALL_HEADERS,
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data:
                for card_data in data['data']:
                    matching = next(
                        (c for c in batch if c['oracle_id'] == card_data.get('oracle_id')),
                        None
                    )
                    
                    if not matching:
                        continue

                    # Prefer normal image_uris for single-faced cards.
                    # Fall back to card_faces for dual-faced cards.
                    face_urls = []
                    single_image_url = pick_image_uri(card_data.get('image_uris', {}))
                    if single_image_url:
                        face_urls = [single_image_url]
                    else:
                        for face in card_data.get('card_faces', []):
                            face_url = pick_image_uri(face.get('image_uris', {}))
                            if face_url:
                                face_urls.append(face_url)

                    if not face_urls:
                        skipped += 1
                        continue
                    
                    try:
                        cmc = int(matching['cmc'])
                        filename = sanitize_filename(matching['name'])
                        filepath = Path(OUTPUT_DIR) / str(cmc) / f"{filename}.jpg"
                        
                        if filepath.exists():
                            already_existed += 1
                            continue

                        if len(face_urls) >= 2:
                            save_dual_face_stacked_image(face_urls[:2], filepath)
                            dual_faced_stacked += 1
                        else:
                            save_single_face_image(face_urls[0], filepath)
                        
                        downloaded += 1
                    
                    except Exception as e:
                        failed += 1
                        print(f"\n   ⚠️  {matching['name']}: {e}", flush=True)
            
            print(f"✓ {len(data.get('data', []))} cards")
            time.sleep(DELAY_BETWEEN_BATCHES)
        
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            failed += len(batch)
    
    print(f"\n✅ Download complete!")
    print(f"   Downloaded:     {downloaded}")
    print(f"   Already existed: {already_existed}")
    print(f"   Failed:         {failed}")
    print(f"   Skipped:        {skipped}")
    print(f"   DFC stacked:    {dual_faced_stacked}")
    print(f"   Directory:      {OUTPUT_DIR}/\n")
    
    return True

if __name__ == '__main__':
    import sys
    
    filter_cmc = None
    if len(sys.argv) > 1:
        try:
            filter_cmc = [int(x.strip()) for x in sys.argv[1].split(',')]
            print(f"Filter: CMC {filter_cmc}\n")
        except:
            print("Usage: python3 pipeline.py [cmc] or python3 pipeline.py [cmc1,cmc2,...]")
            print("Example: python3 pipeline.py 0")
            exit(1)
    
    if run_pipeline(filter_cmc):
        exit(0)
    else:
        exit(1)

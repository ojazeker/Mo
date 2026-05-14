#!/usr/bin/env python3
"""Download token metadata and images from Scryfall."""

import json
import time
from pathlib import Path

import requests


SCRYFALL_SEARCH_URL = 'https://api.scryfall.com/cards/search'
BATCH_SIZE = 70
DELAY_BETWEEN_BATCHES = 0.5
OUTPUT_DIR = Path('images/token')
OUTPUT_JSON = Path('app/data/token_data.json')

# Configurable image size: 'small', 'normal', 'large', etc.
IMAGE_SIZE = 'normal'  # Change to 'large' or 'small' if needed


def get_image_url(card, size=IMAGE_SIZE):
    """Return the best available image url for a Scryfall card object, with configurable size."""
    image_uris = card.get('image_uris') or {}
    if image_uris.get(size):
        return image_uris[size]

    card_faces = card.get('card_faces') or []
    for face in card_faces:
        face_uris = face.get('image_uris') or {}
        if face_uris.get(size):
            return face_uris[size]

    return None


def fetch_tokens():
    """Fetch all token printings from Scryfall, then pick the first printing for each oracle_id."""
    params = {
        'q': 'type:token lang:en -promo',  # Only English, exclude promos
        'unique': 'prints',  # Get all printings
        'order': 'released', # Oldest first
    }
    url = SCRYFALL_SEARCH_URL
    print('📥 Fetching all token printings from Scryfall...')
    all_prints = []
    while url:
        response = requests.get(url, params=params if url == SCRYFALL_SEARCH_URL else None, timeout=15)
        response.raise_for_status()
        payload = response.json()
        all_prints.extend(payload.get('data', []))
        url = payload.get('next_page') if payload.get('has_more') else None
        params = None

    # Group all printings by oracle_id
    from collections import defaultdict
    by_oracle = defaultdict(list)
    for card in all_prints:
        oracle_id = card.get('oracle_id')
        if not oracle_id:
            continue
        by_oracle[oracle_id].append(card)

    tokens = []
    for oracle_id, cards in by_oracle.items():
        # Sort by released_at (oldest first), fallback to empty string if missing
        cards_sorted = sorted(cards, key=lambda c: c.get('released_at') or '')
        for card in cards_sorted:
            image_url = get_image_url(card)
            if image_url:
                # Add 'colors' field, default to [] if missing
                tokens.append({
                    'id': card.get('id'),
                    'oracle_id': oracle_id,
                    'name': card.get('name', 'Unknown Token'),
                    'type_line': card.get('type_line', 'Token'),
                    'image_url': image_url,
                    'search_text': f"{card.get('name', '')} {card.get('type_line', '')}".lower(),
                    'colors': card.get('colors', []),
                })
                break  # Only take the oldest with an image
    print(f'   Selected {len(tokens)} unique tokens (oldest English printing per oracle_id)')
    return tokens


def download_token_images(tokens):
    """Download token images in batches and save local metadata."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    with OUTPUT_JSON.open('w', encoding='utf-8') as handle:
        json.dump(tokens, handle, indent=2)

    downloaded = 0
    skipped = 0
    failed = 0

    print(f'💾 Saved token metadata to {OUTPUT_JSON}')
    print(f'🌐 Downloading {len(tokens)} token images...\n')

    for start in range(0, len(tokens), BATCH_SIZE):
        batch = tokens[start:start + BATCH_SIZE]
        batch_end = min(start + BATCH_SIZE, len(tokens))
        print(f'Batch {start // BATCH_SIZE + 1} ({start + 1}-{batch_end} of {len(tokens)})...', end=' ')

        for token in batch:
            image_path = OUTPUT_DIR / f"{token['id']}.jpg"
            if image_path.exists():
                skipped += 1
                continue

            try:
                response = requests.get(token['image_url'], timeout=15)
                response.raise_for_status()
                image_path.write_bytes(response.content)
                downloaded += 1
            except requests.RequestException:
                failed += 1

        print('✓')
        time.sleep(DELAY_BETWEEN_BATCHES)

    print('\n✅ Token download complete!')
    print(f'   Downloaded: {downloaded}')
    print(f'   Skipped:    {skipped}')
    print(f'   Failed:     {failed}')
    print(f'   Images:     {OUTPUT_DIR}/')
    print(f'   Metadata:   {OUTPUT_JSON}')


def main():
    tokens = fetch_tokens()
    print(f'   Found {len(tokens)} unique token types\n')
    download_token_images(tokens)


if __name__ == '__main__':
    main()
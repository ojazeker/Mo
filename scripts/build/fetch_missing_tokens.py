#!/usr/bin/env python3
"""Fetch Scryfall metadata for token images that exist locally but are missing from token_data.json."""

import json
import time
from pathlib import Path

import requests

OUTPUT_JSON = Path('app/data/token_data.json')
IMAGE_DIR = Path('images/token')
SCRYFALL_CARD_URL = 'https://api.scryfall.com/cards/{id}'
DELAY = 0.1  # Scryfall rate limit: max 10 req/s
# Scryfall rejects requests without a descriptive User-Agent/Accept header (HTTP 400).
SCRYFALL_HEADERS = {'User-Agent': 'MomirPrinter/1.0', 'Accept': '*/*'}


def main():
    with OUTPUT_JSON.open('r', encoding='utf-8') as f:
        tokens = json.load(f)

    existing_ids = {t['id'] for t in tokens}
    all_image_ids = {p.stem for p in IMAGE_DIR.glob('*.jpg')}
    missing_ids = sorted(all_image_ids - existing_ids)

    print(f'Tokens in JSON:       {len(existing_ids)}')
    print(f'Local images:         {len(all_image_ids)}')
    print(f'Missing from JSON:    {len(missing_ids)}')

    if not missing_ids:
        print('Nothing to do.')
        return

    added = 0
    failed = []

    for i, token_id in enumerate(missing_ids, 1):
        print(f'[{i}/{len(missing_ids)}] {token_id}', end=' ... ')
        try:
            response = requests.get(
                SCRYFALL_CARD_URL.format(id=token_id),
                timeout=15,
                headers=SCRYFALL_HEADERS,
            )
            response.raise_for_status()
            card = response.json()

            image_uris = card.get('image_uris') or {}
            image_url = (
                image_uris.get('normal')
                or image_uris.get('large')
                or image_uris.get('small')
                or ''
            )
            if not image_url:
                for face in card.get('card_faces') or []:
                    face_uris = face.get('image_uris') or {}
                    image_url = face_uris.get('normal') or face_uris.get('large') or ''
                    if image_url:
                        break

            entry = {
                'id':           token_id,
                'oracle_id':    card.get('oracle_id', ''),
                'name':         card.get('name', 'Unknown Token'),
                'type_line':    card.get('type_line', 'Token'),
                'image_url':    image_url,
                'search_text':  f"{card.get('name', '')} {card.get('type_line', '')}".lower(),
                'colors':       card.get('colors', []),
                'power':        card.get('power', ''),
                'toughness':    card.get('toughness', ''),
                'keywords':     card.get('keywords', []),
                'oracle_text':  card.get('oracle_text', ''),
            }
            tokens.append(entry)
            added += 1
            print(f"OK ({card.get('name', '?')})")
        except Exception as e:
            print(f'FAILED ({e})')
            failed.append(token_id)

        time.sleep(DELAY)

    with OUTPUT_JSON.open('w', encoding='utf-8') as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)

    print(f'\nAdded:  {added}')
    print(f'Failed: {len(failed)}')
    if failed:
        print('Failed IDs:')
        for fid in failed:
            print(f'  {fid}')
    print(f'Saved to {OUTPUT_JSON}')


if __name__ == '__main__':
    main()

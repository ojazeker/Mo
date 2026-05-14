#!/usr/bin/env python3
"""Refresh token_data.json with extra fields: colors, power, toughness, keywords, oracle_text."""

import json
import time
from pathlib import Path

import requests

SCRYFALL_SEARCH_URL = 'https://api.scryfall.com/cards/search'
OUTPUT_JSON = Path('app/data/token_data.json')


def fetch_extra_fields():
    """Page through Scryfall token search and collect extra fields keyed by oracle_id."""
    params = {
        'q': 'type:token',
        'unique': 'cards',
        'order': 'name',
    }
    url = SCRYFALL_SEARCH_URL
    by_oracle_id = {}

    print('Fetching token metadata from Scryfall...')
    page = 0
    while url:
        response = requests.get(
            url,
            params=params if url == SCRYFALL_SEARCH_URL else None,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        page += 1

        for card in payload.get('data', []):
            oracle_id = card.get('oracle_id')
            if oracle_id:
                by_oracle_id[oracle_id] = {
                    'colors': card.get('colors', []),
                    'power': card.get('power', ''),
                    'toughness': card.get('toughness', ''),
                    'keywords': card.get('keywords', []),
                    'oracle_text': card.get('oracle_text', ''),
                }

        has_more = payload.get('has_more')
        url = payload.get('next_page') if has_more else None
        params = None

        if url:
            time.sleep(0.1)

    print(f'  Fetched {len(by_oracle_id)} token entries across {page} page(s)')
    return by_oracle_id


def main():
    if not OUTPUT_JSON.exists():
        print(f'Error: {OUTPUT_JSON} not found. Run download_tokens.py first.')
        return

    with OUTPUT_JSON.open('r', encoding='utf-8') as f:
        tokens = json.load(f)

    extra = fetch_extra_fields()

    updated = 0
    for token in tokens:
        oracle_id = token.get('oracle_id')
        if oracle_id and oracle_id in extra:
            token.update(extra[oracle_id])
            updated += 1

    with OUTPUT_JSON.open('w', encoding='utf-8') as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)

    print(f'Updated {updated}/{len(tokens)} tokens')
    print(f'Saved to {OUTPUT_JSON}')


if __name__ == '__main__':
    main()

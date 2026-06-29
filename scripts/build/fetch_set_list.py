#!/usr/bin/env python3
"""
Download MTGJSON SetList.json into cards_json/.
This is used by extract_creatures.py to resolve the oldest printing set code per card.

Usage: python3 scripts/build/fetch_set_list.py
Output: cards_json/SetList.json
"""

import json
import requests
from pathlib import Path

SETLIST_URL = 'https://mtgjson.com/api/v5/SetList.json'
HEADERS = {'User-Agent': 'MomirPrinter/1.0', 'Accept': '*/*'}


KEEP_FIELDS = {'code', 'name', 'type', 'releaseDate', 'keyruneCode', 'tokenSetCode', 'isOnlineOnly', 'isFoilOnly'}


def fetch_set_list(output_path: Path) -> bool:
    print(f'Downloading SetList.json from MTGJSON...')
    try:
        response = requests.get(SETLIST_URL, timeout=30, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        sets = data.get('data', [])
        slim = [{k: v for k, v in s.items() if k in KEEP_FIELDS} for s in sets]
        out_data = {'data': slim, 'meta': data.get('meta', {})}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, ensure_ascii=False, separators=(',', ':'))
        size_kb = output_path.stat().st_size // 1024
        print(f'Saved {len(slim)} sets to {output_path} ({size_kb}kb)')
        return True
    except Exception as e:
        print(f'Error: {e}')
        return False


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent.parent
    out = root / 'cards_json' / 'SetList.json'
    fetch_set_list(out)

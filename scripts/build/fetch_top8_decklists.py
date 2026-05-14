#!/usr/bin/env python3
"""
Fetch top-8 decklists from mtgtop8.com for offline use.

Scrapes the format pages, collects the top 8 decks per format,
downloads their full card lists, and stores them as .txt files.

Output structure:
  deck_lists/
    index.json            ← manifest used by the Flask API
    premodern/
      burn.txt
      ...
    modern/
      ...
    pauper/
      ...
    standard/
      ...

Run from the project root:
  python scripts/build/fetch_top8_decklists.py
"""

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Optional, List

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent.parent
DECK_LISTS_DIR = ROOT / 'deck_lists'

FORMATS = {
    'premodern': 'PREM',
    'modern':    'MO',
    'pauper':    'PAU',
    'standard':  'ST',
}

BASE_URL    = 'https://www.mtgtop8.com'
FORMAT_URL  = BASE_URL + '/format?f={code}'
MTGO_URL    = BASE_URL + '/mtgo?d={deck_id}'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

MAX_DECKS   = 8
REQUEST_DELAY = 1.2  # seconds between requests — be polite


def slugify(text: str) -> str:
    """Convert a deck name to a safe filename."""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[\s_-]+', '-', text)
    return text or 'deck'


def fetch(url: str) -> requests.Response:
    """GET a URL with a delay to avoid hammering the server."""
    time.sleep(REQUEST_DELAY)
    resp = SESSION.get(url, timeout=20)
    resp.raise_for_status()
    return resp


def get_event_ids_for_format(format_code: str) -> List[str]:
    """
    Parse the format landing page and return a list of event IDs.
    The most recent events appear first.
    """
    url = FORMAT_URL.format(code=format_code)
    print(f'  Fetching format page: {url}')
    resp = fetch(url)
    soup = BeautifulSoup(resp.text, 'html.parser')

    event_ids = []
    seen = set()
    for a in soup.find_all('a', href=True):
        m = re.search(r'[?&]e=(\d+)', a['href'])
        if m:
            eid = m.group(1)
            if eid not in seen:
                seen.add(eid)
                event_ids.append(eid)
    return event_ids


def get_deck_ids_for_format(format_code: str) -> List[dict]:
    """
    Get MAX_DECKS decks with unique archetype names from the most recent events.
    Duplicate archetype names are skipped; the next unique one is used instead.
    """
    event_ids = get_event_ids_for_format(format_code)
    if not event_ids:
        return []

    decks = []
    seen_deck_ids = set()
    seen_names = set()  # normalised archetype names already collected

    for event_id in event_ids[:6]:  # try up to 6 recent events to find 8 unique archetypes
        if len(decks) >= MAX_DECKS:
            break

        event_url = BASE_URL + f'/event?e={event_id}&f={format_code}'
        print(f'  Fetching event page: {event_url}')
        try:
            resp = fetch(event_url)
        except Exception as e:
            print(f'    WARNING: {e}')
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')

        for a in soup.find_all('a', href=True):
            href = a['href']
            dm = re.search(r'[?&]d=(\d+)', href)
            if not dm:
                continue
            deck_id = dm.group(1)
            if deck_id in seen_deck_ids:
                continue

            name = a.get_text(separator=' ', strip=True)
            # Skip empty names, UI labels, and download links
            if not name or name in ('→', 'Switch to Visual', 'MTGO', '.dec'):
                continue
            if len(name) < 3:
                continue
            if href.startswith('mtgo?') or href.startswith('dec?'):
                continue

            # Skip duplicate archetype names
            name_key = name.lower()
            if name_key in seen_names:
                seen_deck_ids.add(deck_id)  # mark as visited so we don't re-examine
                print(f'    Skipping duplicate archetype: {name}')
                continue

            seen_deck_ids.add(deck_id)
            seen_names.add(name_key)
            decks.append({'deck_id': deck_id, 'name': name})

            if len(decks) >= MAX_DECKS:
                break

    return decks


def download_decklist_text(deck_id: str) -> Optional[str]:
    """
    Download the MTGO-format decklist text from mtgtop8.
    Returns the raw text or None on failure.
    """
    url = MTGO_URL.format(deck_id=deck_id)
    try:
        resp = fetch(url)
        return resp.text.strip()
    except Exception as e:
        print(f'    WARNING: Could not download deck {deck_id}: {e}')
        return None


def normalize_decklist(raw: str) -> str:
    """
    Normalize an MTGO-exported decklist into our standard format:

        4 Counterspell
        17 Island
        ...
        Sideboard
        3 Annul

    Handles both "4 Card Name" and "4x Card Name" styles.
    Also strips comments and blank lines between entries.
    """
    lines_out = []
    section = 'deck'
    in_sideboard = False

    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()

        if lower in ('sideboard', 'side board', 'sb:', 'sideboard:'):
            if not in_sideboard:
                lines_out.append('Sideboard')
                in_sideboard = True
                section = 'sideboard'
            continue

        # "4x Counterspell" → "4 Counterspell"
        m = re.match(r'^(\d+)x?\s+(.+)$', line)
        if m:
            qty   = m.group(1)
            name  = m.group(2).strip()
            lines_out.append(f'{qty} {name}')
        # else skip non-card lines (comments etc.)

    return '\n'.join(lines_out)


def main():
    DECK_LISTS_DIR.mkdir(exist_ok=True)

    index = {}  # format_name → [{name, file}]

    for fmt_name, fmt_code in FORMATS.items():
        print(f'\n=== {fmt_name.upper()} ({fmt_code}) ===')
        fmt_dir = DECK_LISTS_DIR / fmt_name
        fmt_dir.mkdir(exist_ok=True)

        deck_entries = []
        decks_info = get_deck_ids_for_format(fmt_code)

        if not decks_info:
            print(f'  No decks found for {fmt_name}.')
            index[fmt_name] = []
            continue

        for deck in decks_info:
            deck_id   = deck['deck_id']
            deck_name = deck['name']
            slug      = slugify(deck_name)
            filename  = f'{slug}.txt'
            filepath  = fmt_dir / filename

            print(f'  [{deck_id}] {deck_name} → {filename}')

            raw_text = download_decklist_text(deck_id)
            if not raw_text:
                continue

            normalized = normalize_decklist(raw_text)
            if not normalized:
                print(f'    WARNING: Empty decklist after normalization, skipping.')
                continue

            filepath.write_text(normalized, encoding='utf-8')
            deck_entries.append({'name': deck_name, 'file': filename})

        index[fmt_name] = deck_entries
        print(f'  Saved {len(deck_entries)} decks.')

    index_path = DECK_LISTS_DIR / 'index.json'
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nIndex written to {index_path}')
    print('Done.')


if __name__ == '__main__':
    main()

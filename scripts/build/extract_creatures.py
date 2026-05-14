#!/usr/bin/env python3
"""
Extract creature data from all JSON files in cards_json/ using ijson for memory efficiency.
Creates a JSON file with Scryfall Oracle IDs and creature info for batch API lookup.

Drop AtomicCards.json or individual MTGJSON set files into cards_json/ and run this script.
Cards are deduplicated by oracle_id across all files.

Usage: python3 extract_creatures.py
Output: creatures_for_download.json
"""

import ijson
import json
from pathlib import Path


def _load_set_release_dates(cards_json_dir: Path) -> dict:
    """Load set release dates from SetList.json. Returns {code: date_str} or empty dict.
    Only includes regular paper set types — excludes promos, tokens, memorabilia, etc."""
    set_list_path = cards_json_dir / 'SetList.json'
    if not set_list_path.exists():
        print('  ⚠ SetList.json not found — set codes will be empty.')
        print('    Run scripts/build/fetch_set_list.py first for oldest-printing support.')
        return {}

    # Set types considered "real" printings for oldest-print resolution.
    # Excludes promos, tokens, memorabilia, digital-only, and special treatments.
    REGULAR_TYPES = {
        'core', 'expansion', 'masters', 'commander', 'draft_innovation',
        'duel_deck', 'starter', 'from_the_vault', 'premium_deck',
        'archenemy', 'planechase', 'eternal', 'box',
    }

    try:
        with open(set_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        sets = data.get('data', [])
        dates = {
            s['code']: s['releaseDate']
            for s in sets
            if s.get('code') and s.get('releaseDate') and s.get('type') in REGULAR_TYPES
        }
        print(f'  Loaded release dates for {len(dates)} sets')
        return dates
    except Exception as e:
        print(f'  ⚠ Could not load SetList.json: {e}')
        return {}


def _oldest_set_code(printings: list, release_dates: dict) -> str:
    """Return the set code with the earliest release date from a card's printings list."""
    if not printings or not release_dates:
        return ''
    dated = [(release_dates[p], p) for p in printings if p in release_dates]
    if not dated:
        return ''
    return min(dated)[1]


def _is_set_format(json_path):
    """Return True if the file is an MTGJSON per-set file (data.cards list)
    rather than AtomicCards format (data is a dict of card_name -> printings)."""
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            # Peek at the first key under data — set files have 'baseSetSize' etc.
            for key, _ in ijson.kvitems(f, 'data'):
                return key in ('baseSetSize', 'cards', 'code', 'name', 'releaseDate')
        except Exception:
            pass
    return False


def _iter_set_cards(json_path):
    """Yield individual card dicts from an MTGJSON per-set file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        for card in ijson.items(f, 'data.cards.item'):
            yield card


def _iter_atomic_cards(json_path):
    """Yield the first printing dict from each card in an AtomicCards file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        for _card_name, printings in ijson.kvitems(f, 'data'):
            if not isinstance(printings, list):
                continue
            if printings:
                yield printings[0]


def extract_creatures_from_file(json_path, seen_oracle_ids, creatures, release_dates=None):
    """Parse one MTGJSON file and append new creatures to the list."""
    if release_dates is None:
        release_dates = {}
    processed = 0
    skipped = 0

    print(f"\nReading {json_path.name}...")

    if _is_set_format(json_path):
        card_iter = _iter_set_cards(json_path)
    else:
        card_iter = _iter_atomic_cards(json_path)

    for card in card_iter:
        if not isinstance(card, dict):
            skipped += 1
            continue

        if 'Creature' not in card.get('type', ''):
            skipped += 1
            continue

        if card.get('name', '').startswith('A-'):
            skipped += 1
            continue

        # Skip digital-only cards (Arena/Alchemy sets not available in paper).
        # availability field is null for some cards, so also check if all printings
        # are in non-regular set types (e.g. alchemy, treasure_chest).
        availability = card.get('availability') or []
        if availability and 'paper' not in availability:
            skipped += 1
            continue
        printings = card.get('printings', [])
        if printings and release_dates and not any(p in release_dates for p in printings):
            skipped += 1
            continue

        # Skip funny cards (Un-sets, acorn cards, etc.)
        if card.get('isFunny'):
            skipped += 1
            continue

        if card.get('layout') in ['meld', 'scheme']:
            skipped += 1
            continue

        oracle_id = card.get('identifiers', {}).get('scryfallOracleId') or card.get('scryfallOracleId')
        if not oracle_id:
            skipped += 1
            continue

        if oracle_id in seen_oracle_ids:
            skipped += 1
            continue

        seen_oracle_ids.add(oracle_id)

        set_code = _oldest_set_code(card.get('printings', []), release_dates)

        creatures.append({
            'name': card.get('name'),
            'oracle_id': str(oracle_id),
            'cmc': float(card.get('manaValue', 0)),
            'type': card.get('type'),
            'power': card.get('power', '?'),
            'toughness': card.get('toughness', '?'),
            'manaCost': card.get('manaCost', ''),
            'setCode': set_code,
        })
        processed += 1

        if processed % 1000 == 0:
            print(f"  Processed {processed} creatures...")

    print(f"  → {processed} new creatures ({skipped} skipped/duplicate)")
    return processed


def extract_creatures(cards_json_dir='cards_json', output_file='creatures_for_download.json'):
    cards_json_dir = Path(cards_json_dir)
    release_dates = _load_set_release_dates(cards_json_dir)
    json_files = sorted([p for p in cards_json_dir.glob('*.json') if p.name != 'SetList.json'])

    if not json_files:
        print(f"No JSON files found in {cards_json_dir}/")
        print("   Place AtomicCards.json or individual set JSONs there first.")
        return False

    print(f"Found {len(json_files)} file(s) in {cards_json_dir}:")
    for f in json_files:
        print(f"  {f.name}")

    creatures = []
    seen_oracle_ids = set()

    for json_path in json_files:
        try:
            extract_creatures_from_file(json_path, seen_oracle_ids, creatures, release_dates)
        except Exception as e:
            print(f"Error reading {json_path.name}: {e}")
            continue

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(creatures, f, indent=2)

        print(f"\nTotal: {len(creatures)} unique creatures -> {output_file}")

        cmc_counts = {}
        for c in creatures:
            cmc = int(c['cmc'])
            cmc_counts[cmc] = cmc_counts.get(cmc, 0) + 1

        print("\nCreatures by CMC:")
        for cmc in sorted(cmc_counts.keys()):
            print(f"  CMC {cmc:2d}: {cmc_counts[cmc]:5d}")

        return True

    except Exception as e:
        print(f"Error writing output: {e}")
        return False


if __name__ == '__main__':
    root = Path(__file__).parent.parent.parent
    cards_json_dir = root / 'cards_json'

    if not cards_json_dir.exists():
        print(f"Missing {cards_json_dir}/")
        print("   Create it and place your JSON files inside.")
        exit(1)

    if extract_creatures(str(cards_json_dir), str(root / 'cards_json' / 'creatures_for_download.json')):
        exit(0)
    else:
        exit(1)


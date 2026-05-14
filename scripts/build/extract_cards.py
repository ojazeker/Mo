#!/usr/bin/env python3
"""
Extract card data from all JSON files in cards_json/ using ijson for memory efficiency.
Creates a JSON file with Scryfall Oracle IDs and card info for batch API lookup.

Supports all main card types: creature, instant, sorcery, artifact, enchantment,
land, planeswalker.

Drop AtomicCards.json or individual MTGJSON set files into cards_json/ and run.
Cards are deduplicated by oracle_id across all files.

Usage:
  python3 extract_cards.py                        # creatures (default)
  python3 extract_cards.py --type instant
  python3 extract_cards.py --type artifact
  python3 extract_cards.py --type land
  python3 extract_cards.py --type planeswalker
  python3 extract_cards.py --type all             # extract every type at once

Output: {type}s_for_download.json  (e.g. instants_for_download.json)
        Special cases: sorceries, planeswalkers (correct plurals)
"""

import ijson
import json
import argparse
from pathlib import Path


# ── Type filters ───────────────────────────────────────────────────────────────
# Each filter returns True if a card belongs to that type bucket.
# Priority order matters: a card lands in the FIRST bucket whose filter matches.
# e.g. "Artifact Creature" → creature; "Artifact Land" → land.
CARD_TYPE_FILTERS = {
    'creature':     lambda t: 'Creature' in t,
    'planeswalker': lambda t: 'Planeswalker' in t and 'Creature' not in t,
    'battle':       lambda t: 'Battle' in t,
    'land':         lambda t: 'Land' in t and 'Creature' not in t,
    'instant':      lambda t: 'Instant' in t,
    'sorcery':      lambda t: 'Sorcery' in t,
    'artifact':     lambda t: 'Artifact' in t and 'Creature' not in t and 'Land' not in t,
    'enchantment':  lambda t: 'Enchantment' in t and 'Creature' not in t,
}

# Output JSON filenames per type (relative to project root)
TYPE_OUTPUT_FILES = {
    'creature':     'cards_json/creatures_for_download.json',
    'instant':      'cards_json/instants_for_download.json',
    'sorcery':      'cards_json/sorceries_for_download.json',
    'artifact':     'cards_json/artifacts_for_download.json',
    'enchantment':  'cards_json/enchantments_for_download.json',
    'land':         'cards_json/lands_for_download.json',
    'planeswalker': 'cards_json/planeswalkers_for_download.json',
    'battle':       'cards_json/battles_for_download.json',
}


# ── MTGJSON helpers (shared with extract_creatures.py logic) ──────────────────

def _load_set_release_dates(cards_json_dir: Path) -> dict:
    """Load set release dates from SetList.json. Returns {code: date_str} or empty dict."""
    set_list_path = cards_json_dir / 'SetList.json'
    if not set_list_path.exists():
        print('  ⚠ SetList.json not found — set codes will be empty.')
        print('    Run scripts/build/fetch_set_list.py first for oldest-printing support.')
        return {}

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
    """Return True if the file is an MTGJSON per-set file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            for key, _ in ijson.kvitems(f, 'data'):
                return key in ('baseSetSize', 'cards', 'code', 'name', 'releaseDate')
        except Exception:
            pass
    return False


def _iter_set_cards(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        for card in ijson.items(f, 'data.cards.item'):
            yield card


def _iter_atomic_cards(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        for _card_name, printings in ijson.kvitems(f, 'data'):
            if not isinstance(printings, list):
                continue
            if printings:
                yield printings[0]


# ── Core extraction ────────────────────────────────────────────────────────────

def _is_valid_card(card: dict, release_dates: dict) -> bool:
    """Shared validity checks that apply across all card types."""
    if not isinstance(card, dict):
        return False
    if card.get('name', '').startswith('A-'):
        return False  # Alchemy variants
    availability = card.get('availability') or []
    if availability and 'paper' not in availability:
        return False  # digital-only
    printings = card.get('printings', [])
    if printings and release_dates and not any(p in release_dates for p in printings):
        return False  # no paper printing in a regular set
    if card.get('isFunny'):
        return False  # Un-sets, acorn cards
    if card.get('layout') in ('meld', 'scheme'):
        return False
    return True


def extract_cards_from_file(json_path, seen_oracle_ids, cards, card_type, release_dates=None):
    """Parse one MTGJSON file and append new cards of the given type."""
    if release_dates is None:
        release_dates = {}

    type_filter = CARD_TYPE_FILTERS[card_type]
    processed = skipped = 0

    print(f"\nReading {json_path.name}...")

    if _is_set_format(json_path):
        card_iter = _iter_set_cards(json_path)
    else:
        card_iter = _iter_atomic_cards(json_path)

    for card in card_iter:
        if not _is_valid_card(card, release_dates):
            skipped += 1
            continue

        card_type_str = card.get('type', '')
        if not type_filter(card_type_str):
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

        entry = {
            'name':       card.get('name'),
            'oracle_id':  str(oracle_id),
            'cmc':        float(card.get('manaValue', 0)),
            'type':       card_type_str,
            'manaCost':   card.get('manaCost', ''),
            'setCode':    set_code,
        }
        # Include power/toughness only for creatures
        if card_type == 'creature':
            entry['power']     = card.get('power', '?')
            entry['toughness'] = card.get('toughness', '?')

        cards.append(entry)
        processed += 1

        if processed % 1000 == 0:
            print(f"  Processed {processed} {card_type}s...")

    print(f"  → {processed} new {card_type}s ({skipped} skipped/duplicate)")
    return processed


def extract_cards(card_type, cards_json_dir='cards_json', output_file=None):
    """Extract all cards of the given type from MTGJSON files and write JSON."""
    if card_type not in CARD_TYPE_FILTERS:
        print(f"Unknown card type: {card_type}")
        print(f"Valid types: {', '.join(CARD_TYPE_FILTERS)}")
        return False

    if output_file is None:
        output_file = TYPE_OUTPUT_FILES[card_type]

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

    cards = []
    seen_oracle_ids = set()

    for json_path in json_files:
        try:
            extract_cards_from_file(json_path, seen_oracle_ids, cards, card_type, release_dates)
        except Exception as e:
            print(f"Error reading {json_path.name}: {e}")
            continue

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2)

        print(f"\nTotal: {len(cards)} unique {card_type}s → {output_file}")

        cmc_counts = {}
        for c in cards:
            cmc = int(c['cmc'])
            cmc_counts[cmc] = cmc_counts.get(cmc, 0) + 1

        print(f"\n{card_type.capitalize()}s by CMC:")
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

    parser = argparse.ArgumentParser(
        description='Extract cards by type from MTGJSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 extract_cards.py                    # creatures (default)
  python3 extract_cards.py --type instant
  python3 extract_cards.py --type artifact
  python3 extract_cards.py --type all         # all types at once
        """,
    )
    parser.add_argument(
        '--type',
        default='creature',
        choices=list(CARD_TYPE_FILTERS) + ['all'],
        help='Card type to extract (default: creature)',
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output JSON file (default: auto based on type)',
    )
    args = parser.parse_args()

    types_to_run = list(CARD_TYPE_FILTERS) if args.type == 'all' else [args.type]
    success = True
    for t in types_to_run:
        out = args.output if (len(types_to_run) == 1 and args.output) else None
        out = out or str(root / TYPE_OUTPUT_FILES[t])
        if not extract_cards(t, str(cards_json_dir), out):
            success = False

    exit(0 if success else 1)

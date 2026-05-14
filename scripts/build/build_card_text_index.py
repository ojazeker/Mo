#!/usr/bin/env python3
"""Build a compact per-card metadata file for offline card text display.

Reads all JSON files from cards_json/ (AtomicCards.json + any individual set
files) and writes app/card_text_index.json with only the fields needed at
runtime to render rules text under local card images.

Covers all supported card types: creature, instant, sorcery, artifact,
enchantment, land, planeswalker. Each entry includes a 'card_type' slug.

To add a new set: drop its MTGJSON AllPrintings-format JSON into cards_json/
and re-run this script. Cards already in AtomicCards.json are deduplicated.
"""

import json
from pathlib import Path


_EXCLUDED_SET_TYPES = {'funny', 'alchemy'}


def _load_excluded_set_codes(cards_json_dir: Path) -> set:
    """Return set codes for funny and alchemy sets from SetList.json."""
    set_list_path = cards_json_dir / 'SetList.json'
    if not set_list_path.exists():
        return set()
    try:
        with open(set_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        codes = {
            s['code']
            for s in data.get('data', [])
            if s.get('type') in _EXCLUDED_SET_TYPES and s.get('code')
        }
        print(f"  Excluding {len(codes)} funny/alchemy set codes")
        return codes
    except Exception as e:
        print(f"  ⚠ Could not load SetList.json: {e}")
        return set()


# Priority-ordered type classification (first match wins)
_TYPE_CHECKS = [
    ('creature',     lambda t: 'Creature'    in t),
    ('planeswalker', lambda t: 'Planeswalker' in t),
    ('battle',       lambda t: 'Battle'      in t),
    ('land',         lambda t: 'Land'        in t),
    ('instant',      lambda t: 'Instant'     in t),
    ('sorcery',      lambda t: 'Sorcery'     in t),
    ('artifact',     lambda t: 'Artifact'    in t),
    ('enchantment',  lambda t: 'Enchantment' in t),
]


def card_type_slug(type_str: str):
    """Return the card type slug for a given MTGJSON type string, or None to skip."""
    for slug, test in _TYPE_CHECKS:
        if test(type_str):
            return slug
    return None  # Battle, Conspiracy, Dungeon, etc.


def normalize_name(name: str) -> str:
    return (name or "").replace("/", "").replace('"', "").replace("'", "").strip().lower()


def iter_card_data(json_path: Path):
    """Yield individual card dicts from an MTGJSON data file.
    Handles both AtomicCards format (data = {card_name: [printings]})
    and per-set format (data = {cards: [...], code: ..., ...}).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        print(f"  ⚠ Unexpected format in {json_path.name}, skipping")
        return

    # Per-set format: data has a 'cards' list
    if "cards" in data and isinstance(data["cards"], list):
        for card in data["cards"]:
            if isinstance(card, dict):
                yield card
        return

    # AtomicCards format: data is {card_name: [printings_list]}
    for card_name, printings in data.items():
        if not isinstance(printings, list):
            continue
        for printing in printings:
            if isinstance(printing, dict):
                yield printing


def build_card_text_index(
    cards_json_dir: Path,
    output_path: Path,
) -> None:
    json_files = sorted(cards_json_dir.glob("*.json"))
    json_files = [f for f in json_files if f.name != 'SetList.json']
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {cards_json_dir}")

    excluded_sets = _load_excluded_set_codes(cards_json_dir)

    print(f"Found {len(json_files)} file(s) in {cards_json_dir}:")
    for f in json_files:
        print(f"  {f.name}")

    entries = []
    seen = set()
    type_counts = {}

    for json_file in json_files:
        print(f"\nReading {json_file.name}...")
        file_count = 0
        for printing in iter_card_data(json_file):
            if not isinstance(printing, dict):
                continue

            name = printing.get("name", "")
            if not name:
                continue

            if name.startswith('A-'):
                continue  # Alchemy variants

            if printing.get('isFunny'):
                continue  # Un-set / acorn cards

            availability = printing.get('availability', [])
            if availability and 'paper' not in availability:
                continue  # Digital-only (MTGO, Arena, etc.)

            # Per-printing setCode (per-set files) or printings list (AtomicCards)
            set_code = printing.get("setCode", "")
            if set_code and set_code in excluded_sets:
                continue  # Funny or alchemy set
            printings_list = printing.get("printings", [])
            if printings_list and all(code in excluded_sets for code in printings_list):
                continue  # Only ever printed in funny/alchemy sets

            card_type_str = printing.get("type", "")
            slug = card_type_slug(card_type_str)
            if slug is None:
                continue  # skip Battle, Conspiracy, Dungeon, etc.

            cmc = printing.get("manaValue", 0)
            text = (printing.get("text") or "").strip()
            mana_cost = printing.get("manaCost", "")
            power = printing.get("power", "?")
            toughness = printing.get("toughness", "?")

            key = (normalize_name(name), cmc, text, power, toughness)
            if key in seen:
                continue
            seen.add(key)

            entries.append(
                {
                    "name": name,
                    "manaValue": cmc,
                    "text": text,
                    "type": card_type_str,
                    "card_type": slug,
                    "manaCost": mana_cost,
                    "power": power,
                    "toughness": toughness,
                }
            )
            type_counts[slug] = type_counts.get(slug, 0) + 1
            file_count += 1
        print(f"  → {file_count} new entries")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nWrote {len(entries)} total entries to {output_path} ({size_mb:.2f} MB)")
    print("\nBy type:")
    for slug, count in sorted(type_counts.items()):
        print(f"  {slug:<14} {count:>6}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    cards_json_dir = root / "cards_json"
    out_path = root / "app" / "data" / "card_text_index.json"

    if not cards_json_dir.exists():
        raise FileNotFoundError(
            f"Missing {cards_json_dir}\n"
            "Create it and place AtomicCards.json (or individual set JSONs) inside."
        )

    build_card_text_index(cards_json_dir, out_path)

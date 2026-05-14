#!/usr/bin/env python3
"""
Add new cards from an MTGJSON set file to the Momir printer.

Handles all supported card types: creature, instant, sorcery, artifact,
enchantment, land, planeswalker. Each type is stored in its own image folder.

Usage:
    python3 scripts/build/add_cards.py cards_json/additional_sets/SOS.json
    python3 scripts/build/add_cards.py cards_json/additional_sets/SOS.json --type creature
    python3 scripts/build/add_cards.py cards_json/additional_sets/SOS.json --brightness 15

Steps:
  1. Parse the set JSON, extract new cards not in card_text_index.json
  2. Download their images from Scryfall (only the new ones)
  3. Dither the downloaded images (Floyd-Steinberg + brightness lift)
  4. Rebuild app/card_text_index.json from all JSONs in cards_json/
"""

import argparse
import json
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageOps, ImageStat

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT        = Path(__file__).resolve().parent.parent.parent
CARDS_JSON          = PROJECT_ROOT / 'cards_json'
IMAGES_ROOT         = PROJECT_ROOT / 'images'
IMAGES_DITHERED_ROOT = PROJECT_ROOT / 'images_dithered'
INDEX_PATH          = PROJECT_ROOT / 'app' / 'data' / 'card_text_index.json'

# ── Scryfall ───────────────────────────────────────────────────────────────────
SCRYFALL_URL  = 'https://api.scryfall.com/cards/collection'
BATCH_SIZE    = 70
BATCH_DELAY   = 0.1   # seconds between Scryfall requests

# ── Dithering ─────────────────────────────────────────────────────────────────
PRINTER_WIDTH = 384

# ── Card type filters (priority order — first match wins) ─────────────────────
CARD_TYPE_FILTERS = [
    ('creature',     lambda t: 'Creature'     in t),
    ('planeswalker', lambda t: 'Planeswalker' in t and 'Creature' not in t),
    ('battle',       lambda t: 'Battle'       in t),
    ('land',         lambda t: 'Land'         in t and 'Creature' not in t),
    ('instant',      lambda t: 'Instant'      in t),
    ('sorcery',      lambda t: 'Sorcery'      in t),
    ('artifact',     lambda t: 'Artifact'     in t and 'Creature' not in t and 'Land' not in t),
    ('enchantment',  lambda t: 'Enchantment'  in t and 'Creature' not in t),
]

ALL_TYPES = [slug for slug, _ in CARD_TYPE_FILTERS]


def _card_type_slug(type_str: str):
    for slug, test in CARD_TYPE_FILTERS:
        if test(type_str):
            return slug
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers shared across steps
# ─────────────────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    return name.replace('/', '').replace('"', '').replace("'", '')


def _save_dfc_stacked(face_urls: list, dest: Path) -> None:
    """Download two face images and stack them vertically into one JPG."""
    imgs = []
    for url in face_urls[:2]:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        imgs.append(Image.open(BytesIO(r.content)).convert('RGB'))
    w = max(i.width for i in imgs)
    resized = []
    for img in imgs:
        if img.width != w:
            img = img.resize((w, int(img.height * w / img.width)), Image.LANCZOS)
        resized.append(img)
    combined = Image.new('RGB', (w, sum(i.height for i in resized)))
    y = 0
    for img in resized:
        combined.paste(img, (0, y))
        y += img.height
    combined.save(str(dest), 'JPEG', quality=85)


def _image_path(name: str, cmc: int, card_type: str) -> Path:
    return IMAGES_ROOT / card_type / str(cmc) / f"{_safe_filename(name)}.jpg"


def _dithered_path(name: str, cmc: int, card_type: str) -> Path:
    return IMAGES_DITHERED_ROOT / card_type / str(cmc) / f"{_safe_filename(name)}.bmp"


def _normalize(name: str) -> str:
    return name.replace('/', '').replace('"', '').replace("'", '').strip().lower()


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — extract new cards from the set JSON
# ─────────────────────────────────────────────────────────────────────────────

def _iter_set_cards(json_path: Path):
    """Yield card dicts from an MTGJSON set file OR AtomicCards file."""
    with open(json_path, encoding='utf-8') as f:
        raw = json.load(f)

    data = raw.get('data', {}) if isinstance(raw, dict) else {}

    # Per-set format: data has a 'cards' list
    if 'cards' in data and isinstance(data['cards'], list):
        yield from data['cards']
        return

    # AtomicCards format: data is {card_name: [printings]}
    for printings in data.values():
        if isinstance(printings, list):
            for p in printings:
                if isinstance(p, dict):
                    yield p


def extract_new_cards(json_path: Path, card_type: str) -> list[dict]:
    """Return cards of card_type from json_path not already in the index or on disk."""
    # Build set of normalized names already indexed for this type
    known: set[str] = set()
    if INDEX_PATH.exists():
        with open(INDEX_PATH, encoding='utf-8') as f:
            for entry in json.load(f):
                if entry.get('card_type') == card_type:
                    known.add(_normalize(entry.get('name', '')))

    new_cards = []
    seen_in_file: set[str] = set()

    for card in _iter_set_cards(json_path):
        if not isinstance(card, dict):
            continue
        if _card_type_slug(card.get('type', '')) != card_type:
            continue
        if card.get('name', '').startswith('A-'):
            continue
        # Skip digital-only cards (Arena/Alchemy sets not available in paper)
        availability = card.get('availability', [])
        if availability and 'paper' not in availability:
            continue
        # Skip funny cards (Un-sets, acorn cards, etc.)
        if card.get('isFunny'):
            continue
        if card.get('layout') in ('meld', 'scheme'):
            continue

        name = card.get('name', '')
        if not name:
            continue

        norm = _normalize(name)
        if norm in known or norm in seen_in_file:
            continue
        seen_in_file.add(norm)

        # Also skip if image already on disk (re-run safety)
        cmc = int(float(card.get('manaValue', 0)))
        if _image_path(name, cmc, card_type).exists():
            continue

        oracle_id = (card.get('identifiers') or {}).get('scryfallOracleId') \
                    or card.get('scryfallOracleId', '')

        new_cards.append({
            'name':       name,
            'oracle_id':  str(oracle_id),
            'cmc':        cmc,
            'type':       card.get('type', ''),
            'card_type':  card_type,
            'power':      card.get('power', '?'),
            'toughness':  card.get('toughness', '?'),
            'manaCost':   card.get('manaCost', ''),
        })

    return new_cards


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — download images from Scryfall
# ─────────────────────────────────────────────────────────────────────────────

def download_cards(cards: list[dict]) -> list[dict]:
    """Download images; return list of cards that were successfully saved."""
    if not cards:
        return []

    card_type = cards[0]['card_type']

    # Ensure output dirs exist
    for cmc in range(21):
        (IMAGES_ROOT / card_type / str(cmc)).mkdir(parents=True, exist_ok=True)

    saved = []
    failed = 0

    print(f"\n   Downloading {len(cards)} image(s) from Scryfall...")

    for i in range(0, len(cards), BATCH_SIZE):
        batch = cards[i:i + BATCH_SIZE]

        # Build identifier list — prefer oracle_id, fall back to name
        identifiers = []
        for c in batch:
            if c['oracle_id']:
                identifiers.append({'oracle_id': c['oracle_id']})
            else:
                identifiers.append({'name': c['name']})

        try:
            resp = requests.post(
                SCRYFALL_URL,
                json={'identifiers': identifiers},
                timeout=15,
                headers={'User-Agent': 'MomirPrinter/1.0'},
            )
            resp.raise_for_status()
            api_cards = resp.json().get('data', [])
        except requests.RequestException as e:
            print(f"   ❌ Scryfall API error: {e}")
            failed += len(batch)
            continue

        # Map oracle_id → api card
        by_oracle = {c.get('oracle_id', ''): c for c in api_cards}
        # Also map name → api card for fallback
        by_name   = {_normalize(c.get('name', '')): c for c in api_cards}

        for card in batch:
            api_card = by_oracle.get(card['oracle_id']) \
                       or by_name.get(_normalize(card['name']))
            if not api_card:
                print(f"   ⚠  Not found on Scryfall: {card['name']}")
                failed += 1
                continue

            # Single-faced card: use image_uris.large
            # Double-faced card: image_uris is absent; use card_faces[].image_uris
            image_url = api_card.get('image_uris', {}).get('large')
            face_urls = []
            if image_url:
                face_urls = [image_url]
            else:
                for face in api_card.get('card_faces', []):
                    u = face.get('image_uris', {}).get('large')
                    if u:
                        face_urls.append(u)

            if not face_urls:
                print(f"   ⚠  No image URL for: {card['name']}")
                failed += 1
                continue

            dest = _image_path(card['name'], card['cmc'], card['card_type'])
            try:
                if len(face_urls) >= 2:
                    _save_dfc_stacked(face_urls, dest)
                    print(f"   ✓  {card['name']} (DFC stacked)")
                else:
                    img_resp = requests.get(face_urls[0], timeout=15)
                    img_resp.raise_for_status()
                    dest.write_bytes(img_resp.content)
                    print(f"   ✓  {card['name']}")
                saved.append(card)
            except requests.RequestException as e:
                print(f"   ❌ Download failed for {card['name']}: {e}")
                failed += 1

        if i + BATCH_SIZE < len(cards):
            time.sleep(BATCH_DELAY)

    print(f"   Saved: {len(saved)}, Failed: {failed}")
    return saved


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — dither downloaded images
# ─────────────────────────────────────────────────────────────────────────────

def _auto_brightness_factor(gray_img, dark_threshold=100, target_lum=140):
    mean_lum = ImageStat.Stat(gray_img).mean[0]
    if mean_lum >= dark_threshold or mean_lum < 1:
        return 1.0
    return target_lum / mean_lum


def dither_card(card: dict, brightness_boost: int) -> bool:
    card_type = card['card_type']
    src = _image_path(card['name'], card['cmc'], card_type)
    dst = _dithered_path(card['name'], card['cmc'], card_type)
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        img  = Image.open(src).convert('RGB')
        new_h = int(PRINTER_WIDTH * img.height / img.width)
        img  = img.resize((PRINTER_WIDTH, new_h), Image.Resampling.LANCZOS)
        gray = ImageOps.grayscale(img)

        factor = _auto_brightness_factor(gray) + (brightness_boost / 100.0)
        if factor > 1.0:
            gray = ImageEnhance.Brightness(gray).enhance(factor)

        gray.convert('1', dither=Image.Dither.FLOYDSTEINBERG).save(dst, 'BMP')
        return True
    except Exception as e:
        print(f"   ❌ Dither failed for {card['name']}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — rebuild card_text_index.json (delegates to build_card_text_index.py)
# ─────────────────────────────────────────────────────────────────────────────

def rebuild_index():
    build_script = Path(__file__).parent / 'build_card_text_index.py'
    result = subprocess.run(
        [sys.executable, str(build_script)],
        check=False,
    )
    if result.returncode != 0:
        print(f"   ❌ build_card_text_index.py exited with code {result.returncode}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Add new cards from an MTGJSON set file to the Momir printer.'
    )
    parser.add_argument('json_file', help='Path to the set JSON file (e.g. cards_json/additional_sets/SOS.json)')
    parser.add_argument('--type', dest='card_type', default='all',
                        choices=ALL_TYPES + ['all'],
                        help='Card type(s) to process (default: all)')
    parser.add_argument('--brightness', type=int, default=15,
                        help='Extra brightness boost %% for dithering (default: 15)')
    args = parser.parse_args()

    json_path = Path(args.json_file)
    if not json_path.exists():
        # Try relative to cards_json/
        json_path = CARDS_JSON / args.json_file
    if not json_path.exists():
        print(f"❌ File not found: {args.json_file}")
        sys.exit(1)

    # Copy to cards_json/ if it isn't there already
    dest_json = CARDS_JSON / json_path.name
    if json_path.resolve() != dest_json.resolve():
        import shutil
        dest_json.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(json_path, dest_json)
        print(f"📂 Copied {json_path.name} → cards_json/")
        json_path = dest_json

    types_to_process = ALL_TYPES if args.card_type == 'all' else [args.card_type]

    any_new = False
    for card_type in types_to_process:
        # ── Step 1 ────────────────────────────────────────────────────────────
        print(f"\n🔍 Step 1 [{card_type}] — Scanning {json_path.name} for new {card_type}s...")
        new_cards = extract_new_cards(json_path, card_type)
        if not new_cards:
            print(f"   No new {card_type}s found.")
            continue

        any_new = True
        print(f"   Found {len(new_cards)} new {card_type}(s):")
        for c in new_cards:
            print(f"      CMC {c['cmc']:>2}  {c['name']}")

        # ── Step 2 ────────────────────────────────────────────────────────────
        print(f"\n📥 Step 2 [{card_type}] — Downloading images...")
        downloaded = download_cards(new_cards)

        # ── Step 3 ────────────────────────────────────────────────────────────
        if downloaded:
            print(f"\n🎨 Step 3 [{card_type}] — Dithering {len(downloaded)} image(s) "
                  f"(brightness +{args.brightness}%)...")
            ok = sum(dither_card(c, args.brightness) for c in downloaded)
            print(f"   ✓ {ok}/{len(downloaded)} dithered")
        else:
            print(f"\n⚠  No images downloaded for {card_type}, skipping dither.")

    if not any_new:
        print("\n✅ All types already up to date — nothing to do.")
        return

    # ── Step 4 ────────────────────────────────────────────────────────────────
    print(f"\n📖 Step 4 — Rebuilding card_text_index.json...")
    rebuild_index()

    print("\n✅ Done! Deploy with: bash scripts/deploy/deploy_pi.sh\n")


if __name__ == '__main__':
    main()

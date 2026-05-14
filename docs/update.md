# Updating Card Data

Everything here runs on your **Mac** (the build machine). Never run these on the Pi directly — the Pi is runtime-only.

## Prerequisites

- `momir_env` activated
- `cards_json/AtomicCards.json` present (download from [mtgjson.com](https://mtgjson.com/downloads/all-files/) — AtomicCards)
- `requirements.txt` installed (`requests`, `ijson`, `pillow`)

## Card Types

The app supports 7 card types, each stored in its own image folder:

| Type | Image folder | Dithered folder | Input JSON |
|---|---|---|---|
| creature | `images/creature/` | `images_dithered/creature/` | `creatures_for_download.json` |
| instant | `images/instant/` | `images_dithered/instant/` | `instants_for_download.json` |
| sorcery | `images/sorcery/` | `images_dithered/sorcery/` | `sorceries_for_download.json` |
| artifact | `images/artifact/` | `images_dithered/artifact/` | `artifacts_for_download.json` |
| enchantment | `images/enchantment/` | `images_dithered/enchantment/` | `enchantments_for_download.json` |
| land | `images/land/` | `images_dithered/land/` | `lands_for_download.json` |
| planeswalker | `images/planeswalker/` | `images_dithered/planeswalker/` | `planeswalkers_for_download.json` |

You can build all types or just a subset — the app only shows the types that have images on disk.

---

## Full Pipeline (first-time setup)

### 1. Fetch set release dates (one-time)

```bash
source momir_env/bin/activate
python3 scripts/build/fetch_set_list.py
```

Downloads `cards_json/SetList.json`. Only needs re-running when new sets release.

### 2. Extract card data

```bash
# One type:
python3 scripts/build/extract_cards.py --type creature
python3 scripts/build/extract_cards.py --type instant

# Or all at once (~5 min total):
python3 scripts/build/extract_cards.py --type all
```

Reads `cards_json/AtomicCards.json`, writes one JSON per type (e.g. `instants_for_download.json`). Arena/Alchemy exclusives, funny cards (Un-sets, acorn), and non-paper cards are excluded.

### 3. Download images from Scryfall

```bash
# One type:
python3 scripts/build/download_images.py --type creature     # ~30 min, ~17k images
python3 scripts/build/download_images.py --type instant      # ~5 min, ~3.5k images

# Or all at once:
python3 scripts/build/download_images.py --type all

# Specific CMC only:
python3 scripts/build/download_images.py --type instant --cmc 1,2,3
```

Downloads into `images/{type}/<cmc>/`.

### 4. Dither for thermal printing

```bash
# One type:
python3 scripts/build/dither_for_printer.py images/instant/ images_dithered/instant/

# Creatures (shorthand defaults still work):
python3 scripts/build/dither_for_printer.py
```

Converts JPGs to monochrome BMPs using Floyd-Steinberg dithering.

### 5. Build the text index

```bash
python3 scripts/build/build_card_text_index.py
```

Writes `app/card_text_index.json` from all JSONs in `cards_json/`. Includes all card types with a `card_type` field per entry.

### 6. Test locally

```bash
./run.sh
```

You should see `✓ Loaded compact card text index`.

---

## Adding a New Set

Drop the MTGJSON set file into `cards_json/` and run:

```bash
python3 scripts/build/fetch_set_list.py   # refresh set release dates
python3 scripts/build/add_cards.py cards_json/NewSet.json
```

This will:
1. Find creatures not already in the image library
2. Download only the missing images from Scryfall
3. Dither them for the printer
4. Rebuild `app/card_text_index.json`

Then deploy: see [deploy.md](deploy.md).

---

## Token Images

```bash
python3 scripts/build/download_tokens.py      # fetch from Scryfall
python3 scripts/build/dither_tokens.py        # convert to monochrome BMPs
python3 scripts/build/refresh_token_metadata.py  # refresh token_data.json
```

## Momir Avatar Image

```bash
python3 scripts/build/dither_momir_avatar.py
```

Reads `momir_vig.jpeg` from project root, writes dithered BMP to `app/avatar_images_dithered/`.

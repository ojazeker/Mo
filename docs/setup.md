# Initial Setup

This guide takes you from a fresh clone to a running local app with card images. The Python pipeline runs on **Mac, Linux, or Windows**. The shell scripts (`run.sh`, `deploy_pi.sh`) require Mac/Linux — Windows users should use [WSL](https://learn.microsoft.com/en-us/windows/wsl/).

---

## 1. Clone and create the Python environment

```bash
git clone https://github.com/ojazeker/Mo.git
cd Mo

python3 -m venv momir_env

# Mac/Linux:
source momir_env/bin/activate
# Windows:
# momir_env\Scripts\activate

pip install -r requirements.txt
```

---

## 2. Install frontend dependencies

```bash
npm install
npm run build
```

This compiles Sass → `app/static/css/style.css` and bundles JS → `app/static/js/mo.min.js`.

---

## 3. Download AtomicCards.json

This is the master card database from [MTGJSON](https://mtgjson.com/downloads/all-files/). It's the source for all card data — everything else is built from it.

Download **AtomicCards.json** and place it at:

```
cards_json/AtomicCards.json
```

It's about 150MB and gitignored — you only need to re-download it when you want the latest card data.

---

## 4. Fetch the set list

This downloads release dates for all sets, used to pick the oldest printing of each card.

```bash
python3 scripts/build/fetch_set_list.py
```

Writes `cards_json/SetList.json`. Only needs re-running when new sets release.

---

## 5. Extract card data

This reads `AtomicCards.json` and produces a smaller JSON per card type containing only the cards the app needs.

```bash
python3 scripts/build/extract_cards.py --type all
```

This takes ~5 minutes. It writes files like `cards_json/creatures_for_download.json`, `cards_json/instants_for_download.json`, etc.

To do just one type (e.g. creatures only, which is needed for Momir Basic):

```bash
python3 scripts/build/extract_cards.py --type creature
```

---

## 6. Download images from Scryfall

Using the JSON files from step 5, this fetches card images from Scryfall — always the oldest paper printing.

```bash
python3 scripts/build/download_images.py --type all
```

Or one type at a time:

```bash
python3 scripts/build/download_images.py --type creature    # ~17k images, ~30 min
python3 scripts/build/download_images.py --type instant     # ~3.5k images, ~5 min
```

Images land in `images/{type}/<cmc>/`. The app only shows card types that have images on disk, so you can start with just creatures if you want.

---

## 7. Dither images for thermal printing

The thermal printer needs monochrome BMP files. This converts the downloaded JPGs using Floyd-Steinberg dithering.

```bash
python3 scripts/build/dither_for_printer.py images/creature/ images_dithered/creature/

# Or all types at once:
for type in creature instant sorcery artifact enchantment land planeswalker; do
  python3 scripts/build/dither_for_printer.py images/$type/ images_dithered/$type/
done
```

---

## 8. Build the card text index

Used by the in-app card search:

```bash
python3 scripts/build/build_card_text_index.py
```

Writes `app/data/card_text_index.json`.

---

## 9. Run the app locally

```bash
# Mac/Linux:
source momir_env/bin/activate
./run.sh

# Windows (WSL or Git Bash):
source momir_env/bin/activate
bash run.sh
```

Or with live reloading (recommended during development):

```bash
npm run dev:live
```

Open `http://127.0.0.1:8000` (or `http://127.0.0.1:3000` with BrowserSync).

You should see `✓ Loaded compact card text index` in the terminal output.

---

## Optional: tokens and avatars

```bash
python3 scripts/build/download_tokens.py
python3 scripts/build/dither_tokens.py
python3 scripts/build/refresh_token_metadata.py
```

For the Momir avatar image, place `momir_vig.jpeg` in the project root and run:

```bash
python3 scripts/build/dither_momir_avatar.py
```

---

## Next steps

- [develop.md](develop.md) — working on the frontend and Flask app
- [update.md](update.md) — adding new sets, re-running parts of the pipeline
- [deploy.md](deploy.md) — getting it all running on the Pi

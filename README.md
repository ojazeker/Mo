# Mo

Mo is a Raspberry Pi thermal printer solution for Magic: The Gathering.  
Pick a mana value, get a random creature, print cards, decks token, anything really! 
Runs fully offline.

This started as a Momir Basic printer, but right now has functionality way beyond that.


## Features

- Momir Basic, instant printing after one click
- Mo-Jho-Sto support, with custum avatar images
- System 7 web interface with numpad and token/creature search windows and decklist editor
- Card Search feature to get any card
- Completely offline at runtime — all images and databases are stored locally
- Dithered images optimised for thermal printing
- Hotspot mode (when away from home)
- The scrapers always try to pull the first printing image

## How it works

The project has two distinct stages:

**Build (Mac only)** — pull card data from Scryfall, dither images, build databases, test the app locally.  
**Runtime (Pi only)** — serve the Flask app, handle printer output.

## Project Structure

```
Mo/
├── app/                          # Everything that runs on the Pi
│   ├── app.py                    # Flask app entry point
│   ├── utils.py                  # Card loading/filtering
│   ├── helpers.py                # Shared helpers
│   ├── printer.py                # ESC/POS thermal printer driver
│   ├── netswitch.py              # GPIO switch reader — called by systemd at boot
│   ├── run.sh                    # Pi startup script
│   ├── data/                     # Built by pipeline (gitignored)
│   │   ├── card_text_index.json
│   │   └── token_data.json
│   ├── routes/                   # Flask route blueprints
│   ├── templates/index.html
│   └── static/                   # style.css (compiled from sass/), script.js
├── images/                       # Downloaded full-colour images (gitignored)
│   ├── creature/
│   ├── instant/
│   ├── artifact/
│   ├── token/
│   └── ...                       # One folder per card type
├── images_dithered/              # Dithered BMPs deployed to Pi (gitignored)
│   ├── creature/
│   ├── token/
│   └── ...
├── js/                           # JS source modules (built to app/static/js/)
├── sass/                         # Sass source → app/static/css/style.css
├── cards_json/                   # MTGJSON source files (gitignored)
├── deck_lists/                   # Fetched decklists (gitignored)
├── scripts/
│   ├── build/                    # Mac only — data pipeline
│   │   ├── pipeline.py           # Run all build steps
│   │   ├── extract_cards.py
│   │   ├── extract_creatures.py
│   │   ├── download_images.py
│   │   ├── download_tokens.py
│   │   ├── dither_for_printer.py
│   │   ├── dither_tokens.py
│   │   ├── dither_avatars.py
│   │   ├── dither_momir_avatar.py
│   │   ├── build_card_text_index.py
│   │   ├── refresh_token_metadata.py
│   │   ├── fetch_set_list.py
│   │   ├── fetch_top8_decklists.py
│   │   ├── add_cards.py
│   │   └── cleanup_images.py
│   └── deploy/                   # Pi setup and deployment
│       ├── deploy_pi.sh          # Mac → Pi rsync + service restart
│       ├── install_momir_service.sh  # Run once on Pi
│       └── switch_pi_network_mode.sh # Manual network mode switch
├── config.example.sh             # Copy to config.sh and fill in your values
├── docs/
│   ├── develop.md                # Local dev server, Sass, venv
│   ├── update.md                 # Adding cards, running the build pipeline
│   └── deploy.md                 # Pi setup, rsync, systemd, network modes
├── run.sh                        # Local dev start script
└── requirements.txt
```

## Docs

| Guide | Contents |
|---|---|
| [docs/setup.md](docs/setup.md) | First-time setup — environment, downloading data, building images |
| [docs/develop.md](docs/develop.md) | Local dev server, Sass, JS, API routes |
| [docs/update.md](docs/update.md) | Adding new sets, re-running parts of the pipeline |
| [docs/deploy.md](docs/deploy.md) | Pi setup, deploying updates, network modes |
| [docs/bom.md](docs/bom.md) | Bill of materials — hardware components |
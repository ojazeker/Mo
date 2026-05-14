# Developing Locally

Everything here runs on your **Mac** only — not the Pi!

## Prerequisites

- Python 3.9+ with the `momir_env` virtual environment
- Node.js + npm (for Sass + esbuild)

## Python Environment

```bash
cd /path/to/MomirPrinter
source momir_env/bin/activate
python3 -m pip install -r requirements.txt
```

## Frontend (Sass + JS)

Styles live in `sass/` and compile to `app/static/css/style.css`. JS modules live in `js/` and bundle to `app/static/js/mo.min.js`. Never edit either output file directly.

```bash
npm install
npm run build      # one-off compile of both CSS and JS
```

To watch both simultaneously during development:

```bash
npm run dev        # watches CSS and JS in parallel
```

## Running the Dev Server

### Flask + Sass + BrowserSync (recommended)

One command starts Flask, watches Sass, and auto-reloads the browser:

```bash
npm run dev:live
```

If Flask is already running on `:8000` in another terminal:

```bash
npm run dev:live:attach
```

Open BrowserSync at `http://127.0.0.1:3000`.

How it works:
- Flask serves the app on `127.0.0.1:8000`
- Sass watches `sass/site.scss` and rebuilds `app/static/css/style.css`
- esbuild watches `js/main.js` and rebuilds `app/static/js/mo.min.js`
- BrowserSync proxies Flask and reloads on template, CSS, or JS changes

### Flask only

```bash
./run.sh
```

## API Routes

### Cards
| Method | Route | Description |
|---|---|---|
| GET | `/api/card/<cmc>` | Random creature at this CMC |
| GET | `/api/card/random/<card_type>` | Random card of a given type |
| GET | `/api/card/<card_type>/<cmc>` | Random card of type at CMC |
| GET | `/api/image/<cmc>/<filename>` | Serve creature image |
| GET | `/api/image/<card_type>/<cmc>/<filename>` | Serve card image by type |
| GET | `/api/cards/search` | Search cards by query string |
| GET | `/api/stats` | Creature counts per CMC |

### Tokens
| Method | Route | Description |
|---|---|---|
| GET | `/api/tokens/search` | Search tokens by name/type |
| GET | `/api/token/<token_id>` | Token detail by ID |
| GET | `/api/token-image/<token_id>` | Serve token image |

### Avatars
| Method | Route | Description |
|---|---|---|
| GET | `/api/avatars` | List all avatars |
| GET | `/api/avatar-image` | Serve avatar image |

### Decklist
| Method | Route | Description |
|---|---|---|
| POST | `/api/decklist/lookup` | Look up cards in a decklist |
| GET | `/api/top8/index` | List saved top8 decklists |
| GET | `/api/top8/<format>/<filename>` | Fetch a specific decklist |

### Print
| Method | Route | Description |
|---|---|---|
| POST | `/api/print/card/<cmc>/<filename>` | Print a creature card |
| POST | `/api/print/card/<card_type>/<cmc>/<filename>` | Print card by type |
| POST | `/api/print/token/<token_id>` | Print a token |
| POST | `/api/print/avatar` | Print the avatar |
| POST | `/api/decklist/print` | Print a full decklist |

## Troubleshooting

**Port 8000 in use:**
```bash
python3 -m flask --app app run --port 9000
```

**Port 5000:** macOS uses it for AirPlay. Always use 8000 or higher.

**No cards found:** make sure `images/creature/` (or another type folder) exists. See [update.md](update.md).

**App crashed:**
```bash
python3 -m app.app   # run directly for full error output
```

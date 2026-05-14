"""
Utilities for handling Magic card data
"""

import json
import re
import random
from pathlib import Path

def load_cards(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cards = []
        
        # AtomicCards.json has structure: {meta: {...}, data: {card_name: [versions...]}}
        if isinstance(data, dict) and 'data' in data:
            card_data = data['data']
            
            # Each card name maps to a list of printings
            for card_name, card_versions in card_data.items():
                if isinstance(card_versions, list):
                    # Add each version with the card name
                    for version in card_versions:
                        if isinstance(version, dict):
                            # Ensure name is set
                            if 'name' not in version:
                                version['name'] = card_name
                            cards.append(version)
                else:
                    # Single version (not a list)
                    if isinstance(card_versions, dict):
                        if 'name' not in card_versions:
                            card_versions['name'] = card_name
                        cards.append(card_versions)
            
            return cards
        
        print(f"Warning: Unexpected JSON structure. Keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        return []
        
    except FileNotFoundError:
        print(f"Error: Card file not found at {json_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_path}: {e}")
        return []


def load_token_data(json_path):
    """Load locally cached token metadata."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        print(f"Warning: Unexpected token JSON structure in {json_path}")
        return []

    except FileNotFoundError:
        print(f"Warning: Token file not found at {json_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_path}: {e}")
        return []


def normalize_search_text(text):
    """Normalize text for simple token searching."""
    text = text.lower().replace("'", '').replace('\u2019', '')  # strip apostrophes
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def get_creatures_by_mana_value(cards, mana_value):
    """
    Filter creatures by mana value (CMC)
    Excludes tokens and other non-printable cards
    
    Args:
        cards: List of card dictionaries
        mana_value: Target CMC value
    
    Returns:
        List of matching creature cards
    """
    creatures = []
    
    for card in cards:
        # Must be a creature
        card_type = card.get('type', '')
        if 'Creature' not in card_type:
            continue
        
        # Must not be a token
        if 'Token' in card.get('layout', ''):
            continue
        
        # Must match mana value
        if card.get('manaValue', 0) != mana_value:
            continue
        
        # Has a valid name
        if not card.get('name'):
            continue
        
        creatures.append(card)
    
    return creatures


def search_tokens(tokens, query, limit=12):
    """Search local token metadata by name and type."""
    normalized_query = normalize_search_text(query)
    if len(normalized_query) < 2:
        return []

    unique_matches = {}
    for token in tokens:
        # Skip dual-faced tokens (e.g. "Goblin // Soldier") — wrong data, wrong art
        if '//' in token.get('name', ''):
            continue

        haystack = token.get('search_text') or normalize_search_text(
            f"{token.get('name', '')} {token.get('type_line', '')}"
        )

        if normalized_query not in haystack:
            continue

        dedupe_key = (
            normalize_search_text(token.get('name', '')),
            normalize_search_text(token.get('type_line', '')),
            tuple(sorted(token.get('colors', []))),
        )
        unique_matches.setdefault(dedupe_key, token)

    matches = []
    for token in unique_matches.values():
        normalized_name = normalize_search_text(token.get('name', ''))
        starts_with_name = normalized_name.startswith(normalized_query)
        contains_name = normalized_query in normalized_name

        # Improved classic token prioritization
        classic_priority = 1
        # For Zombie: must be 2/2, black, not artifact/enchantment, and type_line must be exactly 'Token Creature — Zombie'
        if (
            normalized_query == 'zombie' and
            token.get('name', '').lower() == 'zombie' and
            token.get('power', '') == '2' and
            token.get('toughness', '') == '2' and
            token.get('colors', ['B']) == ['B'] and
            token.get('type_line', '').strip() == 'Token Creature — Zombie'
        ):
            classic_priority = 0
        # For Goblin: must be 1/1, red, not artifact/enchantment, and type_line must be exactly 'Token Creature — Goblin'
        elif (
            normalized_query == 'goblin' and
            token.get('name', '').lower() == 'goblin' and
            token.get('power', '') == '1' and
            token.get('toughness', '') == '1' and
            token.get('colors', ['R']) == ['R'] and
            token.get('type_line', '').strip() == 'Token Creature — Goblin'
        ):
            classic_priority = 0

        # Use oracle_id as a tiebreaker for oldest printing (lowest lexicographically)
        oracle_id = token.get('oracle_id', '')

        matches.append((
            classic_priority,
            0 if starts_with_name else 1,
            0 if contains_name else 1,
            len(token.get('name', '')),
            oracle_id,
            token.get('name', ''),
            token,
        ))

    # Sort by all keys, classic first, then name match, then oldest oracle_id
    matches.sort(key=lambda match: match[:-1])
    return [match[-1] for match in matches[:limit]]

def get_card_image_url(card):
    """
    Get the Scryfall image URL for a card
    
    Args:
        card: Card dictionary
    
    Returns:
        Image URL string or None
    """
    # Try to use Scryfall URLs if available
    if 'purchaseUrls' in card:
        # We can't directly get image URL from purchase URLs,
        # but we can construct Scryfall URL
        pass
    
    # Build Scryfall URL from card name
    if 'name' in card and 'setCode' in card:
        name = card['name'].replace(' ', '%20').replace('//', '%2F')
        set_code = card['setCode'].lower()
        return f"https://api.scryfall.com/cards/search?q=!%22{name}%22+set%3A{set_code}"
    
    return None

def get_local_image_for_creature(creature_name, cmc):
    """
    Find local image file for a creature.
    Searches dithered images first, then falls back to full-color images.
    
    Args:
        creature_name: Card name (e.g., "Black Lotus")
        cmc: Converted mana cost (CMC)
    
    Returns:
        Path object if found, None otherwise
    """
    # Clean up the creature name to match saved filename
    # Files are saved as: name.replace('/', '').replace('"', '').replace("'", '')
    clean_name = creature_name.replace('/', '').replace('"', '').replace("'", '')

    image_roots = [
        Path(__file__).parent.parent / 'images_dithered' / 'creature' / str(int(cmc)),
        Path(__file__).parent.parent / 'images' / 'creature' / str(int(cmc)),
    ]

    for images_dir in image_roots:
        if not images_dir.exists():
            continue

        bmp_path = images_dir / f"{clean_name}.bmp"
        if bmp_path.exists():
            return bmp_path

        jpg_path = images_dir / f"{clean_name}.jpg"
        if jpg_path.exists():
            return jpg_path
    
    return None


def get_local_image_for_card(card_name, cmc, card_type='creature'):
    """Find local image file for any card type.

    Args:
        card_name: Card name
        cmc: Converted mana cost
        card_type: Type slug (creature/instant/sorcery/artifact/enchantment/land/planeswalker)

    Returns:
        Path object if found, None otherwise
    """
    clean_name = card_name.replace('/', '').replace('"', '').replace("'", '')
    root = Path(__file__).parent.parent
    image_roots = [
        root / 'images_dithered' / card_type / str(int(cmc)),
        root / 'images' / card_type / str(int(cmc)),
    ]

    for images_dir in image_roots:
        if not images_dir.exists():
            continue
        for ext in ('.bmp', '.jpg'):
            p = images_dir / f"{clean_name}{ext}"
            if p.exists():
                return p

    return None


def get_random_local_creature_image(cmc):
    """Pick a random local creature image path for the given CMC. Backward-compat alias."""
    return get_random_local_card_image(cmc, 'creature')


def get_random_local_card_image_any_cmc(card_type='creature'):
    """Pick a random local card image across ALL CMC folders for the given type.

    Returns (image_path, cmc) or (None, None) if no images found.
    """
    root = Path(__file__).parent.parent
    all_candidates = []

    for base in [root / 'images_dithered' / card_type, root / 'images' / card_type]:
        if not base.exists():
            continue
        for cmc_dir in base.iterdir():
            if not cmc_dir.is_dir() or not cmc_dir.name.isdigit():
                continue
            for path in cmc_dir.iterdir():
                if path.is_file() and path.suffix.lower() in {'.bmp', '.jpg'}:
                    all_candidates.append((path, int(cmc_dir.name)))

    if not all_candidates:
        return None, None
    return random.choice(all_candidates)


def get_random_local_card_image(cmc, card_type='creature'):
    """Pick a random local card image path for the given CMC and card type.

    Prefers dithered images when available, falls back to full-color.
    """
    root = Path(__file__).parent.parent
    image_roots = [
        root / 'images_dithered' / card_type / str(int(cmc)),
        root / 'images' / card_type / str(int(cmc)),
    ]

    for images_dir in image_roots:
        if not images_dir.exists():
            continue

        candidates = [
            path for path in images_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {'.bmp', '.jpg'}
        ]

        if candidates:
            return random.choice(candidates)

    return None


def get_local_image_for_token(token_id):
    """Find a local image file for a token by Scryfall card id."""
    image_roots = [
        Path(__file__).parent.parent / 'images_dithered' / 'token',
        Path(__file__).parent.parent / 'images' / 'token',
    ]

    for images_dir in image_roots:
        if not images_dir.exists():
            continue

        bmp_path = images_dir / f"{token_id}.bmp"
        if bmp_path.exists():
            return bmp_path

        jpg_path = images_dir / f"{token_id}.jpg"
        if jpg_path.exists():
            return jpg_path

    return None

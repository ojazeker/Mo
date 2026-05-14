"""Card search route: /api/cards/search"""

from flask import Blueprint, jsonify, request

from ..helpers import get_card_text_index, normalize_card_name_for_image, find_card_image_stem
from ..utils import normalize_search_text

bp = Blueprint('search', __name__)


@bp.route('/api/cards/search')
def card_search():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'results': []})

    card_index = get_card_text_index()
    if not card_index:
        return jsonify({'results': []})

    normalized_query = normalize_search_text(query)
    results = []
    seen_names = set()

    for card in card_index:
        name = card.get('name', '')
        if name in seen_names:
            continue
        if normalized_query not in normalize_search_text(name):
            continue
        card_type = card.get('card_type', 'creature')
        cmc = int(card.get('manaValue', 0))
        filename = find_card_image_stem(name, cmc, card_type)
        if not filename:
            continue
        seen_names.add(name)
        results.append({
            'name':      name,
            'type':      card.get('type', ''),
            'card_type': card_type,
            'cmc':       cmc,
            'power':     card.get('power', ''),
            'toughness': card.get('toughness', ''),
            'text':      card.get('text', ''),
            'manaCost':  card.get('manaCost', ''),
            'filename':  filename,
            'imageUrl':  f'/api/image/{card_type}/{cmc}/{filename}',
        })
        if len(results) >= 12:
            break

    return jsonify({'results': results})

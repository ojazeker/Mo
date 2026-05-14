"""Stats route: /api/stats"""

from flask import Blueprint, jsonify

from ..helpers import get_card_text_index, get_token_data, has_local_token_images

bp = Blueprint('stats', __name__)


@bp.route('/api/stats')
def stats():
    card_index = get_card_text_index()
    if not card_index:
        return jsonify({'error': 'Card index not loaded'}), 500

    cards_by_type = {}
    creatures_by_cmc = {}
    for card in card_index:
        slug = card.get('card_type', 'creature')
        cards_by_type[slug] = cards_by_type.get(slug, 0) + 1
        if slug == 'creature':
            cmc = card.get('manaValue', 0)
            creatures_by_cmc[cmc] = creatures_by_cmc.get(cmc, 0) + 1

    return jsonify({
        'total_cards':      len(card_index),
        'total_creatures':  cards_by_type.get('creature', 0),
        'cards_by_type':    cards_by_type,
        'creatures_by_cmc': creatures_by_cmc,
        'total_tokens':     len(get_token_data()),
        'has_token_images': has_local_token_images(),
    })

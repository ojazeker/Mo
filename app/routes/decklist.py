"""Decklist lookup route: /api/decklist/lookup"""

from flask import Blueprint, jsonify, request

from ..helpers import get_card_text_index, normalize_card_name_for_image, find_card_image_stem

bp = Blueprint('decklist', __name__)


@bp.route('/api/decklist/lookup', methods=['POST'])
def decklist_lookup():
    data = request.get_json(silent=True) or {}
    names = data.get('names', [])
    if not isinstance(names, list) or len(names) > 300:
        return jsonify({'error': 'Invalid names list'}), 400

    card_index = get_card_text_index()

    # Build normalized-name → card mapping.
    # For double-faced cards ("Front // Back"), also index by front face alone.
    name_map = {}
    for card in card_index:
        full_name = card.get('name', '')
        norm = normalize_card_name_for_image(full_name)
        if norm not in name_map:
            name_map[norm] = card
        if ' // ' in full_name:
            front = full_name.split(' // ')[0]
            norm_front = normalize_card_name_for_image(front)
            if norm_front not in name_map:
                name_map[norm_front] = card

    results = []
    for name in names:
        norm = normalize_card_name_for_image(name)
        card = name_map.get(norm)
        if card:
            card_type = card.get('card_type', 'creature')
            cmc = int(card.get('manaValue', 0))
            raw_name = card.get('name', name)
            filename = raw_name.replace('/', '').replace('"', '').replace("'", '').strip()
            stem = find_card_image_stem(filename, cmc, card_type)
            results.append({
                'name':      raw_name,
                'found':     stem is not None,
                'imageUrl':  f'/api/image/{card_type}/{cmc}/{stem}' if stem else '',
                'card_type': card_type,
                'cmc':       cmc,
                'filename':  stem or filename,
                'text':      card.get('text', ''),
                'type':      card.get('type', ''),
            })
        else:
            results.append({
                'name':      name,
                'found':     False,
                'imageUrl':  '',
                'card_type': '',
                'cmc':       0,
                'filename':  '',
                'text':      '',
                'type':      '',
            })

    return jsonify({'results': results})

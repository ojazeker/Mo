"""Card routes: /api/card/... and /api/image/..."""

from flask import Blueprint, jsonify, request, send_file
from pathlib import Path

from ..helpers import (
    VALID_CARD_TYPES,
    get_card_text_index,
    find_card_by_image_name,
    get_random_card_image_with_subtype,
    auto_print_card,
)
from ..utils import get_random_local_card_image, get_random_local_card_image_any_cmc

bp = Blueprint('cards', __name__)


def _build_card_response(image_path, cmc, card_type, preview_only=False):
    matched_card = find_card_by_image_name(image_path.stem, cmc, card_type)
    card_data = {
        'name':          matched_card.get('name', image_path.stem) if matched_card else image_path.stem,
        'type':          matched_card.get('type', card_type.capitalize()) if matched_card else card_type.capitalize(),
        'manaCost':      matched_card.get('manaCost', '') if matched_card else '',
        'manaValue':     cmc,
        'text':          matched_card.get('text', '') if matched_card else '',
        'power':         matched_card.get('power', '?') if matched_card else '?',
        'toughness':     matched_card.get('toughness', '?') if matched_card else '?',
        'setCode':       matched_card.get('setCode', '') if matched_card else '',
        'card_type':     card_type,
        'cmc':           cmc,
        'success':       True,
        'hasLocalImage': True,
        'imageUrl':      f'/api/image/{card_type}/{cmc}/{image_path.stem}',
    }
    if not preview_only:
        auto_print_card(image_path, card_data, card_type)
    return jsonify(card_data)


def _get_random_card_for_type(card_type, cmc):
    if card_type not in VALID_CARD_TYPES:
        return jsonify({'error': f'Unknown card type: {card_type}'}), 400
    if cmc < 0 or cmc > 20:
        return jsonify({'error': 'CMC must be between 0 and 20'}), 400

    subtype = request.args.get('subtype')
    preview_only = request.args.get('preview_only') == 'true'

    if subtype:
        image_path = get_random_card_image_with_subtype(cmc, card_type, subtype)
    else:
        image_path = get_random_local_card_image(cmc, card_type)

    if image_path is None:
        return jsonify({'error': f'No local {card_type} images found with CMC {cmc}', 'cmc': cmc}), 404

    return _build_card_response(image_path, cmc, card_type, preview_only)


@bp.route('/api/card/<int:cmc>')
def get_random_card(cmc):
    return _get_random_card_for_type('creature', cmc)


@bp.route('/api/card/random/<card_type>')
def get_random_card_any_cmc(card_type):
    if card_type not in VALID_CARD_TYPES:
        return jsonify({'error': f'Unknown card type: {card_type}'}), 400
    preview_only = request.args.get('preview_only') == 'true'
    image_path, cmc = get_random_local_card_image_any_cmc(card_type)
    if image_path is None:
        return jsonify({'error': f'No local {card_type} images found'}), 404
    return _build_card_response(image_path, cmc, card_type, preview_only)


@bp.route('/api/card/<card_type>/<int:cmc>')
def get_random_card_typed(card_type, cmc):
    return _get_random_card_for_type(card_type, cmc)


@bp.route('/api/image/<int:cmc>/<filename>')
def get_card_image(cmc, filename):
    return get_card_image_typed('creature', cmc, filename)


@bp.route('/api/image/<card_type>/<int:cmc>/<filename>')
def get_card_image_typed(card_type, cmc, filename):
    root = Path(__file__).parent.parent.parent
    image_roots = [
        root / 'images_dithered' / card_type / str(cmc),
        root / 'images' / card_type / str(cmc),
    ]
    for images_dir in image_roots:
        bmp_path = images_dir / f"{filename}.bmp"
        if bmp_path.exists():
            return send_file(str(bmp_path), mimetype='image/bmp')
        jpg_path = images_dir / f"{filename}.jpg"
        if jpg_path.exists():
            return send_file(str(jpg_path), mimetype='image/jpeg')
    return jsonify({'error': 'Image not found'}), 404

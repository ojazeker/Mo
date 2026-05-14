"""Print routes: /api/print/..."""

import threading
from flask import Blueprint, jsonify, request
from pathlib import Path

from ..helpers import VALID_CARD_TYPES
from ..utils import get_local_image_for_token
from ..printer import print_image

bp = Blueprint('print', __name__)


@bp.route('/api/print/card/<int:cmc>/<filename>', methods=['POST'])
def print_card_legacy(cmc, filename):
    return print_card_typed('creature', cmc, filename)


@bp.route('/api/print/card/<card_type>/<int:cmc>/<filename>', methods=['POST'])
def print_card_typed(card_type, cmc, filename):
    root = Path(__file__).parent.parent.parent
    image_roots = [
        root / 'images_dithered' / card_type / str(cmc),
        root / 'images' / card_type / str(cmc),
    ]
    for images_dir in image_roots:
        for ext, mime in (('.bmp', 'image/bmp'), ('.jpg', 'image/jpeg')):
            path = images_dir / f"{filename}{ext}"
            if path.exists():
                threading.Thread(target=print_image, args=(str(path),), daemon=True).start()
                return jsonify({'success': True, 'message': 'Printing card...'})
    return jsonify({'success': False, 'error': 'Image not found'}), 404


@bp.route('/api/print/token/<token_id>', methods=['POST'])
def print_token(token_id):
    image_path = get_local_image_for_token(token_id)
    if image_path is None:
        return jsonify({'success': False, 'error': 'Token image not found'}), 404
    threading.Thread(target=print_image, args=(str(image_path),), daemon=True).start()
    return jsonify({'success': True, 'message': 'Printing token...'})


@bp.route('/api/print/avatar', methods=['POST'])
def print_avatar():
    name = request.args.get('name', 'momir_avatar')
    name = Path(name).name
    avatar_path = Path(__file__).parent.parent.parent / 'images_dithered' / 'avatar' / f'{name}.bmp'
    if not avatar_path.exists():
        return jsonify({'success': False, 'error': 'Avatar image not found'}), 404
    threading.Thread(target=print_image, args=(str(avatar_path),), daemon=True).start()
    return jsonify({'success': True, 'message': 'Printing avatar...'})


@bp.route('/api/decklist/print', methods=['POST'])
def decklist_print():
    data = request.get_json(silent=True) or {}
    cards = data.get('cards', [])
    if not isinstance(cards, list) or len(cards) > 300:
        return jsonify({'error': 'Invalid cards list'}), 400

    root = Path(__file__).parent.parent.parent

    def _do_print():
        for entry in cards:
            card_type = entry.get('card_type', '')
            if card_type not in VALID_CARD_TYPES:
                continue
            cmc = int(entry.get('cmc', 0))
            filename = entry.get('filename', '')
            quantity = max(1, min(int(entry.get('quantity', 1)), 20))
            if not filename:
                continue
            image_roots = [
                root / 'images_dithered' / card_type / str(cmc),
                root / 'images' / card_type / str(cmc),
            ]
            image_path = None
            for images_dir in image_roots:
                for ext in ('.bmp', '.jpg'):
                    p = images_dir / f"{filename}{ext}"
                    if p.exists():
                        image_path = str(p)
                        break
                if image_path:
                    break
            if not image_path:
                continue
            for _ in range(quantity):
                try:
                    print_image(image_path)
                except Exception as e:
                    print(f"Decklist print failed for {filename}: {e}")

    threading.Thread(target=_do_print, daemon=True).start()
    return jsonify({'success': True, 'message': 'Printing decklist...'})

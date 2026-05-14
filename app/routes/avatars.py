"""Avatar routes: /api/avatars, /api/avatar-image"""

import json
from flask import Blueprint, jsonify, request, send_file
from pathlib import Path

bp = Blueprint('avatars', __name__)


@bp.route('/api/avatars')
def list_avatars():
    avatar_dir = Path(__file__).parent.parent.parent / 'images_dithered' / 'avatar'
    if not avatar_dir.exists():
        return jsonify({'avatars': []})

    rules_path = Path(__file__).parent.parent / 'data' / 'avatar_rules.json'
    rules = {}
    if rules_path.exists():
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except Exception:
            pass

    avatars = sorted([
        {
            'name': p.stem,
            'url':  f'/api/avatar-image?name={p.stem}',
            'rules': rules.get(p.stem, {
                'displayName': p.stem.replace('_', ' '),
                'cardType':    'creature',
                'cmcPrompt':   'Pick a CMC',
            }),
        }
        for p in avatar_dir.glob('*.bmp')
    ], key=lambda a: (a['name'] != 'momir_avatar', a['name']))

    return jsonify({'avatars': avatars})


@bp.route('/api/avatar-image')
def get_avatar_image():
    name = request.args.get('name', 'momir_avatar')
    name = Path(name).name
    avatar_path = Path(__file__).parent.parent.parent / 'images_dithered' / 'avatar' / f'{name}.bmp'
    if not avatar_path.exists():
        return jsonify({'error': 'Avatar image not found'}), 404
    return send_file(str(avatar_path), mimetype='image/bmp')

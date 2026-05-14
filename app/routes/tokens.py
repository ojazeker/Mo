"""Token routes: /api/tokens/search, /api/token/..., /api/token-image/..."""

from flask import Blueprint, jsonify, request, send_file

from ..helpers import get_token_data
from ..utils import get_local_image_for_token, search_tokens

bp = Blueprint('tokens', __name__)


@bp.route('/api/tokens/search')
def token_search():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'results': []})
    tokens = get_token_data()
    if not tokens:
        return jsonify({
            'results': [],
            'error': 'No local token data found. Run scripts/download_tokens.py first.'
        }), 503
    results = search_tokens(tokens, query)
    return jsonify({
        'results': [
            {
                'id':         token.get('id', ''),
                'name':       token.get('name', 'Unknown Token'),
                'type':       token.get('type_line', 'Token'),
                'colors':     token.get('colors', []),
                'power':      token.get('power', ''),
                'toughness':  token.get('toughness', ''),
                'keywords':   token.get('keywords', []),
            }
            for token in results
        ]
    })


@bp.route('/api/token/<token_id>')
def get_token(token_id):
    tokens = get_token_data()
    token = next((t for t in tokens if t.get('id') == token_id), None)
    if token is None:
        return jsonify({'error': 'Token not found'}), 404

    def is_missing(val):
        return val is None or val == '' or (isinstance(val, list) and not val)

    filled = dict(token)
    if 'oracle_id' in token:
        for other in tokens:
            if other is token:
                continue
            if other.get('oracle_id') == token['oracle_id']:
                for key in ['name', 'type_line', 'power', 'toughness', 'colors', 'search_text', 'keywords', 'oracle_text']:
                    if is_missing(filled.get(key)) and not is_missing(other.get(key)):
                        filled[key] = other.get(key)

    image_path = get_local_image_for_token(token_id)
    return jsonify({
        'id':           token_id,
        'name':         filled.get('name', 'Unknown Token'),
        'type':         filled.get('type_line', 'Token'),
        'power':        filled.get('power', ''),
        'toughness':    filled.get('toughness', ''),
        'colors':       filled.get('colors', []),
        'keywords':     filled.get('keywords', []),
        'oracle_text':  filled.get('oracle_text', ''),
        'success':      True,
        'hasLocalImage': image_path is not None,
        'imageUrl':     f"/api/token-image/{token_id}" if image_path else '',
    })


@bp.route('/api/token-image/<token_id>')
def get_token_image(token_id):
    image_path = get_local_image_for_token(token_id)
    if image_path is None:
        return jsonify({'error': 'Token image not found'}), 404
    mimetype = 'image/bmp' if image_path.suffix.lower() == '.bmp' else 'image/jpeg'
    return send_file(str(image_path), mimetype=mimetype)

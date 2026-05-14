"""Top 8 routes: /api/top8/..."""

import json
import re
from flask import Blueprint, jsonify
from pathlib import Path

bp = Blueprint('top8', __name__)


@bp.route('/api/top8/index')
def top8_index():
    index_path = Path(__file__).parent.parent.parent / 'deck_lists' / 'index.json'
    if not index_path.exists():
        return jsonify({'error': 'No deck lists found. Run the build script first.'}), 404
    with open(index_path, encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


@bp.route('/api/top8/<format_name>/<filename>')
def top8_deck(format_name, filename):
    if not re.match(r'^[a-z]+$', format_name):
        return jsonify({'error': 'Invalid format'}), 400
    if not re.match(r'^[\w\-]+\.txt$', filename):
        return jsonify({'error': 'Invalid filename'}), 400
    deck_path = Path(__file__).parent.parent.parent / 'deck_lists' / format_name / filename
    if not deck_path.exists():
        return jsonify({'error': 'Deck not found'}), 404
    return deck_path.read_text(encoding='utf-8'), 200, {'Content-Type': 'text/plain; charset=utf-8'}

#!/usr/bin/env python3
"""Mo Printer: Flask web app for printing Momir Basic creatures and tokens."""

from flask import Flask, render_template

from .routes import cards, tokens, avatars, decklist, search, stats, top8
from .routes import print as print_routes

app = Flask(__name__, template_folder='templates', static_folder='static')

# Register blueprints
app.register_blueprint(cards.bp)
app.register_blueprint(tokens.bp)
app.register_blueprint(print_routes.bp)
app.register_blueprint(avatars.bp)
app.register_blueprint(decklist.bp)
app.register_blueprint(search.bp)
app.register_blueprint(stats.bp)
app.register_blueprint(top8.bp)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
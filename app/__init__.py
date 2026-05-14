"""
Momir Printer
Flask web app for printing Momir Basic creatures and tokens.
"""

from .app import app

__version__ = "0.1.0"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
#!/bin/bash
# Run Momir Magic Generator
# Works when called from anywhere — cd to the project root first.
cd "$(dirname "$0")/.."

# Activate virtual environment
source momir_env/bin/activate

# Run Flask app on port 8000
python3 -m flask --app app run --host 0.0.0.0 --port 8000
#!/bin/bash

# Activate virtual environment
source momir_env/bin/activate

# Run Flask app on port 8000
python3 -m flask --app app run --host 0.0.0.0 --port 8000 --debug
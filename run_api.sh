#!/bin/bash
# Run the PhotoSense-AI API server from any directory

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to project root
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run uvicorn with the project root in PYTHONPATH
PYTHONPATH="$SCRIPT_DIR" uvicorn services.api.main:app --reload --port 8000

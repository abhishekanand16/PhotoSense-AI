#!/bin/bash
# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

PYTHONPATH="$SCRIPT_DIR" uvicorn services.api.main:app --reload --port 8000

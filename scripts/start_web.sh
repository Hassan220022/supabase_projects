#!/bin/bash

# Start the web interface for Supabase project generator
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Run the Flask application directly
python3 "$PROJECT_ROOT/src/web/web_interface.py"

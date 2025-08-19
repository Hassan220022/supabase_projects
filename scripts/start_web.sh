#!/bin/bash

# Start the web interface for Supabase project generator
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root to ensure proper imports
cd "$PROJECT_ROOT"

# Export any necessary environment variables
export FLASK_APP=src/web/web_interface.py
export FLASK_ENV=production

# Run the Flask application directly on port 5000
echo "Starting Supabase Project Generator Web Interface on port 5000..."
python3 "$PROJECT_ROOT/src/web/web_interface.py"

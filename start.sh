#!/bin/bash

# Start Supabase Project Generator automatically
echo "=========================================="
echo "Starting Supabase Project Generator..."
echo "=========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Warning: Docker is not installed. Docker is required to run Supabase projects."
fi

# Install dependencies if not already installed
echo "Checking dependencies..."
pip3 install -r /workspace/config/requirements.txt --quiet

# Set environment variables for database (can be overridden)
export SUPABASE_DB_HOST="${SUPABASE_DB_HOST:-192.168.1.43}"
export SUPABASE_DB_PORT="${SUPABASE_DB_PORT:-5432}"
export SUPABASE_DB_USER="${SUPABASE_DB_USER:-postgres}"
export SUPABASE_DB_PASSWORD="${SUPABASE_DB_PASSWORD:-postgres}"
export SUPABASE_PROJECTS_DIR="${SUPABASE_PROJECTS_DIR:-$HOME/supabase_projects}"

# Start the web interface
echo ""
echo "Starting web interface on http://0.0.0.0:5000"
echo "Press Ctrl+C to stop"
echo ""

cd /workspace
python3 /workspace/src/web/web_interface.py
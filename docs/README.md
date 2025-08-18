# Supabase Project Generator

This tool automates the creation of Supabase projects with self-hosted PostgreSQL databases. It generates all necessary configuration files and Docker Compose setup for running Supabase services.

## Features

- Creates Supabase projects with custom specifications
- Integrates with self-hosted PostgreSQL database (must be accessible at 192.168.1.43:5432 with credentials: postgres / your_password)
- Generates secure anonymous and service keys (32-character length)
- Provides both command-line and web interfaces
- Automatically bootstraps projects with Docker Compose using latest Supabase images
- Includes health checks for all services

## Prerequisites

- Docker installed and running
- Python 3.11+
- Self-hosted PostgreSQL database (must be accessible at 192.168.1.43:5432 with credentials: postgres / your_password)

## Installation

```bash
# Install required Python packages
pip install -r config/requirements.txt
```

## Usage

### Web Interface (Recommended)

```bash
# Start the web interface
./scripts/start_web.sh

# Or run directly
python src/web/web_interface.py
```

Then open your browser to http://localhost:8000

### Command Line Interface

```bash
# Run the CLI
python src/core/main.py
```

The CLI will prompt for project details but will automatically use the fixed database settings:
- Host: 192.168.1.43
- Port: 5432
- User: postgres
- Password: your_password

## Project Structure

- `/root/supabase_projects/` - Directory where all generated projects are stored
- `/root/supabase_project_generator/` - Main application directory
  - `src/` - Source code
    - `core/main.py` - Core logic for project creation
    - `web/web_interface.py` - Flask web application
    - `web/templates/` - HTML templates for web interface
  - `tests/` - Test scripts
  - `config/` - Configuration files
  - `scripts/` - Utility scripts
  - `docs/` - Documentation

## How It Works

1. User provides project details (name, machine size, specs)
2. User provides database connection details
3. Application generates:
   - 32-character anonymous and service keys
   - Docker Compose configuration
   - Kong API gateway configuration
   - Project metadata
4. Project is created in `/root/supabase_projects/{project_name}/`
5. User can start the project with `docker-compose up -d`

## Security Notes

- Keys are generated using Python's `secrets` module for cryptographic security
- Database passwords are not stored in plain text in configurations
- Each project gets unique keys for security isolation

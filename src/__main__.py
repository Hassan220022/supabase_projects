#!/usr/bin/env python3
"""
Main entry point for the Supabase Project Generator
Allows running as: python3 -m supabase_project_generator
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from cli.cli import main

if __name__ == '__main__':
    sys.exit(main())
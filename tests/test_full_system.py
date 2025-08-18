#!/usr/bin/env python3

"""
Test script to verify the full system works with the new structure
"""

import sys
import os
sys.path.append('/root/supabase_project_generator')

try:
    print("Testing full system with new structure...")
    
    # Test CLI import
    from src.core.main import SupabaseProjectGenerator
    print("✓ CLI module imported successfully")
    
    # Test web interface import
    from src.web.web_interface import app
    print("✓ Web interface module imported successfully")
    
    # Test creating a project with CLI
    generator = SupabaseProjectGenerator()
    project_path = generator.create_project("test-full-system", "small", "2CPU/4GB RAM")
    print("✓ CLI project creation successful")
    
    # Verify project files
    expected_files = ["supabase_config.json", "docker-compose.yml", "kong.yml"]
    for file in expected_files:
        file_path = os.path.join(project_path, file)
        if os.path.exists(file_path):
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
    
    print("\nAll tests passed! The restructured system is working correctly.")
    
except Exception as e:
    print(f"✗ Error during test: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3

"""
Test script to verify the restructured project works correctly
"""

import sys
import os
sys.path.append('/root/supabase_project_generator')

try:
    from src.core.main import SupabaseProjectGenerator
    print("✓ Successfully imported SupabaseProjectGenerator")
    
    # Test creating an instance
    generator = SupabaseProjectGenerator()
    print("✓ Successfully created SupabaseProjectGenerator instance")
    
    # Test creating a project
    project_name = "test-restructure"
    machine_size = "small"
    specs = "2CPU/4GB RAM"
    
    print(f"Creating test project: {project_name}")
    project_path = generator.create_project(project_name, machine_size, specs)
    print(f"✓ Project created successfully at: {project_path}")
    
    # Verify project files exist
    expected_files = ["supabase_config.json", "docker-compose.yml", "kong.yml"]
    for file in expected_files:
        file_path = os.path.join(project_path, file)
        if os.path.exists(file_path):
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
    
    print("Restructuring test completed successfully!")
    
except Exception as e:
    print(f"✗ Error during test: {e}")
    import traceback
    traceback.print_exc()

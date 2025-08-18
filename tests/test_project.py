#!/usr/bin/env python3

"""
Test script to demonstrate the Supabase project generator
"""

import os
import sys
sys.path.append('/root/supabase_project_generator')

from src.core.main import SupabaseProjectGenerator

def test_project_creation():
    """Test creating a sample Supabase project"""
    print("Testing Supabase Project Generator...")
    
    # Initialize the generator
    generator = SupabaseProjectGenerator()
    
    # Create a test project
    project_name = "test-project"
    machine_size = "medium"
    specs = "4CPU/8GB RAM"
    db_host = "localhost"
    db_port = "5432"
    db_user = "postgres"
    db_password = "postgres"
    
    print(f"Creating project: {project_name}")
    
    try:
        project_path = generator.create_project(
            project_name, machine_size, specs,
            db_host, db_port, db_user, db_password
        )
        print(f"Project created successfully at: {project_path}")
        
        # Verify the project was created
        if os.path.exists(project_path):
            print("Project directory exists")
            
            # Check for key files
            expected_files = [
                "supabase_config.json",
                "docker-compose.yml",
                "kong.yml"
            ]
            
            for file in expected_files:
                file_path = os.path.join(project_path, file)
                if os.path.exists(file_path):
                    print(f"  ✓ {file} exists")
                else:
                    print(f"  ✗ {file} missing")
        else:
            print("Project directory was not created")
            
    except Exception as e:
        print(f"Error creating project: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_project_creation()

#!/usr/bin/env python3

"""
Test script to verify the fixed database settings in Supabase project generator
"""

import os
import sys
sys.path.append('/root/supabase_project_generator')

from src.core.main import SupabaseProjectGenerator

def test_fixed_db_settings():
    """Test creating a sample Supabase project with fixed database settings"""
    print("Testing Supabase Project Generator with Fixed Database Settings...")
    
    # Initialize the generator
    generator = SupabaseProjectGenerator()
    
    # Create a test project
    project_name = "test-fixed-db"
    machine_size = "small"
    specs = "2CPU/4GB RAM"
    
    print(f"Creating project: {project_name}")
    print("Using fixed database settings: host=192.168.1.43, port=5432, user=postgres, password=your_password")
    
    try:
        project_path = generator.create_project(
            project_name, machine_size, specs
        )
        print(f"Project created successfully at: {project_path}")
        
        # Verify the project was created
        if os.path.exists(project_path):
            print("Project directory exists")
            
            # Check configuration file
            config_path = os.path.join(project_path, "supabase_config.json")
            if os.path.exists(config_path):
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                print("Configuration verification:")
                print(f"  DB Host: {config.get('db_host')}")
                print(f"  DB Port: {config.get('db_port')}")
                print(f"  DB User: {config.get('db_user')}")
                print(f"  DB Password: {'*' * len(config.get('db_password', '')) if config.get('db_password') else 'Not set'}")
                
                # Verify database settings are correct
                if (config.get('db_host') == '192.168.1.43' and 
                    config.get('db_port') == '5432' and 
                    config.get('db_user') == 'postgres' and 
                    config.get('db_password') == 'your_password'):
                    print("✓ Database settings are correctly set to fixed values")
                else:
                    print("✗ Database settings are incorrect")
            else:
                print("✗ Configuration file missing")
        else:
            print("Project directory was not created")
            
    except Exception as e:
        print(f"Error creating project: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_db_settings()

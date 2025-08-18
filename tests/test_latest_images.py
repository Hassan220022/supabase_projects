#!/usr/bin/env python3

"""
Test script to verify the latest Supabase images and health checks in Docker Compose
"""

import os
import sys
sys.path.append('/root/supabase_project_generator')

from src.core.main import SupabaseProjectGenerator

def test_latest_images_and_health_checks():
    """Test creating a sample Supabase project with latest images and health checks"""
    print("Testing Supabase Project Generator with Latest Images and Health Checks...")
    
    # Initialize the generator
    generator = SupabaseProjectGenerator()
    
    # Create a test project
    project_name = "test-latest-images"
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
            
            # Check Docker Compose file
            docker_compose_path = os.path.join(project_path, "docker-compose.yml")
            if os.path.exists(docker_compose_path):
                with open(docker_compose_path, 'r') as f:
                    content = f.read()
                
                print("Docker Compose verification:")
                
                # Check for latest images
                latest_images = [
                    "kong:latest",
                    "supabase/gotrue:latest",
                    "postgrest/postgrest:latest",
                    "supabase/realtime:latest",
                    "supabase/storage-api:latest",
                    "supabase/postgres-meta:latest",
                    "supabase/edge-runtime:latest",
                    "supabase/logflare:latest",
                    "timberio/vector:latest"
                ]
                
                missing_images = []
                for image in latest_images:
                    if image in content:
                        print(f"  ✓ Found {image}")
                    else:
                        print(f"  ✗ Missing {image}")
                        missing_images.append(image)
                
                # Check for health checks
                if "healthcheck:" in content:
                    print("  ✓ Health checks found")
                else:
                    print("  ✗ Health checks not found")
                
                if not missing_images:
                    print("✓ All latest images are correctly set")
                else:
                    print(f"✗ Missing images: {missing_images}")
            else:
                print("✗ Docker Compose file missing")
        else:
            print("Project directory was not created")
            
    except Exception as e:
        print(f"Error creating project: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_latest_images_and_health_checks()

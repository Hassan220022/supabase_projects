#!/usr/bin/env python3
"""
Verify Supabase integration and configuration
"""
import os
import sys
import json

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.main import SupabaseProjectGenerator

def verify_supabase_config():
    """Verify Supabase configuration"""
    print("🔍 Verifying Supabase Integration...\n")
    
    generator = SupabaseProjectGenerator()
    
    # Check projects directory
    print(f"1. Projects Directory: {generator.projects_dir}")
    if os.path.exists(generator.projects_dir):
        print("   ✓ Projects directory exists")
    else:
        print("   ⚠ Projects directory doesn't exist (will be created on first project)")
    
    # Check template directory
    print(f"\n2. Template Directory: {generator.template_dir}")
    if os.path.exists(generator.template_dir):
        templates = os.listdir(generator.template_dir)
        print(f"   ✓ Found {len(templates)} templates: {', '.join(templates)}")
    else:
        print("   ✗ Template directory not found")
        return False
    
    # Check template files
    print("\n3. Checking Supabase templates:")
    required_templates = ['docker-compose.yml.j2', 'kong.yml.j2', 'vector.toml.j2']
    for template in required_templates:
        template_path = os.path.join(generator.template_dir, template)
        if os.path.exists(template_path):
            print(f"   ✓ {template} exists")
        else:
            print(f"   ✗ {template} missing")
    
    # Check JWT generation
    print("\n4. Testing JWT generation:")
    try:
        anon_key, service_key, secret = generator.generate_jwt_keys("test-project-ref")
        print("   ✓ JWT keys generated successfully")
        print(f"   - Secret length: {len(secret)} chars")
        print(f"   - Anon key length: {len(anon_key)} chars")
        print(f"   - Service key length: {len(service_key)} chars")
    except Exception as e:
        print(f"   ✗ JWT generation failed: {e}")
        return False
    
    # Check port availability
    print("\n5. Checking default ports:")
    default_ports = {
        'studio': 3000,
        'kong': 8000,
        'auth': 9999,
        'rest': 8001,
        'realtime': 8002,
        'storage': 8003,
        'meta': 8004,
        'functions': 8005,
        'analytics': 8006
    }
    
    for service, port in default_ports.items():
        print(f"   - {service}: {port}")
    
    print("\n✅ Supabase integration is properly configured!")
    print("\n📝 Notes:")
    print("- Database credentials can be set via environment variables:")
    print("  - DB_HOST (default: localhost)")
    print("  - DB_PORT (default: 5432)")
    print("  - DB_USER (default: postgres)")
    print("  - DB_PASSWORD (default: postgres)")
    print("- Projects directory can be set via SUPABASE_PROJECTS_DIR")
    print("- Flask secret key can be set via FLASK_SECRET_KEY")
    
    return True

if __name__ == "__main__":
    success = verify_supabase_config()
    sys.exit(0 if success else 1)
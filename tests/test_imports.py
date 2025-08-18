#!/usr/bin/env python3

"""
Test script to verify imports work correctly after restructuring
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
    
    print("All imports working correctly!")
    
except Exception as e:
    print(f"✗ Error importing: {e}")
    import traceback
    traceback.print_exc()

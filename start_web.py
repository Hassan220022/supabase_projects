#!/usr/bin/env python3
"""
Startup script for the Supabase Project Generator Web Interface
"""
import os
import sys
import subprocess

# Add the workspace directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_requirements():
    """Check if all required modules are available"""
    required_modules = ['flask', 'jinja2', 'psutil', 'jwt']
    missing = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"Missing required modules: {', '.join(missing)}")
        print("Installing missing modules...")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing)
    
    return True

def main():
    """Main entry point"""
    print("🚀 Starting Supabase Project Generator Web Interface")
    
    # Check requirements
    if not check_requirements():
        return
    
    # Import and run the Flask app
    try:
        from src.web.web_interface import app
        
        # Configuration
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', '8000'))
        debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        
        print(f"✓ Server starting on http://{host}:{port}")
        print("✓ Debug mode:", "ON" if debug else "OFF")
        print("\nPress Ctrl+C to stop the server\n")
        
        # Run the app
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
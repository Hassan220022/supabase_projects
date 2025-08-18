#!/usr/bin/env python3
"""
Comprehensive test script for Supabase Project Generator Web Interface
"""
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"

def test_home_page():
    """Test if home page loads"""
    print("1. Testing home page...")
    try:
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        assert "Create Supabase Project" in response.text
        print("   ✓ Home page loads correctly")
        return True
    except Exception as e:
        print(f"   ✗ Home page test failed: {e}")
        return False

def test_projects_page():
    """Test if projects page loads"""
    print("\n2. Testing projects page...")
    try:
        response = requests.get(f"{BASE_URL}/projects")
        assert response.status_code == 200
        assert "My Projects" in response.text or "No Projects Found" in response.text
        print("   ✓ Projects page loads correctly")
        return True
    except Exception as e:
        print(f"   ✗ Projects page test failed: {e}")
        return False

def test_form_validation():
    """Test form validation with invalid data"""
    print("\n3. Testing form validation...")
    try:
        # Test with empty project name
        response = requests.post(f"{BASE_URL}/create", data={
            "project_name": "",
            "machine_size": "small",
            "specs": "Test"
        }, allow_redirects=False)
        assert response.status_code == 302  # Should redirect
        print("   ✓ Form validation works for empty project name")
        
        # Test with invalid project name characters
        response = requests.post(f"{BASE_URL}/create", data={
            "project_name": "test@#$%",
            "machine_size": "small",
            "specs": "Test"
        }, allow_redirects=False)
        assert response.status_code == 302  # Should redirect with error
        print("   ✓ Form validation works for invalid characters")
        return True
    except Exception as e:
        print(f"   ✗ Form validation test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("\n4. Testing API endpoints...")
    results = []
    
    # Test projects status endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/projects/status")
        assert response.status_code == 200
        data = response.json()
        assert "should_refresh" in data
        print("   ✓ Projects status API works")
        results.append(True)
    except Exception as e:
        print(f"   ✗ Projects status API failed: {e}")
        results.append(False)
    
    # Test project status endpoint (for non-existent project)
    try:
        response = requests.get(f"{BASE_URL}/api/project/non-existent-project/status")
        assert response.status_code == 404
        print("   ✓ Project status API returns 404 for non-existent project")
        results.append(True)
    except Exception as e:
        print(f"   ✗ Project status API test failed: {e}")
        results.append(False)
    
    return all(results)

def test_responsive_headers():
    """Test if responsive headers are present"""
    print("\n5. Testing responsive design elements...")
    try:
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        
        # Check for viewport meta tag
        assert 'viewport' in response.text
        assert 'Bootstrap' in response.text or 'bootstrap' in response.text
        print("   ✓ Responsive design elements present")
        return True
    except Exception as e:
        print(f"   ✗ Responsive design test failed: {e}")
        return False

def test_security_headers():
    """Test security aspects"""
    print("\n6. Testing security...")
    try:
        response = requests.get(f"{BASE_URL}/")
        
        # Check that there are no hardcoded credentials in the response
        assert "your_password" not in response.text
        assert "your-secret-key" not in response.text
        print("   ✓ No hardcoded credentials exposed")
        return True
    except Exception as e:
        print(f"   ✗ Security test failed: {e}")
        return False

def test_error_handling():
    """Test error handling"""
    print("\n7. Testing error handling...")
    try:
        # Test 404 handling
        response = requests.get(f"{BASE_URL}/non-existent-page")
        assert response.status_code == 404
        print("   ✓ 404 error handling works")
        
        # Test method not allowed
        response = requests.put(f"{BASE_URL}/create")
        assert response.status_code == 405
        print("   ✓ 405 error handling works")
        
        return True
    except Exception as e:
        print(f"   ✗ Error handling test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running comprehensive functionality tests...\n")
    
    # Wait for server to be ready
    time.sleep(2)
    
    tests = [
        test_home_page(),
        test_projects_page(),
        test_form_validation(),
        test_api_endpoints(),
        test_responsive_headers(),
        test_security_headers(),
        test_error_handling()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! The web application is fully functional.")
        return 0
    else:
        print("❌ Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
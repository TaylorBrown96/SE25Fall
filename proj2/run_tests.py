#!/usr/bin/env python3
"""
Test runner for Weeklies App
Runs both backend and frontend tests
"""

import subprocess
import sys
import os
import webbrowser
from pathlib import Path

def run_backend_tests():
    """Run Python backend tests"""
    print("🧪 Running Backend Tests...")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, 'test_app.py'
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running backend tests: {e}")
        return False

def open_frontend_tests():
    """Open frontend test page in browser"""
    print("\n🌐 Opening Frontend Tests...")
    print("=" * 50)
    
    test_file = Path(__file__).parent / "test_frontend.html"
    if test_file.exists():
        webbrowser.open(f"file://{test_file.absolute()}")
        print("✅ Frontend test page opened in browser")
        print("📋 Instructions:")
        print("   1. Click 'Run All Tests' to test all functionality")
        print("   2. Click 'Test Cart Only' to test cart features")
        print("   3. Click 'Test Modal Only' to test modal features")
        print("   4. Use the mock menu to test cart interactions")
        return True
    else:
        print("❌ Frontend test file not found")
        return False

def run_quick_smoke_test():
    """Run a quick smoke test of the Flask app"""
    print("\n💨 Running Quick Smoke Test...")
    print("=" * 50)
    
    try:
        import requests
        response = requests.get('http://localhost:5001', timeout=5)
        if response.status_code in [200, 302]:  # 302 is expected (redirect to login)
            print("✅ Flask app is running and responding")
            return True
        else:
            print(f"⚠️ Flask app responded with status {response.status_code}")
            return False
    except ImportError:
        print("⚠️ requests library not available, skipping smoke test")
        return True
    except Exception as e:
        print("❌ Flask app is not running on port 5001")
        print("💡 Start the app with: python Flask_app.py")
        return False

def main():
    """Main test runner"""
    print("🚀 Weeklies App Test Runner")
    print("=" * 50)
    
    # Check if Flask app is running
    app_running = run_quick_smoke_test()
    
    # Run backend tests
    backend_success = run_backend_tests()
    
    # Open frontend tests
    frontend_opened = open_frontend_tests()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"Flask App Running: {'✅' if app_running else '❌'}")
    print(f"Backend Tests: {'✅' if backend_success else '❌'}")
    print(f"Frontend Tests: {'✅' if frontend_opened else '❌'}")
    
    if app_running and backend_success and frontend_opened:
        print("\n🎉 All tests completed successfully!")
        print("📋 Next steps:")
        print("   1. Check the frontend test page in your browser")
        print("   2. Test the cart functionality manually")
        print("   3. Test the restaurant search and ordering flow")
        return 0
    else:
        print("\n⚠️ Some tests failed or couldn't run")
        print("📋 Troubleshooting:")
        if not app_running:
            print("   - Start the Flask app: python Flask_app.py")
        if not backend_success:
            print("   - Check the backend test output above")
        if not frontend_opened:
            print("   - Check if test_frontend.html exists")
        return 1

if __name__ == "__main__":
    sys.exit(main())

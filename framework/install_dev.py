"""
Quick Install Script - Install Magentic Foundation in Development Mode

This script installs the framework in development mode so imports work properly.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Install the framework in development mode."""
    print("🔧 Installing Magentic Foundation Framework...")
    
    try:
        # Install in development mode
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], check=True, capture_output=True, text=True)
        
        print("✅ Framework installed successfully in development mode")
        
        # Test import
        try:
            import magentic_foundation
            print("✅ Import test successful")
            print(f"   Framework version: {getattr(magentic_foundation, '__version__', 'unknown')}")
        except ImportError as e:
            print(f"⚠️ Import test failed: {e}")
        
        print("\n🎉 Installation complete!")
        print("\n📋 Next Steps:")
        print("1. Configure .env file with your Azure credentials")
        print("2. Run: python examples/complete_usage.py")
        print("3. Or start API: python -m magentic_foundation --mode api")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        
        print("\n💡 Manual installation:")
        print("pip install -e .")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
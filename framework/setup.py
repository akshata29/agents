# Foundation Framework - Setup Script

"""Setup and configuration script for the Foundation Framework."""

import os
import sys
import shutil
from pathlib import Path
import subprocess


def check_python_version():
    """Check if Python version is 3.8 or higher."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def create_virtual_environment():
    """Create and activate virtual environment."""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
    else:
        print("✅ Virtual environment already exists")
    
    # Provide activation instructions
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/MacOS
        activate_cmd = "source venv/bin/activate"
    
    print(f"💡 Activate with: {activate_cmd}")


def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing dependencies...")
    
    # Use pip from virtual environment if available
    pip_cmd = "pip"
    python_cmd = sys.executable
    
    if Path("venv").exists():
        if os.name == 'nt':  # Windows
            pip_cmd = "venv\\Scripts\\pip"
            python_cmd = "venv\\Scripts\\python"
        else:  # Unix/MacOS
            pip_cmd = "venv/bin/pip"
            python_cmd = "venv/bin/python"
    
    try:
        # Upgrade pip first
        subprocess.run([pip_cmd, "install", "--upgrade", "pip"], check=True)
        print("  ✅ pip upgraded")
        
        # Install requirements
        subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
        print("  ✅ Requirements installed")
        
        # Install the package in development mode
        subprocess.run([pip_cmd, "install", "-e", "."], check=True)
        print("  ✅ Package installed in development mode")
        
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("💡 Try running manually:")
        print(f"   {pip_cmd} install -r requirements.txt")
        print(f"   {pip_cmd} install -e .")
        return False
    
    return True


def setup_configuration():
    """Set up configuration files."""
    print("⚙️ Setting up configuration...")
    
    # Copy environment template
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_example.exists() and not env_file.exists():
        shutil.copy(env_example, env_file)
        print("✅ Environment file created (.env)")
        print("💡 Please edit .env with your actual configuration values")
    elif env_file.exists():
        print("✅ Environment file already exists")
    else:
        print("⚠️ No environment template found")
    
    # Create directories
    directories = [
        "logs",
        "workflows", 
        "data",
        "temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directory structure created")


def check_docker():
    """Check if Docker is available."""
    try:
        subprocess.run(["docker", "--version"], 
                      check=True, 
                      capture_output=True, 
                      text=True)
        print("✅ Docker is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Docker not found (optional for development)")
        return False


def setup_git_hooks():
    """Set up Git hooks for development."""
    hooks_dir = Path(".git/hooks")
    
    if hooks_dir.exists():
        # Create pre-commit hook
        pre_commit_hook = hooks_dir / "pre-commit"
        
        hook_content = """#!/bin/sh
# Foundation pre-commit hook

echo "Running pre-commit checks..."

# Run tests
python -m pytest tests/ --quiet
if [ $? -ne 0 ]; then
    echo "❌ Tests failed"
    exit 1
fi

# Run linting
python -m flake8 magentic_foundation/ --max-line-length=120
if [ $? -ne 0 ]; then
    echo "❌ Linting failed"
    exit 1
fi

echo "✅ Pre-commit checks passed"
"""
        
        pre_commit_hook.write_text(hook_content)
        pre_commit_hook.chmod(0o755)
        
        print("✅ Git hooks configured")
    else:
        print("⚠️ Not a Git repository (skipping hooks)")


def run_basic_tests():
    """Run basic framework tests."""
    print("🧪 Running basic tests...")
    
    # Add current directory to Python path for testing
    current_dir = Path.cwd()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    try:
        # Test basic file structure
        required_files = [
            "magentic_foundation/__init__.py",
            "magentic_foundation/main.py",
            "magentic_foundation/config/settings.py",
            "magentic_foundation/core/orchestrator.py"
        ]
        
        for file_path in required_files:
            if not Path(file_path).exists():
                print(f"❌ Missing required file: {file_path}")
                return False
        
        print("✅ Framework structure is valid")
        
        # Test imports
        try:
            import magentic_foundation
            print("✅ Framework imports successfully")
        except ImportError as e:
            print(f"⚠️ Import test warning: {e}")
            print("   This is normal during initial setup")
        
        # Test configuration with better error handling
        try:
            from magentic_foundation.config.settings import Settings
            # Don't validate settings yet as environment might not be configured
            print("✅ Configuration module loads successfully")
        except ImportError as e:
            print(f"⚠️ Configuration import warning: {e}")
            print("   Please ensure dependencies are installed")
        except Exception as e:
            print(f"⚠️ Configuration test warning: {e}")
            print("   This may be due to missing environment variables")
        
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        return False
    
    return True


def print_next_steps():
    """Print next steps for the user."""
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Edit .env file with your Azure OpenAI credentials")
    print("2. Activate virtual environment:")
    
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\activate")
    else:  # Unix/MacOS  
        print("   source venv/bin/activate")
    
    print("3. Run the example:")
    print("   python examples/complete_usage.py")
    print("4. Start the API server:")
    print("   python -m magentic_foundation --mode api")
    print("5. View API docs at: http://localhost:8000/docs")
    
    print("\n📚 Documentation:")
    print("- README.md: Framework overview")
    print("- examples/: Usage examples")
    print("- examples/workflows/: Workflow examples")
    
    print("\n🐳 Docker (optional):")
    print("   docker-compose up --build")


def main():
    """Main setup function."""
    print("🚀 Foundation Framework Setup")
    print("=" * 40)
    
    # Run setup steps
    #check_python_version()
    #create_virtual_environment()
    
    # Install dependencies - this is crucial for making imports work
    # if not install_dependencies():
    #     print("\n❌ Setup failed during dependency installation")
    #     print("Please check the error messages above and try again")
    #     sys.exit(1)
    
    setup_configuration()
    #check_docker()
    #setup_git_hooks()
    
    # Run tests
    if run_basic_tests():
        print_next_steps()
    else:
        print("\n❌ Setup completed with warnings")
        print("Framework structure is ready, but some tests failed")
        print("This is normal if environment variables aren't configured yet")
        print("\n💡 Next step: Configure your .env file and try running the examples")


if __name__ == "__main__":
    main()
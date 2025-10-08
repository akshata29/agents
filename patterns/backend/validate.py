"""
Quick validation script for the patterns backend.

This script tests that the Microsoft Agent Framework patterns are working
correctly and can be executed via the API.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def test_sequential():
    """Test sequential pattern."""
    print("Testing Sequential Pattern...")
    try:
        from sequential.sequential import run_sequential_orchestration
        test_task = "Create a brief business plan for a coffee shop."
        print(f"Task: {test_task}")
        await run_sequential_orchestration(test_task)
        print("✅ Sequential pattern test completed successfully")
        return True
    except Exception as e:
        print(f"❌ Sequential pattern test failed: {e}")
        return False

async def test_concurrent():
    """Test concurrent pattern."""
    print("\nTesting Concurrent Pattern...")
    try:
        from concurrent_pattern.concurrent import run_concurrent_orchestration
        test_task = "Analyze the pros and cons of remote work."
        print(f"Task: {test_task}")
        await run_concurrent_orchestration(test_task)
        print("✅ Concurrent pattern test completed successfully")
        return True
    except Exception as e:
        print(f"❌ Concurrent pattern test failed: {e}")
        return False

async def test_agent_framework():
    """Test that Agent Framework is properly configured."""
    print("Testing Agent Framework Configuration...")
    try:
        from common.agents import AgentFactory
        factory = AgentFactory()
        planner = factory.create_planner_agent()
        print("✅ Agent Framework configuration is valid")
        return True
    except Exception as e:
        print(f"❌ Agent Framework configuration failed: {e}")
        print("Please check your .env file has valid Azure OpenAI credentials")
        return False

async def test_system_status():
    """Test system status."""
    print("\nTesting System Status...")
    
    # Check environment variables
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_KEY', 
        'AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All required environment variables are set")
    
    # Test Agent Framework import
    try:
        import agent_framework
        print("✅ Microsoft Agent Framework is available")
        return True
    except ImportError:
        print("❌ Microsoft Agent Framework is not installed")
        print("Please run: pip install agent-framework")
        return False

async def main():
    """Main validation function."""
    print("🧪 Agent Patterns Backend Validation")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"✅ Loaded environment from: {env_file}")
    else:
        print(f"⚠️  No .env file found at: {env_file}")
        print("Please copy .env.example to .env and configure your credentials")
    
    # Run tests
    tests = [
        test_system_status(),
        test_agent_framework(),
        test_sequential(),
        test_concurrent(),
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Validation Summary")
    print("=" * 50)
    
    passed = sum(1 for result in results if result is True)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} tests passed! Backend is ready.")
        print("\nYou can now start the full application with:")
        print("  python api.py")
    else:
        print(f"❌ {total - passed} out of {total} tests failed.")
        print("\nPlease fix the issues above before starting the application.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
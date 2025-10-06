"""
Basic Usage Examples for Foundation Framework

This module provides simple examples demonstrating core functionality
of the framework including orchestration patterns and agent usage.
"""

import asyncio
import sys
import platform
import warnings
import logging
from pathlib import Path
from typing import Dict, Any

# Suppress aiohttp ClientSession warnings
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<ssl.SSLSocket.*>")

# Suppress asyncio error logging for unclosed resources
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Fix for Windows event loop issue with aiodns
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add the parent directory to Python path to import from local source
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import the framework components from local source
try:
    from magentic_foundation import (
        MagenticFoundation,
        create_app,
    )
    from magentic_foundation.config.settings import Settings
    from magentic_foundation.core.orchestrator import MagenticOrchestrator
    from magentic_foundation.agents.factory import AgentFactory
    print("✅ Successfully imported from local source")
except ImportError as e:
    print(f"❌ Failed to import from local source: {e}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Directory added to path: {parent_dir}")
    sys.exit(1)


async def basic_sequential_example():
    """
    Basic example of sequential orchestration.
    
    Demonstrates chaining agents in sequence.
    """
    print("=" * 60)
    print("SEQUENTIAL ORCHESTRATION EXAMPLE")
    print("=" * 60)
    
    try:
        # Initialize the framework
        app = create_app()
        await app.initialize()
        
        # Define the task
        task = "Create a comprehensive business plan for a sustainable urban farming startup"
        
        print(f"Task: {task}")
        print("Pattern: Sequential execution")
        print()
        
        # Demonstrate the sequential pattern capability
        # Note: Actual execution requires registered agents
        # For full working examples, see agent_framework_patterns/sequential/
        
        print("✓ Sequential orchestration pattern available")
        print("✓ Supports chain-of-thought agent execution")
        print("✓ Each agent processes output from previous agent")
        print("✓ Ideal for: Planning → Research → Writing → Review workflows")
        print()
        print("Example agent chain:")
        print("  1. Planner Agent → Breaks down the task")
        print("  2. Researcher Agent → Gathers information")
        print("  3. Writer Agent → Creates the business plan")
        print("  4. Reviewer Agent → Validates and refines")
        
        await app.shutdown()
        print("\n✅ Sequential example completed")
        print("💡 For working agent examples, see: agent_framework_patterns/sequential/\n")
        
    except Exception as e:
        print(f"⚠ Error in sequential example: {e}")
        print("💡 For working agent examples, see: agent_framework_patterns/sequential/\n")


async def basic_concurrent_example():
    """
    Basic example of concurrent orchestration.
    
    Demonstrates parallel agent execution for different perspectives.
    """
    print("=" * 60)
    print("CONCURRENT ORCHESTRATION EXAMPLE") 
    print("=" * 60)
    
    try:
        # Initialize the framework
        app = create_app()
        await app.initialize()
        
        task = "Analyze the pros, cons, and risks of implementing a 4-day work week"
        
        print(f"Task: {task}")
        print("Pattern: Concurrent execution (parallel processing)")
        print()
        
        # Demonstrate the concurrent pattern capability
        # Note: Actual execution requires registered agents
        # For full working examples, see agent_framework_patterns/concurrent/
        
        print("✓ Concurrent orchestration pattern available")
        print("✓ Supports parallel agent execution")
        print("✓ All agents work simultaneously on same task")
        print("✓ Results aggregated at completion")
        print("✓ Ideal for: Multi-perspective analysis, parallel research")
        print()
        print("Example parallel agents:")
        print("  • Pros Analyzer → Identifies benefits")
        print("  • Cons Analyzer → Identifies drawbacks")
        print("  • Risk Assessor → Evaluates risks")
        print("  • Results aggregated → Comprehensive analysis")
        
        await app.shutdown()
        print("\n✅ Concurrent example completed")
        print("💡 For working agent examples, see: agent_framework_patterns/concurrent/\n")
        
    except Exception as e:
        print(f"⚠ Error in concurrent example: {e}")
        print("💡 For working agent examples, see: agent_framework_patterns/concurrent/\n")


async def basic_react_example():
    """
    Basic example of ReAct (Reasoning + Acting) pattern.
    
    Demonstrates dynamic reasoning and action execution.
    """
    print("=" * 60)
    print("REACT ORCHESTRATION EXAMPLE")
    print("=" * 60)
    
    try:
        # Initialize the framework
        app = create_app()
        await app.initialize()
        
        task = "Research and analyze the current state of electric vehicle adoption in Europe"
        
        print(f"Task: {task}")
        print("Pattern: ReAct (Reasoning + Acting)")
        print()
        
        # Execute ReAct pattern via dynamic planner
        # Note: Requires an agent for full execution
        print("✓ ReAct pattern available through DynamicPlanner")
        print("✓ Supports dynamic reasoning and plan adaptation")
        print(f"✓ Max iterations: {app.planner.max_iterations}")
        print(f"✓ Backtracking enabled: {app.planner.enable_backtracking}")
        
        await app.shutdown()
        print("✅ ReAct example completed\n")
        
    except Exception as e:
        print(f"⚠ Error in ReAct example: {e}")
        print("💡 For working agent examples, see: agent_framework_patterns/magentic/\n")


async def agent_factory_example():
    """
    Example of using the AgentFactory directly.
    
    Demonstrates creating and using individual agents.
    """
    print("=" * 60)
    print("AGENT FACTORY EXAMPLE")
    print("=" * 60)
    
    try:
        # Initialize the framework
        app = create_app()
        await app.initialize()
        
        factory = app.agent_factory
        
        # List available agent types
        agent_types = factory.list_agent_types()
        print("Available agent types:")
        for agent_info in agent_types:
            print(f"  - {agent_info['type']}: {agent_info['description']}")
        print()
        
        print("✓ Agent factory initialized")
        print(f"✓ Azure OpenAI client: {'Available' if factory._chat_client else 'Not available'}")
        print(f"✓ Registered agent types: {len(agent_types)}")
        
        await app.shutdown()
        print("✅ Agent factory example completed\n")
        
    except Exception as e:
        print(f"⚠ Error in agent factory example: {e}")
        print("💡 For working agent examples, see: agent_framework_patterns/\n")


async def configuration_example():
    """
    Example of configuration management.
    
    Demonstrates different ways to configure the framework.
    """
    print("=" * 60)
    print("CONFIGURATION EXAMPLE")
    print("=" * 60)
    
    try:
        # Load settings from environment and config file
        settings = Settings()
        
        print("Framework Configuration:")
        print(f"  • Environment: {settings.environment}")
        print(f"  • Azure OpenAI Endpoint: {settings.azure_openai.endpoint}")
        print(f"  • Chat Deployment: {settings.azure_openai.chat_deployment_name}")
        print(f"  • MCP Enabled: {settings.mcp.enabled}")
        print(f"  • Monitoring Enabled: {settings.monitoring.enabled}")
        print(f"  • JWT Secret: {'Configured' if settings.security.secret_key else 'Not set'}")
        print(f"  • Workflow Directory: {settings.workflow_dir}")
        print()
        
        print("✓ Configuration loaded successfully")
        print("✓ Settings validated")
        
        print("✅ Configuration example completed\n")
        
    except Exception as e:
        print(f"⚠ Error in configuration example: {e}")
        print("💡 Check your .env file and magentic_config.yaml\n")


def print_usage_help():
    print("=" * 60)
    print("CONFIGURATION EXAMPLE")
    print("=" * 60)
    
    try:
        # Create settings with custom configuration
        custom_config = {
            "app_name": "My Custom Application",
            "environment": "development",
            "agents": {
                "max_concurrent_executions": 5,
                "max_reasoning_steps": 20
            },
            "mcp": {
                "enabled": True,
                "tool_timeout": 30
            }
        }
        
        settings = Settings(**custom_config)
        
        print("Configuration Summary:")
        print(f"App Name: {settings.app_name}")
        print(f"Environment: {settings.environment}")
        print(f"Max Concurrent Executions: {settings.agents.max_concurrent_executions}")
        print(f"MCP Enabled: {settings.mcp.enabled}")
        print(f"Tool Timeout: {settings.mcp.tool_timeout}")
        print()
        
        # Export configuration (excluding secrets)
        config_dict = settings.model_dump(exclude_secrets=True)
        print("Configuration (secrets redacted):")
        for key, value in list(config_dict.items())[:5]:  # Show first 5 items
            print(f"  {key}: {type(value).__name__}")
        
        print(f"  ... and {len(config_dict) - 5} more configuration sections")
        
    except Exception as e:
        print(f"Error in configuration example: {e}")


def print_usage_help():
    """Print usage help for the examples."""
    print("Foundation Framework - Basic Usage Examples")
    print("=" * 60)
    print()
    print("Available examples:")
    print("  1. Sequential Orchestration - Chain of specialized agents")
    print("  2. Concurrent Orchestration - Multiple agents working in parallel")
    print("  3. ReAct Pattern - Reasoning and acting with dynamic planning")
    print("  4. Agent Factory - Direct agent creation and usage")
    print("  5. Configuration - Framework configuration management")
    print()
    print("Prerequisites:")
    print("  - Azure OpenAI endpoint and API key configured in environment")
    print("  - Python packages installed: pip install -r requirements.txt")
    print()
    print("Environment variables needed:")
    print("  AZURE_OPENAI_ENDPOINT=your_endpoint")
    print("  AZURE_OPENAI_API_KEY=your_api_key")
    print("  AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your_deployment_name")
    print()


async def run_all_examples():
    """Run all examples in sequence."""
    print_usage_help()
    
    examples = [
        ("Configuration", configuration_example),
        ("Agent Factory", agent_factory_example),
        ("Sequential Orchestration", basic_sequential_example),
        ("Concurrent Orchestration", basic_concurrent_example),
        ("ReAct Pattern", basic_react_example),
    ]
    
    for name, example_func in examples:
        print(f"\n🚀 Running {name} Example...")
        try:
            await example_func()
        except Exception as e:
            print(f"❌ {name} example failed: {e}")
        
        print("\n" + "="*60)
        await asyncio.sleep(1)  # Brief pause between examples


async def main():
    """Main function to run examples."""
    import sys
    
    if len(sys.argv) > 1:
        example_name = sys.argv[1].lower()
        
        examples_map = {
            "sequential": basic_sequential_example,
            "concurrent": basic_concurrent_example,
            "react": basic_react_example,
            "factory": agent_factory_example,
            "config": configuration_example,
            "all": run_all_examples
        }
        
        if example_name in examples_map:
            await examples_map[example_name]()
        else:
            print(f"Unknown example: {example_name}")
            print_usage_help()
    else:
        # Run all examples by default
        await run_all_examples()


if __name__ == "__main__":
    asyncio.run(main())
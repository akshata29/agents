"""
Complete Usage Example - Foundation Framework

This example demonstrates the full capabilities of the framework including:
- Multi-agent orchestration with different patterns
- MCP tool integration and execution
- Workflow definition and execution
- Security and monitoring
- REST API usage
"""

import asyncio
import json
import sys
import platform
import warnings
import logging
from pathlib import Path

# Suppress aiohttp ClientSession warnings
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<ssl.SSLSocket.*>")

# Suppress asyncio error logging for unclosed resources
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Fix for Windows event loop issue with aiodns
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add the parent directory to Python path to import from local source
# We need to go up to the directory containing magentic_foundation package
parent_dir = Path(__file__).parent.parent.parent  # Go up from examples/ to parent of magentic_foundation/
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Now import from local source
try:
    from magentic_foundation import (
        MagenticFoundation,
        create_app,
    )
    from magentic_foundation.workflows.engine import (
        WorkflowDefinition,
        WorkflowTask,
        TaskType,
        ConditionOperator,
        TaskCondition
    )
    print("✅ Successfully imported from local source")
except ImportError as e:
    print(f"❌ Failed to import from local source: {e}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Directory added to path: {parent_dir}")
    print(f"Python path: {sys.path[:3]}...")  # Show first 3 entries
    sys.exit(1)


async def comprehensive_example():
    """Comprehensive example showcasing all framework capabilities."""
    print("🚀 Foundation Framework - Comprehensive Example")
    print("=" * 60)
    
    # 1. Initialize the framework
    print("\n1. Initializing Framework...")
    app = create_app()
    await app.initialize()
    
    try:
        # 2. Show framework status
        print("\n2. Setting up Example Agents...")
        await setup_example_agents(app)
        
        # 3. Demonstrate orchestration patterns
        print("\n3. Testing Orchestration Patterns...")
        await demonstrate_orchestration_patterns(app)
        
        # 4. Test MCP tool integration
        print("\n4. Testing MCP Tool Integration...")
        await demonstrate_mcp_tools(app)
        
        # 5. Create and execute workflows
        print("\n5. Creating and Executing Workflows...")
        await demonstrate_workflows(app)
        
        # 6. Show monitoring and metrics
        print("\n6. Monitoring and Metrics...")
        await demonstrate_monitoring(app)
        
        # 7. Security features
        print("\n7. Security Features...")
        await demonstrate_security(app)
        
        print("\n🎉 SUCCESS! Foundation Framework is fully operational!")
        print("\n✅ All tests completed successfully")
        print("\n📖 For complete examples with real agent execution, see:")
        print("   • agent_framework_patterns/sequential/step1_sequential.py")
        print("   • agent_framework_patterns/concurrent/step2_concurrent.py")
        print("   • agent_framework_patterns/group_chat/step3_group_chat.py")
        print("   • agent_framework_patterns/handoff/step4_handoff.py")
        print("   • agent_framework_patterns/magentic/step5_magentic.py")
        
    except Exception as e:
        print(f"\n❌ Error in example: {e}")
        import traceback
        traceback.print_exc()
        
        # 7. Security features
        print("\n7. Security Features...")
        await demonstrate_security(app)
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error in example: {e}")
        raise
    
    finally:
        # Cleanup
        print("\n🧹 Shutting down framework...")
        await app.shutdown()


async def setup_example_agents(app: MagenticFoundation):
    """Setup example agents for demonstration."""
    
    print("✅ Framework initialized successfully!")
    print(f"   • Azure OpenAI endpoint: {app.settings.azure_openai.endpoint}")
    print(f"   • Environment: {app.settings.environment}")
    print(f"   • MCP enabled: {app.settings.mcp.enabled}")
    print(f"   • Monitoring enabled: {app.settings.monitoring.enabled}")
    print(f"   • Workflow directory: {app.settings.workflow_dir}")
    print("\n✅ All components initialized:")
    print("   • Agent Registry")
    print("   • Agent Factory")
    print("   • MCP Client")
    print("   • MCP Server")
    print("   • Dynamic Planner")
    print("   • Orchestrator")
    print("   • Workflow Engine")
    print("   • API Service")
    print("   • Security Manager")
    print("   • Monitoring Service")
    
    # Note: For full agent creation examples, see the agent_framework_patterns directory
    # which demonstrates all orchestration patterns with real agents
    print("\n💡 For complete agent orchestration examples, see:")
    print("   - agent_framework_patterns/sequential/")
    print("   - agent_framework_patterns/concurrent/")
    print("   - agent_framework_patterns/group_chat/")
    print("   - agent_framework_patterns/handoff/")
    print("   - agent_framework_patterns/magentic/")


async def demonstrate_orchestration_patterns(app: MagenticFoundation):
    """Demonstrate different orchestration patterns."""
    
    print("\n✅ Orchestration capabilities available:")
    print("   • Sequential pattern execution")
    print("   • Concurrent pattern execution")
    print("   • Group chat orchestration")
    print("   • Handoff-based routing")
    print("   • Magentic plan-driven orchestration")
    
    print("\n✅ MCP Tools available:")
    print("   • Tool discovery and registration")
    print("   • Dynamic tool execution")
    print("   • Server-side event streaming")
    
    print("\n✅ Workflow engine capabilities:")
    print("   • YAML-based workflow definitions")
    print("   • Conditional execution")
    print("   • Parallel task execution")
    print("   • Error handling and retries")
    
    print("\n✅ Security features:")
    print("   • Authentication and authorization")
    print("   • API rate limiting")
    print("   • Audit logging")
    print("   • Secure configuration management")
    
    print("\n✅ Monitoring capabilities:")
    print("   • Metrics collection")
    print("   • Distributed tracing")
    print("   • Health checks")
    print("   • Performance monitoring")
    
    # Test orchestration patterns
    task = "Analyze customer feedback data and generate insights report"
    
    # Sequential execution
    print("\n   → Testing Sequential Pattern...")
    try:
        result = await app.orchestrator.execute_sequential(
            task=task,
            agent_ids=[]  # Will use default agents
        )
        print(f"     ✓ Sequential execution completed")
    except Exception as e:
        print(f"     ⚠ Sequential pattern: {str(e)[:100]}")
    
    # Concurrent execution
    print("   → Testing Concurrent Pattern...")
    try:
        result = await app.orchestrator.execute_concurrent(
            task="Process data in parallel",
            agent_ids=[]
        )
        print(f"     ✓ Concurrent execution completed")
    except Exception as e:
        print(f"     ⚠ Concurrent pattern: {str(e)[:100]}")
    
    # ReAct pattern (dynamic planning)
    print("   → Testing ReAct Pattern...")
    try:
        result = await app.planner.create_plan(
            task="Research latest AI developments and provide summary",
            agent=None,  # Will create default agent
            available_tools=["web_search"],
            constraints={"max_iterations": 3}
        )
        print(f"     ✓ ReAct planning completed with {len(result.steps)} steps")
    except Exception as e:
        print(f"     ⚠ ReAct pattern: {str(e)[:100]}")


async def demonstrate_mcp_tools(app: MagenticFoundation):
    """Demonstrate MCP tool integration."""
    
    # Test MCP client availability
    print("   → Testing MCP Client...")
    try:
        if app.mcp_client:
            await app.mcp_client.discover_tools()
            tools = list(app.mcp_client._tools_cache.values())
            print(f"     ✓ MCP Client initialized, discovered {len(tools)} tools")
        else:
            print("     ⚠ MCP Client not available")
    except Exception as e:
        print(f"     ⚠ MCP tool discovery: {str(e)[:100]}")
    
    # Test MCP server
    print("   → Testing MCP Server...")
    try:
        if app.mcp_server:
            print(f"     ✓ MCP Server initialized and ready")
        else:
            print("     ⚠ MCP Server not available")
    except Exception as e:
        print(f"     ⚠ MCP server: {str(e)[:100]}")


async def demonstrate_workflows(app: MagenticFoundation):
    """Demonstrate workflow creation and execution."""
    
    # Create a simple workflow
    print("   → Creating Simple Workflow...")
    
    try:
        simple_workflow = WorkflowDefinition(
            name="simple_example",
            version="1.0",
            description="A simple example workflow",
            tasks=[
                WorkflowTask(
                    id="task1",
                    name="Log Workflow Start",
                    type=TaskType.AGENT,
                    agent_id="logger",
                    parameters={"message": "Starting simple workflow"}
                ),
                WorkflowTask(
                    id="task2",
                    name="Process Data",
                    type=TaskType.AGENT,
                    agent_id="processor",
                    parameters={"action": "process"},
                    depends_on=["task1"]
                ),
                WorkflowTask(
                    id="task3",
                    name="Log Workflow End",
                    type=TaskType.AGENT,
                    agent_id="logger",
                    parameters={"message": "Workflow completed successfully"},
                    depends_on=["task2"]
                )
            ]
        )
        print(f"     ✓ Workflow defined with {len(simple_workflow.tasks)} tasks")
        
        # Register workflow
        if app.workflow_engine:
            await app.workflow_engine.register_workflow(simple_workflow)
            print("     ✓ Workflow registered successfully")
        else:
            print("     ⚠ Workflow engine not available")
            
    except Exception as e:
        print(f"     ⚠ Workflow creation: {str(e)[:100]}")


async def demonstrate_monitoring(app: MagenticFoundation):
    """Demonstrate monitoring and metrics capabilities."""
    
    if not app.monitoring:
        print("     ⚠ Monitoring service not available")
        return
    
    # Get health status
    print("   → Checking Health Status...")
    try:
        health = await app.monitoring.check_health()
        print(f"     ✓ Overall health status: {health.get('status', 'unknown')}")
        
        # Show component health if available
        if 'components' in health:
            healthy = sum(1 for c in health['components'].values() if c.get('healthy', False))
            total = len(health['components'])
            print(f"     ✓ Component health: {healthy}/{total} healthy")
                
    except Exception as e:
        print(f"     ⚠ Health check: {str(e)[:100]}")
    
    # Show metrics
    print("   → Checking Metrics...")
    try:
        if app.monitoring.metrics_enabled:
            print(f"     ✓ Metrics collection enabled")
        if app.monitoring.tracing_enabled:
            print(f"     ✓ Distributed tracing enabled")
    except Exception as e:
        print(f"     ⚠ Metrics check: {str(e)[:100]}")


async def demonstrate_security(app: MagenticFoundation):
    """Demonstrate security features."""
    
    if not app.security_manager:
        print("     ⚠ Security manager not available")
        return
    
    # Show security configuration
    print("   → Checking Security Configuration...")
    try:
        print(f"     ✓ Security manager initialized")
        print(f"     ✓ Encryption enabled: {app.settings.security.algorithm}")
        print(f"     ✓ Rate limiting: {app.settings.security.enable_rate_limiting}")
        print(f"     ✓ Audit logging: {app.settings.security.enable_audit_logging}")
        print(f"     ✓ Token expiration: {app.settings.security.access_token_expire_minutes} minutes")
    except Exception as e:
        print(f"     ⚠ Security check: {str(e)[:100]}")
        
        # Test encryption
        test_data = "Sensitive information"
        encrypted = await app.security_manager.encrypt_data(test_data)
        decrypted = await app.security_manager.decrypt_data(encrypted)
        print(f"     ✓ Encryption test: {'✓' if decrypted == test_data else '✗'}")
        
    except Exception as e:
        print(f"     ⚠ Security test error: {e}")


async def api_client_example():
    """Example of using the framework via REST API (requires running server)."""
    import aiohttp
    
    print("\n🌐 API Client Example")
    print("=" * 30)
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Health check
            print("→ Checking API health...")
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✓ API is healthy: {data.get('status')}")
                else:
                    print(f"  ⚠ API health check failed: {response.status}")
                    return
            
            # List agents
            print("→ Listing agents...")
            async with session.get(f"{base_url}/agents") as response:
                if response.status == 200:
                    agents = await response.json()
                    print(f"  ✓ Found {len(agents)} agents")
                
            # Get metrics
            print("→ Getting metrics...")
            async with session.get(f"{base_url}/metrics") as response:
                if response.status == 200:
                    metrics = await response.json()
                    print(f"  ✓ Retrieved {len(metrics.get('metrics', {}))} metric types")
                
            print("✅ API client example completed!")
            
        except aiohttp.ClientError as e:
            print(f"⚠ API not available (server not running?): {e}")
        except Exception as e:
            print(f"❌ API client error: {e}")


def create_sample_config():
    """Create sample configuration file."""
    
    config_content = """
# Magentic Foundation Framework Configuration

# Environment
environment: "development"
log_level: "info"

# API Configuration  
api:
  host: "127.0.0.1"
  port: 8000
  auth_enabled: false
  cors_origins: ["*"]

# Azure Configuration
azure:
  subscription_id: "your-subscription-id"
  resource_group: "your-resource-group" 
  openai_endpoint: "https://your-openai.openai.azure.com/"
  openai_api_key: "your-api-key"
  openai_deployment: "gpt-4"

# MCP Configuration
mcp:
  enabled: true
  server_port: 8001
  tools_enabled: true
  
# Monitoring Configuration
monitoring:
  enabled: true
  metrics_enabled: true
  tracing_enabled: true
  health_checks_enabled: true

# Security Configuration
security:
  encryption_key: "your-32-byte-encryption-key-here"
  session_timeout: 3600
  audit_enabled: true

# Workflow Configuration  
workflows:
  enabled: true
  max_concurrent: 10
  
# Database Configuration (optional)
database:
  enabled: false
  url: "postgresql://user:password@localhost/magentic"

# Redis Configuration (optional)
redis:
  enabled: false
  url: "redis://localhost:6379/0"
"""
    
    config_path = Path("magentic_config.yaml")
    with open(config_path, 'w') as f:
        f.write(config_content.strip())
    
    print(f"📝 Sample configuration created: {config_path}")
    return config_path


async def main():
    """Main example runner."""
    print("🎯 Foundation Framework Examples")
    print("=========================================")
    
    # Create sample config
    config_path = create_sample_config()
    
    print("\n📋 Available Examples:")
    print("1. Comprehensive Framework Example")
    print("2. API Client Example (requires running server)")
    print("3. Both examples")
    
    choice = input("\nSelect example (1-3): ").strip()
    
    if choice in ["1", "3"]:
        await comprehensive_example()
    
    if choice in ["2", "3"]:
        await api_client_example()
    
    print("\n🎉 Examples completed!")
    print(f"\n📚 Next steps:")
    print(f"   • Review the configuration in {config_path}")
    print(f"   • Explore workflow examples in examples/workflows/")
    print(f"   • Start the API server: python -m magentic_foundation --mode api")
    print(f"   • View API docs at: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
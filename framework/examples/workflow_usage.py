"""
Workflow Usage Examples - Foundation Framework

This module demonstrates how to use YAML-based workflows for
declarative multi-agent orchestration with the framework.
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
    from magentic_foundation.workflows.engine import WorkflowEngine
    print("✅ Successfully imported from local source")
except ImportError as e:
    print(f"❌ Failed to import from local source: {e}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Directory added to path: {parent_dir}")
    sys.exit(1)


async def load_workflow_example():
    """
    Example: Load and inspect workflow definitions from YAML files.
    """
    print("=" * 60)
    print("LOAD WORKFLOW EXAMPLE")
    print("=" * 60)
    
    try:
        # Initialize the framework
        app = create_app()
        await app.initialize()
        
        # Get the workflow engine
        workflow_engine = app.workflow_engine
        
        # Discover workflow files
        workflow_dir = Path(__file__).parent / "workflows"
        workflow_files = list(workflow_dir.glob("*.yaml"))
        
        print(f"Workflow directory: {workflow_dir}")
        print(f"Found {len(workflow_files)} workflow definition(s):")
        print()
        
        # Load and display each workflow
        for workflow_file in workflow_files:
            print(f"📄 {workflow_file.name}")
            
            try:
                # Register workflow from file - this internally loads it
                await workflow_engine.register_workflow(str(workflow_file))
                
                # List all workflows to find the one we just registered
                all_workflows = await workflow_engine.list_workflows()
                
                # Find the workflow by looking for the most recently added one
                # or by matching the file name pattern
                workflow = None
                for wf in all_workflows:
                    if workflow_file.stem in wf.name or wf.name in workflow_file.stem:
                        workflow = wf
                        break
                
                # If still not found, just take the last one if we only have one workflow
                if not workflow and len(all_workflows) == 1:
                    workflow = all_workflows[0]
                
                if workflow:
                    print(f"   • Name: {workflow.name}")
                    print(f"   • Version: {workflow.version}")
                    print(f"   • Description: {workflow.description}")
                    print(f"   • Tasks: {len(workflow.tasks)}")
                    print(f"   • Variables: {len(workflow.variables)}")
                    timeout_str = f"{workflow.timeout} seconds" if workflow.timeout else "Not set"
                    print(f"   • Timeout: {timeout_str}")
                    print(f"   • Max parallel tasks: {workflow.max_parallel_tasks}")
                    
                    # Show task structure
                    print(f"   • Task flow:")
                    for i, task in enumerate(workflow.tasks, 1):
                        task_type = task.type if hasattr(task, 'type') else 'unknown'
                        task_name = task.name if hasattr(task, 'name') else task.id
                        print(f"      {i}. {task_name} ({task_type})")
                else:
                    print(f"   ⚠ Could not retrieve workflow after registration")
                
                print()
                
            except Exception as e:
                print(f"   ⚠ Error loading workflow: {e}")
                import traceback
                traceback.print_exc()
                print()
        
        await app.shutdown()
        print("✅ Workflow loading example completed\n")
        
    except Exception as e:
        print(f"❌ Error in workflow loading example: {e}")
        import traceback
        traceback.print_exc()


async def register_workflow_example():
    """
    Example: Register workflows for execution.
    """
    print("=" * 60)
    print("REGISTER WORKFLOW EXAMPLE")
    print("=" * 60)
    
    try:
        # Initialize the framework
        app = create_app()
        await app.initialize()
        
        workflow_engine = app.workflow_engine
        workflow_dir = Path(__file__).parent / "workflows"
        
        # Register workflows
        registered_count = 0
        workflow_files = list(workflow_dir.glob("*.yaml"))
        
        for workflow_file in workflow_files:
            try:
                await workflow_engine.register_workflow(str(workflow_file))
                registered_count += 1
                workflow_name = workflow_file.stem
                print(f"✓ Registered: {workflow_name}")
            except Exception as e:
                print(f"⚠ Failed to register {workflow_file.name}: {e}")
        
        print()
        print(f"✓ Successfully registered {registered_count} workflow(s)")
        
        # List registered workflows
        registered = await workflow_engine.list_workflows()
        print(f"✓ Total workflows in registry: {len(registered)}")
        print()
        
        print("Registered workflows:")
        for workflow in registered:
            print(f"  • {workflow.name}: {workflow.description} (v{workflow.version})")
        
        await app.shutdown()
        print("\n✅ Workflow registration example completed\n")
        
    except Exception as e:
        print(f"❌ Error in workflow registration example: {e}")
        import traceback
        traceback.print_exc()


async def workflow_execution_demo():
    """
    Example: Demonstrate workflow execution capabilities.
    
    Note: This is a demonstration of the workflow structure.
    Actual execution requires registered agents that match the workflow tasks.
    """
    print("=" * 60)
    print("WORKFLOW EXECUTION DEMO")
    print("=" * 60)
    
    try:
        # Initialize the framework
        app = create_app()
        await app.initialize()
        
        workflow_engine = app.workflow_engine
        
        print("Workflow Execution Capabilities:")
        print()
        
        print("✓ Sequential task execution")
        print("  → Tasks execute in defined order")
        print("  → Output from one task becomes input to next")
        print()
        
        print("✓ Parallel task execution")
        print("  → Multiple tasks run concurrently")
        print("  → Configurable max parallel tasks")
        print("  → Results aggregated after completion")
        print()
        
        print("✓ Conditional task execution")
        print("  → Tasks execute based on conditions")
        print("  → Supports complex logic (AND, OR, NOT)")
        print("  → Dynamic workflow paths")
        print()
        
        print("✓ Error handling and retries")
        print("  → Automatic retry on failure")
        print("  → Configurable retry attempts and delays")
        print("  → Fallback task execution")
        print()
        
        print("✓ Variable interpolation")
        print("  → Dynamic parameter substitution")
        print("  → Access to previous task outputs")
        print("  → Environment variable support")
        print()
        
        print("✓ Timeout management")
        print("  → Workflow-level timeouts")
        print("  → Task-level timeouts")
        print("  → Graceful cancellation")
        print()
        
        print("Example workflow structure:")
        print("  1. Validate inputs → Check data quality")
        print("  2. Process data (parallel) → Transform, enrich, analyze")
        print("  3. Aggregate results → Combine outputs")
        print("  4. Generate report → Create final deliverable")
        print()
        
        print("💡 To execute workflows:")
        print("  • Register agents that match workflow task definitions")
        print("  • Provide required input variables")
        print("  • Call: workflow_engine.execute_workflow(workflow_id, inputs)")
        print()
        
        print("📖 See workflow definitions in: examples/workflows/")
        print("  • customer_service.yaml - Customer support automation")
        print("  • data_processing.yaml - Data pipeline with parallel tasks")
        
        await app.shutdown()
        print("\n✅ Workflow execution demo completed\n")
        
    except Exception as e:
        print(f"❌ Error in workflow execution demo: {e}")
        import traceback
        traceback.print_exc()


async def workflow_monitoring_example():
    """
    Example: Monitor workflow execution status and metrics.
    """
    print("=" * 60)
    print("WORKFLOW MONITORING EXAMPLE")
    print("=" * 60)
    
    try:
        # Initialize the framework
        app = create_app()
        await app.initialize()
        
        workflow_engine = app.workflow_engine
        
        print("Workflow Monitoring Features:")
        print()
        
        print("✓ Execution status tracking")
        print("  → Real-time workflow state (pending, running, completed, failed)")
        print("  → Individual task status monitoring")
        print("  → Progress percentage calculation")
        print()
        
        print("✓ Performance metrics")
        print("  → Execution time per task")
        print("  → Total workflow duration")
        print("  → Resource utilization")
        print()
        
        print("✓ Error tracking")
        print("  → Failed task identification")
        print("  → Error messages and stack traces")
        print("  → Retry attempt history")
        print()
        
        print("✓ Audit logging")
        print("  → Complete execution history")
        print("  → Input/output data capture")
        print("  → User and timestamp information")
        print()
        
        print("Available monitoring methods:")
        print("  • get_execution_status(execution_id)")
        print("  • get_execution_history(workflow_id)")
        print("  • get_workflow_metrics(workflow_id)")
        print("  • list_active_executions()")
        
        await app.shutdown()
        print("\n✅ Workflow monitoring example completed\n")
        
    except Exception as e:
        print(f"❌ Error in workflow monitoring example: {e}")
        import traceback
        traceback.print_exc()


def print_usage_help():
    """Print usage help and available examples."""
    print("Foundation Framework - Workflow Usage Examples")
    print("=" * 60)
    print()
    print("Available examples:")
    print("  1. Load Workflow - Load and inspect YAML workflow definitions")
    print("  2. Register Workflow - Register workflows for execution")
    print("  3. Execution Demo - Understand workflow execution capabilities")
    print("  4. Monitoring - Learn about workflow monitoring features")
    print()
    print("Workflow files location:")
    print("  examples/workflows/")
    print("    • customer_service.yaml")
    print("    • data_processing.yaml")
    print()
    print("Prerequisites:")
    print("  - Azure OpenAI endpoint and API key configured in environment")
    print("  - Workflow YAML files in examples/workflows/ directory")
    print("  - Agents registered that match workflow task definitions")
    print()


async def main():
    """Main function to run all workflow examples."""
    print_usage_help()
    
    # Run all examples
    examples = [
        ("Load Workflow Example", load_workflow_example),
        ("Register Workflow Example", register_workflow_example),
        ("Workflow Execution Demo", workflow_execution_demo),
        ("Workflow Monitoring Example", workflow_monitoring_example),
    ]
    
    for name, example_func in examples:
        print(f"\n🚀 Running {name}...")
        print("=" * 60)
        await example_func()
        print("=" * 60)
    
    print("\n✅ All workflow examples completed!")
    print("\n📚 Next steps:")
    print("  • Review the workflow YAML files in examples/workflows/")
    print("  • Create your own workflow definitions")
    print("  • Register agents that implement the workflow tasks")
    print("  • Execute workflows with: workflow_engine.execute_workflow()")


if __name__ == "__main__":
    asyncio.run(main())

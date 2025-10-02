"""Test variable substitution in workflows"""
import asyncio
import sys
import platform
from pathlib import Path

# Fix for Windows event loop
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from magentic_foundation import create_app

async def test_variables():
    load_dotenv()
    
    print("Testing Variable Substitution...")
    print("=" * 80)
    
    app = create_app()
    await app.initialize()
    
    # Register workflow
    workflow_path = Path(__file__).parent / "workflows" / "test_variables.yaml"
    await app.workflow_engine.register_workflow(str(workflow_path))
    
    # Execute with test input
    test_input = "Hello World from Variable Substitution Test"
    print(f"\nInput: {test_input}")
    print()
    
    execution_id = await app.workflow_engine.execute_workflow(
        workflow_name="test_variables_workflow",
        variables={"test_input": test_input}
    )
    
    # Wait for completion
    while True:
        status = await app.workflow_engine.get_execution_status(execution_id)
        if status and status.get("status", "").lower() in ["success", "failed", "workflowstatus.success"]:
            break
        await asyncio.sleep(1)
    
    # Get result
    execution = await app.workflow_engine.get_execution(execution_id)
    if execution:
        print("Result:")
        print("=" * 80)
        print(execution.variables.get("test_output", "NO OUTPUT"))
        print()
        
        if test_input in str(execution.variables.get("test_output", "")):
            print("✅ Variable substitution WORKING!")
        else:
            print("❌ Variable substitution FAILED!")
            print(f"Expected to find: '{test_input}'")
            print(f"In output: {execution.variables.get('test_output', 'NONE')}")
    
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(test_variables())

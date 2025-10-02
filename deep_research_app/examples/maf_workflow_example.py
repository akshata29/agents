"""
Example: Using MAF Workflows for Research

This example demonstrates how to use the new MAF workflow execution mode
for deep research tasks. It shows the three different execution modes and
when to use each one.
"""

import asyncio
import httpx
import json
from datetime import datetime


async def execute_maf_workflow_research():
    """
    Execute research using MAF graph-based workflow.
    
    Best for:
    - Visual workflow design needs
    - Type-safe message passing
    - Fan-out/fan-in patterns
    - Workflow visualization requirements
    """
    print("\n" + "="*60)
    print("MAF WORKFLOW EXECUTION (Graph-based)")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # Start research with MAF workflow mode
        print("\n1. Starting MAF workflow research...")
        response = await client.post(
            "http://localhost:8000/api/research/start",
            json={
                "topic": "quantum computing applications in drug discovery",
                "execution_mode": "maf-workflow",  # <-- MAF workflow mode
                "max_sources": 5
            },
            timeout=300.0
        )
        
        result = response.json()
        execution_id = result["execution_id"]
        
        print(f"   Execution ID: {execution_id}")
        print(f"   Status: {result['status']}")
        print(f"   Pattern: {result['orchestration_pattern']}")
        
        # Poll status
        print("\n2. Monitoring workflow progress...")
        
        completed = False
        while not completed:
            await asyncio.sleep(5)
            
            status_response = await client.get(
                f"http://localhost:8000/api/research/status/{execution_id}"
            )
            
            status = status_response.json()
            
            print(f"\n   Status: {status['status']}")
            print(f"   Progress: {status.get('progress', 0):.0f}%")
            
            if status.get('current_task'):
                print(f"   Current: {status['current_task']}")
            
            if status.get('completed_tasks'):
                print(f"   Completed: {len(status['completed_tasks'])} tasks")
            
            if status['status'] in ['success', 'completed', 'failed']:
                completed = True
        
        # Display results
        print("\n3. Results:")
        
        if status['status'] in ['success', 'completed']:
            result_data = status.get('result', {})
            
            print("\n   Executive Summary:")
            print("   " + "-"*56)
            summary = result_data.get('executive_summary', 'N/A')
            for line in summary.split('\n')[:5]:  # First 5 lines
                print(f"   {line}")
            print("   ...")
            
            print(f"\n   Workflow Events: {len(result_data.get('events', []))}")
            print(f"   Quality Score: {result_data.get('metadata', {}).get('quality_score', 'N/A')}")
            
            # Show event timeline
            events = result_data.get('events', [])
            if events:
                print("\n   Event Timeline:")
                for event in events[-5:]:  # Last 5 events
                    print(f"     - {event.get('type')}: {event.get('executor_id', 'system')}")
        else:
            print(f"\n   Error: {status.get('error', 'Unknown error')}")
        
        print("\n" + "="*60)


async def execute_yaml_workflow_research():
    """
    Execute research using declarative YAML workflow.
    
    Best for:
    - Simple, declarative workflows
    - Easy modification without code changes
    - Configuration-driven execution
    """
    print("\n" + "="*60)
    print("YAML WORKFLOW EXECUTION (Declarative)")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        print("\n1. Starting YAML workflow research...")
        response = await client.post(
            "http://localhost:8000/api/research/start",
            json={
                "topic": "quantum computing applications in drug discovery",
                "execution_mode": "workflow",  # <-- YAML workflow mode (default)
                "max_sources": 5,
                "depth": "comprehensive"
            },
            timeout=300.0
        )
        
        result = response.json()
        print(f"   Execution ID: {result['execution_id']}")
        print(f"   Pattern: {result['orchestration_pattern']}")
        print(f"   Mode: Declarative YAML-based")


async def execute_code_based_research():
    """
    Execute research using programmatic code-based approach.
    
    Best for:
    - Complex logic requiring programmatic control
    - Dynamic decision-making
    - Custom orchestration patterns
    """
    print("\n" + "="*60)
    print("CODE-BASED EXECUTION (Programmatic)")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        print("\n1. Starting code-based research...")
        response = await client.post(
            "http://localhost:8000/api/research/start",
            json={
                "topic": "quantum computing applications in drug discovery",
                "execution_mode": "code",  # <-- Code-based mode
                "max_sources": 5
            },
            timeout=300.0
        )
        
        result = response.json()
        print(f"   Execution ID: {result['execution_id']}")
        print(f"   Pattern: {result['orchestration_pattern']}")
        print(f"   Mode: Programmatic with Framework Patterns")


async def compare_execution_modes():
    """Compare all three execution modes side by side."""
    print("\n" + "="*60)
    print("EXECUTION MODE COMPARISON")
    print("="*60)
    
    comparison = {
        "YAML Workflow": {
            "execution_mode": "workflow",
            "description": "Declarative YAML-based",
            "best_for": [
                "Simple workflows",
                "Easy modification",
                "Configuration-driven"
            ],
            "pattern": "Task-based with dependencies",
            "complexity": "Low",
            "flexibility": "Medium"
        },
        "Code-Based": {
            "execution_mode": "code",
            "description": "Programmatic patterns",
            "best_for": [
                "Complex logic",
                "Dynamic decisions",
                "Custom orchestration"
            ],
            "pattern": "Sequential + Concurrent patterns",
            "complexity": "Medium",
            "flexibility": "High"
        },
        "MAF Workflow": {
            "execution_mode": "maf-workflow",
            "description": "Graph-based with executors",
            "best_for": [
                "Visual design",
                "Type-safe messages",
                "Fan-out/fan-in patterns"
            ],
            "pattern": "Graph with nodes and edges",
            "complexity": "High",
            "flexibility": "High"
        }
    }
    
    print("\n")
    for mode_name, details in comparison.items():
        print(f"{mode_name}:")
        print(f"  Mode: {details['execution_mode']}")
        print(f"  Description: {details['description']}")
        print(f"  Pattern: {details['pattern']}")
        print(f"  Complexity: {details['complexity']}")
        print(f"  Flexibility: {details['flexibility']}")
        print(f"  Best for:")
        for item in details['best_for']:
            print(f"    - {item}")
        print()


async def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("MAF WORKFLOWS EXAMPLE - Deep Research App")
    print("="*60)
    print("\nThis example demonstrates three execution modes:")
    print("1. YAML Workflow (declarative)")
    print("2. Code-Based (programmatic)")
    print("3. MAF Workflow (graph-based) ← NEW!")
    print("\nMake sure the backend is running: python -m deep_research_app.backend.app.main")
    
    # Show comparison first
    await compare_execution_modes()
    
    # Wait for user
    input("\nPress Enter to execute MAF workflow example (or Ctrl+C to exit)...")
    
    # Execute MAF workflow
    try:
        await execute_maf_workflow_research()
    except httpx.ConnectError:
        print("\n❌ ERROR: Could not connect to backend.")
        print("   Please start the backend first:")
        print("   python -m deep_research_app.backend.app.main")
        return
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

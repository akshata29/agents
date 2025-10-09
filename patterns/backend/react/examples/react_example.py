"""
Deep Research Pattern - Standalone Demo

This script demonstrates the Deep Research pattern with various modes.
Run directly: python examples/deep_research_example.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from patterns.backend.react.react import (
    run_deep_research_orchestration,
    run_baseline_research,
    run_research_with_reviewer,
    run_research_with_analyst
)


async def demo_baseline():
    """Demo: Basic research workflow."""
    print("\n" + "=" * 80)
    print("DEMO 1: BASELINE DEEP RESEARCH")
    print("=" * 80)
    
    task = (
        "Analyze the current state of Large Language Models in enterprise software development, "
        "including adoption rates, productivity impacts, and security considerations."
    )
    
    results = await run_baseline_research(task)
    
    print("\n" + "=" * 80)
    print(f"✓ Baseline research completed with {len(results)} agent outputs")
    print("=" * 80)
    
    return results


async def demo_with_reviewer():
    """Demo: Research with quality review loop."""
    print("\n" + "=" * 80)
    print("DEMO 2: RESEARCH WITH REVIEWER LOOP")
    print("=" * 80)
    
    task = (
        "Evaluate the feasibility and benefits of adopting microservices architecture "
        "for a legacy monolithic e-commerce platform."
    )
    
    results = await run_research_with_reviewer(task)
    
    print("\n" + "=" * 80)
    print(f"✓ Research with review completed with {len(results)} agent outputs")
    print("=" * 80)
    
    return results


async def demo_with_analyst():
    """Demo: Research with code interpreter analysis."""
    print("\n" + "=" * 80)
    print("DEMO 3: RESEARCH WITH CODE INTERPRETER ANALYSIS")
    print("=" * 80)
    
    task = (
        "Research cloud computing market trends and provider comparison "
        "for enterprise AI/ML workloads."
    )
    
    # Note: Requires user_role=analyst or admin
    os.environ["USER_ROLE"] = "analyst"
    
    results = await run_research_with_analyst(task)
    
    print("\n" + "=" * 80)
    print(f"✓ Research with analysis completed with {len(results)} agent outputs")
    print("=" * 80)
    
    return results


async def demo_full_mode():
    """Demo: Full-featured research with all options."""
    print("\n" + "=" * 80)
    print("DEMO 4: FULL-FEATURED DEEP RESEARCH")
    print("=" * 80)
    
    task = (
        "Comprehensive analysis of AI safety and alignment research: "
        "current approaches, challenges, and future directions."
    )
    
    # Note: Requires admin role for full features
    os.environ["USER_ROLE"] = "admin"
    
    results = await run_deep_research_orchestration(
        task=task,
        mode="full"
    )
    
    print("\n" + "=" * 80)
    print(f"✓ Full research completed with {len(results)} agent outputs")
    print("=" * 80)
    
    return results


async def demo_custom_mode():
    """Demo: Custom research with specific configuration."""
    print("\n" + "=" * 80)
    print("DEMO 5: CUSTOM CONFIGURATION")
    print("=" * 80)
    
    task = (
        "Research best practices for implementing CI/CD pipelines "
        "in cloud-native applications."
    )
    
    results = await run_deep_research_orchestration(
        task=task,
        mode="reviewer",  # Use reviewer mode
        user_role="doc-reader"  # Access to MCP but not code interpreter
    )
    
    print("\n" + "=" * 80)
    print(f"✓ Custom research completed with {len(results)} agent outputs")
    print("=" * 80)
    
    return results


async def interactive_demo():
    """Interactive demo - let user choose mode."""
    print("\n" + "=" * 80)
    print("DEEP RESEARCH PATTERN - INTERACTIVE DEMO")
    print("=" * 80)
    print("\nAvailable Modes:")
    print("1. Baseline - Standard research workflow")
    print("2. Reviewer - With quality review loop")
    print("3. Analyst - With code interpreter analysis")
    print("4. Full - All features enabled")
    print("5. Custom - Specify your own configuration")
    print("0. Exit")
    
    try:
        choice = input("\nSelect mode (0-5): ").strip()
        
        if choice == "0":
            print("Exiting...")
            return
        
        task = input("\nEnter research objective (or press Enter for demo task): ").strip()
        
        if choice == "1":
            results = await run_baseline_research(task or None)
        elif choice == "2":
            results = await run_research_with_reviewer(task or None)
        elif choice == "3":
            os.environ["USER_ROLE"] = "analyst"
            results = await run_research_with_analyst(task or None)
        elif choice == "4":
            os.environ["USER_ROLE"] = "admin"
            results = await run_deep_research_orchestration(task=task or None, mode="full")
        elif choice == "5":
            mode = input("Mode (baseline/reviewer/analyst/full): ").strip() or "baseline"
            role = input("User role (viewer/doc-reader/analyst/admin): ").strip() or "viewer"
            results = await run_deep_research_orchestration(
                task=task or None,
                mode=mode,
                user_role=role
            )
        else:
            print("Invalid choice!")
            return
        
        print("\n" + "=" * 80)
        print("RESEARCH RESULTS SUMMARY")
        print("=" * 80)
        for i, output in enumerate(results, 1):
            print(f"\n{i}. {output['agent']} ({output['timestamp']})")
            print(f"   Input: {output['input'][:80]}...")
            print(f"   Output: {len(output['output'])} characters")
        
        print("\n" + "=" * 80)
        print(f"✓ Research completed with {len(results)} agent outputs")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main entry point."""
    # Check for required environment variables
    if not os.getenv("AZURE_AI_PROJECT_ENDPOINT"):
        print("ERROR: AZURE_AI_PROJECT_ENDPOINT not configured!")
        print("Please set up your .env file with required configuration.")
        print("\nRequired:")
        print("  AZURE_AI_PROJECT_ENDPOINT=https://<foundry>.services.ai.azure.com/api/projects/<project>")
        print("  AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini")
        return
    
    # Check if running in interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await interactive_demo()
    else:
        # Run automated demos
        print("\n" + "=" * 80)
        print("DEEP RESEARCH PATTERN - AUTOMATED DEMOS")
        print("=" * 80)
        print("\nRunning multiple demos to showcase different modes...")
        print("(Use --interactive flag for interactive mode)")
        
        try:
            # Demo 1: Baseline
            await demo_baseline()
            
            # Uncomment to run additional demos:
            # await demo_with_reviewer()
            # await demo_with_analyst()
            # await demo_full_mode()
            # await demo_custom_mode()
            
            print("\n" + "=" * 80)
            print("ALL DEMOS COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            
        except KeyboardInterrupt:
            print("\n\nDemos interrupted by user. Exiting...")
        except Exception as e:
            print(f"\n\nError during demo: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

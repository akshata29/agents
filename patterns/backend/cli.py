"""
Command-Line Interface for Microsoft Agent Framework Orchestration Patterns

This CLI provides easy access to all orchestration patterns with custom task support.
"""

import argparse
import asyncio
import sys
from typing import Optional

from sequential.sequential import run_sequential_orchestration
from concurrent.concurrent import run_concurrent_orchestration  
from group_chat.group_chat import run_group_chat_orchestration
from handoff.handoff import run_handoff_orchestration
from magentic.magentic import run_magentic_orchestration


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Microsoft Agent Framework - Multi-Agent Orchestration Patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cli --pattern sequential
  python -m cli --pattern concurrent --task "Analyze market trends"
  python -m cli --list
  python -m cli --all
        """
    )
    
    parser.add_argument(
        "--pattern", "-p",
        choices=["sequential", "concurrent", "group_chat", "handoff", "magentic"],
        help="Orchestration pattern to execute"
    )
    
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="Custom task/request to process (uses default if not specified)"
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available orchestration patterns"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all orchestration patterns sequentially"
    )
    
    return parser


def list_patterns():
    """List all available orchestration patterns."""
    patterns = [
        ("sequential", "Sequential Orchestration", "Planner → Researcher → Writer → Reviewer"),
        ("concurrent", "Concurrent Orchestration", "Summarizer ⟺ ProsCons ⟺ RiskAssessor"),
        ("group_chat", "Group Chat Orchestration", "Writer ⟷ Reviewer ⟷ Moderator"),
        ("handoff", "Handoff Orchestration", "Router → Specialist Agents"),
        ("magentic", "Magentic Orchestration", "Plan-driven collaboration with tools")
    ]
    
    print("🎯 Available Microsoft Agent Framework Orchestration Patterns:\n")
    
    for pattern_id, name, description in patterns:
        print(f"  {pattern_id:12} : {name}")
        print(f"                 {description}")
        print()
    
    print("💡 Usage:")
    print("  python -m agent_framework_patterns.cli --pattern <pattern_name>")
    print("  python -m agent_framework_patterns.cli --pattern <pattern_name> --task 'Your custom task'")


async def run_pattern(pattern_name: str, task: Optional[str] = None):
    """Run a specific orchestration pattern."""
    
    pattern_functions = {
        "sequential": run_sequential_orchestration,
        "concurrent": run_concurrent_orchestration,
        "group_chat": run_group_chat_orchestration,
        "handoff": run_handoff_orchestration,
        "magentic": run_magentic_orchestration,
    }
    
    if pattern_name not in pattern_functions:
        print(f"❌ Unknown pattern: {pattern_name}")
        return False
    
    try:
        pattern_function = pattern_functions[pattern_name]
        
        print(f"🚀 Executing {pattern_name} orchestration pattern...")
        if task:
            print(f"📋 Custom task: {task}")
        else:
            print("📋 Using default task for demonstration")
        print()
        
        # Execute the pattern
        if task:
            await pattern_function(task)
        else:
            await pattern_function()
        
        return True
        
    except Exception as e:
        print(f"❌ Error executing {pattern_name} pattern: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_patterns(task: Optional[str] = None):
    """Run all orchestration patterns."""
    patterns = ["sequential", "concurrent", "group_chat", "handoff", "magentic"]
    
    print("🎯 Running all Microsoft Agent Framework orchestration patterns...\n")
    
    results = {}
    
    for i, pattern in enumerate(patterns, 1):
        print(f"\n{'='*60}")
        print(f"PATTERN {i}/{len(patterns)}: {pattern.upper()}")
        print("="*60)
        
        success = await run_pattern(pattern, task)
        results[pattern] = success
        
        if i < len(patterns):
            print(f"\n⏸️  Waiting 3 seconds before next pattern...")
            await asyncio.sleep(3)
    
    # Print summary
    print(f"\n{'='*60}")
    print("ALL PATTERNS EXECUTION SUMMARY")
    print("="*60)
    
    for pattern, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{pattern.capitalize():15}: {status}")
    
    successful = sum(results.values())
    total = len(results)
    print(f"\nOverall: {successful}/{total} patterns successful ({successful/total*100:.1f}%)")


async def main():
    """Main CLI function."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle list command
    if args.list:
        list_patterns()
        return
    
    # Handle run all patterns
    if args.all:
        await run_all_patterns(args.task)
        return
    
    # Handle specific pattern
    if args.pattern:
        success = await run_pattern(args.pattern, args.task)
        sys.exit(0 if success else 1)
    
    # No command specified, show help
    parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
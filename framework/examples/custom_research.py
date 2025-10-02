"""
Custom Research Topic Runner
Run AI-powered deep research on any topic
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from examples.deep_research_enhanced import execute_enhanced_research
from magentic_foundation.core.app import MagenticApp


async def research_topic(topic: str, depth: str = "comprehensive"):
    """Run deep research on a custom topic."""
    
    load_dotenv()
    
    print("=" * 80)
    print("CUSTOM AI-POWERED DEEP RESEARCH")
    print("=" * 80)
    print()
    
    # Initialize framework
    print("[Initializing Magentic Foundation Framework...]")
    app = MagenticApp()
    await app.initialize()
    print("[OK] Framework initialized")
    print()
    
    # Execute research
    results = await execute_enhanced_research(
        app=app,
        topic=topic,
        depth=depth,
        max_sources=10
    )
    
    if results:
        print("\n" + "=" * 80)
        print("[SUCCESS] Research completed!")
        print("=" * 80)
    
    return results


def main():
    """Main CLI entry point."""
    
    if len(sys.argv) < 2:
        print("Usage: python custom_research.py \"Your research topic here\" [depth]")
        print()
        print("Examples:")
        print('  python custom_research.py "Impact of AI on healthcare"')
        print('  python custom_research.py "Renewable energy trends 2025" quick')
        print()
        print("Depth options: quick, standard, comprehensive (default), exhaustive")
        sys.exit(1)
    
    topic = sys.argv[1]
    depth = sys.argv[2] if len(sys.argv) > 2 else "comprehensive"
    
    asyncio.run(research_topic(topic, depth))


if __name__ == "__main__":
    main()

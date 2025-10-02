"""
Quick test of Deep Research workflow with a predefined topic.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Now we can import deep_research_cli module
sys.path.insert(0, str(Path(__file__).parent))
import deep_research_cli

async def main():
    """Test deep research with a predefined topic."""
    
    # Test topic
    topic = "The future of quantum computing in cybersecurity"
    
    print(f"\n🧪 Testing Deep Research with topic:")
    print(f"   '{topic}'\n")
    
    # Execute research
    results = await deep_research_cli.execute_deep_research(
        topic=topic,
        depth="comprehensive",
        max_sources=10,
        include_citations=True
    )
    
    if results:
        print("\n✅ Research completed successfully!")
        print(f"\n📊 Results keys: {list(results.keys())}")
    else:
        print("\n⚠️  Research completed with no results")

if __name__ == "__main__":
    asyncio.run(main())

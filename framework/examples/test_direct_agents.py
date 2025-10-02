"""
Quick test of AI agents with explicit topic (no workflow)
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from openai import AzureOpenAI
from tavily import TavilyClient

# Load env
load_dotenv()

async def test_direct_agents():
    """Test agents directly without workflow to verify they work."""
    
    print("=" * 80)
    print("DIRECT AGENT TEST")
    print("=" * 80)
    print()
    
    # Initialize clients
    azure_client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_VERSION", "2024-10-21")
    )
    
    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    # Test 1: Research Planner
    print("[TEST 1: Research Planner]")
    print("-" * 80)
    
    topic = "The impact of quantum computing on modern cryptography"
    
    response = azure_client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "chat4o"),
        messages=[
            {"role": "system", "content": "You are an expert research planner. Create a detailed research plan."},
            {"role": "user", "content": f"Create a comprehensive research plan for: {topic}"}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    plan = response.choices[0].message.content
    print(plan)
    print()
    
    # Test 2: Web Research with Tavily
    print("[TEST 2: Web Research with Tavily]")
    print("-" * 80)
    
    search_results = tavily_client.search(
        query="quantum computing cryptography 2024 2025",
        search_depth="advanced",
        max_results=3,
        include_answer=True
    )
    
    print(f"Tavily Answer: {search_results.get('answer', 'N/A')}")
    print()
    print("Top Sources:")
    for i, result in enumerate(search_results.get('results', [])[:3], 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   {result['content'][:200]}...")
    print()
    
    # Test 3: Synthesize with AI
    print("[TEST 3: AI Synthesis]")
    print("-" * 80)
    
    sources_text = "\n\n".join([
        f"Source: {r['title']}\n{r['content'][:500]}"
        for r in search_results.get('results', [])[:3]
    ])
    
    synthesis_prompt = f"""Based on these research sources about {topic}, provide a comprehensive summary:

{sources_text}

Provide a well-structured summary highlighting key findings and implications."""
    
    response = azure_client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "chat4o"),
        messages=[
            {"role": "system", "content": "You are an expert research analyst who synthesizes information."},
            {"role": "user", "content": synthesis_prompt}
        ],
        temperature=0.7,
        max_tokens=1500
    )
    
    synthesis = response.choices[0].message.content
    print(synthesis)
    print()
    
    print("=" * 80)
    print("[SUCCESS] All agents are working with real AI and web search!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_direct_agents())

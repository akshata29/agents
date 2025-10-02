"""
Test Enhanced Deep Research with Real AI
"""
import asyncio

if __name__ == "__main__":
    print("=" * 80)
    print("TESTING ENHANCED DEEP RESEARCH WITH REAL AI")
    print("=" * 80)
    print()
    print("This will perform actual web research using:")
    print("  * Tavily Search API for web research")
    print("  * Azure OpenAI for AI synthesis and analysis")
    print()
    print("Expected duration: 2-3 minutes for comprehensive research")
    print()
    
    # Import and run
    from deep_research_enhanced import main
    asyncio.run(main())

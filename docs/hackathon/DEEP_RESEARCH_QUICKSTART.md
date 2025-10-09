# Deep Research Quick Start Guide
## Get Running in 15 Minutes

> **Goal**: Get a working Deep Research application running quickly so you can start customizing it for your hackathon project.

---

## 🚀 Quick Setup Steps

### Step 1: Clone Template (2 mins)

```bash
# Create your project folder
mkdir my-deep-research
cd my-deep-research

# Create folder structure
mkdir -p backend/agents
mkdir -p backend/workflows
```

### Step 2: Install Dependencies (3 mins)

Create `requirements.txt`:

```txt
agent-framework>=0.1.0
azure-identity>=1.15.0
openai>=1.12.0
tavily-python>=0.3.0
fastapi>=0.109.0
uvicorn>=0.27.0
python-dotenv>=1.0.0
pydantic>=2.6.0
```

Install:

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment (3 mins)

Create `.env` file:

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://YOUR-ENDPOINT.openai.azure.com/
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21

# Tavily Search
TAVILY_API_KEY=your-tavily-key-here
```

**Get API Keys**:
- Azure OpenAI: [Azure Portal](https://portal.azure.com)
- Tavily: [Tavily Dashboard](https://app.tavily.com) (Free tier available)

### Step 4: Create Simple Agent (5 mins)

Create `backend/simple_research.py`:

```python
"""Simplest possible deep research implementation."""

import os
import asyncio
from dotenv import load_dotenv
from agent_framework import SequentialBuilder
from agent_framework.azure import AzureOpenAIChatClient
from tavily import TavilyClient

# Load environment
load_dotenv()

async def quick_research(objective: str) -> str:
    """Simplest research workflow."""
    
    # Setup Azure OpenAI
    chat_client = AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    )
    
    # Setup Tavily
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    # Create agents
    planner = chat_client.create_agent(
        name="Planner",
        instructions="Break down the research objective into 3 key questions to investigate."
    )
    
    researcher = chat_client.create_agent(
        name="Researcher",
        instructions="You are a thorough researcher. Analyze the questions and provide detailed findings."
    )
    
    writer = chat_client.create_agent(
        name="Writer",
        instructions="Synthesize the research into a clear, comprehensive report."
    )
    
    # Build sequential workflow
    workflow = SequentialBuilder().participants([
        planner,
        researcher,
        writer
    ]).build()
    
    # Execute
    print(f"🔍 Researching: {objective}\n")
    
    result_messages = []
    async for event in workflow.run_stream(objective):
        if hasattr(event, 'data'):
            result_messages = event.data
    
    # Get final report
    if result_messages:
        final_message = result_messages[-1]
        return final_message.text
    
    return "Research failed"

# Test it
if __name__ == "__main__":
    research_topic = "What are the latest developments in quantum computing?"
    result = asyncio.run(quick_research(research_topic))
    print("\n" + "="*80)
    print("RESEARCH REPORT")
    print("="*80)
    print(result)
```

### Step 5: Run It! (2 mins)

```bash
python backend/simple_research.py
```

You should see:
```
🔍 Researching: What are the latest developments in quantum computing?

================================================================================
RESEARCH REPORT
================================================================================
[Your AI-generated research report will appear here]
```

---

## 🎯 What Just Happened?

You just created a **3-agent sequential research workflow**:

```
User Objective → Planner → Researcher → Writer → Final Report
```

**Key Components**:
1. **AzureOpenAIChatClient** - Connects to Azure OpenAI
2. **Sequential Pattern** - Runs agents in order
3. **Agent Instructions** - Tells each agent what to do

---

## 🔧 Next: Add Web Search

### Enhanced Version with Tavily

Update `backend/simple_research.py`:

```python
"""Enhanced research with web search."""

import os
import asyncio
from dotenv import load_dotenv
from agent_framework import SequentialBuilder
from agent_framework.azure import AzureOpenAIChatClient
from tavily import TavilyClient
from openai import AzureOpenAI

load_dotenv()

async def research_with_web_search(objective: str) -> str:
    """Research workflow with actual web search."""
    
    # Setup clients
    chat_client = AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    )
    
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    azure_client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    )
    
    print(f"🔍 Researching: {objective}\n")
    
    # Step 1: Plan
    print("📋 Planning research...")
    planner = chat_client.create_agent(
        name="Planner",
        instructions="Break the objective into 2-3 specific search queries. Output just the queries, one per line."
    )
    
    plan_response = await planner.run(objective)
    queries = plan_response.messages[-1].text.strip().split('\n')
    queries = [q.strip('- ').strip() for q in queries if q.strip()]
    
    print(f"✓ Generated {len(queries)} search queries\n")
    
    # Step 2: Search
    print("🌐 Searching the web...")
    all_findings = []
    
    for i, query in enumerate(queries[:3], 1):  # Limit to 3 queries
        print(f"  [{i}] {query}")
        
        # Perform search
        search_results = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=3
        )
        
        # Synthesize results
        sources = "\n".join([
            f"- {r['title']}: {r['content'][:200]}..."
            for r in search_results.get('results', [])
        ])
        
        synthesis_prompt = f"""Query: {query}

Sources:
{sources}

Provide a concise summary of the key findings."""

        response = azure_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
            messages=[
                {"role": "system", "content": "You are a research analyst."},
                {"role": "user", "content": synthesis_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        finding = response.choices[0].message.content
        all_findings.append(f"**Finding {i}: {query}**\n{finding}")
    
    print(f"✓ Completed {len(all_findings)} searches\n")
    
    # Step 3: Write Report
    print("✍️  Writing report...")
    
    combined_findings = "\n\n".join(all_findings)
    
    writer = chat_client.create_agent(
        name="Writer",
        instructions="Create a comprehensive research report with: 1) Executive Summary, 2) Key Findings, 3) Conclusion"
    )
    
    report_response = await writer.run(
        f"Research Objective: {objective}\n\nFindings:\n{combined_findings}\n\nCreate a detailed report."
    )
    
    report = report_response.messages[-1].text
    
    print("✓ Report complete!\n")
    
    return report

# Test
if __name__ == "__main__":
    topic = "What are the latest developments in quantum computing?"
    result = asyncio.run(research_with_web_search(topic))
    
    print("="*80)
    print("RESEARCH REPORT")
    print("="*80)
    print(result)
```

Run it:
```bash
python backend/simple_research.py
```

---

## 🎨 Customize for Your Use Case

### Example 1: Market Research

```python
objective = "Analyze the competitive landscape for AI-powered customer service tools"

planner_instructions = """
Break down market research into:
1. Key competitors and their offerings
2. Market size and growth trends
3. Customer pain points and needs
Output 3 specific search queries.
"""
```

### Example 2: Technical Research

```python
objective = "What are best practices for implementing RAG in production?"

planner_instructions = """
Create search queries covering:
1. Architecture patterns and design
2. Common challenges and solutions
3. Performance optimization techniques
Output 3 specific search queries.
"""
```

### Example 3: Academic Research

```python
objective = "Recent advances in protein folding prediction using AI"

planner_instructions = """
Focus on:
1. Latest models and approaches (AlphaFold, etc.)
2. Key research papers and findings
3. Real-world applications and impact
Output 3 academic-focused search queries.
"""
```

---

## 🔄 Add Concurrent Search

Speed up searches by running them in parallel:

```python
import asyncio

# Replace sequential search loop with concurrent execution
search_tasks = [
    search_and_synthesize(query, tavily, azure_client)
    for query in queries[:3]
]

all_findings = await asyncio.gather(*search_tasks)

async def search_and_synthesize(query, tavily, azure_client):
    """Search and synthesize one query."""
    search_results = tavily.search(query=query, max_results=3)
    # ... synthesis logic ...
    return finding
```

**Result**: 3x faster research! 🚀

---

## 📊 Monitor Your Usage

### Track Costs

```python
import time

start_time = time.time()
tokens_used = 0

# ... run research ...

duration = time.time() - start_time

print(f"\n📊 Metrics:")
print(f"  Duration: {duration:.1f}s")
print(f"  Searches: {len(queries)}")
print(f"  Estimated cost: ${estimated_cost:.2f}")
```

### Add Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Starting research: {objective}")
logger.info(f"Generated {len(queries)} queries")
logger.info(f"Research complete in {duration:.1f}s")
```

---

## 🐛 Common Issues & Solutions

### Issue 1: API Key Errors

```
Error: Missing required environment variables
```

**Solution**:
- Check `.env` file exists
- Verify all keys are filled in
- Make sure no extra spaces around `=`

### Issue 2: Import Errors

```
ModuleNotFoundError: No module named 'agent_framework'
```

**Solution**:
```bash
pip install agent-framework
# OR
pip install -r requirements.txt
```

### Issue 3: Tavily Rate Limits

```
TavilyError: Rate limit exceeded
```

**Solution**:
- Use free tier: 1000 requests/month
- Add delays between searches:
  ```python
  await asyncio.sleep(1)  # 1 second delay
  ```

### Issue 4: Timeout Errors

```
TimeoutError: Search took too long
```

**Solution**:
```python
# Add timeout to search
search_results = tavily.search(query, timeout=30)
```

---

## ✅ Validation Checklist

Before moving to advanced features:

- [ ] Basic workflow runs successfully
- [ ] Web search returns relevant results
- [ ] Report is well-formatted and comprehensive
- [ ] Environment variables are secure (not in code)
- [ ] Error handling works (try invalid API key)
- [ ] Logging provides useful information

---

## 🚀 You're Ready!

You now have a working Deep Research application. Next steps:

1. **Customize** - Modify agent instructions for your domain
2. **Enhance** - Add concurrent search, better synthesis
3. **Scale** - Add API server, database, frontend
4. **Deploy** - Run on Azure, add monitoring

**Continue to**: [Full Implementation Guide](./DEEP_RESEARCH_GUIDE.md)

---

## 💡 Pro Tips

1. **Start Small**: Test with 1-2 search queries first
2. **Use Good Prompts**: Specific agent instructions = better results
3. **Monitor Costs**: Track API usage to avoid surprises
4. **Cache Results**: Save search results to avoid re-searching
5. **Iterate**: First version doesn't need to be perfect

---

**Happy Researching! 🎯**

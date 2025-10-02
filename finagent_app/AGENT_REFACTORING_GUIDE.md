# Financial Agents - MAF Pattern Refactoring Guide

## Overview

This document explains how our financial research agents are refactored to properly leverage the **Microsoft Agent Framework (MAF)** and the **Magentic Foundation Framework** patterns.

## Architecture Alignment

### Before: Custom Implementation ❌
```python
# Old approach - custom execution logic
class FinancialOrchestrationService:
    async def execute_sequential(self, ticker, scope):
        # Custom sequential execution logic
        for agent_id in agent_sequence:
            agent = self.agents.get(agent_id)
            result = await agent.run(...)
        # Manual result aggregation
```

### After: Framework Patterns ✅
```python
# New approach - leverage framework patterns
from framework.patterns import SequentialPattern, ConcurrentPattern
from framework.core.registry import AgentRegistry

# Use built-in patterns
pattern = SequentialPattern(
    agents=["company", "sec", "earnings"],
    config={"preserve_context": True}
)
result = await orchestrator.execute(task, pattern=pattern)
```

## Agent Structure - MAF Compliant

### Required Components

All financial agents now inherit from `agent_framework.BaseAgent` and implement:

1. **`run()` method** - Execute agent task (synchronous)
2. **`run_stream()` method** - Execute with streaming (async generator)
3. **`process()` method** - Legacy compatibility for YAML workflows

### Example: CompanyAgent Structure

```python
from agent_framework import (
    BaseAgent, ChatMessage, Role, TextContent,
    AgentRunResponse, AgentRunResponseUpdate, AgentThread
)

class CompanyAgent(BaseAgent):
    """MAF-compliant financial research agent."""
    
    def __init__(self, name, description, azure_client, model, fmp_api_key):
        # Initialize MAF BaseAgent
        super().__init__(name=name, description=description)
        
        # Store custom attributes
        self.azure_client = azure_client
        self.model = model
        self.fmp_utils = FMPUtils(fmp_api_key)
        self.yf_utils = YFUtils()
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute agent task - MAF required method."""
        
        # 1. Normalize messages
        normalized_messages = self._normalize_messages(messages)
        
        # 2. Extract task and context
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        context = kwargs.get("context", {})
        ticker = context.get("ticker", kwargs.get("ticker"))
        
        # 3. Fetch REAL data from providers
        market_data = await self._fetch_market_data(ticker, context)
        
        # 4. Build prompt with real data
        prompt = self._build_analysis_prompt_with_data(task, ticker, market_data, context)
        
        # 5. Execute LLM
        response = await self._execute_llm(prompt)
        
        # 6. Return MAF response
        return AgentRunResponse(messages=[
            ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text=response)]
            )
        ])
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Streaming execution - MAF required method."""
        response = await self.run(messages, thread=thread, **kwargs)
        for message in response.messages:
            for content in message.contents:
                if isinstance(content, TextContent):
                    yield AgentRunResponseUpdate(
                        contents=[content],
                        role=Role.ASSISTANT
                    )
    
    async def process(self, task: str, context: Dict[str, Any] = None) -> str:
        """Legacy method for YAML workflow compatibility."""
        context = context or {}
        response = await self.run(messages=task, thread=None, context=context)
        return response.messages[-1].text if response.messages else ""
```

## Orchestration Patterns

### 1. Sequential Pattern

**Use Case**: Linear agent execution with context building

```python
from framework.patterns import SequentialPattern

pattern = SequentialPattern(
    agents=["company", "sec", "earnings", "fundamentals", "technicals"],
    name="comprehensive_research",
    config={
        "preserve_context": True,      # Pass context between agents
        "fail_fast": False,             # Continue on agent errors
        "context_window_limit": 32000   # Token limit
    }
)

result = await orchestrator.execute(
    task=f"Analyze {ticker} for investment research",
    pattern=pattern
)
```

**How it works:**
- Each agent receives previous agents' outputs
- Context accumulates (research_plan → findings → analysis)
- Perfect for building comprehensive reports

### 2. Concurrent Pattern

**Use Case**: Parallel execution with result aggregation

```python
from framework.patterns import ConcurrentPattern

pattern = ConcurrentPattern(
    agents=["fundamentals", "technicals", "sec"],
    name="parallel_analysis",
    config={
        "aggregation_strategy": "merge",  # How to combine results
        "max_concurrent": 3,              # Max parallel executions
        "timeout_per_agent": 120          # Timeout in seconds
    }
)

result = await orchestrator.execute(
    task=f"Analyze {ticker} from multiple perspectives",
    pattern=pattern
)
```

**How it works:**
- All agents execute simultaneously
- Results aggregated when all complete
- Perfect for independent analyses (fundamentals + technicals + SEC)

### 3. Handoff Pattern

**Use Case**: Dynamic agent delegation based on expertise

```python
from framework.patterns import HandoffPattern

pattern = HandoffPattern(
    agents=["triage", "company", "fundamentals", "technicals", "sec"],
    initial_agent="triage",
    handoff_relationships={
        "triage": ["company", "fundamentals", "technicals", "sec"],
        "company": ["fundamentals", "technicals"],
        "fundamentals": ["technicals"],
        "technicals": [],
        "sec": []
    },
    config={
        "handoff_strategy": "explicit",     # Explicit vs. automatic
        "allow_return_handoffs": True,      # Can return to previous
        "max_handoffs": 10                  # Prevent infinite loops
    }
)

result = await orchestrator.execute(
    task=f"Research {ticker} - route to appropriate specialists",
    pattern=pattern
)
```

**How it works:**
- Triage agent routes to specialists
- Specialists can handoff to each other
- Perfect for adaptive workflows (user question → right expert)

### 4. Group Chat Pattern

**Use Case**: Multi-agent collaborative discussion

```python
from framework.patterns import GroupChatPattern

pattern = GroupChatPattern(
    agents=["company", "fundamentals", "technicals", "sec", "report"],
    name="investment_committee",
    config={
        "manager_type": "round_robin",   # or "llm_based"
        "max_iterations": 40,            # Conversation rounds
        "require_consensus": False       # All agents must agree
    }
)

result = await orchestrator.execute(
    task=f"Collaboratively analyze {ticker} for investment decision",
    pattern=pattern
)
```

**How it works:**
- All agents participate in discussion
- Manager coordinates turn-taking
- Perfect for collaborative analysis (investment committee simulation)

## Hybrid Workflows

Combine patterns for complex workflows:

```python
# Phase 1: Sequential planning
planning_pattern = SequentialPattern(
    agents=["company", "sec"],
    config={"preserve_context": True}
)
plan_result = await orchestrator.execute(task, pattern=planning_pattern)

# Phase 2: Concurrent deep research
research_pattern = ConcurrentPattern(
    agents=["earnings", "fundamentals", "technicals"],
    config={"aggregation_strategy": "merge"}
)
research_result = await orchestrator.execute(task, pattern=research_pattern)

# Phase 3: Sequential synthesis
synthesis_pattern = SequentialPattern(
    agents=["report"],
    config={"preserve_context": True}
)
final_result = await orchestrator.execute(task, pattern=synthesis_pattern)
```

## Data Provider Integration

All agents integrate **real data providers**:

### FMPUtils (Financial Modeling Prep API)
- Company profiles
- Financial metrics (5 years)
- Earnings call transcripts
- SEC filing metadata
- Analyst ratings and scores
- Company news

### YFUtils (Yahoo Finance)
- Real-time stock quotes
- Historical price data
- Analyst recommendations
- Technical analysis (7 indicators)
- Pattern recognition

### Example Data Fetching

```python
async def _fetch_market_data(self, ticker: str, context: Dict) -> Dict:
    """Fetch real data from multiple sources."""
    data = {}
    
    # FMP: Company profile
    data["company_profile"] = self.fmp_utils.get_company_profile(ticker)
    
    # FMP: Financial metrics
    metrics_df = self.fmp_utils.get_financial_metrics(ticker, years=4)
    data["financial_metrics"] = metrics_df.to_markdown()
    
    # Yahoo Finance: Stock data
    data["stock_info"] = self.yf_utils.get_stock_info(ticker)
    data["historical_data"] = self.yf_utils.get_historical_data(ticker, period="1y")
    
    # Yahoo Finance: Technical analysis
    data["technical_analysis"] = self.yf_utils.run_technical_analysis(ticker)
    
    return data
```

## Agent Registry Integration

All agents are registered in the framework's `AgentRegistry`:

```python
from framework.core.registry import AgentRegistry

agent_registry = AgentRegistry()

# Register agents
for agent_name, agent_instance in agents.items():
    agent_registry.register_agent(
        name=agent_name,
        agent=agent_instance,
        capabilities=agent_instance.capabilities,
        metadata={
            "type": "financial_research",
            "domain": agent_name
        }
    )
```

## Orchestrator Usage

```python
from framework.core.orchestrator import MagenticOrchestrator
from framework.patterns import SequentialPattern

# Initialize orchestrator
orchestrator = MagenticOrchestrator(
    settings=settings,
    agent_registry=agent_registry,
    observability=observability_service
)

# Execute with pattern
pattern = SequentialPattern(
    agents=["company", "earnings", "fundamentals"],
    config={"preserve_context": True}
)

result = await orchestrator.execute(
    task="Comprehensive analysis of MSFT",
    pattern=pattern
)
```

## Migration Checklist

- [x] **CompanyAgent**: Refactored to MAF pattern with FMP + YF integration
- [ ] **SECAgent**: Update to MAF pattern
- [ ] **EarningsAgent**: Update to MAF pattern  
- [ ] **FundamentalsAgent**: Update to MAF pattern
- [ ] **TechnicalsAgent**: Update to MAF pattern
- [ ] **ReportAgent**: Update to MAF pattern
- [ ] **Orchestrator**: Replace custom logic with framework patterns
- [ ] **DTO**: Align with framework pattern types
- [ ] **API Endpoints**: Update to use framework patterns

## Reference Examples

- **Deep Research App**: `deep_research_app/backend/app/main.py`
  - `AIResearchAgent`: MAF-compliant custom agent
  - `TavilySearchAgent`: MAF-compliant with external API
  
- **Framework Examples**: `framework/examples/`
  - `basic_usage.py`: Pattern demonstrations
  - `complete_usage.py`: Full workflow examples

## Benefits

✅ **Leverages Framework**: Use battle-tested orchestration patterns  
✅ **MAF Integration**: Full Microsoft Agent Framework compatibility  
✅ **Context Management**: Automatic context preservation  
✅ **Error Handling**: Built-in retry and fallback logic  
✅ **Observability**: Framework logging and tracing  
✅ **Real Data**: All agents fetch actual market data  
✅ **Type Safety**: MAF message types (ChatMessage, TextContent)  
✅ **Extensibility**: Easy to add new patterns and agents

## Next Steps

1. **Complete Agent Migration**: Update remaining 5 agents to MAF pattern
2. **Refactor Orchestrator**: Replace custom execution with framework patterns
3. **Update DTO**: Align request/response models with framework
4. **Add Pattern Endpoints**: Expose pattern selection in API
5. **Implement PDF Generation**: Complete ReportAgent with ReportLab
6. **End-to-End Testing**: Test all patterns with real tickers

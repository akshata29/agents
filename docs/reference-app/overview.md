# Deep Research App - Reference Implementation

## Overview

The Deep Research App is a comprehensive reference implementation demonstrating how to build AI applications using the Foundation Framework. It showcases both YAML-based declarative workflows and code-based programmatic orchestration patterns.

## Application Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (React + TypeScript)             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Dashboard  │  │  Research  │  │  Execution │            │
│  │            │  │   Form     │  │  Monitor   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST API + WebSocket
┌────────────────────────▼─────────────────────────────────────┐
│                  Backend (FastAPI + Python)                   │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              Dual Execution Modes                         ││
│  │  ┌───────────────────┐  ┌───────────────────┐           ││
│  │  │  YAML Workflow    │  │  Code-Based       │           ││
│  │  │  (Declarative)    │  │  (Programmatic)   │           ││
│  │  └───────────────────┘  └───────────────────┘           ││
│  └──────────────────────────────────────────────────────────┘│
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐│
│  │            Custom MAF-Compliant Agents                    ││
│  │  ┌────────────────┐  ┌────────────────┐                 ││
│  │  │ AIResearchAgent│  │ TavilySearchAgent│                ││
│  │  └────────────────┘  └────────────────┘                 ││
│  └──────────────────────────────────────────────────────────┘│
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│           Foundation Framework                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Orchestrator │  │   Registry   │  │   Workflow   │      │
│  │              │  │              │  │    Engine    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Custom Agents

#### AIResearchAgent

A Microsoft Agent Framework compliant agent using Azure OpenAI for AI-powered research.

**Implementation** (`backend/app/main.py`):

```python
from agent_framework import BaseAgent, AgentRunResponse, ChatMessage, Role, TextContent

class AIResearchAgent(BaseAgent):
    """AI-powered research agent using Azure OpenAI."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        azure_client: AzureOpenAI,
        model: str,
        system_prompt: str
    ):
        # Initialize MAF BaseAgent
        super().__init__(name=name, description=description)
        
        # Store custom attributes
        self.agent_id = agent_id
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = system_prompt
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent - MAF required method."""
        
        # 1. Normalize messages (MAF helper)
        normalized_messages = self._normalize_messages(messages)
        
        # 2. Extract last message content
        last_message = normalized_messages[-1] if normalized_messages else None
        message_content = last_message.text if hasattr(last_message, 'text') else str(last_message)
        
        # 3. Get context from kwargs (framework-specific)
        context = kwargs.get('context', {})
        prompt = self._build_prompt(message_content, context)
        
        # 4. Call Azure OpenAI
        response = await asyncio.to_thread(
            self.azure_client.chat.completions.create,
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content
        
        # 5. Create MAF response
        response_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text=result_text)]
        )
        
        # 6. Notify thread if provided
        if thread:
            await self._notify_thread_of_new_messages(
                thread, normalized_messages, response_message
            )
        
        return AgentRunResponse(messages=[response_message])
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncGenerator[AgentRunResponseUpdate, None]:
        """Stream responses - MAF required method."""
        response = await self.run(messages, thread=thread, **kwargs)
        
        for message in response.messages:
            if message.contents:
                for content in message.contents:
                    yield AgentRunResponseUpdate(
                        contents=[content],
                        role=Role.ASSISTANT
                    )
    
    async def process(self, task: str, context: Dict[str, Any] = None) -> str:
        """Legacy method for YAML-based workflow compatibility."""
        context = context or {}
        response = await self.run(messages=task, thread=None, context=context)
        return response.messages[-1].text if response.messages else ""
```

**Key Features:**
- ✅ MAF compliant (`run()` and `run_stream()`)
- ✅ Azure OpenAI integration
- ✅ Context-aware prompting
- ✅ Dual compatibility (YAML + Code)

#### TavilySearchAgent

Web search agent using Tavily API with AI synthesis.

```python
class TavilySearchAgent(BaseAgent):
    """Research agent with web search capabilities."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        tavily: TavilyClient,
        azure_client: AzureOpenAI,
        model: str
    ):
        super().__init__(name=name, description=description)
        self.agent_id = agent_id
        self.tavily = tavily
        self.azure_client = azure_client
        self.model = model
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute web search + AI synthesis."""
        
        normalized_messages = self._normalize_messages(messages)
        last_message = normalized_messages[-1] if normalized_messages else None
        message_content = last_message.text if hasattr(last_message, 'text') else str(last_message)
        
        # 1. Perform web search with Tavily
        search_query = message_content.strip()
        search_results = await asyncio.to_thread(
            self.tavily.search,
            query=search_query,
            max_results=5
        )
        
        # 2. Format search results
        sources_text = "\n\n".join([
            f"Source: {r['title']}\nURL: {r['url']}\n{r['content']}"
            for r in search_results.get('results', [])
        ])
        
        # 3. Synthesize with AI
        synthesis_prompt = f"""Based on the following web search results, {message_content}

Search Results:
{sources_text}

Provide a comprehensive, well-structured response."""
        
        response = await asyncio.to_thread(
            self.azure_client.chat.completions.create,
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a research analyst."},
                {"role": "user", "content": synthesis_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content
        
        response_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text=result_text)]
        )
        
        if thread:
            await self._notify_thread_of_new_messages(
                thread, normalized_messages, response_message
            )
        
        return AgentRunResponse(messages=[response_message])
```

**Key Features:**
- ✅ Web search integration
- ✅ AI-powered synthesis
- ✅ Source citation
- ✅ Error handling

### 2. Agent Setup & Registration

```python
async def setup_research_agents(agent_registry: AgentRegistry, settings: Settings):
    """Setup and register all research agents."""
    
    # Get Azure OpenAI client
    azure_client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-02-15-preview",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    # Get Tavily client
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    # Create agent instances
    planner = AIResearchAgent(
        agent_id="planner",
        name="Research Planner",
        description="Creates comprehensive research plans",
        azure_client=azure_client,
        model="chat4o",
        system_prompt="You are an expert research planner..."
    )
    
    researcher = TavilySearchAgent(
        agent_id="researcher",
        name="Web Researcher",
        description="Conducts web research using Tavily",
        tavily=tavily,
        azure_client=azure_client,
        model="chat4o"
    )
    
    writer = AIResearchAgent(
        agent_id="writer",
        name="Report Writer",
        description="Writes comprehensive research reports",
        azure_client=azure_client,
        model="chat4o",
        system_prompt="You are an expert technical writer..."
    )
    
    reviewer = AIResearchAgent(
        agent_id="reviewer",
        name="Quality Reviewer",
        description="Reviews and validates reports",
        azure_client=azure_client,
        model="chat4o",
        system_prompt="You are a quality assurance specialist..."
    )
    
    summarizer = AIResearchAgent(
        agent_id="summarizer",
        name="Executive Summarizer",
        description="Creates executive summaries",
        azure_client=azure_client,
        model="chat4o",
        system_prompt="You are an expert at creating executive summaries..."
    )
    
    # Register all agents
    agents = [
        ("planner", planner),
        ("researcher", researcher),
        ("writer", writer),
        ("reviewer", reviewer),
        ("summarizer", summarizer)
    ]
    
    for agent_id, agent_instance in agents:
        await agent_registry.register_agent(
            agent_id=agent_id,
            agent_instance=agent_instance,
            metadata={
                "type": "research",
                "framework": "Microsoft Agent Framework",
                "status": "active"
            }
        )
        logger.info(f"Registered agent: {agent_id}")
```

## Execution Modes

### Mode 1: YAML-Based Workflow

**Configuration** (`examples/workflows/deep_research.yaml`):

```yaml
name: deep_research_workflow
version: "1.0"
description: "Comprehensive AI-powered research workflow"
max_parallel_tasks: 5
timeout: 3600

variables:
  - name: topic
    type: string
    required: true
    description: "Research topic"

tasks:
  # Phase 1: Planning
  - id: create_research_plan
    name: "Create Research Plan"
    type: agent
    agent: planner
    prompt: |
      Create a comprehensive research plan for the topic: {{topic}}.
      Break down the research into key areas to investigate.
    timeout: 60

  # Phase 2: Parallel Research
  - id: investigate_core_concepts
    name: "Investigate Core Concepts"
    type: agent
    agent: researcher
    depends_on: [create_research_plan]
    prompt: |
      Research and analyze the core concepts related to: {{topic}}
      Context: {{create_research_plan.output}}
    timeout: 120

  - id: investigate_current_state
    name: "Investigate Current State"
    type: agent
    agent: researcher
    depends_on: [create_research_plan]
    prompt: |
      Research the current state and recent developments in: {{topic}}
      Context: {{create_research_plan.output}}
    timeout: 120

  - id: investigate_applications
    name: "Investigate Applications"
    type: agent
    agent: researcher
    depends_on: [create_research_plan]
    prompt: |
      Research practical applications and use cases of: {{topic}}
      Context: {{create_research_plan.output}}
    timeout: 120

  - id: investigate_challenges
    name: "Investigate Challenges"
    type: agent
    agent: researcher
    depends_on: [create_research_plan]
    prompt: |
      Research challenges and limitations in: {{topic}}
      Context: {{create_research_plan.output}}
    timeout: 120

  - id: investigate_future_trends
    name: "Investigate Future Trends"
    type: agent
    agent: researcher
    depends_on: [create_research_plan]
    prompt: |
      Research future trends and predictions for: {{topic}}
      Context: {{create_research_plan.output}}
    timeout: 120

  # Phase 3: Synthesis
  - id: synthesize_findings
    name: "Synthesize Findings"
    type: agent
    agent: writer
    depends_on: [
      investigate_core_concepts,
      investigate_current_state,
      investigate_applications,
      investigate_challenges,
      investigate_future_trends
    ]
    prompt: |
      Synthesize the following research findings into a comprehensive report:
      
      Topic: {{topic}}
      Plan: {{create_research_plan.output}}
      
      Core Concepts: {{investigate_core_concepts.output}}
      Current State: {{investigate_current_state.output}}
      Applications: {{investigate_applications.output}}
      Challenges: {{investigate_challenges.output}}
      Future Trends: {{investigate_future_trends.output}}
    timeout: 180

  # Phase 4: Validation
  - id: validate_report
    name: "Validate Report"
    type: agent
    agent: reviewer
    depends_on: [synthesize_findings]
    prompt: |
      Review and validate the following research report:
      {{synthesize_findings.output}}
    timeout: 120

  # Phase 5: Finalization
  - id: finalize_report
    name: "Finalize Report"
    type: agent
    agent: writer
    depends_on: [validate_report]
    prompt: |
      Finalize the research report based on review feedback:
      
      Original Report: {{synthesize_findings.output}}
      Review Feedback: {{validate_report.output}}
    timeout: 120

  # Phase 6: Summary
  - id: create_summary
    name: "Create Executive Summary"
    type: agent
    agent: summarizer
    depends_on: [finalize_report]
    prompt: |
      Create a concise executive summary of the research report:
      {{finalize_report.output}}
    timeout: 60
```

**Execution:**

```python
# Load workflow
await workflow_engine.load_workflow("examples/workflows/deep_research.yaml")

# Execute
execution = await workflow_engine.execute_workflow(
    workflow_name="deep_research_workflow",
    input_data={"topic": "Artificial Intelligence in Healthcare"}
)

# Get status
status = await workflow_engine.get_execution_status(execution.id)
```

**Advantages:**
- ✅ Declarative and readable
- ✅ Easy to modify without code changes
- ✅ Automatic dependency resolution
- ✅ Built-in parallel execution

### Mode 2: Code-Based Orchestration

**Implementation** (`backend/app/main.py`):

```python
async def execute_research_programmatically(
    orchestrator_instance: MagenticOrchestrator,
    topic: str,
    execution_id: str
) -> Dict[str, Any]:
    """Execute research using programmatic orchestration patterns."""
    
    results = {}
    
    # Phase 1: Sequential Planning with SequentialPattern
    logger.info("Code-based execution: Phase 1 - Sequential Planning with SequentialPattern")
    
    plan_pattern = SequentialPattern(
        name="research_planning",
        description="Create comprehensive research plan",
        agents=["planner"],
        preserve_context=True
    )
    
    plan_context = await orchestrator_instance.execute(
        task=f"Create a comprehensive research plan for the topic: {topic}. Break down the research into key areas to investigate.",
        pattern=plan_pattern
    )
    
    # Extract plan from results
    if plan_context.result and "results" in plan_context.result:
        results["research_plan"] = plan_context.result["results"][0].get("content", "")
    
    # Phase 2: Concurrent Investigation with Parallel Execution
    logger.info("Code-based execution: Phase 2 - Concurrent Investigation with ConcurrentPattern")
    
    research_aspects = [
        ("core_concepts", "Research and analyze the core concepts"),
        ("current_state", "Research the current state and recent developments"),
        ("applications", "Research practical applications and use cases"),
        ("challenges", "Research challenges and limitations"),
        ("future_trends", "Research future trends and predictions")
    ]
    
    async def execute_research_task(key: str, task_prompt: str):
        """Execute a single research task."""
        task_full = f"{task_prompt} related to: {topic}\n\nContext: {results.get('research_plan', '')}"
        
        sequential_result = await orchestrator_instance.execute_sequential(
            task=task_full,
            agent_ids=["researcher"],
            tools=[]
        )
        
        if sequential_result and "results" in sequential_result:
            response_content = sequential_result["results"][0].get("content", "")
            return (key, response_content)
        else:
            return (key, f"Error: No response received")
    
    # Execute all 5 research tasks in parallel
    research_results = await asyncio.gather(
        *[execute_research_task(key, task_prompt) for key, task_prompt in research_aspects],
        return_exceptions=True
    )
    
    # Process results
    for result in research_results:
        if isinstance(result, Exception):
            logger.error("Research task failed", error=str(result))
        else:
            key, content = result
            results[key] = content
    
    # Phase 3-6: Sequential Processing with SequentialPattern
    logger.info("Code-based execution: Phase 3-6 - Sequential Processing with SequentialPattern")
    
    comprehensive_context = f"""Research Topic: {topic}

Research Plan:
{results.get('research_plan', '')}

Core Concepts:
{results.get('core_concepts', '')}

Current State:
{results.get('current_state', '')}

Applications:
{results.get('applications', '')}

Challenges:
{results.get('challenges', '')}

Future Trends:
{results.get('future_trends', '')}

Please:
1. Synthesize these findings into a comprehensive report
2. Review the report for quality and accuracy
3. Create an executive summary"""
    
    final_phases_pattern = SequentialPattern(
        name="synthesis_validation_finalization",
        description="Sequential synthesis, validation, and summarization",
        agents=["writer", "reviewer", "summarizer"],
        preserve_context=True,
        fail_fast=False
    )
    
    final_context = await orchestrator_instance.execute(
        task=comprehensive_context,
        pattern=final_phases_pattern
    )
    
    # Extract results
    if final_context.result and "results" in final_context.result:
        responses = final_context.result["results"]
        if len(responses) >= 3:
            results["draft_report"] = responses[0].get("content", "")
            results["validation_results"] = responses[1].get("content", "")
            results["executive_summary"] = responses[2].get("content", "")
            results["final_report"] = responses[0].get("content", "")
    
    return results
```

**Key Pattern Usage:**

1. **SequentialPattern** (Phase 1):
   - Single agent planning
   - Context preservation enabled

2. **Parallel Execution** (Phase 2):
   - 5 independent research tasks
   - Each uses SequentialPattern with single agent
   - Parallelism via `asyncio.gather`

3. **SequentialPattern** (Phase 3-6):
   - Multi-agent sequential processing
   - Writer → Reviewer → Summarizer
   - Full context propagation

**Advantages:**
- ✅ Full programmatic control
- ✅ Dynamic decision-making
- ✅ Complex logic and conditionals
- ✅ Fine-grained error handling

## API Endpoints

### REST API

```python
# Start research
POST /api/research/start
{
    "topic": "Artificial Intelligence in Healthcare",
    "execution_mode": "code",  # or "workflow"
    "max_sources": 5
}

Response:
{
    "execution_id": "uuid",
    "status": "running",
    "message": "Research started"
}

# Get status
GET /api/research/status/{execution_id}

Response:
{
    "execution_id": "uuid",
    "status": "running",
    "progress": 45.0,
    "current_task": "Phase 2: Concurrent Investigation",
    "completed_tasks": ["Phase 1: Research Planning"],
    "results": {...}
}

# Get workflow info
GET /api/workflow/info

Response:
{
    "name": "deep_research_workflow",
    "total_tasks": 10,
    "orchestration_pattern": "Hybrid (Sequential → Concurrent → Sequential)",
    "execution_modes": ["workflow", "code"]
}
```

### WebSocket

```python
# Real-time updates
WS /ws/research/{execution_id}

Messages:
{
    "type": "status",
    "status": "running",
    "progress": 25.0,
    "current_task": "Phase 1: Research Planning"
}

{
    "type": "task_completed",
    "task_id": "create_research_plan",
    "result": "..."
}

{
    "type": "execution_complete",
    "final_results": {...}
}
```

## Frontend Implementation

### Key Components

**ResearchForm.tsx** - Research initiation
**ExecutionMonitor.tsx** - Real-time progress tracking
**WorkflowVisualization.tsx** - Workflow graph display
**Dashboard.tsx** - Results presentation

### State Management

```typescript
// Using TanStack Query for API state
const { mutate: startResearch } = useMutation({
  mutationFn: apiClient.startResearch,
  onSuccess: (data) => {
    setExecutionId(data.execution_id);
    // Switch to monitor tab
  }
});

// WebSocket connection for real-time updates
useEffect(() => {
  if (!executionId) return;
  
  const ws = new WebSocket(
    `ws://localhost:8000/ws/research/${executionId}`
  );
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Update UI based on message type
  };
  
  return () => ws.close();
}, [executionId]);
```

## Summary

The Deep Research App demonstrates:

1. **Custom MAF-Compliant Agents**: AIResearchAgent, TavilySearchAgent
2. **Dual Execution Modes**: YAML declarative vs Code programmatic
3. **Pattern Implementation**: Sequential, Concurrent, Hybrid
4. **Real-time Monitoring**: WebSocket updates, progress tracking
5. **Features**: Error handling, logging, metrics

See [Building Your Own Application](./building-your-own.md) for a step-by-step guide to creating similar applications.

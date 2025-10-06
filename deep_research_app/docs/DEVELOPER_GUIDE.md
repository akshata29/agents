# Developer Guide

> Comprehensive guide for developers working with the Deep Research application.

---

## 📋 Table of Contents

1. [Execution Modes](#execution-modes)
2. [Orchestration Patterns](#orchestration-patterns)
3. [Concurrency Model](#concurrency-model)
4. [Code Examples](#code-examples)
5. [Best Practices](#best-practices)
6. [Extending the Application](#extending-the-application)

---

## 🎯 Execution Modes

The application supports three distinct execution modes, each with different trade-offs.

### Quick Comparison

| Feature | YAML Workflows | Code-Based | MAF Workflows |
|---------|---------------|------------|---------------|
| **Configuration** | YAML files | Python code | Graph executors |
| **Complexity** | Simple | Moderate | Advanced |
| **Flexibility** | Limited | High | Very High |
| **Type Safety** | No | Partial | Full |
| **Best For** | Standard flows | Custom logic | Production systems |
| **Learning Curve** | Easy | Moderate | Steep |

---

### Mode 1: YAML Workflows (Declarative)

**When to use:**
- ✅ Standard, predictable workflows
- ✅ Non-developers need to modify workflows
- ✅ Configuration-driven deployments
- ✅ Quick prototyping

**Example workflow:**

```yaml
# workflows/deep_research.yaml
name: deep_research_workflow
version: 1.0.0

variables:
  - name: topic
    type: string
    required: true
  - name: max_sources
    type: integer
    default: 5

tasks:
  # Phase 1: Planning (Sequential)
  - id: plan
    type: agent
    agent: planner
    inputs:
      topic: ${topic}
    outputs:
      research_plan: result
  
  # Phase 2: Research (Parallel)
  - id: research
    type: agent
    agent: researcher
    dependencies: [plan]
    parallel: 5  # Run 5 researchers in parallel
    inputs:
      plan: ${research_plan}
      max_sources: ${max_sources}
    outputs:
      findings: result
  
  # Phase 3: Synthesis (Sequential)
  - id: synthesize
    type: agent
    agent: writer
    dependencies: [research]
    inputs:
      findings: ${findings}
    outputs:
      report: result
  
  # Phase 4: Review (Sequential)
  - id: review
    type: agent
    agent: reviewer
    dependencies: [synthesize]
    inputs:
      report: ${report}
    outputs:
      validated_report: result
```

**Backend implementation:**

```python
# Starting YAML workflow
execution_id = await workflow_engine.execute_workflow(
    workflow_name="deep_research_workflow",
    variables={
        "topic": request.topic,
        "max_sources": request.max_sources
    }
)

# Monitor execution
execution = await workflow_engine.get_execution(execution_id)
status = await workflow_engine.get_execution_status(execution_id)
```

**Pros:**
- 📝 Easy to read and modify
- 🔧 No coding required
- 📊 Clear visual structure
- 🚀 Quick to deploy

**Cons:**
- ⚠️ Limited conditional logic
- ⚠️ Static dependencies
- ⚠️ Basic error handling

---

### Mode 2: Code-Based (Programmatic)

**When to use:**
- ✅ Complex orchestration logic
- ✅ Dynamic decision-making
- ✅ Custom error handling
- ✅ Integration with external systems

**Implementation pattern:**

```python
async def execute_research_programmatically(
    topic: str,
    orchestrator: MagenticOrchestrator,
    registry: AgentRegistry
) -> Dict[str, Any]:
    """
    Implements Sequential → Concurrent → Sequential pattern.
    
    Pattern: Planning → Parallel Research → Synthesis
    """
    
    # Phase 1: Sequential Planning
    planning_result = await orchestrator.execute_sequential(
        task=f"Create research plan for: {topic}",
        agent_ids=["planner"],
        context={"topic": topic}
    )
    research_plan = planning_result["planner"]["result"]
    
    # Phase 2: Concurrent Research (5 parallel tasks)
    research_tasks = [
        execute_research_task(
            agent_id="researcher",
            area="core_concepts",
            plan=research_plan
        ),
        execute_research_task(
            agent_id="researcher",
            area="current_state",
            plan=research_plan
        ),
        execute_research_task(
            agent_id="researcher",
            area="applications",
            plan=research_plan
        ),
        execute_research_task(
            agent_id="researcher",
            area="challenges",
            plan=research_plan
        ),
        execute_research_task(
            agent_id="researcher",
            area="future",
            plan=research_plan
        )
    ]
    
    # Wait for all research to complete
    research_results = await asyncio.gather(*research_tasks)
    
    # Phase 3: Sequential Synthesis
    synthesis_result = await orchestrator.execute_sequential(
        task="Synthesize findings into comprehensive report",
        agent_ids=["writer", "reviewer", "summarizer"],
        context={
            "findings": research_results,
            "plan": research_plan
        }
    )
    
    return {
        "plan": research_plan,
        "findings": research_results,
        "report": synthesis_result["writer"]["result"],
        "validation": synthesis_result["reviewer"]["result"],
        "summary": synthesis_result["summarizer"]["result"]
    }

async def execute_research_task(
    agent_id: str,
    area: str,
    plan: str
) -> Dict[str, Any]:
    """Execute single research task."""
    agent = await registry.get_agent(agent_id)
    result = await agent.execute({
        "task": f"Research {area}",
        "plan": plan
    })
    return {
        "area": area,
        "findings": result
    }
```

**Orchestrator patterns available:**

```python
# 1. Sequential execution
result = await orchestrator.execute_sequential(
    task="Multi-step task",
    agent_ids=["agent1", "agent2", "agent3"]
)

# 2. Concurrent execution
result = await orchestrator.execute_concurrent(
    task="Parallel task",
    agent_ids=["agent1", "agent2", "agent3"]
)

# 3. ReAct pattern (reasoning + acting)
result = await orchestrator.execute_react(
    task="Complex reasoning task",
    agent_id="reasoning_agent",
    max_iterations=5
)
```

**Pros:**
- 💪 Full programmatic control
- 🧠 Dynamic decision-making
- 🔄 Custom error recovery
- 🎯 Complex conditional logic

**Cons:**
- ⚠️ Requires coding skills
- ⚠️ More verbose than YAML
- ⚠️ Harder to visualize

---

### Mode 3: MAF Workflows (Graph-Based)

**When to use:**
- ✅ Type-safe message passing
- ✅ Complex graph topologies
- ✅ Fan-out/fan-in patterns
- ✅ OpenTelemetry observability

**Architecture:**

```
Request → Planner → [Researcher 0, Researcher 1, Researcher 2] → Synthesizer → Reviewer → Summarizer → FinalOutput
          (start)   (fan-out: broadcast to 3)    (fan-in: collect)   (sequential chain)
```

**Implementation:**

```python
from agent_framework import (
    WorkflowBuilder,
    Executor,
    handler,
    WorkflowContext
)
from dataclasses import dataclass
from datetime import datetime

# Define message types (type-safe)
@dataclass
class ResearchRequest:
    topic: str
    execution_id: str
    max_sources: int
    timestamp: datetime

@dataclass
class ResearchPlan:
    topic: str
    execution_id: str
    areas: List[str]
    strategy: str

@dataclass
class ResearchFindings:
    area: str
    findings: str
    sources: List[str]

# Define executors (graph nodes)
class ResearchPlannerExecutor(Executor):
    """Creates research plan (start node)."""
    
    def __init__(self, azure_client, model, executor_id="planner"):
        super().__init__(id=executor_id)
        self.azure_client = azure_client
        self.model = model
    
    @handler
    async def run(
        self,
        request: ResearchRequest,
        ctx: WorkflowContext[ResearchPlan]
    ) -> None:
        """Create research plan and send to downstream executors."""
        
        # Generate plan using LLM
        plan = await self.create_plan(request.topic)
        
        # Send plan to all connected executors (fan-out)
        await ctx.send_message(ResearchPlan(
            topic=request.topic,
            execution_id=request.execution_id,
            areas=plan["areas"],
            strategy=plan["strategy"]
        ))

class ResearchExecutor(Executor):
    """Executes research for one area."""
    
    def __init__(self, index, tavily_client, azure_client, model, executor_id):
        super().__init__(id=executor_id)
        self.index = index
        self.tavily_client = tavily_client
        self.azure_client = azure_client
        self.model = model
    
    @handler
    async def run(
        self,
        plan: ResearchPlan,
        ctx: WorkflowContext[ResearchFindings]
    ) -> None:
        """Research assigned area and send findings."""
        
        # Get assigned area
        area = plan.areas[self.index] if self.index < len(plan.areas) else None
        if not area:
            return
        
        # Conduct research
        findings = await self.research_area(area, plan.strategy)
        
        # Send findings to synthesizer (fan-in)
        await ctx.send_message(ResearchFindings(
            area=area,
            findings=findings["content"],
            sources=findings["sources"]
        ))

class SynthesizerExecutor(Executor):
    """Combines findings from all researchers (fan-in node)."""
    
    @handler
    async def run(
        self,
        findings: List[ResearchFindings],  # Collects from all researchers
        ctx: WorkflowContext[SynthesizedReport]
    ) -> None:
        """Synthesize all findings into report."""
        
        # Combine all findings
        report = await self.synthesize(findings)
        
        # Send to reviewer
        await ctx.send_message(report)

# Build workflow graph
async def create_research_workflow(
    azure_client,
    tavily_client,
    model="chat4o",
    max_research_areas=3
):
    """Build MAF workflow graph."""
    
    # Create executor instances
    planner = ResearchPlannerExecutor(azure_client, model, "planner")
    
    researchers = [
        ResearchExecutor(i, tavily_client, azure_client, model, f"researcher_{i}")
        for i in range(max_research_areas)
    ]
    
    synthesizer = SynthesizerExecutor(azure_client, model, "synthesizer")
    reviewer = ReviewerExecutor(azure_client, model, "reviewer")
    summarizer = SummarizerExecutor(azure_client, model, "summarizer")
    
    # Build graph with edges
    workflow = (
        WorkflowBuilder()
        .set_start_executor(planner)
        # Fan-out: Broadcast plan to all researchers
        .add_fan_out_edges(planner, researchers)
        # Fan-in: Collect all findings to synthesizer
        .add_fan_in_edges(researchers, synthesizer)
        # Sequential chain
        .add_edge(synthesizer, reviewer)
        .add_edge(reviewer, summarizer)
        .build()
    )
    
    return workflow

# Execute workflow with event streaming
async def execute_maf_workflow(topic: str, execution_id: str):
    """Execute MAF workflow and handle events."""
    
    workflow = await create_research_workflow(azure_client, tavily_client)
    
    request = ResearchRequest(
        topic=topic,
        execution_id=execution_id,
        max_sources=5,
        timestamp=datetime.utcnow()
    )
    
    final_output = None
    
    # Stream execution events
    async for event in workflow.run_stream(request):
        if isinstance(event, ExecutorCompletedEvent):
            print(f"✓ Completed: {event.executor_id}")
        
        elif isinstance(event, WorkflowOutputEvent):
            if isinstance(event.data, FinalOutput):
                final_output = event.data
        
        elif isinstance(event, WorkflowFailedEvent):
            print(f"✗ Failed: {event.error}")
    
    return final_output
```

**Key features:**

1. **Type-Safe Messages**
   - Python dataclasses for all messages
   - Compile-time type checking
   - Clear message contracts

2. **Graph Topology**
   - Fan-out: Broadcast to multiple executors
   - Fan-in: Collect from multiple executors
   - Sequential chains

3. **Event-Driven**
   - Stream events during execution
   - React to executor completions
   - Handle failures gracefully

4. **Observability**
   - OpenTelemetry integration
   - Distributed tracing
   - Metrics and logging

**Pros:**
- ✅ Type-safe messaging
- ✅ Advanced graph patterns
- ✅ Observability
- ✅ Clear separation of concerns

**Cons:**
- ⚠️ Steeper learning curve
- ⚠️ More boilerplate code
- ⚠️ Requires MAF knowledge

---

## 🎭 Orchestration Patterns

### Sequential Pattern

Execute agents one after another, passing output as input:

```python
result = await orchestrator.execute_sequential(
    task="Multi-step analysis",
    agent_ids=["analyzer", "validator", "reporter"],
    context={"data": input_data}
)
```

**Use cases:**
- Linear workflows
- Output depends on previous step
- Quality gates (validate before proceeding)

---

### Concurrent Pattern

Execute multiple agents in parallel:

```python
result = await orchestrator.execute_concurrent(
    task="Parallel research",
    agent_ids=["researcher1", "researcher2", "researcher3"],
    context={"topic": research_topic}
)
```

**Use cases:**
- Independent tasks
- Speed optimization
- Diverse perspectives

---

### ReAct Pattern

Reasoning + Acting loop with observations:

```python
result = await orchestrator.execute_react(
    task="Complex problem solving",
    agent_id="reasoning_agent",
    max_iterations=5,
    context={"problem": problem_statement}
)
```

**Use cases:**
- Complex reasoning tasks
- Multi-step problem solving
- Self-correcting workflows

---

## ⚡ Concurrency Model

### Understanding Parallel Execution

```
Sequential Phase:          Concurrent Phase:           Sequential Phase:
     
  [Planner]               [Researcher 0]                [Synthesizer]
      ↓                   [Researcher 1]                      ↓
  (10 seconds)            [Researcher 2]                 [Reviewer]
                          [Researcher 3]                      ↓
                          [Researcher 4]                 [Summarizer]
                               ↓
                          (30 seconds total)
                          (6 seconds each)
```

### Configuration

**YAML Mode:**
```yaml
tasks:
  - id: research
    parallel: 5  # Run 5 instances
```

**Code Mode:**
```python
# Create 5 parallel tasks
tasks = [execute_research(i) for i in range(5)]
results = await asyncio.gather(*tasks)
```

**MAF Mode:**
```python
# Create 3 researcher executors
researchers = [
    ResearchExecutor(i, ..., f"researcher_{i}")
    for i in range(3)
]
# Add fan-out edges (broadcasts to all)
.add_fan_out_edges(planner, researchers)
```

### Best Practices

1. **Right-size parallelism:**
   - Too few: Underutilized
   - Too many: API rate limits, resource contention
   - Sweet spot: 3-5 parallel tasks

2. **Handle failures:**
   ```python
   # Use return_exceptions to handle individual failures
   results = await asyncio.gather(*tasks, return_exceptions=True)
   
   for result in results:
       if isinstance(result, Exception):
           logger.error(f"Task failed: {result}")
       else:
           process_result(result)
   ```

3. **Rate limiting:**
   ```python
   import asyncio
   from asyncio import Semaphore
   
   semaphore = Semaphore(3)  # Max 3 concurrent
   
   async def rate_limited_task(task_id):
       async with semaphore:
           return await execute_task(task_id)
   ```

---

## 💻 Code Examples

### Adding a New Agent

```python
# 1. Define agent in framework/agents/
from framework.agents.base import Agent

class CustomAgent(Agent):
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        result = await self.process(task)
        return {"result": result}

# 2. Register agent
from framework.core.registry import AgentRegistry

registry = AgentRegistry()
registry.register_agent("custom_agent", CustomAgent)

# 3. Use in workflow
# YAML:
tasks:
  - id: custom_task
    type: agent
    agent: custom_agent

# Code:
result = await orchestrator.execute_sequential(
    agent_ids=["custom_agent"],
    context={"task": "..."}
)
```

### Custom Error Handling

```python
async def execute_with_retry(agent_id: str, task: Dict, max_retries=3):
    """Execute agent with retry logic."""
    
    for attempt in range(max_retries):
        try:
            agent = await registry.get_agent(agent_id)
            result = await agent.execute(task)
            return result
        
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Rate limited, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise
        
        except Exception as e:
            logger.error(f"Agent {agent_id} failed: {e}")
            if attempt == max_retries - 1:
                raise
```

### Progress Tracking

```python
async def execute_with_progress(
    tasks: List[Callable],
    progress_callback: Callable[[float, str], None]
):
    """Execute tasks with progress updates."""
    
    total = len(tasks)
    completed = 0
    
    for i, task in enumerate(tasks):
        # Update progress
        progress = (i / total) * 100
        progress_callback(progress, f"Executing task {i+1}/{total}")
        
        # Execute task
        result = await task()
        
        completed += 1
    
    # Final progress
    progress_callback(100.0, "All tasks completed")
```

---

## ✅ Best Practices

### 1. Error Handling

**Do:**
```python
try:
    result = await agent.execute(task)
except RateLimitError:
    await asyncio.sleep(1)
    result = await agent.execute(task)
except ValidationError as e:
    return {"error": str(e), "status": "invalid_input"}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

**Don't:**
```python
# Bare except catches everything
try:
    result = await agent.execute(task)
except:
    pass  # Silent failure
```

### 2. Resource Management

**Do:**
```python
async with aiohttp.ClientSession() as session:
    # Use session
    pass
# Automatically closed
```

**Don't:**
```python
session = aiohttp.ClientSession()
# Use session
# Never closed - resource leak
```

### 3. Logging

**Do:**
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "Task completed",
    task_id=task_id,
    duration=duration,
    status="success"
)
```

**Don't:**
```python
print(f"Task {task_id} completed in {duration}s")  # Not searchable
```

### 4. Configuration

**Do:**
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    azure_endpoint: str
    api_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**Don't:**
```python
api_key = os.getenv("API_KEY")  # No validation
```

---

## 🔧 Extending the Application

### Adding a New Execution Mode

1. **Backend:**
   ```python
   # main.py
   @app.post("/api/research/start")
   async def start_research(request: ResearchRequest):
       if request.execution_mode == "custom":
           background_tasks.add_task(
               execute_custom_mode,
               execution_id,
               request
           )
   ```

2. **Frontend:**
   ```typescript
   // types.ts
   export type ExecutionMode = 
     | 'workflow' 
     | 'code' 
     | 'maf-workflow'
     | 'custom';  // Add new mode
   ```

### Adding Custom Metrics

```python
from prometheus_client import Counter, Histogram

# Define metrics
task_counter = Counter(
    'research_tasks_total',
    'Total research tasks executed',
    ['status']
)

task_duration = Histogram(
    'research_task_duration_seconds',
    'Time spent executing research tasks'
)

# Use metrics
with task_duration.time():
    result = await execute_task()
    task_counter.labels(status='success').inc()
```

### Integration with External APIs

```python
async def integrate_external_api(query: str):
    """Example integration with external API."""
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.example.com/search",
            json={"query": query},
            headers={"Authorization": f"Bearer {api_key}"}
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data
```

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Microsoft Agent Framework](https://microsoft.github.io/autogen/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Pydantic](https://docs.pydantic.dev/)
- [React Query](https://tanstack.com/query/latest)

---

**Need more help?** Check the [Architecture Guide](ARCHITECTURE.md) for system design details, or the [Quick Start](QUICKSTART.md) for setup instructions.

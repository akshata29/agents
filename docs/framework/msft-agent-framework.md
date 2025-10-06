# Microsoft Agent Framework Integration

## Overview

The Foundation Framework is built on top of **Microsoft Agent Framework (MAF)**, leveraging its core capabilities while adding enterprise-grade orchestration, security, and monitoring features. This document explains how we integrate with MAF and what enhancements we provide.

## Microsoft Agent Framework Fundamentals

### What is Microsoft Agent Framework?

Microsoft Agent Framework is a Python framework for building AI agents that can:
- Communicate via structured messages (`ChatMessage`)
- Execute workflows with multiple agents
- Support both sequential and concurrent execution patterns
- Provide standardized agent interfaces (`AgentProtocol`)

### Core MAF Components We Use

#### 1. AgentProtocol / BaseAgent

All custom agents in Framework implement MAF's `BaseAgent` interface:

```python
from agent_framework import BaseAgent, AgentRunResponse, ChatMessage

class CustomAgent(BaseAgent):
    """MAF-compliant custom agent."""
    
    def __init__(self, name: str, description: str):
        super().__init__(name=name, description=description)
        # Your initialization
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent - REQUIRED by MAF."""
        # Process messages
        # Return AgentRunResponse with ChatMessage results
        pass
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncGenerator[AgentRunResponseUpdate, None]:
        """Stream responses - REQUIRED by MAF."""
        # Yield AgentRunResponseUpdate chunks
        pass
```

**Key Requirements:**
- Extend `BaseAgent`
- Implement `run()` method returning `AgentRunResponse`
- Implement `run_stream()` method yielding `AgentRunResponseUpdate`
- Use `ChatMessage` with `contents` (list of `TextContent`)
- Handle `AgentThread` for conversation context

#### 2. ChatMessage Structure

MAF uses a specific message format:

```python
from agent_framework import ChatMessage, Role, TextContent

# Correct way to create messages
message = ChatMessage(
    role=Role.USER,
    contents=[TextContent(text="Your message here")]
)

# Accessing message content
text = message.text  # Property that returns the text content
```

**Important Notes:**
- Use `contents` (list), NOT `content` (string)
- Messages have a `text` property to access content
- Use `Role.USER`, `Role.ASSISTANT`, `Role.SYSTEM`

#### 3. Workflow Builders

MAF provides builders for creating workflows:

```python
from agent_framework import SequentialBuilder, ConcurrentBuilder

# Sequential workflow
builder = SequentialBuilder()
builder = builder.participants([agent1, agent2, agent3])
workflow = builder.build()

# Concurrent workflow (fan-out)
builder = ConcurrentBuilder()
builder = builder.participants([agent1, agent2])  # Minimum 2 agents
workflow = builder.build()

# Execute workflow
messages = [ChatMessage(role=Role.USER, contents=[TextContent(text=task)])]
workflow_run = await workflow.run(messages)  # Returns WorkflowRunResult (list)
```

**Key Constraints:**
- SequentialBuilder: 1+ agents, executes in order
- ConcurrentBuilder: 2+ agents (minimum), executes in parallel
- No duplicate agent instances allowed in a single workflow
- `workflow.run()` returns `WorkflowRunResult` (list of events), not async iterator

#### 4. Workflow Events

When a workflow executes, it returns a list of events:

```python
# Execute workflow
workflow_run = await workflow.run(messages)  # Returns list of events

# Process events
for event in workflow_run:  # Regular for loop, not async for
    if isinstance(event, WorkflowOutputEvent):
        # WorkflowOutputEvent has:
        # - data: list[ChatMessage] - the conversation messages
        # - source_executor_id: str - which agent produced this
        last_message = event.data[-1] if event.data else None
        content = last_message.text if last_message else ""
```

**Event Types:**
- `ExecutorInvokedEvent` - Agent started
- `AgentRunEvent` - Agent produced output
- `ExecutorCompletedEvent` - Agent finished
- `WorkflowOutputEvent` - Final workflow output with all messages

## Framework Enhancements

### 1. Orchestrator Layer

**What MAF Provides:** Basic workflow builders
**What Framework Adds:** High-level orchestration with pattern abstraction

```python
from framework.core.orchestrator import MagenticOrchestrator
from framework.patterns.sequential import SequentialPattern

orchestrator = MagenticOrchestrator(settings, agent_registry)

# Define pattern declaratively
pattern = SequentialPattern(
    name="research_planning",
    agents=["planner", "researcher"],
    preserve_context=True
)

# Execute with automatic MAF workflow creation
result = await orchestrator.execute(
    task="Research AI in healthcare",
    pattern=pattern
)
```

**Benefits:**
- Declarative pattern definitions (Pydantic models)
- Automatic MAF workflow building from patterns
- Context preservation between agents
- Error handling and retry logic
- Pattern composition

### 2. Agent Registry

**What MAF Provides:** Agent instances
**What Framework Adds:** Centralized lifecycle management

```python
from framework.core.registry import AgentRegistry

registry = AgentRegistry(settings)

# Register agents
await registry.register_agent(
    agent_id="planner",
    agent_instance=planner_agent,
    metadata={"role": "planning", "priority": "high"}
)

# Retrieve agents for workflows
agent = await registry.get_agent("planner")

# List all agents
agents = await registry.list_agents()
```

**Benefits:**
- Centralized agent storage
- Metadata and tagging
- Lifecycle hooks
- Health monitoring
- Dynamic agent discovery

### 3. ReAct Pattern

**What MAF Provides:** Sequential and Concurrent patterns
**What Framework Adds:** ReAct (Reasoning + Acting) pattern

```python
from framework.patterns.react import ReactPattern

pattern = ReactPattern(
    name="research_task",
    agent="researcher",
    tools=["web_search", "calculator"],
    max_iterations=5,
    think_aloud=True
)

result = await orchestrator.execute(
    task="Find the latest AI research papers",
    pattern=pattern
)
```

**Implementation:**
- Reasoning step: Agent thinks about what to do
- Action step: Agent uses tools or produces output
- Observation: Process tool results
- Iteration: Repeat until goal achieved

### 4. Security Module

**What MAF Provides:** None
**What Framework Adds:** Authentication, authorization, audit

```python
from framework.core.security import SecurityManager

security = SecurityManager(settings)

# Check permissions
allowed = await security.check_permission(
    user_id="user123",
    action="execute_workflow",
    resource="deep_research"
)

# Audit logging
await security.audit_log(
    action="workflow_executed",
    user_id="user123",
    details={"workflow": "deep_research"}
)
```

### 5. Monitoring & Observability

**What MAF Provides:** None
**What Framework Adds:** Metrics, tracing, performance analytics

```python
from framework.core.monitoring import MonitoringService

monitoring = MonitoringService(settings)

# Track execution
with monitoring.track_execution("workflow_execution"):
    result = await orchestrator.execute(task, pattern)

# Get metrics
metrics = await monitoring.get_metrics()
```

### 6. Workflow Engine (YAML)

**What MAF Provides:** Programmatic workflow building
**What Framework Adds:** Declarative YAML-based workflows

```yaml
# workflows/research.yaml
name: deep_research_workflow
version: "1.0"
description: "AI-powered deep research workflow"

tasks:
  - id: plan
    type: agent
    agent: planner
    prompt: "Create research plan for: {{topic}}"
  
  - id: research
    type: agent
    agent: researcher
    depends_on: [plan]
    prompt: "Research: {{plan.output}}"
```

```python
from framework.workflows.engine import WorkflowEngine

engine = WorkflowEngine(settings, agent_registry)

# Load workflow
await engine.load_workflow("workflows/research.yaml")

# Execute
execution = await engine.execute_workflow(
    workflow_name="deep_research_workflow",
    input_data={"topic": "AI in Healthcare"}
)
```

## Integration Patterns

### Pattern 1: Custom MAF-Compliant Agent

```python
from agent_framework import BaseAgent, AgentRunResponse, ChatMessage, Role, TextContent
from typing import Any, AsyncGenerator

class AIResearchAgent(BaseAgent):
    """Custom agent that uses Azure OpenAI."""
    
    def __init__(self, name: str, azure_client, model: str):
        super().__init__(name=name, description="AI-powered researcher")
        self.azure_client = azure_client
        self.model = model
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent."""
        # 1. Normalize messages
        normalized = self._normalize_messages(messages)
        
        # 2. Get last message
        last_message = normalized[-1] if normalized else None
        content = last_message.text if last_message else ""
        
        # 3. Process with Azure OpenAI
        response = await asyncio.to_thread(
            self.azure_client.chat.completions.create,
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a researcher."},
                {"role": "user", "content": content}
            ]
        )
        
        result_text = response.choices[0].message.content
        
        # 4. Create response message
        response_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text=result_text)]
        )
        
        # 5. Notify thread (if provided)
        if thread:
            await self._notify_thread_of_new_messages(
                thread, normalized, response_message
            )
        
        return AgentRunResponse(messages=[response_message])
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncGenerator[AgentRunResponseUpdate, None]:
        """Stream responses."""
        # Get complete response
        response = await self.run(messages, thread=thread, **kwargs)
        
        # Yield as update
        for message in response.messages:
            if message.contents:
                for content in message.contents:
                    yield AgentRunResponseUpdate(
                        contents=[content],
                        role=Role.ASSISTANT
                    )
```

### Pattern 2: Using Agents in Orchestrator

```python
# Register agent
await agent_registry.register_agent(
    agent_id="researcher",
    agent_instance=AIResearchAgent(
        name="Research Agent",
        azure_client=azure_client,
        model="gpt-4"
    )
)

# Use in orchestrator
result = await orchestrator.execute_sequential(
    task="Research AI trends",
    agent_ids=["researcher"],
    tools=[]
)
```

### Pattern 3: Building Workflows Programmatically

```python
async def execute_research_workflow(orchestrator, topic):
    """Execute research using orchestrator + MAF."""
    
    # Phase 1: Sequential planning
    plan_result = await orchestrator.execute_sequential(
        task=f"Create research plan for: {topic}",
        agent_ids=["planner"],
        tools=[]
    )
    
    # Phase 2: Parallel research
    research_tasks = [
        ("concepts", "Research core concepts"),
        ("trends", "Research current trends"),
        ("applications", "Research applications")
    ]
    
    async def research_task(key, prompt):
        result = await orchestrator.execute_sequential(
            task=prompt,
            agent_ids=["researcher"],
            tools=[]
        )
        return (key, result["results"][0]["content"])
    
    # Run in parallel
    research_results = await asyncio.gather(
        *[research_task(k, p) for k, p in research_tasks]
    )
    
    # Phase 3: Sequential synthesis
    synthesis_result = await orchestrator.execute_sequential(
        task=f"Synthesize: {research_results}",
        agent_ids=["writer", "reviewer"],
        tools=[]
    )
    
    return synthesis_result
```

## Best Practices

### 1. Agent Implementation

✅ **DO:**
- Extend `BaseAgent`
- Implement both `run()` and `run_stream()`
- Use `ChatMessage` with `contents` list
- Handle `None` messages gracefully
- Notify thread when provided

❌ **DON'T:**
- Use `content` parameter (use `contents`)
- Return plain strings (use `AgentRunResponse`)
- Forget to implement `run_stream()`
- Ignore thread parameter

### 2. Workflow Building

✅ **DO:**
- Use orchestrator for pattern-based execution
- Register agents in registry first
- Handle `WorkflowRunResult` as a list
- Check for `WorkflowOutputEvent` in results
- Use `event.source_executor_id` for agent tracking

❌ **DON'T:**
- Use duplicate agent instances
- Pass less than 2 agents to ConcurrentBuilder
- Use `async for` on `workflow.run()` result
- Access `event.source` (use `source_executor_id`)

### 3. Message Handling

✅ **DO:**
```python
# Create messages correctly
message = ChatMessage(
    role=Role.USER,
    contents=[TextContent(text="content")]
)

# Access content
text = message.text  # Use .text property
```

❌ **DON'T:**
```python
# Wrong - no 'content' parameter
message = ChatMessage(role=Role.USER, content="text")

# Wrong - accessing .content attribute
text = message.content  # Doesn't exist
```

## Troubleshooting

### Common Issues

**Issue:** `'ChatMessage' object has no attribute 'content'`
**Solution:** Use `message.text` property or `message.contents` list

**Issue:** `'async for' requires an object with __aiter__ method`
**Solution:** `workflow.run()` returns a list, use regular `for` loop

**Issue:** `Duplicate agent participant detected`
**Solution:** Don't reuse same agent instance in one workflow, create new instances or use sequential execution per task

**Issue:** `FanOutEdgeGroup must contain at least two targets`
**Solution:** ConcurrentBuilder requires minimum 2 agents

## Summary

**Microsoft Agent Framework provides:**
- Agent protocol and base classes
- Sequential and concurrent workflow builders
- Message structures and conversation threading
- Workflow execution engine

**Foundation Framework adds:**
- High-level orchestration patterns
- Agent registry and lifecycle management
- Security and monitoring
- ReAct and advanced patterns
- YAML workflow engine

Together, they provide a complete platform for building enterprise AI agent applications.

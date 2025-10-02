# Framework Architecture

## System Overview

The Magentic Foundation Framework is designed as a layered architecture that extends Microsoft Agent Framework with enterprise orchestration, security, and monitoring capabilities.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  (Your AI Applications - e.g., Deep Research App)                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│              Magentic Foundation Framework                       │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Orchestration Layer                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│  │  │ Orchestrator │  │   Patterns   │  │   Planning   │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Core Services                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│  │  │   Registry   │  │   Security   │  │  Monitoring  │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                Workflow & Integration                    │   │
│  │  ┌──────────────┐  ┌──────────────┐                    │   │
│  │  │    Workflow  │  │     MCP      │                    │   │
│  │  │    Engine    │  │  Integration │                    │   │
│  │  └──────────────┘  └──────────────┘                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│              Microsoft Agent Framework                           │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Agent        │  │  Workflow    │  │  Message     │         │
│  │ Protocol     │  │  Builders    │  │  Types       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Orchestrator (`framework/core/orchestrator.py`)

The central coordination engine that manages agent execution and pattern implementation.

**Responsibilities:**
- Execute orchestration patterns
- Manage MAF workflow lifecycle
- Coordinate agent interactions
- Handle context propagation
- Implement retry logic

**Key Methods:**
```python
class MagenticOrchestrator:
    async def execute(
        task: str,
        pattern: Union[str, BasePattern],
        agents: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> ExecutionContext
    
    async def execute_sequential(
        task: str,
        agent_ids: List[str],
        tools: Optional[List[str]] = None
    ) -> Dict[str, Any]
    
    async def execute_concurrent(
        task: str,
        agent_ids: List[str],
        tools: Optional[List[str]] = None
    ) -> Dict[str, Any]
```

**Integration with MAF:**
```python
# Orchestrator creates MAF workflows internally
builder = SequentialBuilder()
builder = builder.participants(agent_instances)
workflow = builder.build()

# Executes with proper message formatting
messages = [ChatMessage(role=Role.USER, contents=[TextContent(text=task)])]
workflow_run = await workflow.run(messages)

# Processes MAF events
for event in workflow_run:
    if isinstance(event, WorkflowOutputEvent):
        # Extract results
        last_message = event.data[-1]
        content = last_message.text
```

### 2. Agent Registry (`framework/core/registry.py`)

Centralized management system for agent lifecycle and discovery.

**Responsibilities:**
- Store agent instances
- Manage agent metadata
- Handle agent discovery
- Track agent health
- Support dynamic registration

**Architecture:**
```python
class AgentRegistry:
    """
    Registry Structure:
    {
        "agent_id": {
            "instance": BaseAgent,
            "metadata": {
                "role": "researcher",
                "priority": "high",
                "capabilities": ["web_search", "analysis"]
            },
            "health": {
                "status": "healthy",
                "last_check": "2025-10-02T04:00:00Z"
            },
            "stats": {
                "total_executions": 42,
                "avg_duration": 2.5
            }
        }
    }
    """
    
    async def register_agent(
        agent_id: str,
        agent_instance: BaseAgent,
        metadata: Optional[Dict] = None
    ) -> None
    
    async def get_agent(agent_id: str) -> Optional[BaseAgent]
    
    async def list_agents(
        filter_by: Optional[Dict] = None
    ) -> List[Dict[str, Any]]
    
    async def unregister_agent(agent_id: str) -> None
```

**Usage Pattern:**
```python
# Register custom MAF agent
agent = AIResearchAgent(name="Researcher", azure_client=client)
await registry.register_agent(
    agent_id="researcher",
    agent_instance=agent,
    metadata={
        "role": "research",
        "tools": ["tavily_search"],
        "model": "gpt-4"
    }
)

# Retrieve for orchestration
agent = await registry.get_agent("researcher")
```

### 3. Security Manager (`framework/core/security.py`)

Enterprise-grade security controls for agent operations.

**Responsibilities:**
- Authentication & authorization
- Permission management
- Audit logging
- Data encryption
- Rate limiting

**Architecture:**
```python
class SecurityManager:
    async def check_permission(
        user_id: str,
        action: str,
        resource: str
    ) -> bool
    
    async def audit_log(
        action: str,
        user_id: str,
        resource: str,
        details: Dict[str, Any]
    ) -> None
    
    async def encrypt_data(data: bytes) -> bytes
    async def decrypt_data(encrypted: bytes) -> bytes
```

**Security Model:**
```
User → Role → Permissions → Resources

Example:
user_123 → researcher_role → [execute_workflow, read_data] → research_workflows
```

### 4. Monitoring Service (`framework/core/monitoring.py`)

Comprehensive observability for agent systems.

**Responsibilities:**
- Execution tracking
- Performance metrics
- Error tracking
- Resource usage
- Custom events

**Metrics Collected:**
```python
{
    "execution_metrics": {
        "total_executions": 1000,
        "success_rate": 0.95,
        "avg_duration": 3.2,
        "p95_duration": 5.1,
        "p99_duration": 8.3
    },
    "agent_metrics": {
        "agent_id": "researcher",
        "executions": 250,
        "avg_duration": 2.8,
        "error_rate": 0.02
    },
    "pattern_metrics": {
        "sequential": 600,
        "concurrent": 300,
        "react": 100
    }
}
```

### 5. Pattern Library (`framework/patterns/`)

Reusable orchestration patterns built on MAF.

**Available Patterns:**

#### Sequential Pattern (`patterns/sequential.py`)
```python
class SequentialPattern(BasePattern):
    """Execute agents in sequence, passing context."""
    
    agents: List[str]
    preserve_context: bool = True
    fail_fast: bool = False
    context_window_limit: int = 32000
```

**Use Cases:**
- Multi-step workflows
- Refinement pipelines
- Review chains

#### Concurrent Pattern (`patterns/concurrent.py`)
```python
class ConcurrentPattern(BasePattern):
    """Execute agents in parallel, aggregate results."""
    
    agents: List[str]
    aggregation_strategy: str = "merge"
    timeout: Optional[int] = None
```

**Use Cases:**
- Parallel research
- Multi-source analysis
- Independent tasks

#### ReAct Pattern (`patterns/react.py`)
```python
class ReactPattern(BasePattern):
    """Reasoning + Acting with tool use."""
    
    agent: str
    tools: List[str]
    max_iterations: int = 5
    think_aloud: bool = True
```

**Use Cases:**
- Research tasks
- Problem solving
- Tool-assisted reasoning

### 6. Workflow Engine (`framework/workflows/engine.py`)

YAML-based declarative workflow execution.

**Architecture:**
```python
class WorkflowEngine:
    """
    Workflow Execution Pipeline:
    1. Load YAML definition
    2. Parse and validate
    3. Build execution graph
    4. Resolve dependencies
    5. Execute tasks
    6. Aggregate results
    """
    
    async def load_workflow(path: str) -> WorkflowDefinition
    async def execute_workflow(
        workflow_name: str,
        input_data: Dict[str, Any]
    ) -> WorkflowExecution
```

**Workflow Structure:**
```yaml
name: my_workflow
version: "1.0"

variables:
  - name: topic
    type: string
    required: true

tasks:
  - id: task1
    type: agent
    agent: planner
    prompt: "Plan for: {{topic}}"
  
  - id: task2
    type: agent
    agent: researcher
    depends_on: [task1]
    prompt: "Research: {{task1.output}}"
```

### 7. MCP Integration (`framework/mcp_integration/`)

Model Context Protocol support for dynamic tool integration.

**Components:**
- **MCP Client**: Connects to MCP servers
- **MCP Server**: Exposes agent capabilities
- **Tool Registry**: Manages available tools

**Architecture:**
```python
class MCPClient:
    async def connect_to_server(server_url: str) -> None
    async def list_tools() -> List[ToolDefinition]
    async def call_tool(
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any

class MCPServer:
    async def register_tool(
        name: str,
        handler: Callable,
        schema: Dict[str, Any]
    ) -> None
```

## Data Flow

### Typical Execution Flow

```
1. Application Request
   │
   ├─→ Orchestrator.execute(task, pattern)
   │
2. Pattern Processing
   │
   ├─→ Resolve agents from Registry
   ├─→ Check permissions (Security)
   ├─→ Start monitoring (Monitoring)
   │
3. MAF Workflow Creation
   │
   ├─→ Create SequentialBuilder/ConcurrentBuilder
   ├─→ Add agent participants
   ├─→ Build workflow
   │
4. Workflow Execution
   │
   ├─→ Create ChatMessage with task
   ├─→ workflow.run(messages)
   ├─→ Process WorkflowOutputEvents
   │
5. Agent Execution (per agent)
   │
   ├─→ agent.run(messages)
   ├─→ Process with AI/Tools
   ├─→ Return AgentRunResponse
   │
6. Result Aggregation
   │
   ├─→ Collect all agent outputs
   ├─→ Format results
   ├─→ Update monitoring metrics
   │
7. Return to Application
   │
   └─→ ExecutionContext with results
```

### Message Flow (Sequential Pattern)

```
User Input
   │
   ▼
ChatMessage(role=USER, contents=[TextContent("Research AI")])
   │
   ▼
Agent 1 (Planner)
   │
   ├─→ Processes: "Research AI"
   ├─→ Returns: ChatMessage(role=ASSISTANT, contents=[TextContent("Plan: ...")])
   │
   ▼
Agent 2 (Researcher)
   │
   ├─→ Receives full context: [User message, Planner response]
   ├─→ Processes with context
   ├─→ Returns: ChatMessage(role=ASSISTANT, contents=[TextContent("Research: ...")])
   │
   ▼
Final Result: All conversation messages
```

## Configuration

### Settings Structure (`framework/config/settings.py`)

```python
class Settings(BaseModel):
    # Application
    app_name: str = "Magentic Framework"
    environment: str = "production"
    
    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str
    
    # Security
    enable_authentication: bool = True
    enable_authorization: bool = True
    enable_audit_log: bool = True
    
    # Monitoring
    enable_monitoring: bool = True
    metrics_retention_days: int = 30
    
    # Execution
    default_timeout: int = 300
    max_retries: int = 3
    retry_delay: int = 1
    
    # MCP
    mcp_servers: List[str] = []
```

## Extension Points

### 1. Custom Patterns

```python
from framework.patterns import BasePattern

class CustomPattern(BasePattern):
    """Your custom pattern."""
    
    # Define fields
    custom_param: str
    
    # Optional: override validation
    @field_validator('custom_param')
    def validate_param(cls, v):
        # Your validation
        return v
```

### 2. Custom Agents

See [Microsoft Agent Framework Integration](./msft-agent-framework.md#pattern-1-custom-maf-compliant-agent)

### 3. Custom Monitoring

```python
class CustomMonitoring(MonitoringService):
    async def track_custom_metric(self, name: str, value: float):
        # Your implementation
        pass
```

## Performance Considerations

### 1. Agent Instance Reuse

**Good:**
```python
# Reuse same agent instance across executions
agent = AIResearchAgent(...)
await registry.register_agent("researcher", agent)

# Use in multiple workflows
result1 = await orchestrator.execute_sequential(task1, ["researcher"])
result2 = await orchestrator.execute_sequential(task2, ["researcher"])
```

**Bad:**
```python
# Don't create new instances for each execution
for task in tasks:
    agent = AIResearchAgent(...)  # Wasteful
    result = await agent.run(task)
```

### 2. Parallel Execution

```python
# Use asyncio.gather for independent tasks
results = await asyncio.gather(
    orchestrator.execute_sequential(task1, ["agent1"]),
    orchestrator.execute_sequential(task2, ["agent2"]),
    orchestrator.execute_sequential(task3, ["agent3"])
)
```

### 3. Context Management

```python
# Limit context window in sequential patterns
pattern = SequentialPattern(
    agents=["agent1", "agent2", "agent3"],
    context_window_limit=32000  # Prevent token overflow
)
```

## Summary

The Magentic Foundation Framework architecture provides:

1. **Clean separation of concerns** - Each component has a single responsibility
2. **MAF integration** - Leverages Microsoft Agent Framework while adding value
3. **Extensibility** - Custom patterns, agents, and monitoring
4. **Production-ready** - Security, monitoring, error handling
5. **Developer-friendly** - Clear APIs and documentation

See [Orchestration Patterns](./patterns.md) for pattern implementation details.

# Foundational Framework

An enterprise-grade multi-agent foundational framework built on top of **Microsoft Agent Framework**, designed to provide robust, multi-modal orchestration capabilities for building advanced AI applications.

**Latest Updates (October 2025):**
- ✅ **MAF Observability** - Native OpenTelemetry integration
- ✅ **Hybrid MCP** - Both MAF and custom MCP implementations
- ✅ **MAF Workflows** - Graph-based workflow execution

## 🏗️ Architecture Overview

The Foundation Framework is designed as a comprehensive foundation for building sophisticated multi-agent applications with:

- **Multi-Agent Orchestration**: Support for complex agent collaboration patterns
- **Three Workflow Paradigms**: YAML declarative, code-based, and MAF graph-based
- **Dual MCP Integration**: MAF's simple client + our advanced server hosting
- **Dynamic Plan Updating**: ReAct (Reasoning + Acting) pattern implementation
- **Agent Registry**: Dynamic agent discovery and management
- **Enterprise Security**: Containerized execution and secure communication
- **Native Observability**: OpenTelemetry with OTLP, Application Insights, VS Code AI Toolkit

## 🚀 Key Features

### 1. Three Workflow Execution Modes

#### **YAML Workflows** (Declarative)
Simple, configuration-driven workflows perfect for non-technical users:
```yaml
name: research_workflow
tasks:
  - id: plan
    type: agent
    agent: planner
  - id: research
    type: agent
    agent: researcher
    dependencies: [plan]
```

#### **Code-Based Workflows** (Programmatic)
Full programmatic control with framework patterns:
```python
from framework.patterns import SequentialPattern, ConcurrentPattern

# Execute with patterns
result = await orchestrator.execute(
    pattern=SequentialPattern(agents=["planner", "researcher"]),
    task="Research AI trends"
)
```

#### **MAF Workflows** (Graph-Based) ✨ NEW
Visual graph-based workflows with executors, fan-out/fan-in, and type-safe messages:
```python
from agent_framework import WorkflowBuilder

workflow = (
    WorkflowBuilder()
    .set_start_executor(planner)
    .add_fan_out_edges(planner, researchers)  # Parallel execution
    .add_fan_in_edges(researchers, synthesizer)  # Collect results
    .build()
)
```

**See:** `EXECUTION_MODES_COMPARISON.md` for detailed comparison

### 2. Hybrid MCP Integration

#### **MAF MCP** (External Servers)
Simple connection to external MCP servers:
```python
from framework.mcp_integration import MAFMCPAdapter

adapter = MAFMCPAdapter()
adapter.register_external_server(
    server_label="github",
    server_url="https://gitmcp.io/Azure/azure-rest-api-specs"
)
```

#### **Custom MCP** (Internal Hosting)
Host your own MCP servers with advanced features:
```python
from framework.mcp_integration import MCPServer

server = MCPServer(settings)

@server.register_tool(name="analyze")
async def analyze(data: str) -> dict:
    # Custom implementation
    return {"result": ...}

await server.start(port=8080)
```

**See:** `PHASE_2_MCP_ANALYSIS.md` for comparison and use cases

### 3. Native Observability (OpenTelemetry)

Built on Microsoft Agent Framework's OpenTelemetry integration:
```python
from framework.core.observability import ObservabilityService

observability = ObservabilityService(settings)
await observability.initialize()

# Automatic instrumentation for:
# - Agent runs
# - Chat completions
# - Tool calls
# - Custom spans
```

**Export to:**
- OTLP (OpenTelemetry Protocol)
- Azure Application Insights
- VS Code AI Toolkit
- Jaeger (local development)

**See:** `OBSERVABILITY_MIGRATION.md` for setup guide

### 4. Multi-Agent Orchestration Patterns

- **Sequential**: Chain-based execution with context passing
- **Concurrent**: Parallel agent execution with result aggregation  
- **ReAct**: Reasoning and acting with dynamic plan updates (custom)
- **Group Chat**: Multi-agent collaborative conversations (MAF wrapper) ✨ NEW
- **Handoff**: Dynamic agent delegation and routing (MAF wrapper) ✨ NEW
- **Hierarchical**: Manager-worker coordination (custom) ✨ NEW
- **MAF Workflows**: Graph-based with executors and edges ✨ NEW

### 5. Enterprise Features

- **Agent Registry**: Centralized agent management and discovery
- **Security**: Role-based access, audit trails, secure execution
- **Scalability**: Horizontal scaling with load balancing
- **Observability**: OpenTelemetry, metrics, tracing, logging
- **Configuration**: Environment-specific deployment configs

## 📁 Framework Structure

```
framework/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project configuration
├── docker-compose.yml                 # Development environment
├── core/                              # Core framework components
│   ├── orchestrator.py               # Main orchestration engine
│   ├── registry.py                   # Agent registry management
│   ├── planning.py                   # Dynamic planning engine
│   ├── security.py                   # Security and authentication
│   └── observability.py              # ✨ NEW: OpenTelemetry wrapper
├── agents/                           # Agent implementations
│   ├── base.py                       # Base agent class
│   └── factory.py                    # Agent factory
├── patterns/                         # Orchestration patterns
│   ├── sequential.py                # Sequential execution
│   ├── concurrent.py                # Parallel execution
│   ├── react.py                     # Reasoning + Acting (custom)
│   ├── group_chat.py                # ✨ NEW: Group chat (MAF wrapper)
│   ├── handoff.py                   # ✨ NEW: Agent handoffs (MAF wrapper)
│   └── hierarchical.py              # ✨ NEW: Manager-worker (custom)
├── mcp_integration/                 # Model Context Protocol
│   ├── client.py                    # Advanced MCP client (697 lines)
│   ├── server.py                    # Full MCP server (792 lines)
│   ├── tools.py                     # Tool registry (322 lines)
│   └── maf_adapter.py               # ✨ NEW: MAF MCP integration (446 lines)
├── workflows/                       # Declarative workflow engine
│   └── engine.py                    # YAML workflow execution
├── config/                          # Configuration management
│   └── settings.py                  # Settings with observability config
├── api/                            # REST API interface
│   └── service.py                  # FastAPI application
├── examples/                       # Usage examples
│   ├── basic_usage.py
│   ├── complete_usage.py
│   ├── workflow_usage.py
│   └── custom_research.py
├── docs/                           # Documentation
│   ├── getting_started.md
│   ├── architecture.md
│   └── deployment.md
└── tests/                          # Test suite
    ├── unit/
    └── integration/
```
├── deployment/                    # Deployment configurations
│   ├── docker/                   # Docker configurations
│   │   ├── Dockerfile
│   │   ├── agent.Dockerfile
│   │   └── mcp-tool.Dockerfile
│   ├── kubernetes/               # Kubernetes manifests
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── terraform/                # Infrastructure as Code
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── examples/                     # Usage examples
│   ├── __init__.py
│   ├── basic_usage.py           # Simple examples
│   ├── advanced_orchestration.py # Complex scenarios
│   ├── custom_agents.py         # Custom agent development
│   └── mcp_integration.py       # MCP tool integration
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── performance/             # Performance tests
└── docs/                        # Documentation
    ├── getting_started.md
    ├── architecture.md
    ├── agent_development.md
    ├── mcp_integration.md
    └── deployment.md
```

## 🔧 Quick Start

### Prerequisites
## 🔧 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (optional)
- Azure OpenAI or compatible LLM service
- Azure CLI (for authentication)

### Installation

1. **Clone and Setup**
```bash
cd framework
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit with your credentials:
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_DEPLOYMENT
```

3. **Initialize Observability** (Optional)

Choose one of three options:

**Option A: Local Jaeger (Development)**
```bash
# Start Jaeger
docker run -d --name jaeger \
  -p 16686:16686 -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Configure in .env
OBSERVABILITY_ENABLED=true
OBSERVABILITY_OTLP_ENDPOINT=http://localhost:4317

# View traces at http://localhost:16686
```

**Option B: Azure Application Insights (Production)**
```bash
# Configure in .env
OBSERVABILITY_ENABLED=true
OBSERVABILITY_APPLICATIONINSIGHTS_CONNECTION_STRING=<your-connection-string>
```

**Option C: VS Code AI Toolkit (Development)**
```bash
# Configure in .env
OBSERVABILITY_ENABLED=true
OBSERVABILITY_VS_CODE_EXTENSION_PORT=51000
```

See `OBSERVABILITY_MIGRATION.md` for detailed setup.

4. **Run Examples**
```bash
# Basic usage
python examples/basic_usage.py

# Complete workflow example
python examples/complete_usage.py

# Custom research workflow
python examples/custom_research.py
```

## 🎯 Usage Examples

### Example 1: YAML-Based Workflow (Simple)

```python
from framework.workflows.engine import WorkflowEngine
from framework.config.settings import Settings

# Initialize
engine = WorkflowEngine(Settings())
await engine.load_workflow("workflows/research_workflow.yaml")

# Execute
execution_id = await engine.execute_workflow(
    workflow_name="research_workflow",
    variables={"topic": "AI trends"}
)

# Get status
status = await engine.get_execution_status(execution_id)
```

### Example 2: Code-Based Workflow (Programmatic)

```python
from framework.core.orchestrator import MagenticOrchestrator
from framework.patterns import SequentialPattern

orchestrator = MagenticOrchestrator()

# Sequential execution
result = await orchestrator.execute(
    pattern=SequentialPattern(agents=["planner", "researcher", "writer"]),
    task="Create market analysis report"
)

# Concurrent execution
from framework.patterns import ConcurrentPattern

results = await orchestrator.execute(
    pattern=ConcurrentPattern(agents=["researcher1", "researcher2", "researcher3"]),
    task="Research from multiple angles"
)
```

### Example 3: MAF Workflow (Graph-Based) ✨ NEW

```python
from agent_framework import WorkflowBuilder, Executor, handler
from dataclasses import dataclass

# Define message types
@dataclass
class Request:
    topic: str

@dataclass
class Plan:
    areas: List[str]

# Define executors (graph nodes)
class PlannerExecutor(Executor):
    @handler
    async def run(self, request: Request, ctx: WorkflowContext[Plan]):
        plan = await self.create_plan(request.topic)
        await ctx.send_message(plan)

class ResearchExecutor(Executor):
    @handler
    async def run(self, plan: Plan, ctx: WorkflowContext[Findings]):
        findings = await self.research(plan)
        await ctx.send_message(findings)

# Build workflow graph
workflow = (
    WorkflowBuilder()
    .set_start_executor(planner)
    .add_fan_out_edges(planner, researchers)  # Parallel
    .add_fan_in_edges(researchers, synthesizer)  # Collect
    .build()
)

# Execute
async for event in workflow.run_stream(Request(topic="AI")):
    print(f"Event: {event}")
```

See `EXECUTION_MODES_COMPARISON.md` for detailed comparison of all three modes.

### Example 4: Hybrid MCP Usage

```python
from framework.mcp_integration import MAFMCPAdapter, MCPServer

# External servers via MAF (simple)
external = MAFMCPAdapter()
external.register_external_server(
    server_label="github",
    server_url="https://gitmcp.io/Azure/azure-rest-api-specs"
)

# Internal server via our MCP (advanced)
internal = MCPServer(settings)

@internal.register_tool(name="company_search")
async def company_search(query: str, context: dict) -> dict:
    # Custom implementation with security, analytics, etc.
    return {"results": [...]}

await internal.start(port=8081)

# Agent uses both
agent = create_agent(
    external_tools=external.get_tool_definitions("github"),
    internal_tools=internal.get_tool_definitions()
)
```

### Example 5: Observability

```python
from framework.core.observability import ObservabilityService

observability = ObservabilityService(settings)
await observability.initialize()

# Custom spans
with observability.start_span("custom_operation") as span:
    span.set_attribute("user_id", "123")
    result = await do_work()

# Custom metrics
observability.record_metric(
    "custom.metric",
    value=42,
    attributes={"component": "research"}
)

# Automatic instrumentation for agents, chats, tools
# No manual tracing needed!
```
    tools=["web_search", "data_analysis", "report_generator"],
    max_iterations=10
)

# Execute with dynamic planning
result = await orchestrator.execute(
    pattern=react_pattern,
    task="Analyze competitive landscape and recommend strategic positioning"
)
```

### MCP Tool Integration
```python
from magentic_foundation.mcp import MCPToolRegistry

# Register MCP tools
tool_registry = MCPToolRegistry()
await tool_registry.register_server("https://tools.example.com/mcp")

# Use tools in orchestration
result = await orchestrator.execute_with_tools(
    task="Process customer data and generate insights",
    tools=["customer_db", "analytics_engine", "report_builder"]
)
```

### Declarative Workflows
```yaml
# workflows/templates/market_analysis.yaml
name: "Market Analysis Workflow"
version: "1.0"
description: "Comprehensive market analysis with competitive intelligence"

agents:
  - name: "market_researcher"
    role: "researcher"
    tools: ["web_search", "market_data_api"]
  
  - name: "data_analyst" 
    role: "analyst"
    tools: ["data_processing", "visualization"]
    
  - name: "report_writer"
    role: "writer"
    tools: ["document_generator", "template_engine"]

workflow:
  - step: "research"
    agent: "market_researcher"
    task: "Gather market intelligence and competitive data"
    
  - step: "analysis"
    agent: "data_analyst"
    task: "Process and analyze collected data"
    depends_on: ["research"]
    
  - step: "reporting"
    agent: "report_writer"
    task: "Generate comprehensive market analysis report"
    depends_on: ["analysis"]
```

## 🔐 Security Features

- **Role-Based Access Control**: Granular permissions for agents and tools
- **Audit Logging**: Comprehensive execution tracking via OpenTelemetry
- **Container Isolation**: MCP tools run in isolated containers
- **Encrypted Communication**: TLS for all inter-service communication
- **Secret Management**: Secure credential storage and rotation

## 📊 Monitoring & Observability

### Built on OpenTelemetry

The framework uses Microsoft Agent Framework's native OpenTelemetry integration:

- **Automatic Instrumentation**: Agents, chats, tool calls
- **Distributed Tracing**: End-to-end execution tracking
- **Metrics Collection**: Performance, usage, error rates
- **Structured Logging**: Centralized logs with context
- **Multiple Exporters**: OTLP, Application Insights, VS Code

### Export Options

**1. OTLP (OpenTelemetry Protocol)**
- Compatible with Jaeger, Zipkin, Prometheus
- Standard protocol for observability data

**2. Azure Application Insights**
- Native Azure integration
- Application Performance Management
- Log Analytics workspace integration

**3. VS Code AI Toolkit**
- Local development and debugging
- Real-time trace visualization
- Agent interaction insights

See `OBSERVABILITY_MIGRATION.md` for setup instructions.

## 🚀 Deployment

### Development
```bash
# Local development
python -m framework.main

# With Docker
docker-compose up
```

### Production (Azure)
```bash
# Deploy to Azure Container Apps
az containerapp up \
  --name magentic-framework \
  --resource-group my-rg \
  --environment my-env \
  --source .
```

### Infrastructure (Terraform)
```bash
cd deployment/terraform
terraform init
terraform apply
```

## 📚 Documentation

### Framework Documentation
- **Architecture & Design**: `docs/framework/architecture.md`
- **Pattern Reference**: `docs/framework/pattern-reference.md` - All 7 patterns with financial services use cases
- **Microsoft Agent Framework Integration**: `docs/framework/msft-agent-framework.md`
- **MCP Integration**: Hybrid approach with MAF adapter + custom server
- **Execution Modes**: YAML, Code-based, MAF Workflows (see `EXECUTION_MODES_COMPARISON.md`)

### Getting Started
- **Quick Start**: `docs/README.md`
- **API Reference**: Framework API documentation
- **Developer Guides**: Agent development, workflow authoring, security

### Reference Application
- **Deep Research App**: `deep_research_app/README.md`
- Demonstrates all three workflow modes
- Complete reference implementation with financial services examples

## 🆕 What's New (October 2025)

### Three Workflow Execution Modes
- **YAML Workflows**: Declarative, configuration-driven (no code required)
- **Code-Based Patterns**: Programmatic control with 7 orchestration patterns
- **MAF Workflows**: Graph-based with visual design and type-safe messaging

### 7 Orchestration Patterns
1. **Sequential** - Linear task chains
2. **Concurrent** - Parallel execution
3. **ReAct** - Reasoning + Acting with dynamic planning
4. **Group Chat** - Multi-agent collaborative discussions
5. **Handoff** - Dynamic agent-to-agent delegation
6. **Hierarchical** - Manager-worker coordination
7. **MAF Workflows** - Graph-based with executors

### Native Observability
- OpenTelemetry-based automatic instrumentation
- OTLP, Application Insights, VS Code AI Toolkit support
- Zero-code tracing for agents, chats, tools

### Hybrid MCP Integration
- MAF MCP adapter for external servers
- Custom MCP server for internal hosting
- Best of both approaches

## 🔗 Quick Links

- **Pattern Reference**: `docs/framework/pattern-reference.md` - Complete guide with financial services examples
- **Framework Documentation**: `docs/README.md`
- **Reference App**: `deep_research_app/README.md`
- **Execution Modes Comparison**: `EXECUTION_MODES_COMPARISON.md`

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) - Core orchestration and observability
- [OpenTelemetry](https://opentelemetry.io/) - Observability standard
- [Model Context Protocol](https://modelcontextprotocol.io/) - Tool integration standard
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) - LLM capabilities

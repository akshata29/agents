# Foundation Framework Documentation

## Overview

The Foundation Framework is an enterprise-grade, orchestration framework built on top of Microsoft Agent Framework. It provides advanced multi-agent coordination, execution patterns, security controls, and monitoring capabilities for building sophisticated AI applications.

## Documentation Structure

### Framework Documentation
- **[Architecture Overview](./framework/architecture.md)** - System architecture and design principles
- **[Pattern Reference](./framework/pattern-reference.md)** - Complete guide to all 7 orchestration patterns with financial services use cases
- **[Core Components](./framework/core-components.md)** - Registry, Orchestrator, Security, Observability
- **[Microsoft Agent Framework Integration](./framework/msft-agent-framework.md)** - How we leverage and extend MAF
- **[MCP Integration](./framework/mcp-integration.md)** - Model Context Protocol support
- **[Workflow Engine](./framework/workflow-engine.md)** - YAML-based declarative workflows
- **[API Reference](./framework/api-reference.md)** - Complete API documentation

### Developer Guides
- **[Getting Started](./guides/getting-started.md)** - Quick start guide
- **[Building Custom Agents](./guides/custom-agents.md)** - Creating MAF-compliant agents
- **[Implementing Patterns](./guides/implementing-patterns.md)** - Using orchestration patterns
- **[YAML Workflows](./guides/yaml-workflows.md)** - Declarative workflow authoring
- **[Security & Compliance](./guides/security.md)** - Security best practices
- **[Production Deployment](./guides/deployment.md)** - Deployment strategies

### Reference Application
- **[Deep Research App Overview](./reference-app/overview.md)** - Application architecture
- **[Pattern Implementation](./reference-app/patterns.md)** - How patterns are used
- **[Backend Implementation](./reference-app/backend.md)** - FastAPI backend details
- **[Frontend Implementation](./reference-app/frontend.md)** - React frontend details
- **[Dual Execution Modes](./reference-app/execution-modes.md)** - YAML vs Code-based
- **[Building Your Own](./reference-app/building-your-own.md)** - Step-by-step guide

## Quick Links

- [Installation & Setup](./guides/getting-started.md#installation)
- [Framework Architecture](./framework/architecture.md)
- [Pattern Examples](./framework/patterns.md#examples)
- [Deep Research App Tutorial](./reference-app/building-your-own.md)

## Key Features

### Framework Core
- **Enterprise Orchestration**: Multi-agent coordination
- **Microsoft Agent Framework Integration**: Full MAF compliance with enhancements
- **7 Orchestration Patterns**: Sequential, Concurrent, ReAct, Group Chat, Handoff, Hierarchical, MAF Workflows
- **Security & Observability**: Built-in security controls and OpenTelemetry-based observability
- **MCP Support**: Dynamic tool integration via Model Context Protocol
- **Workflow Engine**: YAML-based declarative workflow definitions

### Framework Enhancements Over Microsoft Agent Framework
1. **Orchestration Layer**: High-level coordination beyond basic workflows
2. **Pattern Library**: 7 battle-tested patterns including ReAct, Hierarchical, Group Chat
3. **Agent Registry**: Centralized agent lifecycle management
4. **Security Module**: Authentication, authorization, audit logging
5. **Dynamic Planning**: AI-powered workflow generation
6. **Observability Service**: OpenTelemetry integration with Application Insights & VS Code AI Toolkit

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                 Foundation Framework                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Orchestrator │  │   Registry   │  │   Security   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│  ┌──────▼──────────────────▼──────────────────▼───────┐    │
│  │           Microsoft Agent Framework                  │    │
│  │  ┌────────────────────────────────────────────┐    │    │
│  │  │  SequentialBuilder | ConcurrentBuilder     │    │    │
│  │  │  Workflow | AgentProtocol | ChatMessage    │    │    │
│  │  └────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Patterns   │  │   Workflow   │  │     MCP      │      │
│  │   Library    │  │    Engine    │  │  Integration │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │   Your Application      │
              │  (e.g., Deep Research)  │
              └─────────────────────────┘
```

## Getting Started

```bash
# Clone the repository
git clone https://github.com/yourusername/foundation-framework.git
cd foundation-framework

# Install dependencies
pip install -e .

# Run the reference application
cd deep_research_app/backend
python app/main.py
```

See [Getting Started Guide](./guides/getting-started.md) for detailed instructions.

## Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details.

## License

[Your License Here]


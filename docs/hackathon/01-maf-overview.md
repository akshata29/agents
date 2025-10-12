# Microsoft Agent Framework Overview

## Why MAF

Microsoft Agent Framework (MAF) gives you a consistent way to describe, run, and observe multi-agent systems. It provides type-safe message contracts, workflow builders, and pluggable tools so you can focus on business logic rather than orchestration plumbing. Every application in this repository—Deep Research, Multimodal Insights, Advisor Productivity, FinAgent, FinAgent Dynamic, and the Patterns Sandbox—leans on those primitives.

## Core Building Blocks

| Concept | What it Represents | Notes |
| --- | --- | --- |
| **Agent** | A component that can receive and emit `ChatMessage` payloads | Implement `run` / `run_stream`; often wraps Azure OpenAI or another service |
| **Tool** | A callable capability exposed to agents | MCP servers, REST clients, or local utilities |
| **Workflow Builder** | Fluent API that wires agents together | Sequential, Concurrent, Group Chat, Handoff, Magentic, Deep Research builders are used across the portfolio |
| **Workflow Run** | Executable instance returned by a builder | Streams `WorkflowEvent` objects you can log or display |
| **Conversation / Thread** | Context wrapper around a series of messages | Lets you resume or replay an execution |

## Runtime Architecture

```
MAF Workflow Builder
    ├─ Participants (Agents)
    ├─ Tools (MCP / REST / SDK)
    └─ Settings (timeouts, metadata)
          │
          ▼
Workflow Run (Async iterator of events)
    ├─ Token / trace updates
    ├─ Tool invocations
    └─ Final responses + artifacts
```

Across the reference apps:
- **Deep Research** uses Sequential + Concurrent builders to mix planning, research, and synthesis
- **Patterns Sandbox** surfaces every builder with UI toggles for experimentation
- **FinAgent Dynamic** layers a planner ahead of Sequential execution to insert human approvals
- **Multimodal Insights** uses Sequential workflows combined with custom steps for multimodal preprocessing

## Working with Agents

1. **Define the agent** – inherit from `BaseAgent`, normalize messages, and call out to Azure OpenAI or a domain API
2. **Register tools** – when the agent needs structured data, wire MCP servers or helper classes
3. **Emit telemetry** – bubble intermediate messages to the UI, Application Insights, or logs for observability
4. **Keep responsibilities narrow** – each agent handles one concern (plan, gather data, summarize, validate)

Minimal template:

```python
from agent_framework import BaseAgent, AgentRunResponse, ChatMessage, Role, TextContent

class SummaryAgent(BaseAgent):
    def __init__(self, client, deployment):
        super().__init__(name="Summary Agent", description="Creates executive summaries")
        self.client = client
        self.deployment = deployment

    async def run(self, messages=None, *, thread=None, **kwargs) -> AgentRunResponse:
        prompt = self._normalize_messages(messages)[-1].text
        completion = await self.client.responses.create(
            model=self.deployment,
            input=[{"role": "system", "content": "You are a concise summarizer."},
                   {"role": "user", "content": prompt}]
        )
        output = completion.output_text
        response = ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=output)])
        return AgentRunResponse(messages=[response])
```

## Message Types You Will See

- `ChatMessage` – base payload carrying role + contents
- `ToolCallMessage` / `ToolResultMessage` – emitted when an agent invokes a tool
- `WorkflowOutputEvent` – event raised by the run iterator; final item carries aggregated results
- `WorkflowTokenCountEvent` – helpful for tracking cost and applying limits

## Recommended Learning Path

1. Clone the repository and run the Patterns Sandbox to watch each builder in action
2. Read `docs/hackathon/03-orchestration-patterns.md` to understand when to apply each strategy
3. Study `docs/hackathon/04-agent-implementation.md` for guidance on writing production-quality agents
4. Open any app README to see how these concepts translate to real code

## External Resources

- [MAF GitHub Repository](https://github.com/microsoft/agent-framework)
- [MAF API Reference](https://microsoft.github.io/autogen/api)
- [Model Context Protocol](https://modelcontextprotocol.io/) for tool interoperability

---

Next: move to [02-framework-architecture.md](./02-framework-architecture.md) for a cross-app architecture blueprint grounded in the refreshed portfolio.

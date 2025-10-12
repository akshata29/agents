# Agent Implementation Guide

This guide distills current best practices for writing agents that plug into the refreshed Microsoft Agent Framework portfolio.

## Agent Lifecycle

1. **Initialization** – Capture dependencies (Azure OpenAI clients, REST clients, MCP tool handles) through constructor parameters.
2. **Execution** – Implement `run` (and optionally `run_stream`) to normalize incoming messages, call external services, and return `AgentRunResponse` objects.
3. **Telemetry** – Emit structured logs/metrics so orchestrators and dashboards can display progress.
4. **Persistence** – When needed, store artifacts (JSON, Markdown, binary) alongside the step metadata in Cosmos DB or Azure Storage.

## Baseline Template

```python
from agent_framework import BaseAgent, AgentRunResponse, ChatMessage, Role, TextContent

class PlanningAgent(BaseAgent):
    def __init__(self, client, deployment, system_prompt: str):
        super().__init__(name="Planning Agent", description="Creates execution plans")
        self.client = client
        self.deployment = deployment
        self.system_prompt = system_prompt

    async def run(self, messages=None, *, thread=None, **kwargs) -> AgentRunResponse:
        history = self._normalize_messages(messages)
        latest = history[-1].text if history else ""
        context = kwargs.get("context", {})
        composed_prompt = self._build_prompt(latest, context)

        response = await self.client.responses.create(
            model=self.deployment,
            input=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": composed_prompt},
            ],
            temperature=0.4,
            max_output_tokens=1800,
        )

        text = response.output_text
        message = ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=text)])
        return AgentRunResponse(messages=[message])

    def _build_prompt(self, objective: str, context: dict) -> str:
        prior_steps = "\n".join([f"- {item['summary']}" for item in context.get("session_context", [])])
        return (
            "You design execution plans.\n"
            f"Objective: {objective}\n"
            f"Prior context:\n{prior_steps}"
        )
```

## Prompt Engineering Tips

- Keep the **system message** fixed for a given agent; store it next to the code or in configuration.
- Pass structured context (lists, dicts) via kwargs and stringify inside `_build_prompt` so you can unit test prompt assembly.
- Annotate outputs with JSON when downstream steps expect structure—use `json.dumps` and clearly label the section.

## Tool Integration

### MCP Client

```python
from mcp import MCPClient

class CompanyAgent(BaseAgent):
    def __init__(self, mcp_client: MCPClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mcp_client = mcp_client

    async def _get_company_profile(self, ticker: str) -> dict:
        return await self.mcp_client.call_tool("get_stock_info", {"ticker": ticker})
```

Best practices:
- Cache MCP clients at startup; avoid reconnecting per request.
- Validate responses and guard against empty payloads so the UI can show friendly errors.

### REST/SDK Integrations

- Wrap third-party SDK calls in helper modules (see `finagent_dynamic_app/backend/app/helpers`).
- Handle rate limiting with retries and exponential backoff when the API allows.
- Convert raw data into concise summaries before passing to Azure OpenAI prompts.

## Context Management

- Use `dependency_artifacts` for data-gathering agents that only need explicit upstream outputs.
- Use `session_context` (see `finagent_dynamic_app/docs/SYNTHESIS_AGENT_PATTERN.md`) for synthesis agents that should see the full run history.
- Store large payloads (PDFs, JSON) in Azure Storage and pass references to avoid exceeding token budgets.

## Testing Strategies

- **Unit tests** – Mock Azure OpenAI responses and MCP clients; assert prompts and result parsing logic.
- **Integration smoke tests** – Hit FastAPI endpoints with sample payloads to confirm wiring.
- **Playwright/Cypress** (optional) – Validate front-end flows that depend on agent streaming.

## Telemetry

- Use `structlog` or `logging` with JSON renderers so Application Insights displays useful fields (`execution_id`, `agent`, `step_id`).
- Emit counters for success/failure and latency; the hackathon dashboards can surface them quickly.

## Reuse Checklist

- [ ] Constructor only accepts explicit dependencies (no module-level singletons)
- [ ] Prompts reside next to the agent code and are easy to tweak per customer
- [ ] Tool failures raise descriptive errors surfaced to the UI
- [ ] Agent outputs include both narrative text and machine-readable summaries when appropriate

Next: read [05-reference-apps.md](./05-reference-apps.md) to see how these patterns show up across the portfolio.

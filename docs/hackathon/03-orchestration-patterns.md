# Orchestration Pattern Catalogue

The refreshed documentation removes the legacy “Foundation Framework” terminology. This guide now maps directly to the MAF builders you can inspect in the repository.

## Pattern Summary

| Pattern | When to Use | Portfolio Examples | Key Considerations |
| --- | --- | --- | --- |
| **Sequential** | Tasks with hard dependencies or review loops | Deep Research (YAML mode), Advisor Productivity follow-up actions | Propagate context carefully; great for narrative workflows |
| **Concurrent** | Independent subtasks that can run in parallel | Deep Research (multi-search), FinAgent market data fetch | Aggregate results consistently; watch rate limits |
| **ReAct / Dynamic Planning** | Objectives where plan emerges after reading the request | FinAgent Dynamic planner, Multimodal Insights planner | Keep step prompts concise; add human approval gates |
| **Group Chat** | Collaborative agent discussions, perspective diversity | FinAgent static app, Patterns Sandbox | Provide roles + guardrails; moderate for tangents |
| **Handoff** | Escalating context between specialists | Patterns Sandbox, Advisor Productivity post-call pipeline | Ensure each agent writes structured outputs for the next |
| **Magentic / Deep Research** | YAML-defined multi-phase investigations | Deep Research YAML workflows | Great for hackathon scenarios where non-devs tweak flows |

## Picking the Right Pattern

1. **Do steps depend on previous results?** → Start with Sequential.
2. **Is the task heavy on data gathering from many sources?** → Consider Concurrent or combine Sequential → Concurrent → Sequential.
3. **Does the user need visibility and control?** → Add human approvals (Sequential + planner) or use Group Chat for live debate.
4. **Are you orchestrating tooling as well as agents?** → ReAct excels, especially with MCP + Azure OpenAI tool calling.

## Hybrid Recipes

- **Plan → Parallel → Synthesize** (Deep Research): `Sequential(planner) → Concurrent(search_agents) → Sequential(writer, reviewer)`
- **Planner + Human Approval** (FinAgent Dynamic): `PlannerAgent` writes a plan → user approves steps → Sequential execution
- **Multi-modal Insight Loop**: `Planner` checks files → `Sequential(multimodal_processor → sentiment → summarizer → analytics)` with optional `Concurrent` for data enrichment

## Code Snippets

### Sequential Builder

```python
from agent_framework.workflows import SequentialBuilder

builder = SequentialBuilder()
builder = builder.participants([planner_agent, writer_agent, reviewer_agent])
workflow = builder.build()

messages = planner_agent.format_request(user_prompt)
async for event in workflow.run(messages):
    if event.is_output:
        yield event.data[-1]
```

### Concurrent Builder

```python
from agent_framework.workflows import ConcurrentBuilder

builder = ConcurrentBuilder()
builder = builder.participants([fundamentals_agent, technicals_agent, sec_agent])
workflow = builder.build()

results = []
async for event in workflow.run(messages):
    if event.is_output:
        results.append(event.data[-1])
```

### ReAct-Inspired Planner

```python
plan = await planner_agent.plan(objective, available_tools)
for step in plan.steps:
    if require_approval:
        await approval_gateway.prompt(step)
        if not step.approved:
            continue
    result = await executor.run(step)
    await history_store.save(step, result)
```

## Observability Tips

- Attach `execution_id` metadata to each workflow run; store it alongside Cosmos DB session entities
- Stream `WorkflowEvent` instances over WebSocket/SSE to power live dashboards
- Log tool calls and model usage separately: it simplifies post-hackathon cost analysis

## Further Reading

- `patterns/README.md` – contains the actual code that wires each builder
- `finagent_dynamic_app/docs/SYNTHESIS_AGENT_PATTERN.md` – example of layering context management on top of Sequential runs
- `docs/hackathon/06-hackathon-implementation.md` – maps patterns to project ideas

Next: explore [04-agent-implementation.md](./04-agent-implementation.md) to learn how to author agents that plug into these builders.

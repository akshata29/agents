# Synthesis Agent Pattern

## Purpose

Financial research requires agents that can both gather raw data and produce synthesized insights. The FinAgent Dynamic App uses a dual-context pattern so synthesis-oriented agents receive the full session history, while data-gathering agents stay lightweight and consume only explicit dependencies.

## Agent Classes

- **Data gathering** – Company, SEC, Earnings, Fundamentals, Technicals. They execute targeted calls (Yahoo Finance MCP, FMP, SEC) and only read `dependency_artifacts` derived from their declared prerequisites.
- **Synthesis** – Summarizer (and other future synthesis agents such as Forecaster/Report). They need holistic context and therefore read `session_context`, a chronological view of all completed steps.

## Implementation Overview

1. **Agent detection** – `TaskOrchestrator._is_synthesis_agent(step)` checks if the current agent belongs to the synthesis list (`[AgentType.SUMMARIZER, AgentType.REPORT, ...]`).
2. **Context assembly** –
   - Synthesis agents call `_get_session_context`, which retrieves every completed step earlier in the plan and serializes agent, tools, and outputs.
   - Data agents call `_get_dependency_artifacts` to load only the artifacts from their declared dependencies.
3. **Execution hook** – During `_execute_step` the orchestrator merges either `session_context` or `dependency_artifacts` into the payload passed to the agent implementation.
4. **Agent consumption** – Agents prioritize `session_context` but gracefully fall back to dependency artifacts for backward compatibility.

### Key Code Paths

```python
def _is_synthesis_agent(self, step: Step) -> bool:
    return step.agent in self._synthesis_agents

async def _get_session_context(self, step: Step) -> dict[str, Any]:
    steps = await self.cosmos.get_steps_by_plan(step.plan_id, step.session_id)
    completed = [s for s in steps if s.status == StepStatus.COMPLETED and s.order < step.order]
    return {"session_context": [self._serialize_step(s) for s in completed]}
```

```python
if self._is_synthesis_agent(step):
    context.update(await self._get_session_context(step))
elif step.dependencies:
    context.update(await self._get_dependency_artifacts(step))
```

## Benefits

- **Comprehensive synthesis** – Summaries and forecasts leverage every prior artifact without developers manually wiring dependencies.
- **Lean data steps** – Data gathering agents avoid large payloads and remain focused on the specific inputs they require.
- **Backwards compatibility** – Agents still support `dependency_artifacts`, allowing gradual rollout or mixed plans.
- **Reduced misconfiguration** – Fewer chances of missing a dependency link when new data steps are introduced.

## Example Sequence

```
1. Company Agent → get_stock_info
2. Company Agent → get_yahoo_finance_news
3. Fundamentals Agent → compute_ratios (depends on 1)
4. Summarizer Agent → synthesizes 

Session context delivered to Summarizer includes outputs from steps 1–3, ensuring recommendations reference fundamentals, news, and company metadata.
```

## Extending the Pattern

1. Add the new agent type to `_synthesis_agents` within `task_orchestrator.py`.
2. Update the agent implementation to read `session_context` first and extract the needed artifacts.
3. Include defensive fallbacks to `dependency_artifacts` for compatibility with legacy plans.

## Validation Checklist

- Create a multi-step plan that ends with the synthesis agent and inspect logs for `Added comprehensive session context` messages.
- Confirm the agent output references data from earlier steps (e.g., SEC insights plus technical signals).
- Run unit/integration tests covering both dependency-only and session-context paths.
- Verify Cosmos DB persists the expanded context payload for auditing.

This pattern keeps synthesis agents authoritative and context-aware while preserving performance for the rest of the pipeline.

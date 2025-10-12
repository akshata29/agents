# Deep Research Decision Guide

Use this guide when teams need help selecting execution modes, patterns, or extensions for their scenario.

## 1. Clarify the Desired Outcome

| Goal | Questions to Ask |
| --- | --- |
| Fast prototype | “Do you need code-free configuration? Who maintains the workflow after the event?” |
| Production signal | “What telemetry and persistence are required? Who will operate the app?” |
| Differentiated insight | “What sources or expert personas will deliver a unique perspective?” |

## 2. Choose an Execution Mode

| If you need… | Pick… | Why |
| --- | --- | --- |
| Rapid iteration, minimal code changes | **YAML Workflow** | Declarative, easy for analysts, matches quick start tasks. |
| Full control, complex branching | **Code Orchestration** | Python-first, straightforward to integrate new APIs or retries. |
| Observability, typed messages, fan-out graphs | **MAF Workflow** | Rich telemetry, explicit topology, ideal for demos and production stories. |

Tip: teams can start in YAML, then migrate to MAF once requirements stabilize.

## 3. Select Orchestration Patterns

| Scenario | Recommended Pattern |
| --- | --- |
| Need multiple perspectives quickly | Concurrent researchers + synthesizer |
| Quality gate before publishing | Sequential reviewer (and optional validator) |
| Tool-driven investigation | ReAct loop feeding MCP or REST tools |
| Iterative refinement | Loop planner/synthesizer until review score passes a threshold |

Reference [DEEP_RESEARCH_PATTERNS.md](./DEEP_RESEARCH_PATTERNS.md) for implementation details.

## 4. Decide on Data & Tools

- **Tavily** – Generic web search; low effort, broad coverage.
- **Custom MCP servers** – Domain-specific data (financials, policies, transcripts). Requires extra setup but differentiates demos.
- **Internal APIs** – Use `requests` or SDKs inside agents; remember to sanitize outputs before serialization.

Validate rate limits early and plan fallbacks (cached responses, reduced source counts) if quotas are tight.

## 5. Plan Telemetry & Persistence

| Requirement | Action |
| --- | --- |
| Need history replay | Configure `COSMOSDB_*` variables and run a smoke test. |
| Want end-to-end traces | Provide `OBSERVABILITY_APPLICATIONINSIGHTS_CONNECTION_STRING` and check Application Insights. |
| Light-touch logging | Use structured `logging` with `execution_id`, `agent`, and `step_id` fields. |

## 6. Final Check

- Execution mode aligns with skill set and demo story.
- Pattern choice supports the outcome (speed, quality, adaptability).
- Data sources and tools are provisioned and tested.
- Telemetry plan is in place, or you know why it is not needed.
- Team can articulate “why this approach” in under two minutes.

Once decisions are made, update your team notes or README so reviewers can follow the reasoning.

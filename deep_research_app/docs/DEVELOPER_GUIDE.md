# Developer Guidefrom agent_framework import (

    WorkflowBuilder,

Use this guide to tailor the Deep Research App, extend orchestration logic, and keep all execution modes aligned.    Executor,

    handler,

## Execution Modes        

        except Exception as e:

| Mode | Entry Point | Strengths | Choose When |            logger.error(f"Agent {agent_id} failed: {e}")

| --- | --- | --- | --- |            if attempt == max_retries - 1:

| YAML Workflow | `workflows/deep_research.yaml` | Low-code edits, declarative dependencies, predictable outputs | Business stakeholders or facilitators tweak flows without writing Python. |                raise

| Code Orchestration | `backend/app/services/code_mode_service.py` (or equivalent helper) | Fine-grained logic, custom retries, easy integration of new tools | Complex branching, specialized prompts, or tight API coordination. |# Developer Guide

| MAF Workflow | `backend/app/maf_workflow.py` | Type-safe graph, streaming events, rich telemetry hooks | Production scenarios or demos that demand observability and replayability. |

Use this guide to tailor the Deep Research App, extend orchestration logic, and keep all execution modes aligned.

All three paths emit identical `ExecutionStatus` responses so the UI and Cosmos DB history stay in sync.

## Execution Modes

### YAML Workflow Highlights

| Mode | Entry Point | Strengths | Choose When |

- Declare variables, dependencies, and fan-out in one place.| --- | --- | --- | --- |

- Use `${variable}` placeholders to pass context between tasks.| YAML Workflow | `workflows/deep_research.yaml` | Low-code edits, declarative dependencies, predictable outputs | Business stakeholders or facilitators tweak flows without writing Python. |

- Document new or modified tasks inline so operators know expected side effects.| Code Orchestration | `backend/app/services/code_mode_service.py` (or equivalent helper) | Fine-grained logic, custom retries, easy integration of new tools | Complex branching, specialized prompts, or tight API coordination. |

| MAF Workflow | `backend/app/maf_workflow.py` | Type-safe graph, streaming events, rich telemetry hooks | Production scenarios or demos that demand observability and replayability. |

### Code Orchestration Highlights

All three paths emit identical `ExecutionStatus` responses so the UI and Cosmos DB history stay in sync.

- Compose `execute_sequential`, `execute_concurrent`, and `execute_react` patterns directly in Python.

- Inject custom error handling (backoff, circuit breakers) around tool calls.### YAML Workflow Highlights

- Ideal for experimentation before promoting changes back into YAML or the MAF workflow.

- Declare variables, dependencies, and fan-out in one place.

### MAF Workflow Highlights- Use `${variable}` placeholders to pass context between tasks.

- Document new or modified tasks inline so operators know expected side effects.

- `WorkflowBuilder` ensures every executor receives typed payloads.

- Fan-out/fan-in behaviour is explicit, making scaling parallel researchers straightforward.### Code Orchestration Highlights

- Event streaming powers the Execution Monitor; include `summary`, `tokens_used`, and `sources` metadata to enrich the UI.

- Compose `execute_sequential`, `execute_concurrent`, and `execute_react` patterns directly in Python.

## Orchestration Patterns- Inject custom error handling (backoff, circuit breakers) around tool calls.

- Ideal for experimentation before promoting changes back into YAML or the MAF workflow.

| Pattern | Usage | Guidance |

| --- | --- | --- |### MAF Workflow Highlights

| Sequential | Planner → Writer → Reviewer chains | Great for staged approvals; keep each agent focused on one responsibility. |

| Concurrent | Researcher fan-out | Provide immutable context; aggregate results before persisting. |- `WorkflowBuilder` ensures every executor receives typed payloads.

| ReAct | Fact checking, investigative loops | Cap iterations, surface intermediate reasoning for debugging. |- Fan-out/fan-in behaviour is explicit, making scaling parallel researchers straightforward.

- Event streaming powers the Execution Monitor; include `summary`, `tokens_used`, and `sources` metadata to enrich the UI.

When introducing a new pattern, expose a feature flag or API switch so teams can A/B test without disrupting existing runs.

## Orchestration Patterns

## Extending the App

| Pattern | Usage | Guidance |

1. **Define the agent** – Create a class in `backend/app/agents/` and register it with the agent registry.| --- | --- | --- |

2. **Configure settings** – Add new environment variables to `settings.py` and `.env.example` so scripts remain reproducible.| Sequential | Planner → Writer → Reviewer chains | Great for staged approvals; keep each agent focused on one responsibility. |

3. **Update orchestration** – Wire the agent into YAML, code orchestration, and the MAF workflow to keep parity.| Concurrent | Researcher fan-out | Provide immutable context; aggregate results before persisting. |

4. **Adjust models** – Extend Pydantic schemas if new inputs or outputs travel across the API boundary.| ReAct | Fact checking, investigative loops | Cap iterations, surface intermediate reasoning for debugging. |

5. **Refresh docs** – Capture behaviour changes here or in the hackathon supplements so teams know how to exercise the feature.

When introducing a new pattern, expose a feature flag or API switch so teams can A/B test without disrupting existing runs.

## Persistence & Telemetry

## Extending the App

- Cosmos DB persistence (optional) lives in `persistence/cosmos_memory.py`. Extend `ALIAS_MAP` when you add new result sections.

- `save_execution_to_cosmos` snapshots workflow variables; verify new fields serialize cleanly.1. **Define the agent** – Create a class in `backend/app/agents/` and register it with the agent registry.

- Application Insights / OTLP exporters toggle via `OBSERVABILITY_*` flags. Emit structured logs including `execution_id`, `agent`, and `step_id`.2. **Configure settings** – Add new environment variables to `settings.py` and `.env.example` so scripts remain reproducible.

- Surface additional telemetry in the WebSocket payloads only after ensuring the frontend knows how to render them.3. **Update orchestration** – Wire the agent into YAML, code orchestration, and the MAF workflow to keep parity.

4. **Adjust models** – Extend Pydantic schemas if new inputs or outputs travel across the API boundary.

## Testing Checklist5. **Refresh docs** – Capture behaviour changes here or in the hackathon supplements so teams know how to exercise the feature.



- `pytest` backends with fixtures that stub Azure OpenAI and Tavily responses.## Persistence & Telemetry

- End-to-end smoke tests for each execution mode before committing significant changes.

- `npm run test` for frontend components that display new result sections or statuses.- Cosmos DB persistence (optional) lives in `persistence/cosmos_memory.py`. Extend `ALIAS_MAP` when you add new result sections.

- Optional load checks (Locust, k6) when modifying streaming behaviour or Cosmos persistence.- `save_execution_to_cosmos` snapshots workflow variables; verify new fields serialize cleanly.

- Application Insights / OTLP exporters toggle via `OBSERVABILITY_*` flags. Emit structured logs including `execution_id`, `agent`, and `step_id`.

## Helpful References- Surface additional telemetry in the WebSocket payloads only after ensuring the frontend knows how to render them.



- [ARCHITECTURE.md](ARCHITECTURE.md) for data flow and integration details.## Testing Checklist

- [QUICKSTART.md](QUICKSTART.md) for environment setup and troubleshooting.

- Hackathon materials in `../../docs/hackathon/DEEP_RESEARCH_*.md` for workshop-focused playbooks.- `pytest` backends with fixtures that stub Azure OpenAI and Tavily responses.

- `../scripts/dev.ps1` to launch backend, frontend, and shared MCP tooling in one command.- End-to-end smoke tests for each execution mode before committing significant changes.

- `npm run test` for frontend components that display new result sections or statuses.

Iterate incrementally, observe telemetry, and ensure every execution mode continues to emit the same canonical payloads.- Optional load checks (Locust, k6) when modifying streaming behaviour or Cosmos persistence.


## Helpful References

- [ARCHITECTURE.md](ARCHITECTURE.md) for data flow and integration details.
- [QUICKSTART.md](QUICKSTART.md) for environment setup and troubleshooting.
- Hackathon materials in `../../docs/hackathon/DEEP_RESEARCH_*.md` for workshop-focused playbooks.
- `../scripts/dev.ps1` to launch backend, frontend, and shared MCP tooling in one command.

Iterate incrementally, observe telemetry, and ensure every execution mode continues to emit the same canonical payloads.


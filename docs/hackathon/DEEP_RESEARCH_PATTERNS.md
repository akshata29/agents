# Deep Research Pattern Playbook

Use these patterns to evolve the baseline Deep Research workflow. Each idea builds on the planner → parallel researchers → synthesis loop shipped with the app.

## Baseline (Planner → Researchers → Synthesis → Review)

- Planner defines 3–5 investigation areas based on the topic and desired depth.
- Parallel researchers pull sources (Azure OpenAI + Tavily) and summarize findings.
- Synthesizer assembles a comprehensive report; reviewer validates tone, accuracy, and citation coverage.
- Optional summarizer creates an executive brief for stakeholders.

**Implementation Tips**
- YAML: modify `workflows/deep_research.yaml` to adjust task order or counts.
- Code mode: expand the sequential/concurrent helpers inside the code orchestration service.
- MAF workflow: update `backend/app/maf_workflow.py` to add new executors or edges.

## Variation 1 – Domain Expert Panel

**Goal**: Blend multiple expert personas (e.g., legal, technical, financial) for richer insight.

- Create specialized researcher agents with targeted prompts and tools.
- In YAML/MAF, fan out to each persona; label outputs with the persona name for downstream synthesis.
- Synthesizer merges perspectives and calls out disagreements or alignment.

## Variation 2 – Evidence & Confidence Loop

**Goal**: Increase trust by verifying key claims.

- Add a fact-checking agent after the initial synthesis.
- Use ReAct prompts to fetch sources (Tavily, Bing, internal search) and validate statements.
- Update the final report with confidence scores and citation links.

## Variation 3 – Temporal Comparison

**Goal**: Contrast historical vs. current state to surface trends.

- Introduce two researcher groups: "Historical" and "Current Year" with distinct prompts.
- Add a comparison agent that highlights movement over time and supporting metrics.
- Persist delta metrics in Cosmos DB so the UI can display change over time.

## Variation 4 – Strategic Recommendations

**Goal**: Move beyond reporting by suggesting actions.

- After synthesis, route findings to a strategy agent that produces recommendations tailored to the customer persona.
- Optionally add a reviewer or compliance agent to score the recommendations.
- Surface recommendations in the UI as a separate section with priority tags.

## Variation 5 – Observability Boost

**Goal**: Demonstrate operational readiness.

- Instrument agent execution with Application Insights custom events (`telemetry.py`).
- Track duration, token usage, and error rates per agent.
- Create a simple dashboard (Workbook or screenshot) to showcase during the demo.

## Stretch Ideas

- **Adaptive Execution Mode** – Start in YAML for speed, escalate to MAF workflow when topic complexity crosses a threshold.
- **MCP-powered Research** – Plug in domain-specific MCP servers for proprietary datasets (e.g., financial filings, support tickets).
- **Collaboration Hooks** – Publish results to Teams or OneNote automatically using existing connectors.

## When to Ship Which Pattern

| Scenario | Recommended Pattern |
| --- | --- |
| Exec briefing with contrasting viewpoints | Variation 1 + Variation 4 |
| Compliance or regulatory review | Variation 2 with evidence tracking |
| Trend analysis over time | Variation 3 |
| Observability-focused showcase | Variation 5 |

Document chosen patterns in your team README so judges and peers can follow the orchestration story.

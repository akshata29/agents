# Deep Research Facilitation Guide

This guide equips facilitators to run the Deep Research track, from kickoff through demos. Use it alongside `deep_research_app/docs/` and the quickstart to keep teams unblocked.

## Goals

- Produce a research copilot that showcases planner → researcher → synthesis orchestration.
- Encourage teams to extend the baseline with new agents, tools, or telemetry.
- Capture measurable improvements (latency, quality, coverage) to highlight during demos.

## Agenda Blueprint (Half-Day)

| Time | Focus | Outcomes |
| --- | --- | --- |
| 00:00 – 00:20 | Kickoff | Explain objectives, show baseline demo, assign domains. |
| 00:20 – 00:50 | Environment setup | Backend/frontend running locally, env vars configured. |
| 00:50 – 01:40 | Baseline run + pattern selection | First research session completed, team picks execution mode. |
| 01:40 – 02:30 | Extension sprint | New agent/tool integrated, telemetry validated. |
| 02:30 – 03:00 | Demo prep | Capture artifacts, rehearse story, confirm metrics. |

Adjust timing for longer events; revisit the decision guide whenever teams stall on direction.

## Facilitator Prep Checklist

- ✅ Review `deep_research_app/docs/ARCHITECTURE.md` and `DEVELOPER_GUIDE.md`.
- ✅ Ensure Azure OpenAI, Tavily, and optional Cosmos/App Insights resources are ready.
- ✅ Clone repo, run through `deep_research_app/docs/QUICKSTART.md`, and verify the three execution modes succeed.
- ✅ Familiarize yourself with `../../patterns/` for inspiration on hybrid orchestration.

## Environment Reminders

1. `pwsh deep_research_app/scripts/dev.ps1 --check` validates prerequisites.
2. Copy `backend/.env.example` to `.env` and provide Azure OpenAI + Tavily keys.
3. Frontend expects `VITE_API_BASE_URL=http://localhost:8000`.
4. Optional persistence: configure `COSMOSDB_*` values, then confirm history view renders previous runs.

## Quality Bar

- **Functionality** – At least one differentiated capability (e.g., new research lens, MCP integration, adaptive plan).
- **Telemetry** – Logging or Application Insights traces proving how agents executed.
- **Reliability** – Two consecutive successful runs in the target mode.
- **Storytelling** – Clear articulation of the user problem, orchestration solution, and business impact.

## Checkpoint Prompts

1. **Setup Check** – “Can you show the backend logs and confirm the Execution Monitor streams updates?”
2. **Pattern Review** – “Which execution mode did you select and why? Do you need ReAct or pure concurrent patterns?”
3. **Data & Tools** – “What external sources or MCP tools feed the researchers? Any rate limit considerations?”
4. **Telemetry** – “How are you measuring success? Share a log snippet or Insights chart.”
5. **Demo Rehearsal** – “Walk me through the storyline in under three minutes—what should judges remember?”

## Demo Tips

- Start with the problem statement, not the tech stack.
- Show the Execution Monitor to highlight orchestration decisions.
- Present a before/after metric (e.g., runtime reduction, citation quality, number of perspectives).
- Close with next steps—production hardening, data governance, or additional agent ideas.

## Common Blockers & Quick Fixes

| Blocker | Fix |
| --- | --- |
| Azure OpenAI auth failures | Re-run `az login`, verify deployment name, ensure API version matches `.env` value. |
| Frontend 404 or empty data | Confirm `VITE_API_BASE_URL`, restart `npm run dev`, and check browser console for CORS errors. |
| Cosmos persistence missing | Double-check connection string, database/container names, and firewall settings. |
| Tavily quota exceeded | Rotate to another API key or temporarily disable Tavily-dependent agents. |

Need a different angle? Consult the [DEEP_RESEARCH_PATTERNS.md](./DEEP_RESEARCH_PATTERNS.md) playbook or the [decision guide](./DEEP_RESEARCH_DECISION_GUIDE.md) to reframe the challenge.

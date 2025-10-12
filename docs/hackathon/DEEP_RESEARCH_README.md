# Deep Research Track Overview

This track helps hackathon teams build a research copilot on top of the refreshed Microsoft Agent Framework (MAF) portfolio. Use the resources below to plan sessions, launch environments, and coach teams toward a compelling demo.

## Resource Map

- **[DEEP_RESEARCH_QUICKSTART.md](./DEEP_RESEARCH_QUICKSTART.md)** – 30-minute setup checklist for backend, frontend, and core services.
- **[DEEP_RESEARCH_GUIDE.md](./DEEP_RESEARCH_GUIDE.md)** – Facilitation script, suggested agenda, and checkpoints.
- **[DEEP_RESEARCH_PATTERNS.md](./DEEP_RESEARCH_PATTERNS.md)** – Pattern playbook with baseline flow and stretch ideas.
- **[DEEP_RESEARCH_DECISION_GUIDE.md](./DEEP_RESEARCH_DECISION_GUIDE.md)** – Decision tree to help teams pick the right execution mode and extensions.

Pair these with `deep_research_app/docs/` for architecture details and the main repo `README.md` for screenshots.

## What Teams Build

- Planner → parallel researcher → synthesizer → reviewer pipeline with real-time progress for a chosen domain (e.g., industry analysis, compliance, product research).
- Optional persistence to Cosmos DB so historical runs replay during demos.
- Stretch: additional agents, MCP-backed tools, or decision logic that adapts based on research depth.

## Session Flow

1. **Kickoff (30 min)** – Review goals, demo the baseline app, align on the target research domain.
2. **Build Blocks (90–120 min)** – Follow the quickstart, run first research session, then iterate on agents/patterns.
3. **Checkpoints (every 60 min)** – Confirm teams have telemetry, persistence, and at least one differentiated capability.
4. **Demo Prep (45 min)** – Capture screenshots, export sample reports, and document key learnings.

## Recommended Deliverables

- Recorded or live demo showing plan → research → synthesis flow with commentary on orchestration choices.
- README or slide that highlights agents used, data sources added, and metrics for quality/latency.
- Optional: Application Insights dashboard or Cosmos DB query showcasing observability.

## Support Plan

- Direct teams to `deep_research_app/docs/QUICKSTART.md` when they hit environment issues.
- Use the decision guide to unblock debates about execution mode or pattern selection.
- Encourage changelog notes in `docs/` or the team workspace so reviewers can follow progress.

Ready for deeper facilitation detail? Jump to [DEEP_RESEARCH_GUIDE.md](./DEEP_RESEARCH_GUIDE.md).

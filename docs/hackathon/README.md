# Hackathon Curriculum

## Overview

This curriculum helps teams ramp on the Microsoft Agent Framework (MAF) portfolio that ships with this repository. It replaces the retired “Foundation Framework” material with up-to-date guidance focused on the apps you have just refreshed—Deep Research, FinAgent Dynamic, FinAgent, Advisor Productivity, Multimodal Insights, and the Patterns Sandbox.

## Document Map

1. **[01-maf-overview.md](./01-maf-overview.md)** – Core concepts, terminology, and architecture primitives in MAF
2. **[02-reference-architecture.md](./02-framework-architecture.md)** – Cross-app architecture blueprint and shared infrastructure choices
3. **[03-orchestration-patterns.md](./03-orchestration-patterns.md)** – Pattern catalogue with links back to working code in the portfolio
4. **[04-agent-implementation.md](./04-agent-implementation.md)** – Agent authoring checklist, MCP integration, and context strategies
5. **[05-reference-apps.md](./05-reference-apps.md)** – How each reference application applies patterns, agents, and Azure services
6. **[06-hackathon-implementation.md](./06-hackathon-implementation.md)** – Project backlogs that map to refreshed requirements
7. **[07-development-guide.md](./07-development-guide.md)** – Environment setup, debugging tips, and deployment helpers
8. **[08-advanced-topics.md](./08-advanced-topics.md)** – Observability, governance, evaluation, and production hardening

Deep Research specific add-ons:
- [DEEP_RESEARCH_README.md](./DEEP_RESEARCH_README.md) – consolidated workbook with facilitators’ notes
- [DEEP_RESEARCH_QUICKSTART.md](./DEEP_RESEARCH_QUICKSTART.md) – 15-minute path to a working demo
- [DEEP_RESEARCH_PATTERNS.md](./DEEP_RESEARCH_PATTERNS.md) – optional pattern extensions and iterative improvements
- [DEEP_RESEARCH_DECISION_GUIDE.md](./DEEP_RESEARCH_DECISION_GUIDE.md) – mode selection and evaluation worksheet

## How to Use This Curriculum

1. **Kick-off (30 min)** – Review the overview doc to ground the team in MAF concepts
2. **Architecture Workshop (45 min)** – Walk through the reference architecture and pattern catalogue; pick a starting point
3. **Build Sprint (2–4 hrs)** – Follow the development guide and project checklists to stand up the first end-to-end flow
4. **Polish + Demo (1–2 hrs)** – Layer in approvals, telemetry, and presentation collateral using the advanced topics guide

## Hackathon Projects

The refreshed portfolio supports five core project themes. Each now points to the new docs set and active code paths:

| Theme | Focus | Starter Assets |
| --- | --- | --- |
| Orchestrator Enhancement | Expand the Patterns Sandbox with new approval flows or hybrid plans | `patterns/`, [03-orchestration-patterns](./03-orchestration-patterns.md) |
| Multi-Modal Researcher | Extend Multimodal Insights or Deep Research with new modalities/tools | `multimodal_insights_app/`, `deep_research_app/`, [05-reference-apps](./05-reference-apps.md) |
| Data Retrieval Optimization | Swap in new financial/news data sources and caching layers | `finagent_app/`, `finagent_dynamic_app/`, [04-agent-implementation](./04-agent-implementation.md) |
| General Purpose Agent | Create reusable MCP-enabled agents for the Patterns Sandbox | `patterns/backend/app/agents`, [04-agent-implementation](./04-agent-implementation.md) |
| Real-Time Call Analysis | Add post-call workflows or analytics to Advisor Productivity | `advisor_productivity_app/`, [05-reference-apps](./05-reference-apps.md) |

## Getting Started Checklist

1. Clone the repo and skim `docs/README.md` for portfolio context
2. Choose a project theme and open the referenced application README
3. Follow `docs/hackathon/07-development-guide.md` to configure environments
4. Use `docs/hackathon/06-hackathon-implementation.md` to track work items
5. Capture learnings in the decision guide or pattern worksheet for your finale demo

## Key Takeaways

- MAF provides the orchestration primitives; the refreshed docs show how to wield them across production-grade examples
- Every app in the portfolio is self-contained—use the docs to copy proven patterns rather than re-inventing them
- The hackathon material now mirrors the same architecture and terminology used throughout the repository, keeping onboarding friction low

Happy building! Document improvements or feedback in the main repo discussions so the curriculum stays fresh.

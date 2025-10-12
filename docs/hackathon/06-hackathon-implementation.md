# Hackathon Implementation Guide

Use this guide to turn the refreshed documentation into actionable workstreams. Each project below references the updated applications and documentation.

## Project 1 – Orchestrator Enhancement

**Goal**: Extend the Patterns Sandbox with a new orchestration capability or approval flow.

1. Review `patterns/README.md` and run the app locally.
2. Pick a builder to enhance—examples: add approval gating to Sequential runs, or create a hybrid Plan → Parallel → Synthesize option.
3. Update `patterns/backend/app/services/orchestrator_service.py` (or equivalent) to wire the new flow.
4. Surface controls in `patterns/frontend/src/components/` so the UI can toggle the feature.
5. Document the change in `patterns/docs/` and capture screenshots for the final demo.

**Artifacts**
- Demo script highlighting before/after
- Updated README section and screenshots
- Optional telemetry dashboard in Application Insights

## Project 2 – Multi-Modal Researcher

**Goal**: Combine Deep Research and Multimodal Insights capabilities into a richer investigation experience.

1. Read `multimodal_insights_app/docs/ARCHITECTURE.md` and `deep_research_app/docs/QUICKSTART.md`.
2. Decide which ingestion types you want to add (audio/video/PDF) and which research modes should leverage them.
3. Create or adapt agents that normalize the new data, then feed outputs into the existing Deep Research planner or writer.
4. Persist artifacts in Cosmos DB or Azure Storage so users can replay sessions.
5. Update documentation explaining configuration steps and limitations.

**Artifacts**
- Recorded demo of multimodal workflow
- Updated quickstart instructions
- Cost/latency notes for each modality

## Project 3 – Data Retrieval Optimization

**Goal**: Enhance FinAgent or FinAgent Dynamic with smarter data pipelines.

1. Audit current adapters in `finagent_app/backend/app/agents` and `finagent_dynamic_app/backend/app/agents`.
2. Introduce caching, batching, or new data sources (e.g., news APIs, custom MCP servers).
3. Update environment templates with new secrets and document them.
4. Adjust planner or execution prompts to incorporate the additional insights.
5. Create metrics that show before/after latency or coverage.

**Artifacts**
- Comparison report (baseline vs optimized)
- Updated `.env.template` and README sections
- Telemetry screenshots (App Insights, Cosmos run history)

## Project 4 – General Purpose Agent Pack

**Goal**: Build reusable agents that can drop into any MAF workflow.

1. Drop new agents inside `patterns/backend/app/agents` or `deep_research_app/backend/app/agents`.
2. Follow the checklist in `04-agent-implementation.md` (single responsibility, prompt clarity, tool integration).
3. Register agents via configuration so they can be selected from the UI.
4. Write sample prompts and test cases demonstrating each agent’s specialty.
5. Publish a short README explaining how to adopt these agents in other apps.

**Artifacts**
- Agent module(s) with tests
- Usage documentation and example prompts
- Optional MCP tool definitions if the agent exposes new capabilities

## Project 5 – Real-Time Call Analysis

**Goal**: Extend Advisor Productivity with new post-call workflows.

1. Read `advisor_productivity_app/README.md` to understand existing flows.
2. Add new agents (e.g., compliance checker, coaching tips) or integrate additional data sources.
3. Update the frontend (`frontend/src/components/`) to display new insights.
4. Instrument additional telemetry for accuracy and latency.
5. Document how to configure Azure services required for the enhancements.

**Artifacts**
- Demo highlighting call insights end-to-end
- Configuration guide for new services
- Quality/impact metrics (accuracy, response time)

## Delivery Checklist

- [ ] Update relevant README/Quickstart files with new prerequisites, env variables, and screenshots
- [ ] Capture Application Insights charts or Cosmos DB dashboards that support your story
- [ ] Ensure deployment scripts (`deploy.ps1`, `deploy_mcp.ps1`, Dockerfiles) still work or document the adjustments
- [ ] Prepare a 5-minute presentation that covers problem, solution, architecture, and demo

## Collaboration Tips

- Create a shared OneNote or document using the decision guides in this folder to track scope changes
- Tag commits with project identifiers (e.g., `orchestrator-enhancement`) so others can follow along
- Run daily sanity checks using `scripts/dev.ps1` or app-specific scripts to keep environments aligned

Ready to build? Jump to [07-development-guide.md](./07-development-guide.md) for environment setup specifics.

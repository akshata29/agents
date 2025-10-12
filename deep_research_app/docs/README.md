# Deep Research Documentation Hub

The Deep Research App ships with three core references. Use this page to decide which guide to open first and where to find supporting assets.

## Document Map

- **[QUICKSTART.md](QUICKSTART.md)** – Local setup, environment variables, and your first successful run.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** – Component responsibilities, data flow, integrations, and observability.
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** – Execution mode deep dive, orchestration patterns, extension points, and testing tips.

## Suggested Paths

- **Hands-on engineer**: `QUICKSTART.md` → run a topic → `ARCHITECTURE.md` (System Overview) → `DEVELOPER_GUIDE.md` (Execution Modes & Extending Agents).
- **Tech lead / reviewer**: Main [`README.md`](../README.md) → `ARCHITECTURE.md` (Integration & Security) → `DEVELOPER_GUIDE.md` (Persistence & Telemetry).
- **Facilitator / hackathon coach**: `QUICKSTART.md` (requirements) → `DEVELOPER_GUIDE.md` (Patterns) → `docs/hackathon/DEEP_RESEARCH_GUIDE.md` for workshop framing.

## Screenshot Library

Screenshots live under [`images/`](images/):

- `homepage.png` – Landing dashboard.
- `execution_mode_workflow_engine.png`, `execution_mode_code_based.png`, `execution_mode_maf_workflow.png` – Mode selector states.
- `yaml_research_progress.png`, `code_research_progress.png`, `maf_research_progress.png` – Live execution monitors.
- `yaml_output.png`, `maf_output.png` – Synthesis views.

## Related Resources

- Portfolio overview: `../README.md` and `../../docs/README.md`.
- Hackathon track: `../../docs/hackathon/DEEP_RESEARCH_README.md` plus quickstart/pattern supplements in the same folder.
- Patterns sandbox inspiration: `../../patterns/README.md`.

## Getting Support

1. Start with the troubleshooting sections in `QUICKSTART.md`.
2. Inspect backend logs under `backend/app/logs/` and the browser console for runtime issues.
3. Review environment variables in `backend/.env`; mismatched Azure OpenAI deployments are the most common blocker.
4. File a discussion or issue in the repository if problems persist.

_Last updated: October 2025_

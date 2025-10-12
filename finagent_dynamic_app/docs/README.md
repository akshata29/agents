# Documentation Hub

Use this folder to navigate the FinAgent Dynamic App reference material.

## Document Map

- **[QUICKSTART.md](QUICKSTART.md)** – Backend, MCP server, and frontend setup with troubleshooting tips.
- **[SYNTHESIS_AGENT_PATTERN.md](SYNTHESIS_AGENT_PATTERN.md)** – Deep dive on dual-context orchestration for synthesis agents.

## Suggested Reading Paths

- **New teammates**: Quickstart → run a sample ticker → explore the main README screenshots.
- **Architecture reviewers**: Synthesis pattern overview → README architecture section → inspect `backend/app/services/task_orchestrator.py`.
- **Product stakeholders**: Main README walkthrough → screenshots below → Quickstart for configuration requirements.

## Screenshot Library

All UI assets live in `images/`:

- `homepage_research.png` – Landing page and research prompt.
- `researchplan.png` – Dynamic plan with approvals.
- `task_dependency.png` – Dependency graph view.
- `task_inprogress.png` – Live execution updates.
- `completed_research.png` – Final research brief.
- `completed_task_detail.png` – Agent output detail panel.
- `history.png` – Session history browser.

## Getting Help

1. Confirm environment variables against `backend/.env.template` if APIs fail to respond.
2. Review backend logs for orchestrator warnings and agent errors.
3. Restart the Yahoo Finance MCP server when market data requests hang.
4. Open an issue in the main repository if additional support is required.

---

Last updated: October 2025

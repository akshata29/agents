# Documentation Hub

Use this folder to navigate the Multimodal Insights App reference material.

## Document Map

- **[QUICKSTART.md](QUICKSTART.md)** – Local setup, environment configuration, first run, troubleshooting.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** – Component responsibilities, execution flow, integrations, and data model.
- **[MAF_PATTERN_INTEGRATION.md](MAF_PATTERN_INTEGRATION.md)** – How the app applies Microsoft Agent Framework patterns across agents.

## Suggested Reading Paths

- **New teammates**: Quickstart → Architecture overview → explore backend/app/ for services and agents.
- **Architecture reviewers**: Architecture doc → Pattern integration notes → screenshots below.
- **Feature designers**: Main README screenshots → Quickstart run-through → Architecture data flow.

## Screenshot Library

All UI assets live in `images/`:

- `homepage.png` – Landing screen with file upload.
- `multimodal_insights.png` – Dynamic plan view.
- `analysis_in_progress.png` – Live execution monitor.
- `completed_task_detail_1.png` .. `completed_task_detail_4.png` – Detailed agent outputs.
- `history.png` – Session history timeline.

## Getting Help

1. Validate environment variables against `.env.example` if services fail.
2. Check backend logs (`backend/magentic_foundation.log`) for agent errors.
3. Review Architecture and Pattern docs for orchestration details.
4. File an issue in the main repository when additional assistance is needed.

---

Last updated: October 2025

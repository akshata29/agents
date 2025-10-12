# Getting Started

This guide orients new contributors to the FinAgent Dynamic App codebase and points to the most useful resources for local development.

## What You Are Building

A multi-agent financial research assistant that combines dynamic planning, human approvals, Cosmos DB persistence, and a React dashboard. The solution relies on the Microsoft Agent Framework, Azure OpenAI, Yahoo Finance (via MCP), FMP, and SEC data sources.

## Repository Tour

```
finagent_dynamic_app/
├─ backend/              # FastAPI + MAF orchestrator, agents, persistence
├─ backend/mcp_servers/  # Yahoo Finance MCP server assets
├─ frontend/             # React + Vite dashboard
├─ docs/                 # Quickstart, synthesis pattern, screenshots
├─ scripts/              # PowerShell helpers for setup and dev workflow
├─ deploy.ps1            # Azure deployment automation
├─ deploy_mcp.ps1        # Yahoo Finance MCP deployment
└─ README.md             # Product overview and architecture
```

Key files worth skimming on day one:

- `backend/app/services/task_orchestrator.py` – Plan management and execution logic.
- `backend/app/agents/` – Financial specialist implementations.
- `backend/app/persistence/cosmos_memory.py` – Cosmos DB integration.
- `frontend/src/components/` – Plan view, approval cards, execution monitor, and history browser.

## Local Environment Checklist

1. **Install prerequisites** – Python 3.11+, Node.js 18+, Azure OpenAI GPT-4o deployment, FMP API key. Optional: Cosmos DB + Application Insights for state and telemetry.
2. **Copy the backend template** – `copy backend/.env.template backend/.env` and fill in Azure OpenAI, FMP, Cosmos, storage, and telemetry settings.
3. **Install dependencies** – `pip install -r backend/requirements.txt`, `pip install -r backend/mcp_servers/requirements.txt`, and `npm install` inside `frontend/`.
4. **Start services** – Use three terminals or run `scripts/dev.ps1` to launch backend, Yahoo Finance MCP server, and frontend dev server.
5. **Verify** – Visit `http://localhost:5173`, submit a research objective, approve the plan, and ensure agent outputs populate the dashboard.

See [`docs/QUICKSTART.md`](docs/QUICKSTART.md) for expanded commands and troubleshooting tips.

## Helpful Scripts

- `scripts/setup_backend.ps1` – Creates a virtual environment, installs packages, and prepares `.env` for you.
- `scripts/setup_frontend.ps1` – Installs Node dependencies and seeds `.env`.
- `scripts/dev.ps1` – Launches backend, frontend, and MCP server in one terminal using background jobs.

## Documentation Path

1. Start with the main [`README.md`](README.md) for screenshots, architecture, and agent summary.
2. Follow [`docs/QUICKSTART.md`](docs/QUICKSTART.md) to stand up the environment.
3. Review [`docs/SYNTHESIS_AGENT_PATTERN.md`](docs/SYNTHESIS_AGENT_PATTERN.md) to understand the dual-context orchestration model.

## Common Next Steps

- Add new financial data sources by extending `backend/app/agents/` and registering tools with the orchestrator.
- Customize the plan approval flow in `frontend/src/components/PlanView.tsx` and `StepCard.tsx`.
- Enable telemetry by providing an `APPLICATIONINSIGHTS_CONNECTION_STRING` and confirming logs arrive in Azure.
- Prepare for production by testing `deploy.ps1` against a sandbox Azure subscription.

## Support

- Backend logging surfaces in the terminal running Uvicorn.
- MCP server output highlights tool availability and rate limit errors.
- Issues and enhancements should be filed through the main repository’s GitHub Issues board.

Welcome aboard—happy shipping!

# Quickstart

Bring the Deep Research App online locally and complete your first investigation.

## Prerequisites

- Windows, macOS, or Linux workstation
- Python 3.11+
- Node.js 18+
- Azure OpenAI resource (endpoint, API key, chat deployment)
- Tavily API key (optional but recommended for web research)
- Optional: Azure Cosmos DB and Application Insights for persistence and telemetry

## 1. Backend Setup

```powershell
cd deep_research_app/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# edit .env and provide at minimum:
#   AZURE_OPENAI_ENDPOINT / KEY / API_VERSION
#   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
#   TAVILY_API_KEY (optional)
#   COSMOSDB_* and OBSERVABILITY_* values if you plan to persist history
uvicorn app.main:app --reload --port 8000
```

Wait for Uvicorn to report `http://0.0.0.0:8000`.

## 2. Frontend Setup

Use a second terminal so the backend keeps running.

```powershell
cd deep_research_app/frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
npm run dev -- --port 5173
```

The dashboard is now available at `http://localhost:5173`.

## 3. Launch Your First Research Session

1. Open the browser to `http://localhost:5173`.
2. Select **New Research** and enter a topic such as `AI regulation landscape 2025`.
3. Choose an execution mode (YAML Workflow, Code Orchestration, or MAF Workflow).
4. Start the run and observe the Execution Monitor for streaming updates.
5. Inspect the final report, executive summary, and citations; revisit the run later if Cosmos DB persistence is enabled.

## Troubleshooting

| Issue | Fix |
| --- | --- |
| `uvicorn` exits immediately | Confirm Python 3.11 is active (`.venv\Scripts\python --version`) and rerun `start.ps1 --reset` if dependencies are stale. |
| Frontend cannot reach backend | Ensure both services are running, ports 8000/5173 are free, and `VITE_API_BASE_URL` matches the backend host. |
| Azure OpenAI errors | Double-check endpoint URL, deployment name, API version, and quota in the Azure portal. |
| No research history | Supply `COSMOSDB_ENDPOINT`, database, container, and credentials; verify the firewall allows your IP. |
| Tavily results missing | Set `TAVILY_API_KEY` or disable Tavily-dependent agents in `backend/app/settings.py`. |

## Optional Accelerators

- `pwsh ../setup.ps1` runs a combined dependency install if you prefer an automated bootstrap.
- `pwsh ../scripts/dev.ps1 --mcp` installs shared MCP servers used in other apps when you plan to extend tool coverage.

## Next Steps

- Dive into [ARCHITECTURE.md](ARCHITECTURE.md) for component diagrams and data flow.
- Review [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) to customize execution modes or add agents.
- Exploring a hackathon? Pair this quickstart with `../../docs/hackathon/DEEP_RESEARCH_QUICKSTART.md` for team exercises.

Happy researching!

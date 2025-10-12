# Deep Research Quickstart (Hackathon Edition)

Use this checklist to get the Deep Research App running during the event. It assumes you are working inside the `agent_foundation` repository.

## 1. Prerequisites

- Python 3.11+ (`py -3.11 --version`)
- Node.js 18+ (`node --version`)
- Azure OpenAI resource (endpoint, API key, deployment name)
- Tavily API key (optional but recommended)
- Optional: Azure Cosmos DB and Application Insights for persistence and telemetry

## 2. Backend Setup

```powershell
cd deep_research_app/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# Update .env with at minimum:
#   AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
#   AZURE_OPENAI_API_KEY=<key>
#   AZURE_OPENAI_API_VERSION=2024-10-21
#   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
#   TAVILY_API_KEY=<key>   # optional but unlocks richer research

uvicorn app.main:app --reload --port 8000
```

Keep this terminal running; the API should report `http://0.0.0.0:8000`.

## 3. Frontend Setup

Open a second terminal.

```powershell
cd deep_research_app/frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
npm run dev -- --port 5173
```

Browse to `http://localhost:5173` to confirm the dashboard loads.

## 4. Optional Services

- **Cosmos DB history** – Add `COSMOSDB_ENDPOINT`, `COSMOSDB_DATABASE`, `COSMOSDB_CONTAINER`, and key or managed identity values in `backend/.env`.
- **Application Insights** – Provide `OBSERVABILITY_APPLICATIONINSIGHTS_CONNECTION_STRING` to capture traces and metrics.
- **MCP tooling** – `pwsh deep_research_app/scripts/dev.ps1 --mcp` installs shared MCP servers if your scenario needs additional data sources.

## 5. Smoke Test

1. In the UI, select **New Research**.
2. Enter a topic (e.g., `Emerging trends in renewable energy`).
3. Choose an execution mode—start with **YAML Workflow** for a sanity check.
4. Launch the run and verify the Execution Monitor streams planner → researchers → synthesis updates.
5. Repeat using **Code Orchestration** and **MAF Workflow** to ensure parity.

## 6. Troubleshooting Cheatsheet

| Symptom | Resolution |
| --- | --- |
| `401` from Azure OpenAI | Confirm endpoint URL, deployment name, and API version; re-run `az login` if using managed identity. |
| Frontend cannot reach backend | Ensure both services run, ports 8000/5173 are free, and `VITE_API_BASE_URL` matches the backend address. |
| No history entries | Double-check Cosmos settings and firewall; run one more session after configuring. |
| Tavily errors | Verify the API key, or temporarily disable Tavily-dependent researchers in `settings.py`. |

## 7. Next Moves

- Reference [DEEP_RESEARCH_PATTERNS.md](./DEEP_RESEARCH_PATTERNS.md) to decide how you will extend the workflow.
- Use [DEEP_RESEARCH_DECISION_GUIDE.md](./DEEP_RESEARCH_DECISION_GUIDE.md) to pick the execution mode that matches your goals.
- Document notable changes in your team notes or repo branch so judges can follow the evolution.

Once the basics are solid, shift focus to differentiation—new agents, better telemetry, or creative research visualizations.

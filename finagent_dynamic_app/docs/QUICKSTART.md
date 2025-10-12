# Quickstart

Bring the FinAgent Dynamic App online locally and complete your first financial research workflow.

## Prerequisites

- Windows, macOS, or Linux workstation
- Python 3.11+
- Node.js 18+
- Azure OpenAI resource with a GPT-4o deployment
- Financial Modeling Prep (FMP) API key
- Optional: Azure Cosmos DB and Application Insights instances for persistence and telemetry

## 1. Backend Setup

```powershell
cd finagent_dynamic_app/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.template .env

# edit .env and provide at minimum:
#   AZURE_OPENAI_ENDPOINT / KEY / DEPLOYMENT / API_VERSION
#   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
#   FMP_API_KEY
#   YAHOO_FINANCE_ENABLED=true and YAHOO_FINANCE_MCP_URL
#   COSMOS_DB_* (or comment if running without persistence)
uvicorn app.main:app --reload --port 8000
```

Backend is ready when Uvicorn reports `http://0.0.0.0:8000`.

## 2. Yahoo Finance MCP Server

Open a new terminal so the backend keeps running.

```powershell
cd finagent_dynamic_app/backend/mcp_servers
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python start_server.py
```

By default the server streams from `http://localhost:8001/sse`. Keep this running while the backend executes MCP-enabled steps.

## 3. Frontend Setup

Use another terminal session for the frontend dev server.

```powershell
cd finagent_dynamic_app/frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
npm run dev -- --port 5173
```

Open `http://localhost:5173` to launch the dashboard. Live reload keeps the UI in sync as you iterate.

## 4. Run Your First Research Session

1. Enter a research objective such as `Build a bull/bear case for MSFT`.
2. Choose the scope (Company, SEC, Earnings, Fundamentals, Technicals) and keep Sequential execution for the first run.
3. Approve the generated plan so the orchestrator can execute agents.
4. Watch the execution monitor for live updates and review agent outputs.
5. Download the equity brief or inspect the session history view.

## Troubleshooting

- **Azure OpenAI errors** → Confirm endpoint URL, deployment name, and API version match your resource; ensure quota remains.
- **FMP or SEC data issues** → Verify `FMP_API_KEY`, optional `SEC_API_KEY`, and respect FMP rate limits (250 calls/day on the free tier).
- **Cosmos DB connection failures** → Supply `COSMOS_DB_KEY` (or Managed Identity settings) and allow your IP through Cosmos firewall rules.
- **MCP requests hang** → Restart `backend/mcp_servers` process and confirm `YAHOO_FINANCE_MCP_URL` aligns with the running port.
- **Frontend cannot reach backend** → Check that both services run, ports 8000/5173 are free, and `VITE_API_BASE_URL` matches.

## Next Steps

- Review [SYNTHESIS_AGENT_PATTERN.md](SYNTHESIS_AGENT_PATTERN.md) to understand how synthesis agents consume session context.
- Explore [scripts/dev.ps1](../scripts/dev.ps1) for a single command workflow that launches backend, frontend, and MCP server together.
- Enable telemetry by setting `APPLICATIONINSIGHTS_CONNECTION_STRING` to capture orchestrator traces in Azure.

Happy researching!

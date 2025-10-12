# Deep Research Architecture

Understand how the Deep Research App stitches together a responsive UI, multi-agent orchestration, and optional persistence.

## System Overview

```
Browser (React + Vite)
    │  REST + WebSocket
    ▼
FastAPI Backend (Uvicorn)
    │  Orchestration adapters
    ▼
Workflow Engine & MAF Executors
    │  Agent invocations
    ▼
Agents + External Services
    ├─ Azure OpenAI (LLM)
    ├─ Tavily (web search)
    └─ Cosmos DB / Application Insights (optional)
```

The frontend streams user intent to the backend, which launches one of three execution modes (YAML, code, or MAF workflow). Results stream back to the UI in real time and can be persisted for replay.

## Component Breakdown

### Frontend (`frontend/`)

- React + TypeScript single-page app built with Vite and Tailwind.
- React Query handles REST calls; a lightweight WebSocket client handles streaming updates.
- Key surfaces: Dashboard, New Research form, Workflow visualization, Execution Monitor.
- Result views normalize output sections (plan, findings, summary, citations) regardless of execution mode.

### Backend (`backend/app/`)

- **`main.py`** exposes REST endpoints (`/api/research/start`, `/status`, `/list`) and a WebSocket hub.
- **`routers/`** separates concerns for research execution, history, and health checks.
- **`services/`** contains orchestration adapters for each execution mode plus persistence helpers.
- **`persistence/`** (optional) saves canonical `ResearchRun` records to Cosmos DB.
- **`settings.py`** centralizes configuration for Azure OpenAI, Tavily, CORS, telemetry, and Cosmos DB.

### Orchestration Layer

- **YAML Workflow Engine** loads `workflows/deep_research.yaml`, resolves variables, and enforces dependencies.
- **Programmatic Orchestrator** uses helper functions (sequential, concurrent, ReAct) to stitch planner → researchers → synthesis chains.
- **MAF Workflow** leverages `WorkflowBuilder` to model fan-out/fan-in graphs with typed messages and rich telemetry.

### Agents & Tools

- Planner, researcher variants, writer/synthesizer, reviewer, and optional fact-checker agents live under `backend/app/agents/`.
- Agents call Azure OpenAI deployments; researchers optionally enrich context with Tavily results through helper modules.
- Additional MCP tools or REST integrations register through configuration and can be reused across modes.

## Execution Flow

1. **Start** – Frontend posts `/api/research/start` with topic, depth, and execution mode; backend returns an `execution_id`.
2. **Stream** – Frontend opens `ws://.../ws/research/{execution_id}` to receive status, task, and result events.
3. **Orchestrate** – Backend selects the requested mode, invokes agents, and normalizes outputs into canonical sections.
4. **Persist (optional)** – When Cosmos DB is configured, the final payload and workflow variables are upserted as a `ResearchRun` document.
5. **Replay** – History requests hydrate the same structure used during live runs so archived sessions render identically to active ones.

## Data Schema Highlights

`ResearchRun` documents capture:

| Field | Purpose |
| --- | --- |
| `id` | Execution UUID returned to the client. |
| `mode` | `yaml`, `code`, or `maf_workflow` to identify orchestration strategy. |
| `topic` | User-supplied research prompt. |
| `result_sections` | Canonical dictionary (plan, findings, report, executive_summary, citations, validation). |
| `task_results` | Chronological agent outputs keyed by agent identifier. |
| `variables` | Final workflow variables for replay (YAML mode snapshot). |
| `execution_details` | Durations, token usage, errors, and metadata surfaced in the UI. |

## Observability and Telemetry

- Structured logging emits `execution_id`, agent name, and step metadata for easy filtering.
- Application Insights / OTLP exporters activate when `OBSERVABILITY_*` settings are provided.
- Frontend visualizations mirror backend events, providing a real-time lens into progress and failures.

## Security & Compliance

- CORS origins, allowed headers, and credentials are controlled via environment variables.
- Secrets stay in `.env`; production deployments should prefer Azure Key Vault or managed identity.
- Cosmos DB persistence supports both key-based auth and Azure AD client credentials; ensure data retention policies align with customer requirements.

## Extension Points

- Add new agents by registering them in the agent factory and updating workflows or orchestration adapters.
- Introduce additional data sources by wiring MCP tools or REST clients into the researcher agents.
- Extend the UI by surfacing new result sections or metrics; the API already returns normalized structures for consumption.

This architecture balances rapid experimentation with production-grade observability, making it easy to iterate on research workflows without sacrificing reliability.

### Backend State
```python
active_executions: Dict[str, Dict[str, Any]] = {
    "exec-123": {
        "id": "exec-123",
        "status": "running",
        "start_time": "2024-01-01T00:00:00",
        "request": {...},
        "execution": WorkflowExecution(...)
    }
}
```

### Frontend State
```typescript
// React Query cache
- workflowInfo: WorkflowInfo
- executionStatus: ExecutionStatus
- health: HealthStatus

// Component local state
- currentExecutionId: string
- activeTab: 'new' | 'workflow' | 'monitor'
- wsMessages: WebSocketMessage[]
```

## 🔐 Configuration Flow

```
.env file
    │
    ├─ AZURE_OPENAI_API_KEY
    ├─ AZURE_OPENAI_ENDPOINT
    ├─ AZURE_OPENAI_DEPLOYMENT
    │
    ▼
Settings (config/settings.py)
    │
    ├─ Load environment variables
    ├─ Validate configuration
    │
    ▼
Framework Components
    │
    ├─ AgentRegistry (uses settings)
    ├─ Orchestrator (uses settings)
    ├─ WorkflowEngine (uses settings)
    │
    ▼
Agent Creation
    │
    └─ Agents use LLM credentials from settings
```

## 🎨 UI Component Hierarchy

```
App
├── Header
│   ├── Logo
│   ├── Title
│   └── Status Badges
│
├── Navigation Tabs
│   ├── New Research
│   ├── Workflow Configuration
│   └── Execution Monitor
│
├── Main Content (conditional)
│   │
│   ├─ [New Research Tab]
│   │   ├── Dashboard
│   │   │   ├── System Status Card
│   │   │   ├── Running Count Card
│   │   │   ├── Completed Count Card
│   │   │   └── Failed Count Card
│   │   │
│   │   └── ResearchForm
│   │       ├── Topic Input
│   │       ├── Depth Selector
│   │       ├── Options Grid
│   │       └── Submit Button
│   │
│   ├─ [Workflow Tab]
│   │   └── WorkflowVisualization
│   │       ├── Workflow Info Header
│   │       ├── React Flow Graph
│   │       ├── Variables Panel
│   │       └── Tasks Panel
│   │
│   └─ [Monitor Tab]
│       └── ExecutionMonitor
│           ├── Status Header
│           ├── Progress Bar
│           ├── Current Task Indicator
│           ├── Completed Tasks List
│           ├── Failed Tasks List
│           ├── Results Viewer
│           └── Event Log
│
└── Footer
    └── Credits
```

This architecture provides a **complete, scalable** foundation for building multi-agent applications with lightweight Microsoft Agent Framework utilities! 🚀

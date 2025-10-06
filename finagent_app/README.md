# Financial Research Multi-Agent Application

A multi-agent financial research system built on the Microsoft Agent Framework, combining the agent taxonomy from **finagentsk** with orchestration patterns and UI/UX from the **agents framework** and **deep_research_app** reference.

## Overview

This application provides comprehensive equity research capabilities through coordinated AI agents, supporting multiple execution patterns for different research workflows:

- **Sequential**: Planner → SEC → Earnings → Fundamentals → Technicals → Report
- **Concurrent**: Parallel execution with result aggregation
- **Handoff**: Dynamic agent-to-agent delegation
- **Group Chat**: Multi-agent collaborative analysis

## Architecture

```
finagent_app/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── routers/     # API routes (orchestration, reports, agents)
│   │   ├── services/    # Core services (orchestrator, planner, reducer)
│   │   ├── adapters/    # Data source and MCP adapters
│   │   ├── models/      # Request/response DTOs
│   │   ├── infra/       # Settings, telemetry
│   │   ├── agents/      # Financial agent implementations
│   │   │   ├── company_agent.py      # Company intelligence & market data
│   │   │   ├── sec_agent.py          # SEC filings analysis
│   │   │   ├── earnings_agent.py     # Earnings calls analysis
│   │   │   ├── fundamentals_agent.py # Financial statements & ratios
│   │   │   ├── technicals_agent.py   # Technical analysis & charts
│   │   │   └── report_agent.py       # PDF equity brief generation
│   │   ├── helpers/     # Utility classes (FMP, Yahoo Finance)
│   │   └── tools/       # MCP tool wrappers
│   └── framework_bindings/   # Bindings to agents framework patterns
├── frontend/            # React + Vite UI
│   └── src/
│       ├── components/  # UI components
│       ├── pages/       # Application pages
│       ├── hooks/       # React hooks
│       └── lib/         # Utilities
├── docs/                # Documentation
└── scripts/             # Dev and deployment scripts
```

## Agents

### Company Agent
- Company profile, metrics, news
- Stock quotes and historical data
- Analyst recommendations
- Market sentiment

### SEC Agent
- 10-K/10-Q analysis
- Business highlights extraction
- Risk assessment
- Financial statement analysis
- Equity report generation

### Earnings Agent
- Transcript retrieval and summarization
- Positive/negative outlook extraction
- Growth opportunities identification
- Guidance credibility assessment

### Fundamentals Agent
- Financial statement analysis (3-5 years)
- Key ratio computation (ROE, ROA, margins, etc.)
- Altman Z-Score (bankruptcy risk)
- Piotroski F-Score (financial strength)
- Trend analysis

### Technicals Agent
- Technical indicators (EMA, RSI, MACD, Bollinger Bands)
- Candlestick pattern detection
- Support/resistance levels
- Overall technical rating

### Report Agent
- Synthesizes all agent analyses
- Generates 1-3 page PDF equity brief
- Investment thesis and key risks
- Valuation snapshot and recommendation

## Orchestration Patterns

### 1. Sequential
Agents execute in order, each building on previous context.

**API**: `POST /orchestration/sequential`
```json
{
  "ticker": "MSFT",
  "scope": ["sec", "earnings", "fundamentals", "technicals"],
  "depth": "deep",
  "includePdf": true
}
```

### 2. Concurrent
Agents run in parallel, results are merged by Reducer agent.

**API**: `POST /orchestration/concurrent`
```json
{
  "ticker": "MSFT",
  "modules": ["sec", "earnings", "fundamentals", "technicals"],
  "aggregationStrategy": "merge"
}
```

### 3. Handoff
Agents dynamically delegate to specialists based on context.

**API**: `POST /orchestration/handoff`
```json
{
  "ticker": "MSFT",
  "initialAgent": "company",
  "question": "Assess risk factors",
  "maxHandoffs": 10
}
```

### 4. Group Chat
Multi-agent debate for hypothesis testing and consensus.

**API**: `POST /orchestration/groupchat`
```json
{
  "ticker": "MSFT",
  "question": "Is the current valuation justified?",
  "maxTurns": 40,
  "requireConsensus": true
}
```

## Data Sources

- **Yahoo Finance**: Real-time quotes, historical data
- **Financial Modeling Prep (FMP)**: Company financials, SEC filings
- **SEC EDGAR**: Regulatory filings (10-K, 10-Q, 8-K)
- **Azure Storage**: PDF report persistence
- **Azure Cosmos DB**: Session state management

## Tech Stack

### Backend
- **FastAPI**: API framework
- **Microsoft Agent Framework**: Agent orchestration
- **Azure OpenAI**: GPT-4o for agent intelligence
- **OpenTelemetry**: Observability and tracing
- **Pydantic**: Data validation
- **Structlog**: Structured logging

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool
- **TanStack Query**: Data fetching
- **TailwindCSS**: Styling
- **Lucide Icons**: Icon library
- **WebSocket**: Real-time updates

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Azure OpenAI account
- FMP API key (for financial data)

### Backend Setup

1. **Create virtual environment**:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```powershell
   cp .env.template .env
   # Edit .env with your API keys and configuration
   ```

4. **Run backend**:
   ```powershell
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Install dependencies**:
   ```powershell
   cd frontend
   npm install
   ```

2. **Run development server**:
   ```powershell
   npm run dev
   ```

3. **Access UI**:
   ```
   http://localhost:5173
   ```

## Environment Variables

See `.env.template` for all configuration options. Key variables:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Financial Data
FMP_API_KEY=your-fmp-key
YAHOO_FINANCE_ENABLED=true

# Storage
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
COSMOS_DB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
```

## API Endpoints

### Orchestration
- `POST /orchestration/sequential` - Run sequential workflow
- `POST /orchestration/concurrent` - Run concurrent workflow
- `POST /orchestration/handoff` - Run handoff workflow
- `POST /orchestration/groupchat` - Run group chat workflow
- `GET /orchestration/runs/{run_id}` - Get run status
- `DELETE /orchestration/runs/{run_id}` - Cancel run

### Reports
- `GET /reports` - List generated reports
- `GET /reports/{report_id}` - Get specific report
- `GET /reports/{report_id}/pdf` - Download PDF

### Agents
- `GET /agents` - List available agents
- `GET /agents/{agent_id}/health` - Agent health status

### System
- `GET /health` - System health check
- `GET /status` - Detailed system status

## UI Features

### Left Pane: Research Control
- Ticker input and scope selection
- Pattern selector (Sequential/Concurrent/Handoff/Group)
- Depth configuration (Standard/Deep/Comprehensive)
- Run history and saved reports

### Center Pane: Conversation Timeline
- Agent messages with avatars
- Collapsible tool calls
- Artifact previews
- Pattern-specific badges
- Real-time streaming updates

### Right Pane: Insights Drawer
Tabs:
- **Dossier**: Company profile and metrics
- **SEC**: Filing highlights and risks
- **Earnings**: Call insights and outlook
- **Fundamentals**: Ratios and scores
- **Technicals**: Charts and signals
- **Report**: PDF equity brief

## Development

### Run Both Services
```powershell
# Terminal 1 - Backend
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Seed Example Data
```powershell
cd scripts
python seed_examples.py
```

### Run Tests
```powershell
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Deployment

See `docs/DEPLOYMENT.md` for deployment guide covering:
- Azure App Service deployment
- Container deployment
- Environment configuration
- Monitoring and alerts
- Cost optimization

## Observability

The application integrates with Azure Application Insights for:
- Request/response tracing
- Agent execution metrics
- Error tracking and alerts
- Performance monitoring
- Custom telemetry events

## Security

- API key rotation support
- Azure Managed Identity integration
- CORS configuration
- Rate limiting (coming soon)
- Input validation and sanitization

## Roadmap

- [ ] PDF export with custom templates
- [ ] Multi-ticker portfolio analysis
- [ ] Custom agent creation UI
- [ ] Scheduled research runs
- [ ] Email/Slack notifications
- [ ] Advanced charting and visualizations
- [ ] Backtesting capabilities
- [ ] Integration with trading platforms

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Discussions: GitHub Discussions

---

**Built with**:
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [finagentsk](https://github.com/akshata29/finagentsk)
- [agents framework](https://github.com/akshata29/agents)

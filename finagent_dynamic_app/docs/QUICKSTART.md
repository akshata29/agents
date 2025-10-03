# Quick Start Guide

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.11+** installed
2. **Node.js 18+** and npm installed
3. **Azure OpenAI** account with GPT-4o deployment
4. **Financial Modeling Prep (FMP) API key** (get from https://financialmodelingprep.com/)

## Installation

### 1. Backend Setup

```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your API keys
```

### 2. Frontend Setup

```powershell
# Navigate to frontend directory  
cd frontend

# Install dependencies
npm install
```

## Configuration

Edit `backend/.env` with your credentials:

```env
# Required
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Financial Data
FMP_API_KEY=your-fmp-api-key

# Optional (for PDF export and state management)
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection
COSMOS_DB_ENDPOINT=your-cosmos-endpoint
```

## Running the Application

### Option 1: Run Both Services (Recommended)

```powershell
# From project root
.\scripts\dev.ps1
```

### Option 2: Run Separately

**Terminal 1 - Backend:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

## Access the Application

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## First Research Run

1. Open http://localhost:5173
2. Enter a stock ticker (e.g., "MSFT")
3. Select research scope (Company, SEC, Earnings, Fundamentals, Technicals)
4. Choose execution pattern (Sequential recommended for first run)
5. Click "Start Research"
6. Monitor execution in real-time

## Execution Patterns

### Sequential
- Agents run in order: Company → SEC → Earnings → Fundamentals → Technicals → Report
- Each agent builds on previous context
- Best for comprehensive, narrative-driven analysis
- Execution time: ~2-5 minutes

### Concurrent
- All agents run in parallel
- Results are merged by Reducer agent
- Best for faster analysis when context doesn't need to flow
- Execution time: ~1-2 minutes

### Handoff (Coming Soon)
- Dynamic agent-to-agent delegation
- Best for complex, exploratory research

### Group Chat (Coming Soon)
- Multi-agent collaborative discussion
- Best for hypothesis testing and consensus building

## Example Research Questions

Try these queries to test different capabilities:

- **Company Analysis**: "Analyze Microsoft's competitive position"
- **SEC Deep Dive**: "What are the key risk factors for Apple?"
- **Earnings Insight**: "Summarize Tesla's latest earnings outlook"
- **Fundamental Health**: "Evaluate Amazon's financial strength"
- **Technical Signals**: "What are the technical indicators for NVIDIA?"

## Troubleshooting

### Backend Issues

**Import errors for agent_framework:**
```powershell
# Install Microsoft Agent Framework from source
# (Currently placeholder - follow framework installation guide)
```

**Azure OpenAI connection errors:**
- Verify endpoint URL and API key
- Check deployment name matches configuration
- Ensure quota is available

**Financial data API errors:**
- Verify FMP API key is valid
- Check rate limits (free tier: 250 requests/day)

### Frontend Issues

**Cannot connect to backend:**
- Ensure backend is running on port 8000
- Check CORS configuration in backend settings

**Slow loading:**
- Check network connection
- Verify API rate limits not exceeded

## Next Steps

1. **Explore Agent Capabilities**: Test each agent individually via /agents endpoint
2. **Custom Research**: Modify research scope to focus on specific areas
3. **PDF Export**: Enable PDF generation in research form
4. **Advanced Patterns**: Try concurrent execution for speed
5. **Review Documentation**: Read full docs in /docs directory

## Development

### Running Tests

```powershell
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

```powershell
# Backend linting
cd backend
ruff check .
black --check .

# Frontend linting
cd frontend
npm run lint
```

## Support

- **Documentation**: See `/docs` directory
- **API Reference**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Examples**: See `/examples` directory

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         React Frontend (Vite)           │
│  ┌──────────────────────────────────┐  │
│  │  ResearchForm | ExecutionMonitor │  │
│  └──────────────────────────────────┘  │
└─────────────┬───────────────────────────┘
              │ HTTP/WebSocket
┌─────────────▼───────────────────────────┐
│        FastAPI Backend                   │
│  ┌──────────────────────────────────┐  │
│  │   OrchestrationService           │  │
│  │  ┌────────────────────────────┐ │  │
│  │  │ SequentialBuilder          │ │  │
│  │  │ ConcurrentBuilder          │ │  │
│  │  │ HandoffBuilder             │ │  │
│  │  └────────────────────────────┘ │  │
│  └──────────────────────────────────┘  │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│         Financial Agents                 │
│  ┌──────┬──────┬──────┬──────┬──────┐  │
│  │Company│ SEC │Earnings│Funds│Tech │  │
│  └──────┴──────┴──────┴──────┴──────┘  │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│      Data Sources & Azure Services      │
│  FMP | Yahoo Finance | SEC | Storage    │
└─────────────────────────────────────────┘
```

Happy researching! 📈

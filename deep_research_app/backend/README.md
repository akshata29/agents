# Deep Research Backend API

FastAPI backend for the Deep Research application, built on the Magentic Foundation Framework.

## Features

- **REST API** for workflow execution and status monitoring
- **WebSocket** for real-time progress updates
- **Framework Integration** with Magentic Foundation agents and workflows
- **CORS Support** for React frontend integration

## Setup

### Prerequisites

- Python 3.11+
- Magentic Foundation Framework installed

### Installation

1. Install the framework first:
```bash
cd ../../framework
pip install -e .
```

2. Install backend dependencies:
```bash
cd ../deep_research_app/backend
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Running the Server

```bash
# Development mode with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or directly
python app/main.py
```

The API will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- OpenAPI Schema: http://localhost:8000/openapi.json

## API Endpoints

### REST Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/workflow/info` - Get workflow configuration
- `POST /api/research/start` - Start a new research workflow
- `GET /api/research/status/{execution_id}` - Get execution status
- `GET /api/research/list` - List all executions

### WebSocket

- `WS /ws/research/{execution_id}` - Real-time execution updates

## Example Usage

### Start Research

```bash
curl -X POST "http://localhost:8000/api/research/start" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Artificial Intelligence in Healthcare",
    "depth": "comprehensive",
    "max_sources": 10,
    "include_citations": true
  }'
```

### Get Status

```bash
curl "http://localhost:8000/api/research/status/{execution_id}"
```

### WebSocket Connection (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/research/{execution_id}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

## Project Structure

```
backend/
├── app/
│   └── main.py           # FastAPI application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

## Integration with Framework

The backend integrates with:
- **WorkflowEngine** - Executes declarative YAML workflows
- **AgentRegistry** - Manages agent instances
- **MonitoringService** - Tracks execution metrics
- **MagenticOrchestrator** - Coordinates multi-agent workflows

## Development

### Add New Endpoints

Edit `app/main.py` and add new route handlers:

```python
@app.get("/api/custom")
async def custom_endpoint():
    return {"message": "Custom endpoint"}
```

### Configure CORS

Modify the CORS middleware in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

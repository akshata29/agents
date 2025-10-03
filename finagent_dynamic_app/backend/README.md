# Financial Research Backend - Dynamic Planning

Backend API for multi-agent financial research with dynamic planning and approval workflow.

## Architecture

This implementation uses the **Magentic Foundation Framework** for orchestration:

- **DynamicPlanner** - Creates execution plans using ReAct pattern
- **GroupChatPattern** - Executes approved steps via multi-agent collaboration  
- **CosmosDB** - Persists plans, steps, and conversation history
- **Human-in-the-Loop** - Approval workflow for each plan step

## Key Features

✅ **Dynamic Plan Generation** - AI creates structured plans from natural language objectives
✅ **Approval Workflow** - Human approval required before executing each step
✅ **Framework Integration** - Uses existing Magentic patterns (no duplication!)
✅ **CosmosDB Persistence** - Session-partitioned storage for plans and messages
✅ **Microsoft Agent Framework** - Leverages MAF for agent execution

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── models/
│   │   └── task_models.py         # Plan, Step, Message models
│   ├── persistence/
│   │   ├── memory_store_base.py   # Abstract interface
│   │   └── cosmos_memory.py       # CosmosDB implementation
│   ├── services/
│   │   └── task_orchestrator.py   # Bridge framework ↔ Cosmos
│   ├── routers/
│   │   └── orchestration.py       # API endpoints
│   └── infra/
│       ├── settings.py             # Configuration
│       └── telemetry.py            # Logging/monitoring
├── requirements.txt
└── .env.example
```

## Setup

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt

# Install Magentic Framework (from parent directory)
cd ..\..\framework
pip install -e .
cd ..\finagent_dynamic_app\backend
```

### 2. Configure Environment

```powershell
# Copy example environment file
Copy-Item .env.example .env

# Edit .env with your Azure credentials
notepad .env
```

Required configuration:
- `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key  
- `COSMOSDB_ENDPOINT` - Cosmos DB endpoint URL

### 3. Run the Server

```powershell
# Start the API server
uvicorn app.main:app --reload --port 8000
```

API will be available at:
- **REST API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Create Plan from Objective
```http
POST /api/input_task
Content-Type: application/json

{
  "objective": "Analyze MSFT stock comprehensively",
  "user_id": "user123",
  "session_id": "session-abc-123",
  "metadata": {
    "ticker": "MSFT"
  }
}
```

Response: Plan with pending steps

### Get Plan Details
```http
GET /api/plans/{session_id}/{plan_id}
```

### Approve/Reject Step
```http
POST /api/approve_step
Content-Type: application/json

{
  "step_id": "step-123",
  "session_id": "session-abc-123",
  "status": "approved",
  "feedback": "Optional feedback"
}
```

### Get Conversation History
```http
GET /api/messages/{session_id}?plan_id={plan_id}
```

## How It Works

### 1. User Submits Objective
```
POST /api/input_task
{
  "objective": "Create comprehensive financial analysis for AAPL",
  "metadata": {"ticker": "AAPL"}
}
```

### 2. Framework Creates Plan
- **TaskOrchestrator** calls **DynamicPlanner.create_plan()**
- Planner uses ReAct pattern to generate 3-6 steps
- Steps stored in CosmosDB with status = `pending`

### 3. User Reviews and Approves Steps
```
POST /api/approve_step
{
  "step_id": "step-1",
  "status": "approved"
}
```

### 4. Framework Executes Approved Step
- **TaskOrchestrator** calls **GroupChatPattern.execute()**
- Appropriate agent executes the step
- Results stored as **AgentMessage** in Cosmos
- Step status updated to `completed`

### 5. Repeat for All Steps
- Each step requires approval before execution
- Full conversation history maintained in Cosmos

## Data Models

### Plan
```python
{
  "id": "plan-123",
  "session_id": "session-abc",
  "user_id": "user123",
  "objective": "Analyze AAPL",
  "status": "pending_approval",
  "steps": [...]
}
```

### Step
```python
{
  "id": "step-1",
  "plan_id": "plan-123",
  "step_number": 1,
  "description": "Fetch company profile",
  "agent_name": "company",
  "status": "pending",
  "required_tools": ["company_profile"]
}
```

### AgentMessage
```python
{
  "id": "msg-456",
  "session_id": "session-abc",
  "plan_id": "plan-123",
  "step_id": "step-1",
  "agent_name": "company",
  "content": "Analysis results...",
  "role": "assistant"
}
```

## Framework Integration

This app **uses** the Magentic Framework, it doesn't duplicate it:

| Component | Framework Module | Usage |
|-----------|-----------------|-------|
| Plan Creation | `framework.core.planning.DynamicPlanner` | `await planner.create_plan()` |
| Step Execution | `framework.patterns.GroupChatPattern` | `await orchestrator.execute()` |
| Agent Registry | `framework.core.registry.AgentRegistry` | Already integrated |
| Observability | `framework.core.observability` | Already integrated |

## CosmosDB Schema

Container: `memory`  
Partition Key: `/session_id`

Document Types (discriminated by `data_type`):
- `SESSION` - User sessions
- `PLAN` - Execution plans
- `STEP` - Individual plan steps
- `MESSAGE` - Agent conversation messages

## Testing

```powershell
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test
pytest tests/test_task_orchestrator.py
```

## Development

```powershell
# Format code
black app/

# Lint code
ruff check app/

# Type checking (if using mypy)
mypy app/
```

## Deployment

See main [GETTING_STARTED.md](../GETTING_STARTED.md) for deployment instructions.

## Troubleshooting

### "CosmosDB endpoint not configured"
- Set `COSMOSDB_ENDPOINT` in .env file
- Verify endpoint URL format: `https://<account>.documents.azure.com:443/`

### "Framework module not found"
- Install framework: `cd ../../framework && pip install -e .`
- Verify Python path includes framework directory

### "Agent not found"
- Check agent name matches registered agents
- Verify framework orchestrator is initialized

## Architecture Decisions

### Why No BaseAgent Class?
Framework already provides `framework.agents.base.BaseAgent` - we use that.

### Why No AgentFactory Class?
Framework already provides `framework.agents.factory.AgentFactory` - we use that.

### Why No Custom Planner?
Framework already provides `framework.core.planning.DynamicPlanner` with ReAct pattern - we use that.

### What Did We Build?
1. **Data Models** - Our specific Plan/Step/Message schemas
2. **Cosmos Persistence** - Storage layer for our models
3. **TaskOrchestrator** - Bridge between framework patterns and our Cosmos storage
4. **API Endpoints** - REST API exposing the workflow

**Result**: ~500 lines of code instead of ~2000+ by using the framework!

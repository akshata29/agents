# Deep Research Application - Architecture & Flow

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│                     (Browser - Port 3000)                            │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    React Application                           │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │ │
│  │  │  Dashboard   │ │ Research     │ │  Workflow            │  │ │
│  │  │  - Stats     │ │ Form         │ │  Visualization       │  │ │
│  │  │  - Health    │ │ - Input      │ │  - React Flow        │  │ │
│  │  │  - Metrics   │ │ - Config     │ │  - Task Graph        │  │ │
│  │  └──────────────┘ └──────────────┘ └──────────────────────┘  │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │           Execution Monitor                               │ │ │
│  │  │  - Real-time Progress  - Task Status  - Results Viewer   │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────┬──────────────────────┬─────────────────────────────┘
                 │ HTTP REST            │ WebSocket (Real-time)
                 │                      │
┌────────────────▼──────────────────────▼─────────────────────────────┐
│                      BACKEND API LAYER                               │
│                   (FastAPI - Port 8000)                              │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                     FastAPI Application                        │ │
│  │  ┌──────────────────────┐    ┌───────────────────────────┐   │ │
│  │  │   REST Endpoints     │    │   WebSocket Handler       │   │ │
│  │  │  GET  /health        │    │  /ws/research/:id         │   │ │
│  │  │  GET  /api/workflow/ │    │  - Connection management  │   │ │
│  │  │       info           │    │  - Real-time updates      │   │ │
│  │  │  POST /api/research/ │    │  - Task events            │   │ │
│  │  │       start          │    │  - Progress streaming     │   │ │
│  │  │  GET  /api/research/ │    └───────────────────────────┘   │ │
│  │  │       status/:id     │                                     │ │
│  │  │  GET  /api/research/ │                                     │ │
│  │  │       list           │                                     │ │
│  │  └──────────────────────┘                                     │ │
│  │                                                                 │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │            Request/Response Models (Pydantic)             │ │ │
│  │  │  ResearchRequest | ExecutionStatus | WorkflowInfo        │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                           FOUNDATION FRAMEWORK                      │
│                     (Core Orchestration Layer)                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐ │ │
│  │  │ WorkflowEngine   │  │  Orchestrator    │  │   Agent     │ │ │
│  │  │  - Load YAML     │  │  - Pattern exec  │  │   Registry  │ │ │
│  │  │  - Parse tasks   │  │  - Coordination  │  │  - Lookup   │ │ │
│  │  │  - Execute flow  │  │  - Monitoring    │  │  - Create   │ │ │
│  │  │  - Manage state  │  │  - Error handle  │  │  - Manage   │ │ │
│  │  └──────────────────┘  └──────────────────┘  └─────────────┘ │ │
│  │                                                                 │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐ │ │
│  │  │ Planning         │  │  Monitoring      │  │   Security  │ │ │
│  │  │  - Task order    │  │  - Metrics       │  │  - Auth     │ │ │
│  │  │  - Dependencies  │  │  - Logging       │  │  - Access   │ │ │
│  │  │  - Optimization  │  │  - Tracing       │  │  - Encrypt  │ │ │
│  │  └──────────────────┘  └──────────────────┘  └─────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│              MICROSOFT AGENT FRAMEWORK + AGENTS                      │
│                    (Agent Execution Layer)                           │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                     Workflow Execution                         │ │
│  │                                                                 │ │
│  │  ┌────────────┐    ┌────────────┐    ┌─────────────────┐     │ │
│  │  │  Planner   │───→│ Researcher │───→│  Synthesizer    │     │ │
│  │  │  Agent     │    │ Agents     │    │  Agent          │     │ │
│  │  │            │    │ (Parallel) │    │                 │     │ │
│  │  │ - Analyze  │    │ - Core     │    │ - Compile       │     │ │
│  │  │ - Plan     │    │ - Current  │    │ - Structure     │     │ │
│  │  │ - Strategy │    │ - Trends   │    │ - Format        │     │ │
│  │  └────────────┘    │ - Compare  │    └─────────────────┘     │ │
│  │                    │ - Expert   │             │               │ │
│  │                    └────────────┘             ▼               │ │
│  │                                        ┌─────────────────┐    │ │
│  │                                        │   Validator     │    │ │
│  │                                        │   Agent         │    │ │
│  │                                        │  - Quality      │    │ │
│  │                                        │  - Accuracy     │    │ │
│  │                                        │  - Completeness │    │ │
│  │                                        └─────────────────┘    │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow

### 1. Research Initiation Flow

```
User (Browser)
    │
    ├─ 1. Enters research topic and config
    │
    ▼
Frontend (ResearchForm.tsx)
    │
    ├─ 2. Validates input
    ├─ 3. POST /api/research/start
    │
    ▼
Backend API (main.py)
    │
    ├─ 4. Receives ResearchRequest
    ├─ 5. Prepares variables for workflow
    │
    ▼
WorkflowEngine
    │
    ├─ 6. Loads deep_research.yaml
    ├─ 7. Parses tasks and dependencies
    ├─ 8. Creates execution instance
    │
    ▼
Backend API
    │
    ├─ 9. Returns execution_id
    ├─ 10. Starts background monitoring
    │
    ▼
Frontend
    │
    └─ 11. Switches to Execution Monitor
        └─ 12. Opens WebSocket connection
```

### 2. Real-time Execution Flow

```
WorkflowEngine
    │
    ├─ 1. Executes tasks based on dependencies
    │
    ▼
Agent Framework
    │
    ├─ 2. Planner Agent creates research plan
    │      └─ Updates: task_status = 'running'
    │
    ├─ 3. Researcher Agents (parallel)
    │      ├─ Core concepts investigation
    │      ├─ Current state research
    │      ├─ Trends analysis
    │      ├─ Comparison study
    │      └─ Expert opinions
    │      └─ Updates: task_status = 'success'
    │
    ├─ 4. Synthesizer Agent
    │      └─ Compiles findings into report
    │
    └─ 5. Validator Agent
           └─ Validates quality and accuracy
    │
    ▼
Background Monitor (Backend)
    │
    ├─ Detects status changes
    ├─ Broadcasts via WebSocket
    │
    ▼
WebSocket Connection
    │
    ├─ Sends JSON messages:
    │    ├─ { type: 'status', ... }
    │    ├─ { type: 'task_update', ... }
    │    ├─ { type: 'progress', ... }
    │    └─ { type: 'completed', ... }
    │
    ▼
Frontend (ExecutionMonitor.tsx)
    │
    ├─ Receives WebSocket messages
    ├─ Updates UI components
    ├─ Shows progress bar
    ├─ Lists completed/failed tasks
    └─ Displays final results
```

### 3. Component Communication Flow

```
┌─────────────────┐
│   App.tsx       │  Main application state
└────────┬────────┘
         │
         ├──────────────────────┬────────────────────┬──────────────────┐
         │                      │                    │                  │
┌────────▼────────┐   ┌─────────▼──────────┐  ┌────▼──────────┐  ┌───▼──────────┐
│  Dashboard      │   │  ResearchForm      │  │  Workflow     │  │  Execution   │
│                 │   │                    │  │  Visualizer   │  │  Monitor     │
└────────┬────────┘   └─────────┬──────────┘  └────┬──────────┘  └───┬──────────┘
         │                      │                   │                 │
         ├──────────────────────┴───────────────────┴─────────────────┤
         │                                                             │
┌────────▼─────────────────────────────────────────────────────────────▼──────┐
│                          API Client (api.ts)                                 │
│  - apiClient.healthCheck()                                                   │
│  - apiClient.getWorkflowInfo()                                               │
│  - apiClient.startResearch(request)                                          │
│  - apiClient.getExecutionStatus(id)                                          │
│  - apiClient.connectWebSocket(id)                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Key Integration Points

### 1. Backend ↔ Framework

```python
# Backend initializes framework components
settings = Settings()
agent_registry = AgentRegistry(settings)
monitoring = MonitoringService(settings)
orchestrator = MagenticOrchestrator(...)

# Backend uses WorkflowEngine
workflow_engine = WorkflowEngine(
    settings=settings,
    agent_registry=agent_registry,
    monitoring=monitoring
)

# Load and execute workflows
workflow_engine.load_workflow(workflow_path)
execution = await workflow_engine.execute_workflow(
    workflow_name="deep_research_workflow",
    variables=variables
)
```

### 2. Frontend ↔ Backend

```typescript
// REST API calls
const response = await apiClient.startResearch({
  topic: "AI in Healthcare",
  depth: "comprehensive",
  max_sources: 10,
  include_citations: true
});

// WebSocket connection
const ws = apiClient.connectWebSocket(executionId);
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  // Update UI based on message type
};
```

### 3. Framework ↔ Agents

```yaml
# deep_research.yaml defines agent tasks
tasks:
  - id: create_research_plan
    type: agent
    agent: "planner"
    parameters:
      task: "Create plan for: ${research_topic}"
    outputs:
      result: research_plan
```

## 📊 State Management

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

This architecture provides a **complete, scalable** foundation for building multi-agent applications with the Magentic Foundation Framework! 🚀

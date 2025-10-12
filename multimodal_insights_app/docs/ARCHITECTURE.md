# Architecture Overview

## System Diagram

```
React UI ──REST──> FastAPI Backend ──> Task Orchestrator (MAF patterns)
                                    │
                                    ├─ Planner Agent (ReAct)
                                    ├─ Multimodal Processor (Speech, Doc Intelligence)
                                    ├─ Sentiment / Summarizer / Analytics Agents (Azure OpenAI)
                                    └─ Cosmos DB + Export Service
```

## Component Responsibilities

### Frontend (`frontend/`)
- React + TypeScript single-page app served via Vite.
- Key views: file uploader, objective form, dynamic plan viewer, execution monitor, history explorer.
- React Query handles polling; WebSocket support can be toggled for real-time updates.

### Backend (`backend/app/`)
- `main.py` exposes REST endpoints (`/api/upload`, `/api/input_task`, `/api/plans/{id}`) and background task orchestration.
- `routers/` groups file, plan, and export routes; `services/` contain Tavily search, export, validation, and document intelligence helpers.
- `persistence/cosmos_memory.py` manages Cosmos DB sessions, plans, and agent outputs.
- `infra/settings.py` loads configuration, telemetry, and CORS settings; `infra/telemetry.py` activates Application Insights / OTLP exporters when enabled.

### Workflow & Agents
- Planner agent (ReAct) inspects objectives and uploaded files to build ordered plans.
- Sequential execution uses a handoff pattern: Multimodal Processor → Sentiment → Summarizer → Analytics.
- Future enhancements can introduce concurrent or group chat patterns once sentiment/summarizer analytics share the same context.

## Execution Flow

1. **Upload**: Frontend posts files to `/api/upload`; backend saves metadata, streams file paths to the orchestrator.
2. **Plan**: `/api/input_task` triggers planner agent, which records steps in Cosmos DB and returns the plan to the UI.
3. **Approve & Execute**: User approves steps; backend executes them sequentially, emitting progress/state updates.
4. **Results**: Agent outputs (transcripts, sentiment, summaries, analytics) persist in Cosmos DB and surface through status endpoints.
5. **Export**: Export service assembles Markdown/PDF/JSON packages on demand.

## Data Model (Cosmos DB)

| Entity | Contents |
| --- | --- |
| `Plan` | Ordered steps, agent metadata, approvals, timestamps. |
| `Execution` | Status, progress, runtime metrics, error details. |
| `Outputs` | Agent results: transcripts, sentiment, summaries, analytics. |
| `Files` | Upload metadata, storage path, derived features. |

## External Integrations

- **Azure OpenAI** (`AZURE_OPENAI_*`) powers sentiment, summarization, and analytics agents.
- **Azure Speech Services** (`AZURE_SPEECH_*`) handles audio/video transcription with diarization.
- **Azure Document Intelligence** (`AZURE_DOCUMENT_INTELLIGENCE_*`) extracts structured data from PDFs.
- **Azure Cosmos DB** (`COSMOSDB_*` or managed identity) persists plans and results.
- **Application Insights / OTLP** optional telemetry for tracing agent execution.
- **Azure Storage** optional for durable file uploads (defaults to local filesystem).

## Observability & Security

- Structured logging with structlog annotates agent start/stop, file operations, and export events.
- Telemetry toggled via `.env` allows App Insights traces and OTLP spans.
- CORS whitelist configured through `CORS_ORIGINS`; file size limits and type checks guard uploads.
- Service principals or managed identity recommended for Cosmos and other Azure services in production deployments.

---

This architecture balances rich multimodal processing with transparent orchestration, providing a reusable template for Azure-backed agent applications.
# Architecture Overview - Multimodal Insights Application

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                 │
│                     (React + TypeScript + Vite)                          │
│                                                                          │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────────────┐   │
│  │  File Upload   │  │ Task Input   │  │  Execution Monitor      │   │
│  │  (Multi-file   │  │ (Custom      │  │  (Real-time Progress)   │   │
│  │   Drag&Drop)   │  │  Copilot)    │  │                          │   │
│  └────────────────┘  └──────────────┘  └─────────────────────────┘   │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │              Plan View & Step Display                          │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────────────────┐   │
│  │  Export        │  │  Results    │  │  Session History          │   │
│  │  (MD/PDF/JSON) │  │  Display    │  │                           │   │
│  └────────────────┘  └─────────────┘  └──────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ REST API
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      API ROUTERS                                  │  │
│  │                                                                   │  │
│  │  /api/upload          /api/input_task      /api/plans/{id}      │  │
│  │  /api/files           /api/execute         /api/export           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    TASK ORCHESTRATOR                              │  │
│  │                                                                   │  │
│  │  • Plan Creation (via Dynamic Planner)                           │  │
│  │  • Agent Coordination                                             │  │
│  │  • Execution Management                                           │  │
│  │  • Progress Tracking                                              │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                   │                                      │
│         ┌─────────────────────────┼─────────────────────────┐          │
│         ▼                         ▼                         ▼          │
│  ┌─────────────┐          ┌──────────────┐         ┌──────────────┐  │
│  │ File        │          │ Persistence  │         │   Export     │  │
│  │ Handler     │          │ (CosmosDB)   │         │   Service    │  │
│  │             │          │              │         │              │  │
│  │ • Upload    │          │ • Plans      │         │ • Markdown   │  │
│  │ • Storage   │          │ • Steps      │         │ • PDF        │  │
│  │ • Metadata  │          │ • Sessions   │         │ • JSON       │  │
│  └─────────────┘          └──────────────┘         └──────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      MICROSOFT AGENT FRAMEWORK                           │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                       PLANNER AGENT                             │   │
│  │                     (ReAct Pattern)                             │   │
│  │                                                                 │   │
│  │  Observe → Think → Act → Reflect                               │   │
│  │  Creates dynamic execution plans based on:                     │   │
│  │    • User objective                                             │   │
│  │    • Uploaded files                                             │   │
│  │    • Available agent capabilities                               │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    EXECUTION AGENTS                                │ │
│  │                                                                    │ │
│  │  ┌──────────────────────┐        ┌───────────────────────┐      │ │
│  │  │  Multimodal          │        │  Sentiment            │      │ │
│  │  │  Processor Agent     │        │  Analysis Agent       │      │ │
│  │  │                      │        │                       │      │ │
│  │  │  • Audio (Speech)    │        │  • Sentiment Scoring  │      │ │
│  │  │  • Video (Extract)   │        │  • Emotion Detection  │      │ │
│  │  │  • PDF (Doc Intel)   │        │  • Tone Analysis      │      │ │
│  │  └──────────────────────┘        └───────────────────────┘      │ │
│  │                                                                    │ │
│  │  ┌──────────────────────┐        ┌───────────────────────┐      │ │
│  │  │  Summarizer          │        │  Analytics            │      │ │
│  │  │  Agent               │        │  Agent                │      │ │
│  │  │                      │        │                       │      │ │
│  │  │  • Multi-level       │        │  • Pattern Extract    │      │ │
│  │  │  • Persona-based     │        │  • Conversation       │      │ │
│  │  │  • Synthesis         │        │  • Recommendations    │      │ │
│  │  └──────────────────────┘        └───────────────────────┘      │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Pattern Usage:                                                         │
│    • ReAct: Planning & iterative reasoning                              │
│    • Handoff: Single-agent task execution                               │
│    • GroupChat: Multi-agent collaboration                               │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AZURE AI SERVICES                                 │
│                                                                          │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────────┐  │
│  │ Azure OpenAI │  │ Azure Speech  │  │ Azure Document             │  │
│  │              │  │ Services      │  │ Intelligence               │  │
│  │ • GPT-4      │  │               │  │                            │  │
│  │ • Reasoning  │  │ • Speech-to-  │  │ • Layout Analysis          │  │
│  │ • Analysis   │  │   Text        │  │ • Table Extraction         │  │
│  │              │  │ • Diarization │  │ • Key-Value Pairs          │  │
│  └──────────────┘  └───────────────┘  └────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA STORAGE                                   │
│                                                                          │
│  ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │
│  │  Azure CosmosDB  │    │  Local JSON     │    │  File Storage   │   │
│  │                  │    │  Storage        │    │  (Uploads)      │   │
│  │  • Plans         │    │                 │    │                 │   │
│  │  • Steps         │    │  • Extracted    │    │  • Audio        │   │
│  │  • Sessions      │    │    Content      │    │  • Video        │   │
│  │  • Metadata      │    │  • Metadata     │    │  • PDF          │   │
│  └──────────────────┘    └─────────────────┘    └─────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. File Upload & Processing Flow

```
User uploads files (audio/video/PDF)
    │
    ▼
Frontend → POST /api/upload
    │
    ▼
FileHandler saves files locally
    │
    ▼
FileMetadata created and stored in CosmosDB
    │
    ▼
User enters objective/prompt
    │
    ▼
POST /api/input_task with file_ids
```

### 2. Plan Creation Flow

```
Input Task received
    │
    ▼
Task Orchestrator → Dynamic Planner (ReAct Pattern)
    │
    ▼
Planner analyzes:
  • User objective
  • Uploaded files (types)
  • Available agents
  • Agent capabilities
    │
    ▼
Plan created with ordered steps:
  Step 1: Multimodal Processor (process all files)
  Step 2: Sentiment Analysis (on extracted content)
  Step 3: Summarizer (create summaries)
  Step 4: Analytics (deep analysis)
    │
    ▼
Plan + Steps saved to CosmosDB
    │
    ▼
Return plan to frontend
```

### 3. Execution Flow

```
POST /api/plans/{id}/execute
    │
    ▼
Task Orchestrator loads plan and steps
    │
    ▼
For each step in order:
    │
    ├─ Step 1: Multimodal Processor
    │   │
    │   ├─ For each file:
    │   │   ├─ Audio → Azure Speech-to-Text
    │   │   ├─ Video → Extract audio → Transcribe
    │   │   └─ PDF → Azure Document Intelligence
    │   │
    │   └─ Save extracted content as JSON
    │
    ├─ Step 2: Sentiment Agent
    │   │
    │   ├─ Load extracted content
    │   ├─ Analyze sentiment via Azure OpenAI
    │   └─ Save sentiment results
    │
    ├─ Step 3: Summarizer Agent
    │   │
    │   ├─ Load all content
    │   ├─ Generate summaries (persona-based)
    │   └─ Save summaries
    │
    └─ Step 4: Analytics Agent
        │
        ├─ Load all previous outputs
        ├─ Perform deep analysis
        └─ Save analytical insights
    │
    ▼
Update plan status to COMPLETED
    │
    ▼
Return results to frontend
```

### 4. Export Flow

```
User requests export (MD/PDF/JSON)
    │
    ▼
POST /api/export/{format}
    │
    ▼
Export Service:
  • Loads plan + steps + messages
  • Formats data for export type
  • Generates file (MD/PDF/JSON)
    │
    ▼
Return file to user for download
```

## Agent Interaction Patterns

### Pattern 1: Sequential Processing (Common Case)

```
Planner
  │
  ▼
Step 1: Multimodal Processor
  │ (Handoff Pattern)
  ├─ Process audio → transcription
  ├─ Process video → transcription
  └─ Process PDF → text content
  │
  ▼
Step 2: Sentiment Agent
  │ (Handoff Pattern)
  └─ Analyze all transcriptions
  │
  ▼
Step 3: Summarizer Agent
  │ (Handoff Pattern)
  └─ Create executive summary
  │
  ▼
Step 4: Analytics Agent
  │ (Handoff Pattern)
  └─ Extract insights & recommendations
  │
  ▼
Complete
```

### Pattern 2: Collaborative Analysis (Complex Case)

```
Planner
  │
  ▼
Step 1: Multimodal Processor
  │ (Handoff Pattern)
  └─ Extract content from all files
  │
  ▼
Step 2: Multi-Agent Collaboration
  │ (GroupChat Pattern)
  │
  ├─ Sentiment Agent ─┐
  ├─ Summarizer Agent ─┤→ Discuss findings
  └─ Analytics Agent ──┘
  │
  ▼
Step 3: Synthesis
  │ (Handoff Pattern)
  └─ Summarizer creates final report
  │
  ▼
Complete
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.0
- **Agent Framework**: Microsoft Agent Framework (custom)
- **AI**: Azure OpenAI (GPT-4)
- **Speech**: Azure Speech Services
- **Document**: Azure Document Intelligence
- **Database**: Azure CosmosDB
- **Storage**: Local filesystem + optional Azure Blob
- **Logging**: structlog + OpenTelemetry
- **Video**: moviepy
- **PDF**: Azure Form Recognizer SDK

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build**: Vite
- **Styling**: TailwindCSS
- **State**: React Query
- **Icons**: Lucide React
- **HTTP**: Fetch API / Axios

### Infrastructure
- **Hosting**: Azure App Service (planned)
- **Monitoring**: Azure Application Insights
- **Auth**: Azure AD (Easy Auth)

## Security Considerations

1. **File Upload**
   - Size limits enforced (100MB default)
   - File type validation
   - Antivirus scanning (recommended for production)

2. **Authentication**
   - Azure AD integration
   - Token-based authentication
   - User isolation (session-based)

3. **Data Privacy**
   - Extracted content stored per session
   - User-specific access controls
   - Data retention policies

4. **API Security**
   - CORS configuration
   - Rate limiting (recommended)
   - Input validation
   - Error sanitization

## Scalability Patterns

1. **Horizontal Scaling**
   - Stateless backend (can run multiple instances)
   - CosmosDB auto-scaling
   - Azure App Service scaling

2. **Async Processing**
   - File processing is asynchronous
   - Background task execution
   - Status polling pattern

3. **Caching**
   - Extracted content cached locally
   - Agent results cached in memory
   - CosmosDB query optimization

4. **Resource Management**
   - Connection pooling
   - Timeout configurations
   - Graceful degradation

## Monitoring & Observability

```
Application Insights
    │
    ├─ Request Tracking
    ├─ Dependency Tracking (Azure services)
    ├─ Exception Tracking
    ├─ Performance Metrics
    └─ Custom Events
        │
        ├─ File Upload Events
        ├─ Processing Events
        ├─ Agent Execution Events
        └─ Export Events
```

## Future Enhancements

1. **Real-time Updates**: WebSocket support for live progress
2. **Batch Processing**: Process multiple sessions in parallel
3. **Custom Agents**: User-defined agents via configuration
4. **Advanced Analytics**: ML-based pattern recognition
5. **Collaboration**: Multi-user sessions
6. **API Gateway**: Azure API Management integration
7. **CI/CD**: Automated deployment pipelines
8. **Testing**: Comprehensive test suite

---

This architecture provides a solid foundation for a multimodal AI agent application with room for growth and enhancement.

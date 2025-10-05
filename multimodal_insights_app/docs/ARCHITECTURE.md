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

This architecture provides a solid foundation for a production-grade multimodal AI agent application with room for growth and enhancement.

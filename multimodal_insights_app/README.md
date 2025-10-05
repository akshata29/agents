# Multimodal Insights Application

A production-grade multi-agent system built on the Microsoft Agent Framework for processing and analyzing multimodal content (audio, video, PDF) through coordinated AI agents.

## Overview

This application provides comprehensive multimodal content analysis capabilities through specialized AI agents that process, extract, analyze, and synthesize insights from various input formats. It features a Custom Copilot-style experience where users can upload multiple files and receive intelligent, context-aware analysis.

## Key Features

- **Multimodal Input Processing**: Upload and process audio, video, and PDF files
- **Azure AI Integration**: Leverages Azure Speech-to-Text and Document Intelligence
- **Intelligent Agent Orchestration**: Dynamic planning and execution using Microsoft Agent Framework patterns
- **Sentiment Analysis**: Deep sentiment analysis on extracted content
- **Flexible Summarization**: Generate multiple summaries with persona-based customization
- **Dynamic Analytics**: Context-aware analytics with intelligent insights extraction
- **Real-time Progress Tracking**: Live updates as agents process tasks
- **Export Capabilities**: Export results in Markdown, PDF, and other formats

## Architecture

```
multimodal_insights_app/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── agents/      # Agent implementations
│   │   │   ├── multimodal_processor_agent.py  # Audio/Video/PDF processing
│   │   │   ├── sentiment_agent.py              # Sentiment analysis
│   │   │   ├── summarizer_agent.py            # Flexible summarization
│   │   │   ├── analytics_agent.py             # Dynamic analytics
│   │   │   └── planner_agent.py               # ReAct-based planner
│   │   ├── routers/     # API routes
│   │   ├── services/    # Core services (orchestrator, file handler)
│   │   ├── models/      # Request/response DTOs
│   │   ├── persistence/ # CosmosDB integration
│   │   ├── infra/       # Settings, telemetry
│   │   ├── auth/        # Authentication
│   │   └── tools/       # Agent tools
│   ├── data/            # Extracted content storage (JSON)
│   └── uploads/         # Temporary file uploads
├── frontend/            # React + TypeScript + Vite UI
│   └── src/
│       ├── components/  # UI components
│       ├── hooks/       # React hooks
│       └── lib/         # Utilities
├── docs/                # Documentation
└── scripts/             # Dev and deployment scripts
```

## Agents

### Multimodal Processor Agent
- **Audio Processing**: Transcription via Azure Speech-to-Text
- **Video Processing**: Extract audio + transcription, frame analysis
- **PDF Processing**: Content extraction via Azure Document Intelligence
- **Metadata Extraction**: Extract and store comprehensive metadata
- **Local Storage**: Store extracted content in JSON format

### Sentiment Analysis Agent
- Multi-dimensional sentiment analysis
- Emotion detection
- Tone and intent classification
- Speaker/section-based sentiment tracking
- Confidence scoring

### Summarizer Agent
- Multi-level summarization (brief, detailed, comprehensive)
- Persona-based summaries (executive, technical, general audience)
- Multi-document synthesis
- Key points extraction
- Customizable summary formats

### Analytics Agent
- Context-aware analytics
- Dynamic insight generation
- Pattern recognition
- Product/service analysis
- Recommendation extraction
- Next-best-action identification
- Trend analysis

### Planner Agent (ReAct Pattern)
- Dynamic task planning
- Iterative reasoning
- Agent capability assessment
- Step-by-step execution planning
- Human-in-the-loop approval workflow

## Orchestration Patterns

The application uses Microsoft Agent Framework patterns:

### 1. ReAct Pattern (Planning)
- Used by Planner Agent for dynamic plan generation
- Observe → Think → Act → Reflect loop
- Adapts to user objectives and available files

### 2. Handoff Pattern (Execution)
- Single-agent tasks with specialist delegation
- Used for straightforward processing tasks

### 3. GroupChat Pattern (Collaboration)
- Multi-agent collaboration for complex analysis
- Used when multiple perspectives are needed

## Tech Stack

### Backend
- **Framework**: FastAPI + Microsoft Agent Framework
- **AI Services**: Azure OpenAI, Azure Speech, Azure Document Intelligence
- **Storage**: Azure CosmosDB (persistence), Local JSON (extracted content)
- **Auth**: Azure AD integration

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **State Management**: React Query
- **UI Components**: Lucide Icons

## API Endpoints

### Task Management
- `POST /api/input_task` - Create plan from objective with file uploads
- `GET /api/plans/{session_id}/{plan_id}` - Get plan details
- `POST /api/plans/{session_id}/{plan_id}/approve` - Approve plan steps
- `POST /api/plans/{session_id}/{plan_id}/execute` - Execute approved steps
- `GET /api/plans/{session_id}/{plan_id}/status` - Get execution status

### File Management
- `POST /api/upload` - Upload multimodal files
- `GET /api/files/{session_id}` - List uploaded files
- `GET /api/extracted/{session_id}` - Get extracted content

### Export
- `POST /api/export/markdown` - Export as Markdown
- `POST /api/export/pdf` - Export as PDF
- `POST /api/export/json` - Export as JSON

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Azure subscription with:
  - Azure OpenAI
  - Azure Speech Services
  - Azure Document Intelligence
  - Azure CosmosDB

### Installation

1. **Clone the repository**
```bash
cd d:\repos\agent_foundation\multimodal_insights_app
```

2. **Setup Backend**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. **Configure Environment**
Create `.env` file in `backend/` directory:
```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Speech
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=eastus

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-doc-intel-key

# Azure CosmosDB
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
COSMOS_DATABASE=multimodal_insights
COSMOS_CONTAINER=tasks

# Application
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
MAX_UPLOAD_SIZE=104857600  # 100MB
```

4. **Setup Frontend**
```powershell
cd ..\frontend
npm install
```

5. **Run Application**

Backend:
```powershell
cd backend
.\start.ps1
```

Frontend:
```powershell
cd frontend
npm run dev
```

Access the application at: `http://localhost:5173`

## Usage

### Basic Workflow

1. **Upload Files**: Upload audio, video, or PDF files
2. **Enter Objective**: Describe what you want to analyze
3. **Review Plan**: System generates execution plan with steps
4. **Approve Steps**: Review and approve planned steps
5. **Monitor Execution**: Watch real-time progress as agents work
6. **Review Results**: Examine insights, summaries, and analytics
7. **Export**: Download results in preferred format

### Example Use Cases

#### Customer Call Analysis
- Upload: Audio recording of customer call
- Objective: "Analyze this customer call for sentiment, products discussed, and recommendations"
- Agents: Processor → Sentiment → Analytics → Summarizer

#### Multi-Document Research
- Upload: Multiple PDFs and audio files
- Objective: "Synthesize key insights and create executive summary"
- Agents: Processor → Summarizer (persona: executive) → Analytics

#### Video Content Analysis
- Upload: Marketing video
- Objective: "Analyze tone, key messages, and audience sentiment"
- Agents: Processor → Sentiment → Analytics

## Development

### Running Tests
```powershell
cd backend
pytest
```

### Code Formatting
```powershell
black app/
ruff check app/
```

### Build Frontend
```powershell
cd frontend
npm run build
```

## Architecture Patterns

This application implements:
- **ReAct Pattern**: Dynamic planning with iterative reasoning
- **Handoff Pattern**: Single-agent task execution with delegation
- **GroupChat Pattern**: Multi-agent collaboration
- **Human-in-the-Loop**: Approval workflow for all executions
- **Event-Driven Progress**: Real-time status updates via WebSockets

## License

MIT License

## Contributing

Contributions welcome! Please follow the existing code structure and patterns from `finagent_dynamic_app`.

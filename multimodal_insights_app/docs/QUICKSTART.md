# Quickstart

Launch the Multimodal Insights App locally and run your first multimodal analysis.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Azure resources: OpenAI, Speech, Document Intelligence, optional Cosmos DB
- Corresponding API keys or service principal credentials

## 1. Backend Setup

```powershell
cd multimodal_insights_app/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# edit .env and provide:
#   AZURE_OPENAI_ENDPOINT / KEY / DEPLOYMENT
#   AZURE_SPEECH_KEY / REGION
#   AZURE_DOCUMENT_INTELLIGENCE_* values
#   COSMOSDB_* (optional for persistence)
uvicorn app.main:app --reload --port 8000
```

Backend should report `Uvicorn running on http://0.0.0.0:8000`.

## 2. Frontend Setup

```powershell
cd ../frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
npm run dev -- --port 5173
```

Open `http://localhost:5173` in your browser.

## 3. Run A Sample Analysis

1. Upload audio/video/PDF files (drag-and-drop or click to browse).
2. Enter an objective such as `Summarize these documents and capture sentiment`.
3. Review the generated execution plan and approve the steps.
4. Watch the execution monitor stream progress and agent outputs.
5. Download results via the export panel (Markdown, PDF, JSON).

## Troubleshooting

- **Audio transcription fails** → confirm file format support, Speech key/region, and Azure quota.
- **PDF extraction errors** → ensure files are not password protected and Document Intelligence keys are valid.
- **Cosmos DB connectivity** → supply `COSMOSDB_KEY` or TENANT/CLIENT/SECRET and verify firewall rules.
- **Frontend cannot reach backend** → check `VITE_API_BASE_URL`, restart `npm run dev`, and verify port 8000 availability.

## Next Steps

- Review [ARCHITECTURE.md](ARCHITECTURE.md) for component flow and integrations.
- Study [MAF_PATTERN_INTEGRATION.md](MAF_PATTERN_INTEGRATION.md) to customize orchestration patterns.
- Enable telemetry via `APPLICATIONINSIGHTS_CONNECTION_STRING` to observe agent traces in Azure.

Happy analyzing!
# Quick Start Guide - Multimodal Insights Application

## Overview

This guide will help you get started with the Multimodal Insights Application - a comprehensive AI-powered system for processing and analyzing audio, video, and PDF files.

## Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm
- Azure subscription with:
  - Azure OpenAI Service
  - Azure Speech Services
  - Azure Document Intelligence (Form Recognizer)
  - Azure CosmosDB
- Azure CLI (for service principal creation)

## Authentication Setup

### Recommended: Azure AD Authentication

For secure production deployments, use Azure AD instead of keys:

```bash
# Create service principal
az login
az ad sp create-for-rbac --name multimodal-insights-app --role Contributor

# Assign Cosmos DB permissions
az role assignment create \
  --assignee YOUR_CLIENT_ID \
  --role "Cosmos DB Account Contributor" \
  --scope YOUR_COSMOS_RESOURCE_ID
```

**📖 Detailed authentication guide:** See [`AZURE_AUTHENTICATION.md`](AZURE_AUTHENTICATION.md)

## Quick Setup

### 1. Backend Setup

```powershell
# Navigate to backend directory
cd multimodal_insights_app\backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the `backend/` directory:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Azure Speech Services
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=eastus

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-doc-intel-key

# Azure CosmosDB (optional for local dev)
COSMOSDB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOSDB_KEY=your-cosmos-key
COSMOSDB_DATABASE=multimodal_insights
COSMOSDB_CONTAINER=tasks

# Application Settings
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
MAX_UPLOAD_SIZE=104857600
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

### 3. Frontend Setup

```powershell
# Navigate to frontend directory
cd ..\frontend

# Install dependencies
npm install
```

### 4. Run the Application

**Terminal 1 - Backend:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

Access the application at: **http://localhost:5173**

## Basic Usage

### 1. Upload Files

- Click the upload area or drag and drop files
- Supported formats: Audio (.mp3, .wav, .m4a), Video (.mp4, .avi, .mov), PDF (.pdf)
- Multiple files can be uploaded

### 2. Enter Your Request

Examples:
- "Analyze the sentiment in this customer call"
- "Summarize these documents for an executive audience"
- "Extract key insights and recommendations from the uploaded content"
- "Perform deep analytics on the conversation and identify next best actions"

### 3. Review and Monitor

- The system creates an execution plan
- Watch real-time progress as agents process your request
- View intermediate results from each agent

### 4. Export Results

- Download results in Markdown, PDF, or JSON format
- Results include all analyses, summaries, and insights

## Example Workflows

### Customer Call Analysis
```
Upload: customer_call.mp3
Request: "Analyze this customer call for sentiment, products discussed, pain points, and recommendations"

Agents Used:
1. Multimodal Processor → Transcribes audio
2. Sentiment Agent → Analyzes sentiment and emotions
3. Analytics Agent → Extracts products, pain points, recommendations
4. Summarizer Agent → Creates executive summary
```

### Multi-Document Research
```
Upload: report1.pdf, report2.pdf, meeting_notes.pdf
Request: "Synthesize key findings across all documents and provide an executive summary"

Agents Used:
1. Multimodal Processor → Extracts content from all PDFs
2. Summarizer Agent → Synthesizes multi-document insights
3. Analytics Agent → Identifies patterns and trends
```

### Video Content Analysis
```
Upload: marketing_video.mp4
Request: "Analyze the tone, key messages, and overall sentiment of this video"

Agents Used:
1. Multimodal Processor → Extracts and transcribes audio
2. Sentiment Agent → Analyzes tone and sentiment
3. Analytics Agent → Extracts key messages
4. Summarizer Agent → Provides summary
```

## Architecture

### Agents

1. **Planner Agent** (ReAct Pattern)
   - Creates execution plans
   - Determines which agents to use
   - Sequences operations

2. **Multimodal Processor Agent**
   - Transcribes audio (Azure Speech-to-Text)
   - Processes video (extracts audio + transcribes)
   - Extracts PDF content (Azure Document Intelligence)

3. **Sentiment Agent**
   - Multi-dimensional sentiment analysis
   - Emotion detection
   - Tone analysis
   - Speaker tracking

4. **Summarizer Agent**
   - Multiple summary levels (brief, detailed, comprehensive)
   - Persona-based (executive, technical, general)
   - Multi-document synthesis

5. **Analytics Agent**
   - Context-aware analytics
   - Pattern recognition
   - Product/service analysis
   - Recommendation extraction
   - Next-best-action identification

### Orchestration Patterns

- **ReAct Pattern**: Used for planning (iterative reasoning)
- **Handoff Pattern**: Used for sequential agent tasks
- **GroupChat Pattern**: Used for collaborative analysis

## API Endpoints

### Task Management
- `POST /api/input_task` - Create new task with files
- `GET /api/plans/{session_id}/{plan_id}` - Get plan details
- `POST /api/plans/{session_id}/{plan_id}/execute` - Execute plan
- `GET /api/plans/{session_id}/{plan_id}/status` - Get execution status

### File Management
- `POST /api/upload` - Upload files
- `GET /api/files/{session_id}` - List session files
- `GET /api/extracted/{session_id}/{file_id}` - Get extracted content

### Export
- `POST /api/export/markdown` - Export as Markdown
- `POST /api/export/pdf` - Export as PDF
- `POST /api/export/json` - Export as JSON

## Development

### Run Tests
```powershell
cd backend
pytest
```

### Code Formatting
```powershell
black app/
ruff check app/
```

### Build for Production
```powershell
cd frontend
npm run build
```

## Troubleshooting

### Audio Transcription Issues
- Ensure audio file format is supported
- Check Azure Speech Services quota
- Verify AZURE_SPEECH_KEY and AZURE_SPEECH_REGION

### PDF Processing Issues
- Ensure PDF is not password-protected
- Check Azure Document Intelligence quota
- Verify AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and KEY

### General Issues
- Check all Azure service keys are valid
- Verify network connectivity to Azure services
- Check backend logs for detailed error messages

## Next Steps

1. Review the [Architecture Documentation](ARCHITECTURE.md)
2. Explore [Agent Implementation Guide](../docs/framework/pattern-reference.md)
3. Customize agents for your specific use case
4. Deploy to Azure App Service

## Support

For issues and questions:
- Check the logs in `backend/magentic_foundation.log`
- Review Azure service quotas and limits
- Consult Azure documentation for service-specific issues

# Advisor Productivity App - Backend

FastAPI backend for the Advisor Productivity Application.

## Quick Start

### 1. Setup Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```powershell
# Copy environment template
cp .env.example .env

# Edit .env with your Azure credentials
# Required: AZURE_OPENAI_*, AZURE_SPEECH_*, AZURE_LANGUAGE_*, COSMOSDB_*
```

### 3. Run Backend

```powershell
# Using start script (recommended)
.\start.ps1

# Or manually
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test

```
# Health check
curl http://localhost:8000/health

# API documentation
Open http://localhost:8000/docs
```

## Project Structure

```
backend/
├── app/
│   ├── main.py                         # FastAPI application
│   ├── agents/
│   │   └── speech_transcription_agent.py  # Real-time transcription
│   ├── models/
│   │   └── task_models.py             # Data models
│   ├── routers/
│   │   └── transcription.py           # WebSocket & REST endpoints
│   ├── infra/
│   │   └── settings.py                # Configuration
│   └── helpers/
├── uploads/                            # Temporary audio uploads
├── data/                              # Transcription results
├── requirements.txt
├── .env.example
└── start.ps1
```

## Features Implemented (Phase 2)

✅ Speech Transcription Agent
- Real-time audio transcription
- Financial terminology optimization
- Speaker identification (advisor/client)
- Word-level timestamps
- Confidence scores

✅ WebSocket Endpoint
- `/ws/transcribe` - Real-time streaming
- Interim and final results
- Session management

✅ REST Endpoints
- `GET /health` - Health check
- `GET /api/config` - Configuration
- `GET /api/transcription/session/{id}/transcript` - Get transcript
- `POST /api/transcription/session/{id}/stop` - Stop session

## WebSocket Protocol

### Connect
```javascript
const ws = new WebSocket('ws://localhost:8000/api/transcription/ws/transcribe?session_id=123');
```

### Send Audio (Binary)
```javascript
// PCM 16-bit, 16kHz, mono
ws.send(audioData);
```

### Receive Results
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'interim') {
    // Partial result
    console.log('Interim:', data.text);
  } else if (data.type === 'final') {
    // Final result
    console.log('Final:', data.segment);
  }
};
```

## Testing

```powershell
# Test agent initialization
python test_agent.py
```

## Next Steps

- [ ] Phase 3: Sentiment Analysis Agent
- [ ] Phase 4: Recommendation Agent
- [ ] Phase 5: Summarization Agent
- [ ] Phase 6: Entity & PII Agent

## API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

# API Documentation

## Multimodal Insights API - Complete REST API Reference

Base URL: `http://localhost:8000`

---

## 📋 **Table of Contents**

1. [Orchestration Endpoints](#orchestration-endpoints)
2. [File Management Endpoints](#file-management-endpoints)
3. [Export Endpoints](#export-endpoints)
4. [Health & Status Endpoints](#health--status-endpoints)
5. [Usage Examples](#usage-examples)

---

## 🎯 **Orchestration Endpoints**

### Create Plan

Create an execution plan from user objective and uploaded files.

**Endpoint:** `POST /api/orchestration/plans`

**Request Body:**
```json
{
  "session_id": "session-123",
  "user_id": "user-456",
  "description": "Analyze the sentiment and create a summary of the uploaded audio files",
  "file_ids": ["file-1", "file-2"],
  "metadata": {
    "source": "web_ui"
  }
}
```

**Response:** `201 Created`
```json
{
  "id": "plan-789",
  "session_id": "session-123",
  "user_id": "user-456",
  "initial_goal": "Analyze the sentiment...",
  "overall_status": "pending",
  "total_steps": 3,
  "completed_steps": 0,
  "failed_steps": 0,
  "steps": [
    {
      "id": "step-1",
      "order": 0,
      "action": "Process 2 uploaded file(s)...",
      "agent": "multimodal_processor",
      "status": "pending"
    }
  ]
}
```

---

### Execute Plan

Execute a plan in the background.

**Endpoint:** `POST /api/orchestration/plans/{plan_id}/execute`

**Request Body:**
```json
{
  "session_id": "session-123",
  "action": "execute"
}
```

**Response:** `200 OK`
```json
{
  "status": "accepted",
  "message": "Plan execution started for plan plan-789",
  "data": {
    "plan_id": "plan-789",
    "session_id": "session-123",
    "total_steps": 3
  }
}
```

---

### Get Plan Status

Get real-time execution status of a plan.

**Endpoint:** `GET /api/orchestration/plans/{plan_id}/status?session_id=session-123`

**Response:** `200 OK`
```json
{
  "plan_id": "plan-789",
  "session_id": "session-123",
  "overall_status": "in_progress",
  "current_step": "Analyze sentiment and emotions in the content",
  "current_agent": "sentiment",
  "completed_steps": 1,
  "total_steps": 3,
  "progress_percentage": 33.3,
  "recent_messages": [
    "Processing file audio_meeting.mp3...",
    "Transcription completed: 1234 words",
    "Analyzing sentiment..."
  ]
}
```

---

### Get Plan Details

Get complete plan with all steps.

**Endpoint:** `GET /api/orchestration/plans/{plan_id}?session_id=session-123`

**Response:** `200 OK`
```json
{
  "id": "plan-789",
  "session_id": "session-123",
  "user_id": "user-456",
  "initial_goal": "Analyze the sentiment...",
  "overall_status": "completed",
  "total_steps": 3,
  "completed_steps": 3,
  "failed_steps": 0,
  "steps": [
    {
      "id": "step-1",
      "order": 0,
      "action": "Process uploaded files",
      "agent": "multimodal_processor",
      "status": "completed",
      "agent_reply": "{\"processed_files\": 2, ...}"
    }
  ]
}
```

---

### Execute Direct (Convenience Endpoint)

Create plan and execute in one call.

**Endpoint:** `POST /api/orchestration/execute-direct`

**Request Body:**
```json
{
  "session_id": "session-123",
  "user_id": "user-456",
  "description": "Summarize the uploaded PDF documents",
  "file_ids": ["file-1", "file-2"]
}
```

**Response:** `200 OK`
```json
{
  "status": "accepted",
  "message": "Plan created and execution started",
  "data": {
    "plan_id": "plan-790",
    "session_id": "session-123",
    "total_steps": 2,
    "steps": [
      {
        "order": 0,
        "action": "Process 2 uploaded file(s)...",
        "agent": "multimodal_processor"
      },
      {
        "order": 1,
        "action": "Create detailed summary...",
        "agent": "summarizer"
      }
    ]
  }
}
```

---

## 📁 **File Management Endpoints**

### Upload Files

Upload one or more files (audio, video, or PDF).

**Endpoint:** `POST /api/files/upload`

**Request:** `multipart/form-data`
- `files`: List of files to upload
- `session_id`: Session ID
- `user_id`: User ID (optional, defaults to "default_user")

**Supported Formats:**
- Audio: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`
- Video: `.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`
- PDF: `.pdf`

**Response:** `201 Created`
```json
{
  "status": "success",
  "message": "Successfully uploaded 2 file(s)",
  "data": {
    "session_id": "session-123",
    "files": [
      {
        "id": "file-1",
        "filename": "meeting_recording.mp3",
        "file_type": "audio",
        "file_size": 5242880
      },
      {
        "id": "file-2",
        "filename": "presentation.pdf",
        "file_type": "pdf",
        "file_size": 1048576
      }
    ]
  }
}
```

---

### List Session Files

List all files for a session.

**Endpoint:** `GET /api/files/session/{session_id}`

**Response:** `200 OK`
```json
[
  {
    "id": "file-1",
    "session_id": "session-123",
    "user_id": "user-456",
    "filename": "meeting_recording.mp3",
    "file_type": "audio",
    "file_size": 5242880,
    "processing_status": "completed",
    "uploaded_at": "2025-10-04T10:30:00Z",
    "processed_at": "2025-10-04T10:31:00Z"
  }
]
```

---

### Get File Metadata

Get metadata for a specific file.

**Endpoint:** `GET /api/files/{file_id}?session_id=session-123`

**Response:** `200 OK`
```json
{
  "id": "file-1",
  "session_id": "session-123",
  "user_id": "user-456",
  "filename": "meeting_recording.mp3",
  "file_type": "audio",
  "file_size": 5242880,
  "file_path": "uploads/session-123/meeting_recording.mp3",
  "processing_status": "completed",
  "uploaded_at": "2025-10-04T10:30:00Z",
  "processed_at": "2025-10-04T10:31:00Z"
}
```

---

### Download File

Download original uploaded file.

**Endpoint:** `GET /api/files/{file_id}/download?session_id=session-123`

**Response:** `200 OK` (Binary file download)

---

### Delete File

Delete a file and its metadata.

**Endpoint:** `DELETE /api/files/{file_id}?session_id=session-123`

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "File meeting_recording.mp3 deleted successfully",
  "data": {
    "file_id": "file-1"
  }
}
```

---

## 📤 **Export Endpoints**

### Export Plan Results

Export plan execution results in specified format.

**Endpoint:** `POST /api/export/plans/{plan_id}`

**Query Parameters:**
- `session_id` (required): Session ID
- `export_format` (optional): Export format (`markdown`, `pdf`, `json`, `html`)
- `include_metadata` (optional): Include metadata (default: `true`)

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "Results exported successfully as markdown",
  "data": {
    "filename": "insights_report_plan789_20251004_103000.md",
    "format": "markdown",
    "size_bytes": 12345,
    "download_url": "/api/export/download/insights_report_plan789_20251004_103000.md"
  }
}
```

---

### Download Export

Download an exported file.

**Endpoint:** `GET /api/export/download/{filename}`

**Response:** `200 OK` (File download with appropriate media type)

---

### List Exports

List all available exports.

**Endpoint:** `GET /api/export/list?session_id=session-123`

**Response:** `200 OK`
```json
[
  {
    "filename": "insights_report_plan789_20251004_103000.md",
    "file_path": "exports/insights_report_plan789_20251004_103000.md",
    "format": "md",
    "size_bytes": 12345,
    "created_at": "2025-10-04T10:30:00",
    "download_url": "/api/export/download/insights_report_plan789_20251004_103000.md"
  }
]
```

---

### Delete Export

Delete an export file.

**Endpoint:** `DELETE /api/export/{filename}`

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "Export insights_report_plan789_20251004_103000.md deleted successfully",
  "data": {
    "filename": "insights_report_plan789_20251004_103000.md"
  }
}
```

---

## ❤️ **Health & Status Endpoints**

### Health Check

**Endpoint:** `GET /health`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "service": "multimodal-insights-api",
  "timestamp": "2025-10-04T10:30:00Z"
}
```

---

### API Information

**Endpoint:** `GET /`

**Response:** `200 OK`
```json
{
  "name": "Multimodal Insights API",
  "version": "1.0.0",
  "description": "Multi-agent system for multimodal content analysis",
  "features": [
    "Multimodal file processing (audio, video, PDF)",
    "Azure AI service integration",
    "Sentiment analysis",
    "Flexible summarization",
    "Dynamic analytics",
    "Export to multiple formats"
  ],
  "agents": [
    "Planner Agent (ReAct pattern)",
    "Multimodal Processor Agent",
    "Sentiment Analysis Agent",
    "Summarizer Agent",
    "Analytics Agent"
  ]
}
```

---

## 💡 **Usage Examples**

### Example 1: Complete Workflow

```bash
# 1. Upload files
curl -X POST http://localhost:8000/api/files/upload \
  -F "files=@meeting.mp3" \
  -F "files=@slides.pdf" \
  -F "session_id=my-session" \
  -F "user_id=john@example.com"

# Response: { "data": { "files": [{ "id": "file-1" }, { "id": "file-2" }] } }

# 2. Create and execute plan
curl -X POST http://localhost:8000/api/orchestration/execute-direct \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session",
    "user_id": "john@example.com",
    "description": "Analyze sentiment and create executive summary",
    "file_ids": ["file-1", "file-2"]
  }'

# Response: { "data": { "plan_id": "plan-123" } }

# 3. Check status
curl http://localhost:8000/api/orchestration/plans/plan-123/status?session_id=my-session

# 4. Export results
curl -X POST "http://localhost:8000/api/export/plans/plan-123?session_id=my-session&export_format=pdf"

# Response: { "data": { "download_url": "/api/export/download/insights_report_plan123_20251004.pdf" } }

# 5. Download export
curl http://localhost:8000/api/export/download/insights_report_plan123_20251004.pdf \
  --output report.pdf
```

---

### Example 2: Python Client

```python
import requests
import time

BASE_URL = "http://localhost:8000"
session_id = "my-session"
user_id = "john@example.com"

# Upload files
files = [
    ("files", open("meeting.mp3", "rb")),
    ("files", open("slides.pdf", "rb"))
]
data = {
    "session_id": session_id,
    "user_id": user_id
}
response = requests.post(f"{BASE_URL}/api/files/upload", files=files, data=data)
file_ids = [f["id"] for f in response.json()["data"]["files"]]

# Create and execute plan
task = {
    "session_id": session_id,
    "user_id": user_id,
    "description": "Analyze sentiment and summarize the content",
    "file_ids": file_ids
}
response = requests.post(f"{BASE_URL}/api/orchestration/execute-direct", json=task)
plan_id = response.json()["data"]["plan_id"]

# Poll status
while True:
    response = requests.get(
        f"{BASE_URL}/api/orchestration/plans/{plan_id}/status",
        params={"session_id": session_id}
    )
    status = response.json()
    print(f"Progress: {status['progress_percentage']}%")
    
    if status["overall_status"] in ["completed", "failed"]:
        break
    
    time.sleep(2)

# Export results
response = requests.post(
    f"{BASE_URL}/api/export/plans/{plan_id}",
    params={
        "session_id": session_id,
        "export_format": "markdown"
    }
)
download_url = response.json()["data"]["download_url"]

# Download export
response = requests.get(f"{BASE_URL}{download_url}")
with open("report.md", "wb") as f:
    f.write(response.content)

print("Analysis complete! Report saved to report.md")
```

---

## 🔒 **Error Responses**

All endpoints return standard HTTP status codes:

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service not initialized

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## 📊 **Status Values**

### Plan Status
- `pending`: Plan created, not yet executing
- `in_progress`: Plan is executing
- `completed`: All steps completed successfully
- `failed`: One or more steps failed

### Step Status
- `pending`: Step not yet started
- `executing`: Step currently running
- `completed`: Step finished successfully
- `failed`: Step encountered an error

### File Processing Status
- `pending`: File uploaded, not yet processed
- `processing`: File is being processed
- `completed`: Processing finished
- `failed`: Processing failed
- `deleted`: File marked as deleted

---

## 🎨 **Export Formats**

### Markdown (.md)
Clean, readable format with sections:
- Executive Summary
- Processed Files
- Analysis Results (per step)
- Metadata

### HTML (.html)
Styled web page with:
- Professional CSS styling
- Color-coded status badges
- Responsive design
- Code syntax highlighting

### PDF (.pdf)
Print-ready document:
- Professional layout
- Generated via WeasyPrint or ReportLab
- Fallback to HTML if PDF generation unavailable

### JSON (.json)
Structured data format:
- Complete plan data
- All steps with results
- File metadata
- Message history
- Machine-readable

---

## 📚 **Additional Resources**

- [QUICKSTART.md](../docs/QUICKSTART.md) - Quick start guide
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System architecture
- [GETTING_STARTED.md](../GETTING_STARTED.md) - Development guide
- [README.md](../README.md) - Project overview

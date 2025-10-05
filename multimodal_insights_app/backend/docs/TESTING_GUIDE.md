# Backend Testing Guide

## Testing the Multimodal Insights Backend API

This guide provides step-by-step instructions for testing the complete backend API.

---

## 🚀 **Prerequisites**

### 1. Environment Setup

Ensure you have a `.env` file in `backend/` with:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Azure Speech Services
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=eastus

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-doc-intel-key

# Azure Cosmos DB
AZURE_COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
AZURE_COSMOS_KEY=your-cosmos-key
AZURE_COSMOS_DATABASE_NAME=multimodal_insights
AZURE_COSMOS_CONTAINER_NAME=sessions

# Application Settings
BACKEND_HOST=localhost
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 2. Install Dependencies

```powershell
# Navigate to backend directory
cd backend

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Start the Backend

```powershell
# Using start script
.\start.ps1

# Or directly with uvicorn
uvicorn app.main:app --reload --host localhost --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 🧪 **Testing with cURL**

### Test 1: Health Check

```powershell
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "multimodal-insights-api",
  "timestamp": "2025-10-04T10:30:00.123456"
}
```

---

### Test 2: API Information

```powershell
curl http://localhost:8000/
```

**Expected Response:**
```json
{
  "name": "Multimodal Insights API",
  "version": "1.0.0",
  "description": "Multi-agent system for multimodal content analysis",
  "features": [...],
  "agents": [...],
  "patterns": [...]
}
```

---

### Test 3: Upload Files

```powershell
# Upload single audio file
curl -X POST http://localhost:8000/api/files/upload `
  -F "files=@test_audio.mp3" `
  -F "session_id=test-session-1" `
  -F "user_id=test-user"

# Upload multiple files
curl -X POST http://localhost:8000/api/files/upload `
  -F "files=@meeting.mp3" `
  -F "files=@presentation.pdf" `
  -F "session_id=test-session-1" `
  -F "user_id=test-user"
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Successfully uploaded 2 file(s)",
  "data": {
    "session_id": "test-session-1",
    "files": [
      {
        "id": "uuid-file-1",
        "filename": "meeting.mp3",
        "file_type": "audio",
        "file_size": 5242880
      },
      {
        "id": "uuid-file-2",
        "filename": "presentation.pdf",
        "file_type": "pdf",
        "file_size": 1048576
      }
    ]
  }
}
```

**Save the file IDs for next steps!**

---

### Test 4: List Session Files

```powershell
curl http://localhost:8000/api/files/session/test-session-1
```

**Expected Response:**
```json
[
  {
    "id": "uuid-file-1",
    "session_id": "test-session-1",
    "user_id": "test-user",
    "filename": "meeting.mp3",
    "file_type": "audio",
    "file_size": 5242880,
    "processing_status": "pending",
    "uploaded_at": "2025-10-04T10:30:00Z"
  }
]
```

---

### Test 5: Create and Execute Plan (Direct)

```powershell
# Create a JSON file: test_task.json
# {
#   "session_id": "test-session-1",
#   "user_id": "test-user",
#   "description": "Analyze the sentiment and create an executive summary of the uploaded files",
#   "file_ids": ["uuid-file-1", "uuid-file-2"]
# }

curl -X POST http://localhost:8000/api/orchestration/execute-direct `
  -H "Content-Type: application/json" `
  -d "@test_task.json"
```

**Expected Response:**
```json
{
  "status": "accepted",
  "message": "Plan created and execution started",
  "data": {
    "plan_id": "uuid-plan-1",
    "session_id": "test-session-1",
    "total_steps": 3,
    "steps": [
      {
        "order": 0,
        "action": "Process 2 uploaded file(s) to extract content...",
        "agent": "multimodal_processor"
      },
      {
        "order": 1,
        "action": "Analyze sentiment and emotions in the content",
        "agent": "sentiment"
      },
      {
        "order": 2,
        "action": "Create detailed summary for executive audience",
        "agent": "summarizer"
      }
    ]
  }
}
```

**Save the plan_id!**

---

### Test 6: Check Execution Status

```powershell
# Replace {plan_id} with your actual plan ID
curl "http://localhost:8000/api/orchestration/plans/{plan_id}/status?session_id=test-session-1"
```

**Expected Response (In Progress):**
```json
{
  "plan_id": "uuid-plan-1",
  "session_id": "test-session-1",
  "overall_status": "in_progress",
  "current_step": "Analyze sentiment and emotions in the content",
  "current_agent": "sentiment",
  "completed_steps": 1,
  "total_steps": 3,
  "progress_percentage": 33.33,
  "recent_messages": [
    "Processing file meeting.mp3...",
    "Transcription completed: 1234 words",
    "Analyzing sentiment..."
  ]
}
```

**Expected Response (Completed):**
```json
{
  "plan_id": "uuid-plan-1",
  "session_id": "test-session-1",
  "overall_status": "completed",
  "current_step": null,
  "current_agent": null,
  "completed_steps": 3,
  "total_steps": 3,
  "progress_percentage": 100.0,
  "recent_messages": [...]
}
```

---

### Test 7: Get Complete Plan Results

```powershell
curl "http://localhost:8000/api/orchestration/plans/{plan_id}?session_id=test-session-1"
```

**Expected Response:**
```json
{
  "id": "uuid-plan-1",
  "session_id": "test-session-1",
  "user_id": "test-user",
  "initial_goal": "Analyze the sentiment...",
  "overall_status": "completed",
  "total_steps": 3,
  "completed_steps": 3,
  "failed_steps": 0,
  "steps": [
    {
      "id": "step-1",
      "order": 0,
      "action": "Process 2 uploaded file(s)...",
      "agent": "multimodal_processor",
      "status": "completed",
      "agent_reply": "{\"processed_files\": 2, \"results\": {...}}"
    },
    {
      "id": "step-2",
      "order": 1,
      "action": "Analyze sentiment...",
      "agent": "sentiment",
      "status": "completed",
      "agent_reply": "{\"sentiment\": \"positive\", \"score\": 0.85, ...}"
    },
    {
      "id": "step-3",
      "order": 2,
      "action": "Create executive summary...",
      "agent": "summarizer",
      "status": "completed",
      "agent_reply": "{\"summary\": \"...\", \"key_points\": [...]}"
    }
  ]
}
```

---

### Test 8: Export Results

```powershell
# Export as Markdown
curl -X POST "http://localhost:8000/api/export/plans/{plan_id}?session_id=test-session-1&export_format=markdown"

# Export as HTML
curl -X POST "http://localhost:8000/api/export/plans/{plan_id}?session_id=test-session-1&export_format=html"

# Export as PDF
curl -X POST "http://localhost:8000/api/export/plans/{plan_id}?session_id=test-session-1&export_format=pdf"

# Export as JSON
curl -X POST "http://localhost:8000/api/export/plans/{plan_id}?session_id=test-session-1&export_format=json"
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Results exported successfully as markdown",
  "data": {
    "filename": "insights_report_uuid123_20251004_103000.md",
    "format": "markdown",
    "size_bytes": 12345,
    "download_url": "/api/export/download/insights_report_uuid123_20251004_103000.md"
  }
}
```

---

### Test 9: Download Export

```powershell
# Download the exported file
curl "http://localhost:8000/api/export/download/insights_report_uuid123_20251004_103000.md" `
  --output report.md
```

---

### Test 10: List All Exports

```powershell
curl http://localhost:8000/api/export/list
```

**Expected Response:**
```json
[
  {
    "filename": "insights_report_uuid123_20251004_103000.md",
    "file_path": "exports/insights_report_uuid123_20251004_103000.md",
    "format": "md",
    "size_bytes": 12345,
    "created_at": "2025-10-04T10:30:00",
    "download_url": "/api/export/download/insights_report_uuid123_20251004_103000.md"
  }
]
```

---

## 🧪 **Testing with Python**

### Complete Workflow Script

```python
"""
Complete backend testing script
"""

import requests
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"
session_id = "python-test-session"
user_id = "python-tester"

def test_health():
    """Test health check"""
    print("1. Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print(f"   ✓ Health: {response.json()['status']}")

def test_upload_files():
    """Test file upload"""
    print("\n2. Uploading test files...")
    
    # Create dummy files for testing
    test_audio = Path("test_audio.mp3")
    test_pdf = Path("test_doc.pdf")
    
    # In real scenario, use actual files
    files = [
        ("files", ("test_audio.mp3", open(test_audio, "rb") if test_audio.exists() else b"dummy", "audio/mpeg")),
    ]
    
    data = {
        "session_id": session_id,
        "user_id": user_id
    }
    
    response = requests.post(f"{BASE_URL}/api/files/upload", files=files, data=data)
    assert response.status_code == 201
    
    file_ids = [f["id"] for f in response.json()["data"]["files"]]
    print(f"   ✓ Uploaded {len(file_ids)} file(s)")
    return file_ids

def test_create_and_execute(file_ids):
    """Test plan creation and execution"""
    print("\n3. Creating and executing plan...")
    
    task = {
        "session_id": session_id,
        "user_id": user_id,
        "description": "Analyze sentiment and create an executive summary",
        "file_ids": file_ids
    }
    
    response = requests.post(f"{BASE_URL}/api/orchestration/execute-direct", json=task)
    assert response.status_code == 200
    
    plan_id = response.json()["data"]["plan_id"]
    total_steps = response.json()["data"]["total_steps"]
    print(f"   ✓ Plan created: {plan_id}")
    print(f"   ✓ Total steps: {total_steps}")
    return plan_id

def test_monitor_execution(plan_id):
    """Monitor execution progress"""
    print("\n4. Monitoring execution...")
    
    while True:
        response = requests.get(
            f"{BASE_URL}/api/orchestration/plans/{plan_id}/status",
            params={"session_id": session_id}
        )
        assert response.status_code == 200
        
        status = response.json()
        progress = status["progress_percentage"]
        overall_status = status["overall_status"]
        
        print(f"   Progress: {progress:.1f}% - Status: {overall_status}")
        
        if status["current_step"]:
            print(f"   Current: {status['current_step']}")
        
        if overall_status in ["completed", "failed"]:
            break
        
        time.sleep(2)
    
    print(f"   ✓ Execution {overall_status}")
    return overall_status == "completed"

def test_get_results(plan_id):
    """Get complete plan results"""
    print("\n5. Retrieving results...")
    
    response = requests.get(
        f"{BASE_URL}/api/orchestration/plans/{plan_id}",
        params={"session_id": session_id}
    )
    assert response.status_code == 200
    
    plan = response.json()
    print(f"   ✓ Retrieved plan with {len(plan['steps'])} steps")
    
    for step in plan["steps"]:
        print(f"   - Step {step['order']}: {step['status']}")
    
    return plan

def test_export(plan_id):
    """Test export functionality"""
    print("\n6. Exporting results...")
    
    formats = ["markdown", "html", "json"]
    exports = []
    
    for fmt in formats:
        response = requests.post(
            f"{BASE_URL}/api/export/plans/{plan_id}",
            params={
                "session_id": session_id,
                "export_format": fmt
            }
        )
        assert response.status_code == 200
        
        filename = response.json()["data"]["filename"]
        exports.append(filename)
        print(f"   ✓ Exported as {fmt}: {filename}")
    
    return exports

def test_download_export(filename):
    """Test export download"""
    print("\n7. Downloading export...")
    
    response = requests.get(f"{BASE_URL}/api/export/download/{filename}")
    assert response.status_code == 200
    
    output_file = Path(filename)
    output_file.write_bytes(response.content)
    print(f"   ✓ Downloaded: {filename} ({len(response.content)} bytes)")

def main():
    """Run all tests"""
    print("=" * 60)
    print("Multimodal Insights Backend - Integration Test")
    print("=" * 60)
    
    try:
        # Run tests
        test_health()
        file_ids = test_upload_files()
        plan_id = test_create_and_execute(file_ids)
        success = test_monitor_execution(plan_id)
        
        if success:
            plan = test_get_results(plan_id)
            exports = test_export(plan_id)
            test_download_export(exports[0])
            
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED!")
            print("=" * 60)
        else:
            print("\n❌ Execution failed")
    
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
```

Save as `test_backend.py` and run:
```powershell
python test_backend.py
```

---

## 📊 **Interactive Testing with Swagger UI**

FastAPI automatically generates interactive API documentation:

1. Navigate to: http://localhost:8000/docs
2. Explore all endpoints interactively
3. Try out requests directly in the browser
4. View request/response schemas

---

## 🔍 **Troubleshooting**

### Issue: "Service not initialized"
**Solution:** Ensure the backend has fully started. Check logs for initialization errors.

### Issue: File upload fails
**Solution:** 
- Check file type is supported (audio/video/PDF)
- Verify file size is reasonable
- Ensure `uploads/` directory permissions

### Issue: Azure service errors
**Solution:**
- Verify `.env` has correct Azure credentials
- Check Azure service quotas and limits
- Ensure services are in same region when possible

### Issue: Cosmos DB connection fails
**Solution:**
- Verify Cosmos DB endpoint and key
- Check database and container names
- Ensure network connectivity to Azure

---

## 📝 **Test Data**

Create these test files for comprehensive testing:

1. **test_audio.mp3** - Short audio clip (30 seconds - 2 minutes)
2. **test_video.mp4** - Short video with audio (30 seconds - 1 minute)
3. **test_document.pdf** - Simple PDF with text (1-2 pages)

---

## ✅ **Expected Test Coverage**

- [x] Health check
- [x] File upload (single and multiple)
- [x] File listing
- [x] Plan creation
- [x] Plan execution (background)
- [x] Status monitoring
- [x] Result retrieval
- [x] Export (all formats)
- [x] Export download
- [x] Export listing

---

## 📚 **Next Steps**

After successful backend testing:

1. **Build Frontend** - React UI for Custom Copilot experience
2. **Integration Testing** - Full end-to-end with real Azure services
3. **Performance Testing** - Load testing with multiple concurrent users
4. **Security Testing** - Authentication, authorization, input validation

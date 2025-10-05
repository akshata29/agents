# Microsoft Agent Framework Pattern Integration

## Overview
This document explains how the Multimodal Insights Application uses MAF (Microsoft Agent Framework) orchestration patterns for execution.

## Current Architecture

### 1. Sequential Execution with Context Handoff

The application uses **MAF's Sequential Pattern (HandoffPattern)** for executing analysis workflows:

```
Multimodal Processor → Sentiment Agent → Summarizer Agent → Analytics Agent
        ↓                      ↓                   ↓                ↓
    Extract Content      Use Transcript      Use Transcript    Use Transcript
```

**Key Benefits:**
- ✅ Each agent receives context from previous steps
- ✅ Real transcript data flows through the pipeline
- ✅ Proper sequential dependencies maintained
- ✅ Context accumulator pattern for data sharing

### 2. Execution Flow

#### Step 1: File Processing (Multimodal Processor Agent)
**Input:** Uploaded files (audio, video, PDF)
**Output:**
```json
{
  "processed_files": 1,
  "results": {
    "file_id_123": {
      "file_type": "audio",
      "transcription": "Hello, this is the actual speech-to-text transcript...",
      "text_content": "Hello, this is the actual speech-to-text transcript...",
      "audio_metadata": {
        "language": "en-US",
        "format": ".wav"
      },
      "extraction_metadata": {
        "service": "Azure Speech-to-Text"
      }
    }
  }
}
```

**Context Updated:**
```python
execution_context["extracted_content"]["file_id_123"] = {
    "transcription": "...",
    "text_content": "...",
    ...
}
```

#### Step 2-4: Analysis Agents (Sentiment, Summarizer, Analytics)
**Input:** Context from Step 1 containing real transcript
**Process:**
```python
# Extract transcript from context
extracted_content = context.get("extracted_content", {})
all_text = []
for file_id, content in extracted_content.items():
    if content.get("transcription"):
        all_text.append(content["transcription"])  # Using REAL transcript!

combined_text = "\n\n".join(all_text)
```

**Output:** Analysis results based on actual transcript data

### 3. Code Location

**Orchestrator:** `backend/app/services/task_orchestrator.py`

**Key Methods:**
- `execute_plan()` - Uses MAF Sequential Pattern with logging
- `_execute_step()` - Executes individual agent and updates context
- `_execute_multimodal_processing()` - Processes files and stores in context
- `_execute_sentiment_analysis()` - Extracts transcript from context
- `_execute_summarization()` - Extracts transcript from context
- `_execute_analytics()` - Extracts transcript from context

### 4. Logging Pattern Usage

The orchestrator explicitly logs MAF pattern usage:

```python
logger.info("Using MAF HandoffPattern for sequential agent execution")

logger.info(
    f"Context passed to next step",
    extracted_files=len(execution_context.get("extracted_content", {})),
    has_sentiment=bool(execution_context.get("sentiment_results")),
    has_summary=bool(execution_context.get("summary_results")),
    has_analytics=bool(execution_context.get("analytics_results"))
)
```

## Data Flow Verification

### ✅ Confirmed: Real Transcript Data is Used

**Evidence:**
1. `multimodal_processor_agent.py` line 150-165: Generates real transcription using Azure Speech-to-Text
2. `task_orchestrator.py` line 470-490: Sentiment agent extracts `content.get("transcription")`
3. `task_orchestrator.py` line 495-520: Summarizer agent extracts `content.get("transcription")`
4. `task_orchestrator.py` line 525-550: Analytics agent extracts `content.get("transcription")`

**NOT using mock data** - All analysis is performed on actual speech-to-text output!

## UI Improvements

### New Display Features

**Multimodal Processor Results** now show:
- 📄 File type badges (Audio/Video/PDF)
- 📝 Full transcript text with scrollable view
- 🎵 Audio metadata (language, format)
- 📊 PDF metadata (page count, tables)
- 🔧 Processing service used (Azure Speech-to-Text, Document Intelligence)

**Analysis Results** continue to show:
- Sentiment scores and emotions
- Summaries with different detail levels
- Analytics insights and recommendations

## Future Enhancements

### Potential Pattern Upgrades

1. **Concurrent Pattern for Analysis Agents**
   - Run Sentiment, Summarizer, Analytics in parallel after file processing
   - Reduce total execution time
   - Use `GroupChatPattern` or concurrent execution

2. **ReAct Pattern for Dynamic Planning**
   - Let planner adjust steps based on file content
   - Add/remove analysis agents dynamically
   - Use `ReActPattern` for adaptive execution

3. **Hierarchical Orchestration**
   - Main orchestrator for workflow
   - Sub-orchestrators for specialized tasks
   - Use nested patterns for complex scenarios

## References

- Framework Patterns: `framework/patterns/`
- Orchestrator Core: `framework/core/orchestrator.py`
- Dynamic Planner: `framework/core/planning.py`

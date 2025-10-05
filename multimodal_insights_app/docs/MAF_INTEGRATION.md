# MAF Integration - Multimodal Insights Application

## Overview
This application is now fully integrated with the Magentic Agent Framework (MAF), using proper orchestration patterns and MAF-compatible agents.

## Agent Refactoring

All agents have been refactored to inherit from `BaseAgent` and implement the MAF agent interface:

### 1. MultimodalProcessorAgent
**Location**: `backend/app/agents/multimodal_processor_agent.py`

**MAF Compliance**:
- ✅ Inherits from `BaseAgent`
- ✅ Implements `_process_message(message: AgentMessage, context: Dict) -> AgentResponse`
- ✅ Implements `_register_capabilities()` with 3 capabilities:
  - `audio_transcription`: Azure Speech-to-Text
  - `video_processing`: Extract and transcribe audio
  - `pdf_extraction`: Azure Document Intelligence

**Context Requirements**:
```python
{
    "file_path": str,      # Path to file to process
    "file_type": str,      # Type: audio, video, pdf
    "session_id": str,     # Session identifier
    "file_id": str         # File identifier
}
```

### 2. SentimentAgent
**Location**: `backend/app/agents/sentiment_agent.py`

**MAF Compliance**:
- ✅ Inherits from `BaseAgent`
- ✅ Implements `_process_message(message: AgentMessage, context: Dict) -> AgentResponse`
- ✅ Implements `_register_capabilities()` with 3 capabilities:
  - `sentiment_analysis`: Multi-dimensional sentiment
  - `emotion_detection`: Emotion labels and scores
  - `tone_analysis`: Tone classification

**Context Requirements**:
```python
{
    "content": str,        # Text to analyze (optional, uses message.content if not provided)
    "file_type": str,      # Optional: source file type
    "metadata": dict       # Optional: additional context
}
```

### 3. SummarizerAgent
**Location**: `backend/app/agents/summarizer_agent.py`

**MAF Compliance**:
- ✅ Inherits from `BaseAgent`
- ✅ Implements `_process_message(message: AgentMessage, context: Dict) -> AgentResponse`
- ✅ Implements `_register_capabilities()` with 4 capabilities:
  - `brief_summary`: 2-3 paragraph summaries
  - `detailed_summary`: Key points with analysis
  - `comprehensive_summary`: Full detailed analysis
  - `persona_customization`: Executive/Technical/General

**Context Requirements**:
```python
{
    "content": str,              # Text to summarize
    "summary_type": str,         # brief/detailed/comprehensive
    "persona": str,              # executive/technical/general
    "focus_areas": List[str]     # Optional: specific focus areas
}
```

### 4. AnalyticsAgent
**Location**: `backend/app/agents/analytics_agent.py`

**MAF Compliance**:
- ✅ Inherits from `BaseAgent`
- ✅ Implements `_process_message(message: AgentMessage, context: Dict) -> AgentResponse`
- ✅ Implements `_register_capabilities()` with 5 capabilities:
  - `pattern_recognition`: Identify patterns and trends
  - `product_analysis`: Product/service mentions
  - `recommendation_extraction`: Actionable recommendations
  - `next_best_action`: Next steps identification
  - `trend_analysis`: Trend trajectories

**Context Requirements**:
```python
{
    "content": str,                # Text to analyze
    "analysis_focus": List[str],   # Optional: focus areas
    "file_type": str,              # Optional: source type
    "metadata": dict               # Optional: additional context
}
```

## Orchestration Pattern Integration

### Phase 1: Sequential File Processing
**Pattern**: `MagenticOrchestrator.execute_sequential()`

- **Agent**: `multimodal_processor`
- **Flow**: Process files one at a time in order
- **Purpose**: Extract content, transcriptions, and metadata sequentially
- **Implementation**: Uses MAF's `SequentialBuilder` internally

```python
sequential_result = await self.orchestrator.execute_sequential(
    task="Process and extract content from files: file1.mp3, file2.pdf",
    agent_ids=["multimodal_processor"],
    tools=None
)
```

### Phase 2: Concurrent Analysis
**Pattern**: `MagenticOrchestrator.execute_concurrent()`

- **Agents**: `sentiment`, `summarizer`, `analytics`
- **Flow**: All three agents run in parallel on the same extracted content
- **Purpose**: Faster analysis with parallel execution
- **Implementation**: Uses MAF's `ConcurrentBuilder` internally

```python
concurrent_result = await self.orchestrator.execute_concurrent(
    task="Analyze this content: [transcript...]",
    agent_ids=["sentiment", "summarizer", "analytics"],
    tools=None
)
```

## Agent Registration

All agents are registered with the MAF `AgentRegistry` during application startup:

```python
# In task_orchestrator.py
async def initialize_agents(self):
    """Register MAF-compatible agents with the orchestrator registry."""
    await self.orchestrator.agent_registry.register_agent(
        name="multimodal_processor",
        agent=self.multimodal_processor
    )
    await self.orchestrator.agent_registry.register_agent(
        name="sentiment",
        agent=self.sentiment_agent
    )
    await self.orchestrator.agent_registry.register_agent(
        name="summarizer",
        agent=self.summarizer_agent
    )
    await self.orchestrator.agent_registry.register_agent(
        name="analytics",
        agent=self.analytics_agent
    )
```

## Execution Flow

1. **User uploads files** → Stored in Cosmos DB with metadata
2. **User provides objective** → Plan created by DynamicPlanner
3. **Plan execution starts**:
   - **Phase 1 (Sequential)**: 
     - MultimodalProcessor processes each file
     - Extracts transcriptions, content, metadata
     - Results stored in execution context
   - **Phase 2 (Concurrent)**:
     - Sentiment, Summarizer, and Analytics agents run in parallel
     - Each receives the same extracted content
     - Results aggregated and stored
4. **Results displayed** → Task Details page shows all step outputs

## Benefits of MAF Integration

1. **Proper Orchestration**: Uses framework's battle-tested patterns instead of custom loops
2. **Agent Standardization**: All agents follow the same interface (BaseAgent)
3. **Capability Discovery**: Agents declare their capabilities for dynamic routing
4. **Registry Management**: Centralized agent lifecycle and health tracking
5. **Extensibility**: Easy to add new agents or patterns
6. **Observability**: Built-in logging, metrics, and monitoring hooks
7. **Performance**: Concurrent pattern leverages parallel execution for faster results

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Task Orchestrator                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         MagenticOrchestrator (Framework)            │  │
│  │  ┌────────────────┐  ┌──────────────────────────┐  │  │
│  │  │ AgentRegistry  │  │  Sequential/Concurrent   │  │  │
│  │  │   - multimodal │  │       Patterns           │  │  │
│  │  │   - sentiment  │  │  (SequentialBuilder,     │  │  │
│  │  │   - summarizer │  │   ConcurrentBuilder)     │  │  │
│  │  │   - analytics  │  │                          │  │  │
│  │  └────────────────┘  └──────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─ Phase 1: Sequential
                              │  └─ multimodal_processor → Extract content
                              │
                              └─ Phase 2: Concurrent
                                 ├─ sentiment       ──┐
                                 ├─ summarizer      ──┼─ Parallel Execution
                                 └─ analytics       ──┘
```

## Next Steps

- [ ] Add more orchestration patterns (HandoffPattern, GroupChatPattern)
- [ ] Implement agent-to-agent communication
- [ ] Add MCP tool integration for external capabilities
- [ ] Implement dynamic agent selection based on task requirements
- [ ] Add observability metrics and tracing
- [ ] Implement agent health checks and failover

## References

- Framework Base Agent: `framework/agents/base.py`
- MAF Orchestrator: `framework/core/orchestrator.py`
- Sequential Pattern: `framework/patterns/sequential.py`
- Concurrent Pattern: `framework/patterns/concurrent.py`
- Agent Registry: `framework/core/registry.py`

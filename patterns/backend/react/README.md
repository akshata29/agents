# Deep Research Pattern

## Overview

The **Deep Research** pattern is a comprehensive, end-to-end research orchestration system built on the Microsoft Agent Framework with Azure AI Foundry Agents. It combines ReAct planning, concurrent web search, optional integrations (MCP, File Search, Code Interpreter), and produces professional Markdown reports with proper citations and references.

## 🎯 Key Features

- **🧠 ReAct Planning with Probe Tool**: Strategic planning with ability to probe web search for grounded evidence
- **⚡ Concurrent Search**: Parallel web search using MAF Workflows (ConcurrentBuilder) for faster results
- **📚 Microsoft Learn Integration**: Optional MCP server integration for Microsoft technical documentation
- **📄 PDF Ingestion**: Upload and search PDF documents via File Search (multimodal mode)
- **🔒 Private Search**: Query internal vector stores for enterprise knowledge discovery
- **💻 Code Interpreter**: Data analysis and visualization using Python code execution
- **✅ Reviewer Loop**: Quality assurance with automated review and revision cycle
- **🔐 Role-Based Access Control**: Tool gating based on user roles (viewer | doc-reader | analyst | admin)
- **📊 Application Insights Tracing**: Full observability with Azure Application Insights
- **📝 Citation Management**: Professional Markdown output with inline citations and references

## 🏗️ Architecture

### Pattern Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DEEP RESEARCH PATTERN                        │
└─────────────────────────────────────────────────────────────────┘

Stage 1: ReAct Planning
┌─────────────┐      ┌──────────────┐
│  Planner    │─────▶│  Probe Tool  │ (optional web search)
│             │◀─────│  (Agent)     │
└─────────────┘      └──────────────┘
      │
      ▼ Research Plan (JSON)
      
Stage 2: Query Expansion
┌─────────────┐
│ Researcher  │ → Prioritized Queries
└─────────────┘

Stage 3: Evidence Gathering (Choose Mode)
┌─────────────────────────────────────────────────────────┐
│  A) Concurrent Web Search (Workflows)                   │
│     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐│
│     │ Primary  │ │  Latest  │ │ Academic │ │Industry ││
│     │ Sources  │ │   News   │ │ Research │ │ Reports ││
│     └──────────┘ └──────────┘ └──────────┘ └─────────┘│
│            Concurrent Execution (Fan-Out/Fan-In)        │
└─────────────────────────────────────────────────────────┘
                        OR
┌─────────────────────────────────────────────────────────┐
│  B) Private Search (Vector Store)                       │
│     ┌──────────────────────────┐                        │
│     │   File/Vector Search     │                        │
│     │   (Enterprise KB)        │                        │
│     └──────────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
                        OR
┌─────────────────────────────────────────────────────────┐
│  C) Multimodal PDF Search                               │
│     ┌──────────────────────────┐                        │
│     │   PDF Upload + Search    │                        │
│     │   (File Search Tool)     │                        │
│     └──────────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
      │
      ▼ Evidence Collection
      
Stage 4: Analysis (Optional)
┌─────────────┐
│  Analyst    │ → Code Interpreter → Tables, Stats, Charts
└─────────────┘

Stage 5: Report Writing
┌─────────────┐
│   Writer    │ → Streaming Markdown Report with Citations
└─────────────┘

Stage 6: Quality Review (Optional)
┌─────────────┐      ┌─────────────┐
│  Reviewer   │─────▶│   Writer    │
│             │◀─────│ (Revision)  │
└─────────────┘      └─────────────┘
      │
      ▼ Final Report (Markdown)
```

## 🚀 Usage

### Basic Research (Baseline Mode)

```python
from deep_research import run_deep_research_orchestration

# Run basic research workflow
results = await run_deep_research_orchestration(
    task="Analyze the impact of AI on software development",
    mode="baseline"
)
```

### Research with Code Analysis

```python
results = await run_deep_research_orchestration(
    task="Market analysis of cloud infrastructure providers",
    mode="analyst",
    user_role="analyst"
)
```

### Research with Quality Review

```python
results = await run_deep_research_orchestration(
    task="Comprehensive study of quantum computing applications",
    mode="reviewer"
)
```

### Private Enterprise Research

```python
results = await run_deep_research_orchestration(
    task="Internal compliance policy analysis",
    mode="private",
    vector_store_id="vs_abc123",
    user_role="admin"
)
```

### Multimodal PDF Research

```python
results = await run_deep_research_orchestration(
    task="Summarize key findings from the research paper",
    mode="multimodal",
    pdf_path="C:/research/paper.pdf",
    user_role="admin"
)
```

### Full-Featured Research

```python
results = await run_deep_research_orchestration(
    task="Deep dive into blockchain scalability solutions",
    mode="full",
    user_role="admin"
)
```

## 📋 Execution Modes

| Mode | Description | Features |
|------|-------------|----------|
| `baseline` | Standard research workflow | Planner → Researcher → Concurrent Search → Writer |
| `reviewer` | Baseline + quality review | Adds Reviewer loop for critique and revision |
| `analyst` | Baseline + code analysis | Adds Code Interpreter for data tables and stats |
| `private` | Enterprise knowledge search | Uses vector store instead of web search |
| `multimodal` | PDF document research | Ingests and searches uploaded PDF files |
| `full` | All features enabled | Combines all above features |

## 🔐 Role-Based Access Control

The pattern enforces role-based tool access:

| Role | Available Tools |
|------|-----------------|
| **viewer** | Web Search only |
| **doc-reader** | Web Search + Microsoft Learn MCP |
| **analyst** | Web Search + MCP + Code Interpreter |
| **admin** | All tools + File Search + Admin functions |

Set user role via environment variable:
```bash
USER_ROLE=analyst
```

Or pass directly:
```python
results = await run_deep_research_orchestration(
    task="...",
    user_role="analyst"
)
```

## ⚙️ Configuration

### Required Environment Variables

```bash
# Azure AI Foundry Project
AZURE_AI_PROJECT_ENDPOINT=https://<foundry>.services.ai.azure.com/api/projects/<project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
```

### Optional Configuration

```bash
# Application Insights Tracing
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=true

# Role-Based Access Control
USER_ROLE=viewer  # viewer | doc-reader | analyst | admin

# Private Search Mode
AZURE_VECTOR_STORE_ID=vs_123456

# Multimodal PDF Mode
PDF_PATH=C:\path\to\document.pdf
```

## 📊 Output Format

The pattern returns a structured conversation history:

```python
[
    {
        "agent": "Planner",
        "input": "Research objective",
        "output": "JSON research plan with goals, questions, steps",
        "timestamp": "2025-10-08T10:30:00.000Z"
    },
    {
        "agent": "Researcher",
        "input": "Research plan",
        "output": "JSON with prioritized queries and extraction schema",
        "timestamp": "2025-10-08T10:30:15.000Z"
    },
    {
        "agent": "ConcurrentSearch",
        "input": "Query list",
        "output": "JSON array of evidence with URLs and citations",
        "timestamp": "2025-10-08T10:30:45.000Z"
    },
    {
        "agent": "Writer",
        "input": "Plan + Evidence",
        "output": "Markdown report with citations",
        "timestamp": "2025-10-08T10:31:30.000Z"
    }
    // ... additional agents based on mode
]
```

### Sample Markdown Report

The Writer produces professional reports with this structure:

```markdown
# [Research Title]

## Executive Summary
Brief overview of key findings and recommendations.

## Methodology
Description of research approach, data sources, and analysis methods.

## Findings

### Key Insight 1
Detailed analysis with inline citations [1], [2].

### Key Insight 2
Additional findings with supporting evidence [3], [4], [5].

## Limitations
- Scope constraints
- Data availability considerations
- Temporal limitations

## References
[1] Source Title — https://example.com/source1 — (Accessed: 2025-10-08)
[2] Another Source — https://example.com/source2 — (Accessed: 2025-10-08)
...

## Appendix A: Data Analysis (if analyst mode)
| Title | URL | Date |
|-------|-----|------|
| ... | ... | ... |

Domain Distribution:
- example.com: 5 sources
- research.org: 3 sources
```

## 🛠️ Technical Details

### Technologies

- **Agent Framework**: `agent-framework`, `agent-framework-azure-ai`
- **Azure Services**: Azure AI Foundry, Azure OpenAI, Application Insights
- **Tools**: 
  - `HostedWebSearchTool` (Bing Grounding)
  - `HostedMCPTool` (Microsoft Learn)
  - `HostedFileSearchTool` (Vector/File Search)
  - `HostedCodeInterpreterTool` (Python execution)
- **Workflows**: `ConcurrentBuilder` for parallel agent execution
- **Authentication**: `DefaultAzureCredential` (supports managed identity, Azure CLI, etc.)

### Observability

When configured, the pattern emits detailed traces to Application Insights:

- **Spans**: Each agent execution creates a span
- **Events**: Tool calls, workflow transitions, errors
- **Content**: Prompts and responses (when `AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=true`)
- **Metrics**: Execution time, token usage, success rates

View traces in:
- Azure AI Foundry: Project → Tracing
- Application Insights: Transaction search and end-to-end transaction details

## 🎓 Best Practices

1. **Start with Baseline**: Test with `mode="baseline"` before enabling advanced features
2. **Role Gating**: Always set appropriate `USER_ROLE` for security
3. **Query Quality**: Provide clear, specific research objectives
4. **Evidence Limits**: Pattern caps at 24 sources to balance quality vs. cost
5. **Streaming**: Writer uses streaming for real-time progress visibility
6. **Error Handling**: Pattern includes robust JSON parsing with fallbacks
7. **Tracing**: Enable Application Insights for production deployments

## 🔍 Troubleshooting

### Common Issues

**"AZURE_AI_PROJECT_ENDPOINT not configured"**
- Ensure `.env` file contains the Foundry project endpoint
- Check that environment variables are loaded properly

**"PermissionError: Not authorized to call admin_data_export"**
- Set `USER_ROLE=admin` or use appropriate role for the tool
- Review role-based access control configuration

**"AZURE_VECTOR_STORE_ID required for private mode"**
- Set vector store ID in environment or pass as parameter
- Ensure vector store exists and is connected to the project

**"PDF not found"**
- Verify PDF path is correct and file exists
- Use absolute paths for `PDF_PATH`

**No JSON found in agent output**
- Agent may have returned prose instead of JSON
- Check agent instructions and model capabilities
- Enable logging to see raw agent responses

## 📚 Related Patterns

- **Sequential**: Traditional pipeline with ordered agent execution
- **Concurrent**: Parallel execution without planning overhead
- **Group Chat**: Interactive multi-agent collaboration
- **Handoff**: Task routing and delegation

## 🤝 Contributing

To extend the Deep Research pattern:

1. Add new specialized search agents in Stage 3
2. Create custom tools for domain-specific data sources
3. Implement additional analysis modes
4. Enhance report formatting and visualizations

## 📄 License

Part of the Agent Foundation Patterns collection.

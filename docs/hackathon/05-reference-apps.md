# Reference Application Field Guide

This guide links the refreshed documentation set to the live applications in the repository. Use it to decide which codebase to inspect for a given scenario.

## Deep Research App

- **Goal**: Structured research workflows for engineers and analysts
- **Key Patterns**: YAML-defined sequential + concurrent phases, optional plan review
- **Agents**: Planner, Researcher (web/search), Synthesizer, Reviewer
- **Data Sources**: Tavily or other MCP-enabled search services, Azure OpenAI for synthesis
- **Docs**: `deep_research_app/README.md`, `deep_research_app/docs/QUICKSTART.md`, decision/pattern guides in `docs/hackathon`
- **Why reference it**: Best choice for showing YAML workflows, concurrent fan-out, and resume-able research sessions

## Patterns Sandbox

- **Goal**: Demonstrate every MAF builder with real-time visualization
- **Key Patterns**: Sequential, Concurrent, Group Chat, Handoff, Magentic, Deep Research
- **Agents**: Generic helpers that echo patterns, plus sample MCP integrations
- **Docs**: `patterns/README.md`
- **Why reference it**: Fastest playground for experimenting with orchestration settings before copying them into other apps

## Advisor Productivity App

- **Goal**: Transform meeting transcripts into insights, recommendations, and follow-up packages
- **Key Patterns**: Sequential flow with optional branching for sentiment and action items
- **Agents**: Transcription orchestrator, summarizer, recommendation writer, sentiment analyzer
- **Services**: Azure Speech, Azure OpenAI, Cosmos DB, Application Insights, Content Safety
- **Docs**: `advisor_productivity_app/README.md`
- **Why reference it**: Strong template for combining speech services with human-in-the-loop validation and telemetry

## Multimodal Insights App

- **Goal**: Analyze audio, video, and documents in a single workflow with plan approvals
- **Key Patterns**: Planner + Sequential execution, optional parallel ingestion per file type
- **Agents**: Planner, Multimodal Processor, Sentiment, Summarizer, Analytics
- **Services**: Azure Speech, Document Intelligence, Azure OpenAI, Cosmos DB
- **Docs**: `multimodal_insights_app/README.md`, `multimodal_insights_app/docs/ARCHITECTURE.md`, `docs/MAF_PATTERN_INTEGRATION.md`
- **Why reference it**: Exemplifies multimodal preprocessing and agent coordination with Cosmos persistence

## FinAgent App (Static)

- **Goal**: Equity research copilot with predefined execution modes
- **Key Patterns**: Sequential, Concurrent, Group Chat
- **Agents**: Company, SEC, Earnings, Fundamentals, Technicals, Report
- **Services**: FMP API, SEC EDGAR, Azure OpenAI, optional PDF export
- **Docs**: `finagent_app/README.md`, `finagent_app/docs/QUICKSTART.md`
- **Why reference it**: Shows how to blend financial data sources with multiple coordination strategies

## FinAgent Dynamic App

- **Goal**: Human-approved dynamic planning over the same financial domain
- **Key Patterns**: ReAct planner with approval workflow, Sequential execution, Synthesis dual-context pattern
- **Agents**: Planner, Company, SEC, Earnings, Fundamentals, Technicals, Summarizer
- **Services**: Azure OpenAI, Cosmos DB, Yahoo Finance MCP, FMP API
- **Docs**: `finagent_dynamic_app/README.md`, `finagent_dynamic_app/docs/QUICKSTART.md`, `finagent_dynamic_app/docs/SYNTHESIS_AGENT_PATTERN.md`
- **Why reference it**: Teaches how to add approval gates, persist plan history, and manage session-wide context

---

### Choosing the Right Starting Point

| Objective | Start Here |
| --- | --- |
| Learn orchestration patterns quickly | Patterns Sandbox |
| Build a research assistant | Deep Research App |
| Showcase multimodal analytics | Multimodal Insights App |
| Deliver financial intelligence | FinAgent or FinAgent Dynamic |
| Handle meeting intelligence | Advisor Productivity App |

Next: use [06-development-guide.md](./06-development-guide.md) to review the development guide.

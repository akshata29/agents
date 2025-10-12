# Reference Architecture

## Purpose

This document captures the cross-cutting architecture patterns that appear in every application inside the MAF portfolio. You can treat it as the “starter blueprint” when planning a new solution.

## Layered View

```
┌──────────────────────────────────────────────────────────┐
│ Presentation (React + Vite)                              │
│  • Upload/UIs (Forms, History, Approvals, Dashboards)    │
│  • WebSocket or SSE streams for live execution updates   │
│  • Component library: Tailwind + Headless UI + Lucide    │
└───────────────┬──────────────────────────────────────────┘
                │ REST + WebSocket
┌───────────────▼──────────────────────────────────────────┐
│ Application Service (FastAPI)                            │
│  • Routers expose run/start/history endpoints            │
│  • Task orchestrator composes MAF builders               │
│  • Persistence adapters (Cosmos, Storage, Postgres)      │
│  • Telemetry hooks (Application Insights, OpenTelemetry) │
└───────────────┬──────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────┐
│ Microsoft Agent Framework                                │
│  • Builders: Sequential, Concurrent, Group Chat, etc.     │
│  • BaseAgent + message contracts                         │
│  • Tool calling + MCP integration                        │
└───────────────┬──────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────┐
│ External Services                                        │
│  • Azure OpenAI, Azure AI Speech, Document Intelligence   │
│  • Financial data (FMP, Yahoo Finance MCP, SEC EDGAR)     │
│  • Storage (Blob, Cosmos DB, Redis)                       │
│  • Monitoring (App Insights, Log Analytics)               │
└──────────────────────────────────────────────────────────┘
```

## Shared Components

- **Task Orchestrator** – Each backend contains a service module that maps user input to a specific MAF builder and set of agents. It is also responsible for writing run metadata to Cosmos DB or local stores.
- **Agent Registry** – Agents are organized in folders with consistent naming (`planner_agent.py`, `summarizer_agent.py`, etc.). Dependencies (clients, prompts, tool adapters) are injected through constructor arguments.
- **Persistence** – Cosmos DB is the default for session and artifact storage. When Cosmos is optional, backends fall back to in-memory stores so the app still runs locally.
- **Telemetry** – All apps have hooks for Application Insights or OTLP exporters. Logs are structured (usually via `structlog`) so they can be correlated with workflow events.
- **Deployment Scripts** – PowerShell scripts package containers, set environment variables, and deploy to Azure App Service or Container Apps. These scripts expect the `.env` files documented alongside each app.

## Portfolio Crosswalk

| Concern | Deep Research | FinAgent Dynamic | Multimodal Insights | Advisor Productivity | FinAgent | Patterns Sandbox |
| --- | --- | --- | --- | --- | --- | --- |
| Planner | YAML definitions + Sequential builder | ReAct planner agent + approvals | Planner agent seeded with file metadata | Prompt-based meeting orchestration | Static pattern selection | Switchable builders via UI |
| Persistence | Cosmos DB + Blob Storage | Cosmos DB | Cosmos DB (optional) | Cosmos DB | Cosmos DB | Optional Cosmos DB |
| Human-in-the-loop | Mode selection, step approvals | Mandatory plan approval | Step approvals | After-call review | Optional approvals | Execution monitor only |
| MCP / Tools | Tavily, Vector search | Yahoo Finance MCP | MCP hooks for future media tools | Azure Communication Services, Graph | Financial APIs | Demo MCP integrations |
| Telemetry | Application Insights, OTLP | Application Insights | Application Insights | Application Insights | Application Insights | App Insights optional |

## Environment Strategy

1. **Local developer setup** – Python virtual environment + Node.js workspace; `.env` values copied from templates.
2. **Shared dev/test** – Azure Container Apps (for MCP servers) and Azure App Service or Azure Container Apps for the web workload. Cosmos DB is provisioned once and shared across apps with separate containers.
3. **Production** – Same topology as shared dev/test, but with managed identities for Cosmos and Azure Storage, plus Application Insights sampling tuned for real usage.

## Security & Compliance Touchpoints

- Azure App Service Easy Auth (Patterns Sandbox, Advisor Productivity) can be enabled to require Entra ID sign-in.
- Secrets are sourced from `.env` locally and from Azure App Configuration or Key Vault in the deployment scripts.
- MCP servers are isolated in Container Apps and protected with auth tokens when exposed beyond local development.

## What to Customize First

1. Update `.env` templates for your target region, deployments, and feature flags
2. Decide whether Cosmos DB is required or optional for your scenario
3. Review `settings.py` in each backend to confirm the environment variable names align with your cloud resources
4. Enable Application Insights for the services you care about; it dramatically improves debugging during the hackathon

Continue with [03-orchestration-patterns.md](./03-orchestration-patterns.md) to pick the builder that fits your solution.

# Development Environment Guide

Use this guide to bring your laptop into a productive state for the hackathon. Follow the sequence to avoid conflicting runtimes and to align with the Microsoft Agent Framework (MAF) workflows used throughout the repository.

## 1. Base Prerequisites

- Windows 11 with WSL2 enabled (Ubuntu 22.04 recommended) or native Windows PowerShell 7+.
- Visual Studio Code with the Azure, Python, Docker, and AI Toolkit extensions installed.
- Python 3.11.x (ensure `py -3.11 --version` returns the expected build) and `pipx` for isolating CLI tools.
- Node.js 20 LTS with corepack enabled (`corepack enable`).
- Docker Desktop with Kubernetes disabled unless you plan to run containerized stacks locally.
- Azure CLI (`az version`) and Git (`git --version`).

> Tip: Run `./scripts/dev.ps1 --check` from the repo root to validate the presence of core tooling before you start cloning or building apps.

## 2. Repository Bootstrapping

1. Fork or clone `agent_foundation` and run `git submodule update --init --recursive` if you see submodule hints.
2. Copy `.env.template` files to `.env` in each app you plan to use. Do not commit populated secrets.
3. Create a personal `settings.local.json` (or comparable file) to track private keys such as Azure OpenAI or Cosmos DB endpoints.
4. Run `pwsh ./scripts/dev.ps1 --mcp` to install the MCP servers used in the quickstarts.

> Most quickstarts assume PowerShell. If you prefer WSL, mirror these steps in Bash and keep the two environments in sync when installing dependencies.

## 3. Python Environment Strategy

- Use `uv` or `pipenv` only if your team already relies on them; the default scripts assume plain `venv`.
- Each backend folder (`*/backend/`) includes `start.ps1` and `start.bat` scripts that:
  1. Create a `.venv` in-place.
  2. Install `requirements.txt`.
  3. Launch the FastAPI application with hot reload.
- Prefer `pwsh ./backend/start.ps1 --reset` the first time to ensure a clean virtual environment.

**Common pitfalls**
- Mixing Python 3.10 and 3.11 creates binary incompatibilities with LangChain / pydantic. Always confirm the interpreter path by running `Get-Command python` inside the virtual environment.
- If you see `DLL load failed` errors on Windows, delete `.venv` and rerun `start.ps1` to rebuild wheels.

## 4. Frontend Tooling

- Run `corepack enable` once per machine, then `pnpm install` inside each `frontend/` directory.
- Use `pnpm dev` to start Vite development servers. The default ports are documented in each app README; adjust via `.env` files if you plan to run multiple apps at the same time.
- For UI linting and formatting, rely on the provided `eslint.config.js` and Tailwind configuration. Run `pnpm lint` before submitting pull requests.

## 5. Shared Services & Data

- Cosmos DB Emulator: Optional but recommended for offline development. Configure the connection string in relevant `.env` files.
- Azure Storage Emulator or Azurite: Use for file uploads in Advisor Productivity and Deep Research apps.
- Azure OpenAI: Provision a resource in the same region as your other services to minimize cross-region latency. Store deployment names in environment variables (`AZURE_OPENAI_DEPLOYMENT`, etc.).
- Application Insights: Useful for collecting telemetry during the hackathon; integrate via existing instrumentation modules.

When working with real Azure resources, create a dedicated resource group per team and tag resources with `maf-hackathon=<team-name>` to simplify cleanup.

## 6. Running the MCP Toolchain

1. Start the MCP servers defined in `scripts/mcp/` using `pwsh ./scripts/dev.ps1 --mcp`.
2. Verify that the servers register correctly with the hosted MAF orchestrators by checking the logs in `logs/mcp/`.
3. Update the MCP connection configuration in each app (`backend/app/config/mcp_settings.py` or equivalent).
4. Test tool discovery from the orchestrator logs before assigning them to an agent.

## 7. Testing & Quality Gates

- Backends use `pytest`; run `pwsh ./scripts/dev.ps1 --test backend` or call `pytest` directly inside each backend folder.
- Frontends use Vitest; `pnpm test` runs watch mode.
- Linting is bundled in `./scripts/dev.ps1 --check`.
- Add new tests alongside features: for agents, include planner simulations; for frontends, add component tests that ensure orchestrator responses render correctly.

## 8. CI/CD Considerations

- GitHub Actions workflows expect Docker to be available and rely on the same scripts you run locally.
- Keep Dockerfiles up to date if you add system dependencies. Validate with `docker build` before committing.
- Deployment scripts (`deploy.ps1`, `deploy_mcp.ps1`, `deploy.bat`) assume you have the Azure CLI logged in. Test them against a non-production resource group before demo day.

## 9. Collaboration Hygiene

- Use feature branches per project and open pull requests early for async reviews.
- Add `docs/` updates as you progress to capture architecture decisions, prompts, and environment changes.
- Leverage GitHub Discussions or Teams channels for blockers—link the issue to your branch.
- Document new environment variables in `.env.template` and note secrets in your team’s secure vault.

## 10. Troubleshooting

| Issue | Fix |
| --- | --- |
| Backend fails with missing DLLs | Delete `.venv`, reinstall using `start.ps1 --reset`, ensure Python 3.11. |
| Frontend cannot reach backend | Confirm `.env` Vite proxy targets; check CORS settings in FastAPI app. |
| MCP tools not found | Ensure `scripts/dev.ps1 --mcp` ran successfully and update the MCP config paths. |
| Azure auth failures | Run `az login` and set the default subscription with `az account set --subscription <name>`. |
| Docker build is slow | Enable BuildKit (`$env:DOCKER_BUILDKIT=1`) and add layer caching for dependency install steps. |

## Next Steps

Continue to [07-advanced-topics.md](./07-advanced-topics.md) for deeper dives into prompt optimization, telemetry, and production hardening.

"""Financial research orchestration service built on local MAF helpers."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

import structlog
from openai import AsyncAzureOpenAI

from ..agents import (
    CompanyAgent,
    EarningsAgent,
    FundamentalsAgent,
    ReportAgent,
    SECAgent,
    TechnicalsAgent,
)
from ..infra.settings import Settings
from ..maf import MAFOrchestrator
from ..models.dto import (
    AgentMessage,
    ExecutionStatus,
    ExecutionStep,
    OrchestrationPattern,
    OrchestrationResponse,
    ResearchArtifact,
)
from ..models.persistence_models import ResearchRun, ResearchSession
from ..persistence.cosmos_memory import CosmosMemoryStore

logger = structlog.get_logger(__name__)

ProgressCallback = Callable[[str, str, Dict[str, Any]], Awaitable[None]]


class FinancialOrchestrationService:
    """Coordinate sequential and concurrent research workflows for finagent."""

    def __init__(self, settings: Settings, azure_client: AsyncAzureOpenAI) -> None:
        self.settings = settings
        self.azure_client = azure_client

        self.orchestrator = MAFOrchestrator()
        self.agents = self._create_agents()
        for name, agent in self.agents.items():
            self.orchestrator.register_agent(name, agent)

        self._active_runs: Dict[str, OrchestrationResponse] = {}

        self.cosmos: Optional[CosmosMemoryStore] = None
        if settings.cosmos_db_endpoint:
            self.cosmos = CosmosMemoryStore(
                endpoint=settings.cosmos_db_endpoint,
                database_name=settings.cosmos_db_database,
                container_name=settings.cosmos_db_container,
            )
            logger.info(
                "Cosmos DB persistence enabled",
                database=settings.cosmos_db_database,
                container=settings.cosmos_db_container,
            )
        else:
            logger.warning("Cosmos DB not configured - runs will only be stored in memory")

        logger.info(
            "FinancialOrchestrationService initialised",
            agents=list(self.agents.keys()),
        )

    async def initialize(self) -> None:
        if self.cosmos:
            await self.cosmos.initialize()
            logger.info("Cosmos DB persistence initialised")

    async def _save_run_to_cosmos(
        self,
        response: OrchestrationResponse,
        user_id: str,
        session_id: str,
        request_params: Dict[str, Any],
    ) -> None:
        if not self.cosmos:
            return

        try:
            research_run = ResearchRun(
                id=response.run_id,
                run_id=response.run_id,
                session_id=session_id,
                user_id=user_id,
                ticker=response.ticker,
                pattern=response.pattern.value,
                status=response.status.value,
                started_at=response.started_at,
                completed_at=response.completed_at,
                execution_time=response.duration_seconds,
                request_params=request_params,
                summary=response.summary,
                investment_thesis=response.investment_thesis,
                key_risks=response.key_risks,
                pdf_url=response.pdf_url,
                steps_count=len(response.steps),
                messages_count=len(response.messages),
                artifacts_count=len(response.artifacts),
                error=response.error,
                full_response=response.model_dump(),
                metadata=response.metadata,
            )

            await self.cosmos.update_run(research_run)
            logger.debug("Saved run to Cosmos DB", run_id=response.run_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to save run to Cosmos DB",
                run_id=response.run_id,
                error=str(exc),
            )

    def _create_agents(self) -> Dict[str, Any]:
        agents: Dict[str, Any] = {}
        try:
            agents["company"] = CompanyAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
                fmp_api_key=self.settings.fmp_api_key,
            )
            agents["sec"] = SECAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
                fmp_api_key=self.settings.fmp_api_key,
            )
            agents["earnings"] = EarningsAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
                fmp_api_key=self.settings.fmp_api_key,
            )
            agents["fundamentals"] = FundamentalsAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
                fmp_api_key=self.settings.fmp_api_key,
            )
            agents["technicals"] = TechnicalsAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
            )
            agents["report"] = ReportAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
            )
            logger.info("Financial research agents created", count=len(agents))
        except Exception as exc:
            logger.error("Failed to create agents", error=str(exc))
            raise

        return agents

    def _build_agent_sequence(self, scope: List[str], include_pdf: bool) -> List[tuple[str, str]]:
        sequence: List[tuple[str, str]] = []
        if "company" in scope or "all" in scope:
            sequence.append(("company", "Company analysis"))
        if "sec" in scope or "all" in scope:
            sequence.append(("sec", "SEC filing analysis"))
        if "earnings" in scope or "all" in scope:
            sequence.append(("earnings", "Earnings call analysis"))
        if "fundamentals" in scope or "all" in scope:
            sequence.append(("fundamentals", "Fundamental analysis"))
        if "technicals" in scope or "all" in scope:
            sequence.append(("technicals", "Technical analysis"))
        if include_pdf:
            sequence.append(("report", "Generate equity brief"))
        return sequence

    @staticmethod
    def _extract_agent_output(result: Any) -> str:
        if not result:
            return ""

        if hasattr(result, "messages") and result.messages:
            collected: List[str] = []
            for message in result.messages:
                if hasattr(message, "text") and message.text:
                    collected.append(message.text)
                elif hasattr(message, "contents") and message.contents:
                    for content in message.contents:
                        if hasattr(content, "text") and content.text:
                            collected.append(content.text)
            return "\n".join(collected).strip()

        return str(result)

    @staticmethod
    def _ingest_artifacts_from_context(
        response: OrchestrationResponse, context: Dict[str, Any]
    ) -> None:
        for artifact_data in context.get("artifacts", []):
            if isinstance(artifact_data, ResearchArtifact):
                response.artifacts.append(artifact_data)
                continue

            if isinstance(artifact_data, dict):
                response.artifacts.append(
                    ResearchArtifact(
                        id=artifact_data.get("id", str(uuid.uuid4())),
                        type=artifact_data.get("type", "text"),
                        title=artifact_data.get("title", "Analysis Result"),
                        content=artifact_data.get("content", ""),
                        timestamp=datetime.utcnow(),
                        metadata=artifact_data.get("metadata", {}),
                    )
                )

    async def execute_sequential(
        self,
        ticker: str,
        scope: List[str],
        depth: str = "standard",
        include_pdf: bool = True,
        year: Optional[str] = None,
        run_id: Optional[str] = None,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> OrchestrationResponse:
        run_id = run_id or str(uuid.uuid4())
        user_id = user_id or "unknown-user"
        started_at = datetime.utcnow()
        session_id = f"fin-{ticker}-{run_id[:8]}"

        logger.info(
            "Starting sequential execution",
            run_id=run_id,
            session_id=session_id,
            ticker=ticker,
            scope=scope,
            user_id=user_id,
        )

        if self.cosmos:
            try:
                session = ResearchSession(
                    id=session_id,
                    session_id=session_id,
                    user_id=user_id,
                    metadata={
                        "ticker": ticker,
                        "pattern": "sequential",
                        "scope": scope,
                        "depth": depth,
                    },
                )
                await self.cosmos.create_session(session)
                logger.debug("Created session in Cosmos", session_id=session_id)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to create session in Cosmos", error=str(exc))

        agent_sequence = self._build_agent_sequence(scope, include_pdf)

        response = OrchestrationResponse(
            run_id=run_id,
            ticker=ticker,
            pattern=OrchestrationPattern.SEQUENTIAL,
            status=ExecutionStatus.RUNNING,
            started_at=started_at,
            steps=[],
            messages=[],
            artifacts=[],
        )
        self._active_runs[run_id] = response

        context: Dict[str, Any] = {
            "ticker": ticker,
            "depth": depth,
            "year": year or "latest",
            "artifacts": [],
            "scope": scope,
            "run_id": run_id,
        }

        try:
            for step_number, (agent_id, task_desc) in enumerate(agent_sequence, start=1):
                agent = self.agents.get(agent_id)
                if not agent:
                    logger.warning("Agent not found", agent=agent_id)
                    continue

                step = ExecutionStep(
                    step_number=step_number,
                    agent=agent_id,
                    status=ExecutionStatus.RUNNING,
                    started_at=datetime.utcnow(),
                )
                response.steps.append(step)

                task_message = f"Analyze {ticker}: {task_desc}"
                logger.info(
                    "Executing agent",
                    agent=agent_id,
                    ticker=ticker,
                    step=step_number,
                    task=task_desc,
                )

                try:
                    result = await agent.run(
                        messages=task_message,
                        ticker=ticker,
                        context=context,
                    )
                    result_text = self._extract_agent_output(result)

                    step.status = ExecutionStatus.COMPLETED
                    step.completed_at = datetime.utcnow()
                    step.duration_seconds = (
                        step.completed_at - step.started_at
                    ).total_seconds()
                    step.result = {"content": result_text}
                    step.output = result_text[:500]

                    context[f"{agent_id}_analysis"] = result_text

                    response.messages.append(
                        AgentMessage(
                            agent=agent_id,
                            content=result_text,
                            timestamp=datetime.utcnow(),
                        )
                    )

                    if progress_callback:
                        await progress_callback(
                            run_id,
                            "step_completed",
                            response.model_dump(),
                        )

                except Exception as exc:
                    logger.error(
                        "Agent execution failed",
                        agent=agent_id,
                        ticker=ticker,
                        error=str(exc),
                    )
                    step.status = ExecutionStatus.FAILED
                    step.completed_at = datetime.utcnow()
                    step.duration_seconds = (
                        step.completed_at - step.started_at
                    ).total_seconds()
                    step.error = str(exc)

                    if progress_callback:
                        await progress_callback(
                            run_id,
                            "step_failed",
                            response.model_dump(),
                        )

            response.status = ExecutionStatus.COMPLETED
            response.summary = (
                f"Completed sequential analysis of {ticker} with {len(response.steps)} steps"
            )
        except Exception as exc:
            logger.error("Sequential execution failed", run_id=run_id, error=str(exc))
            response.status = ExecutionStatus.FAILED
            response.error = str(exc)
        finally:
            response.completed_at = datetime.utcnow()
            response.duration_seconds = (
                response.completed_at - response.started_at
            ).total_seconds()
            self._ingest_artifacts_from_context(response, context)

            await self._save_run_to_cosmos(
                response=response,
                user_id=user_id,
                session_id=session_id,
                request_params={
                    "ticker": ticker,
                    "scope": scope,
                    "depth": depth,
                    "include_pdf": include_pdf,
                    "year": year,
                },
            )

        return response

    async def execute_concurrent(
        self,
        ticker: str,
        modules: List[str],
        aggregation_strategy: str = "merge",
        include_pdf: bool = True,
        year: Optional[str] = None,
        run_id: Optional[str] = None,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> OrchestrationResponse:
        run_id = run_id or str(uuid.uuid4())
        user_id = user_id or "unknown-user"
        started_at = datetime.utcnow()
        session_id = f"fin-{ticker}-{run_id[:8]}"

        logger.info(
            "Starting concurrent execution",
            run_id=run_id,
            session_id=session_id,
            ticker=ticker,
            modules=modules,
            user_id=user_id,
            aggregation_strategy=aggregation_strategy,
        )

        if self.cosmos:
            try:
                session = ResearchSession(
                    id=session_id,
                    session_id=session_id,
                    user_id=user_id,
                    metadata={
                        "ticker": ticker,
                        "pattern": "concurrent",
                        "modules": modules,
                        "aggregation_strategy": aggregation_strategy,
                    },
                )
                await self.cosmos.create_session(session)
                logger.debug("Created session in Cosmos", session_id=session_id)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to create session in Cosmos", error=str(exc))

        requested_agents = [module for module in modules if module not in {"all", "report"}]

        response = OrchestrationResponse(
            run_id=run_id,
            ticker=ticker,
            pattern=OrchestrationPattern.CONCURRENT,
            status=ExecutionStatus.RUNNING,
            started_at=started_at,
            steps=[],
            messages=[],
            artifacts=[],
        )
        self._active_runs[run_id] = response

        context: Dict[str, Any] = {
            "ticker": ticker,
            "year": year or "latest",
            "artifacts": [],
            "modules": modules,
            "run_id": run_id,
        }

        tasks = []
        executed_agents: List[str] = []
        for step_number, agent_name in enumerate(requested_agents, start=1):
            agent = self.agents.get(agent_name)
            if not agent:
                logger.warning("Agent not found", agent=agent_name)
                continue

            step = ExecutionStep(
                step_number=step_number,
                agent=agent_name,
                status=ExecutionStatus.RUNNING,
                started_at=datetime.utcnow(),
            )
            response.steps.append(step)
            executed_agents.append(agent_name)

            tasks.append(
                self._execute_agent_task(
                    agent=agent,
                    agent_name=agent_name,
                    ticker=ticker,
                    task=f"Analyze {ticker} for investment research",
                    context=context,
                    step=step,
                    run_id=run_id,
                    response=response,
                    progress_callback=progress_callback,
                )
            )

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for agent_name, result in zip(executed_agents, results):
                if isinstance(result, Exception):
                    logger.error(
                        "Concurrent agent failed",
                        agent=agent_name,
                        error=str(result),
                    )
                    continue

                context[f"{agent_name}_analysis"] = result
                response.messages.append(
                    AgentMessage(
                        agent=agent_name,
                        content=result,
                        timestamp=datetime.utcnow(),
                    )
                )

            if include_pdf:
                report_agent = self.agents.get("report")
                if report_agent:
                    report_step = ExecutionStep(
                        step_number=len(response.steps) + 1,
                        agent="report",
                        status=ExecutionStatus.RUNNING,
                        started_at=datetime.utcnow(),
                    )
                    response.steps.append(report_step)

                    try:
                        report_result = await report_agent.run(
                            messages="Generate comprehensive equity research report",
                            ticker=ticker,
                            context=context,
                        )
                        report_text = self._extract_agent_output(report_result)

                        report_step.status = ExecutionStatus.COMPLETED
                        report_step.completed_at = datetime.utcnow()
                        report_step.duration_seconds = (
                            report_step.completed_at - report_step.started_at
                        ).total_seconds()
                        report_step.result = {"content": report_text}
                        report_step.output = report_text[:500]

                        response.messages.append(
                            AgentMessage(
                                agent="report",
                                content=report_text,
                                timestamp=datetime.utcnow(),
                            )
                        )

                        if progress_callback:
                            await progress_callback(
                                run_id,
                                "step_completed",
                                response.model_dump(),
                            )

                    except Exception as exc:
                        logger.error("Report agent failed", error=str(exc))
                        report_step.status = ExecutionStatus.FAILED
                        report_step.completed_at = datetime.utcnow()
                        report_step.duration_seconds = (
                            report_step.completed_at - report_step.started_at
                        ).total_seconds()
                        report_step.error = str(exc)

                        if progress_callback:
                            await progress_callback(
                                run_id,
                                "step_failed",
                                response.model_dump(),
                            )

            response.status = ExecutionStatus.COMPLETED
            response.summary = (
                f"Completed concurrent analysis of {ticker} with {len(response.steps)} steps"
            )
        except Exception as exc:
            logger.error("Concurrent execution failed", run_id=run_id, error=str(exc))
            response.status = ExecutionStatus.FAILED
            response.error = str(exc)
        finally:
            response.completed_at = datetime.utcnow()
            response.duration_seconds = (
                response.completed_at - response.started_at
            ).total_seconds()
            self._ingest_artifacts_from_context(response, context)

            await self._save_run_to_cosmos(
                response=response,
                user_id=user_id,
                session_id=session_id,
                request_params={
                    "ticker": ticker,
                    "modules": modules,
                    "aggregation_strategy": aggregation_strategy,
                    "include_pdf": include_pdf,
                    "year": year,
                },
            )

        return response

    async def _execute_agent_task(
        self,
        *,
        agent: Any,
        agent_name: str,
        ticker: str,
        task: str,
        context: Dict[str, Any],
        step: ExecutionStep,
        run_id: str,
        response: OrchestrationResponse,
        progress_callback: Optional[ProgressCallback],
    ) -> str:
        try:
            logger.info("Starting concurrent agent", agent=agent_name)
            result = await agent.run(
                messages=task,
                ticker=ticker,
                context=context,
            )
            result_text = self._extract_agent_output(result)

            step.status = ExecutionStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            step.duration_seconds = (step.completed_at - step.started_at).total_seconds()
            step.output = result_text[:500]

            if progress_callback:
                await progress_callback(
                    run_id,
                    "step_completed",
                    response.model_dump(),
                )

            return result_text
        except Exception as exc:
            logger.error("Agent failed", agent=agent_name, error=str(exc))
            step.status = ExecutionStatus.FAILED
            step.completed_at = datetime.utcnow()
            step.duration_seconds = (step.completed_at - step.started_at).total_seconds()
            step.error = str(exc)

            if progress_callback:
                await progress_callback(
                    run_id,
                    "step_failed",
                    response.model_dump(),
                )

            raise

    def get_run_status(self, run_id: str) -> Optional[OrchestrationResponse]:
        return self._active_runs.get(run_id)

    def list_active_runs(self) -> List[OrchestrationResponse]:
        return [
            run
            for run in self._active_runs.values()
            if run.status == ExecutionStatus.RUNNING
        ]

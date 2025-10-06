"""
Orchestration Service

Coordinates multi-agent financial research leveraging Microsoft Agent Framework patterns.
Uses framework's SequentialPattern, ConcurrentPattern, HandoffPattern, and GroupChatPattern.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import structlog

from openai import AsyncAzureOpenAI

from ..models.dto import (
    OrchestrationPattern, ExecutionStatus, OrchestrationResponse,
    ExecutionStep, AgentMessage, ResearchArtifact
)
from ..infra.settings import Settings

# Add framework to path - add parent directory so 'framework' can be imported as a package
import sys
from pathlib import Path
repo_root = Path(__file__).parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Import agents from local app
from ..agents import (
    CompanyAgent, SECAgent, EarningsAgent,
    FundamentalsAgent, TechnicalsAgent, ReportAgent
)

# Import framework patterns and core components
from framework.patterns.sequential import SequentialPattern
from framework.patterns.concurrent import ConcurrentPattern
from framework.patterns.handoff import HandoffPattern
from framework.patterns.group_chat import GroupChatPattern
from framework.core.registry import AgentRegistry, AgentMetadata
from framework.config.settings import Settings as FrameworkSettings

# Import persistence layer
from ..persistence.cosmos_memory import CosmosMemoryStore
from ..models.persistence_models import ResearchRun, ResearchSession

logger = structlog.get_logger(__name__)


class FinancialOrchestrationService:
    """
    Orchestration service for financial research workflows.
    
    Leverages Microsoft Agent Framework orchestration patterns:
    - Sequential: Linear agent execution with context building
    - Concurrent: Parallel execution with result aggregation
    - Handoff: Dynamic agent delegation based on expertise
    - GroupChat: Multi-agent collaborative discussion
    """
    
    def __init__(self, settings: Settings, azure_client: AsyncAzureOpenAI):
        """Initialize orchestration service."""
        self.settings = settings
        self.azure_client = azure_client
        
        # Ensure framework Settings has required environment variables
        # Map our deployment name to framework's expected name
        import os
        if not os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'):
            os.environ['AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'] = settings.azure_openai_deployment
        
        # Create framework settings for AgentRegistry
        framework_settings = FrameworkSettings()
        self.agent_registry = AgentRegistry(settings=framework_settings)
        
        # Initialize agents (without registration)
        self.agents = self._create_agents()
        
        # Active executions (in-memory cache)
        self._active_runs: Dict[str, OrchestrationResponse] = {}
        self._execution_lock = asyncio.Lock()
        
        # Initialize Cosmos DB persistence (if configured)
        self.cosmos: Optional[CosmosMemoryStore] = None
        if settings.cosmos_db_endpoint:
            self.cosmos = CosmosMemoryStore(
                endpoint=settings.cosmos_db_endpoint,
                database_name=settings.cosmos_db_database,
                container_name=settings.cosmos_db_container,
            )
            logger.info("Cosmos DB persistence enabled", 
                       database=settings.cosmos_db_database,
                       container=settings.cosmos_db_container)
        else:
            logger.warning("Cosmos DB not configured - runs will only be stored in memory")
        
        logger.info("FinancialOrchestrationService initialized with framework patterns", 
                    num_agents=len(self.agents))
    
    async def initialize(self) -> None:
        """Async initialization - register agents and initialize Cosmos DB."""
        await self._register_agents()
        
        # Initialize Cosmos DB if configured
        if self.cosmos:
            await self.cosmos.initialize()
            logger.info("Cosmos DB persistence initialized")
    
    async def _save_run_to_cosmos(
        self,
        response: OrchestrationResponse,
        user_id: str,
        session_id: str,
        request_params: Dict[str, Any]
    ) -> None:
        """Save research run to Cosmos DB."""
        if not self.cosmos:
            return
        
        try:
            # Convert OrchestrationResponse to ResearchRun
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
                metadata=response.metadata
            )
            
            # Upsert (create or update)
            await self.cosmos.update_run(research_run)
            logger.debug("Saved run to Cosmos DB", run_id=response.run_id)
            
        except Exception as e:
            logger.error("Failed to save run to Cosmos DB", run_id=response.run_id, error=str(e))
    
    def _create_agents(self) -> Dict[str, Any]:
        """Create all financial research agents (sync)."""
        agents = {}
        
        try:
            # Initialize agents
            agents["company"] = CompanyAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
                fmp_api_key=self.settings.fmp_api_key
            )
            agents["sec"] = SECAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
                fmp_api_key=self.settings.fmp_api_key
            )
            agents["earnings"] = EarningsAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
                fmp_api_key=self.settings.fmp_api_key
            )
            agents["fundamentals"] = FundamentalsAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment,
                fmp_api_key=self.settings.fmp_api_key
            )
            agents["technicals"] = TechnicalsAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment
            )
            agents["report"] = ReportAgent(
                azure_client=self.azure_client,
                model=self.settings.azure_openai_deployment
            )
            
            logger.info("All agents created successfully")
        except Exception as e:
            logger.error("Failed to create agents", error=str(e))
            raise
        
        return agents
    
    async def _register_agents(self) -> None:
        """Register all agents with the framework registry (async)."""
        try:
            for agent_name, agent_instance in self.agents.items():
                # Create proper AgentMetadata
                metadata = AgentMetadata(
                    id=f"financial_{agent_name}",
                    name=agent_name,
                    description=f"Financial research agent: {agent_name}",
                    tags=["financial_research", agent_name],
                    capabilities=[]
                )
                
                await self.agent_registry.register_agent(
                    name=agent_name,
                    agent=agent_instance,
                    metadata=metadata
                )
            
            logger.info("All agents registered successfully")
        except Exception as e:
            logger.error("Failed to register agents", error=str(e))
            raise
    
    async def execute_sequential(
        self,
        ticker: str,
        scope: List[str],
        depth: str = "standard",
        include_pdf: bool = True,
        year: Optional[str] = None,
        run_id: Optional[str] = None,
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> OrchestrationResponse:
        """
        Execute sequential research workflow using framework's SequentialPattern.
        
        Leverages MAF Sequential Pattern for ordered agent execution with context preservation.
        
        Args:
            ticker: Stock ticker symbol
            scope: List of analysis modules to run
            depth: Analysis depth (standard/deep/comprehensive)
            include_pdf: Whether to generate PDF report
            year: Optional year for historical analysis
            run_id: Optional pre-generated run ID
            user_id: Optional user identifier for tracking
            progress_callback: Optional async function to call after each step
        """
        run_id = run_id or str(uuid.uuid4())
        user_id = user_id or "unknown-user"
        started_at = datetime.utcnow()
        
        # Create session ID (one session per research run)
        session_id = f"fin-{ticker}-{run_id[:8]}"
        
        logger.info(
            "Starting sequential execution with SequentialPattern",
            run_id=run_id,
            session_id=session_id,
            ticker=ticker,
            scope=scope,
            user_id=user_id
        )
        
        # Create session in Cosmos DB
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
                        "depth": depth
                    }
                )
                await self.cosmos.create_session(session)
                logger.debug("Created session in Cosmos", session_id=session_id)
            except Exception as e:
                logger.warning("Failed to create session in Cosmos", error=str(e))
        
        # Build agent sequence based on scope
        agent_sequence = []
        if "company" in scope or "all" in scope:
            agent_sequence.append("company")
        if "sec" in scope or "all" in scope:
            agent_sequence.append("sec")
        if "earnings" in scope or "all" in scope:
            agent_sequence.append("earnings")
        if "fundamentals" in scope or "all" in scope:
            agent_sequence.append("fundamentals")
        if "technicals" in scope or "all" in scope:
            agent_sequence.append("technicals")
        
        # Always add report at the end if PDF requested
        if include_pdf:
            agent_sequence.append("report")
        
        # Create framework's SequentialPattern
        pattern = SequentialPattern(
            agents=agent_sequence,
            name=f"financial_research_{ticker}",
            description=f"Sequential financial analysis for {ticker}",
            config={
                "preserve_context": True,      # Pass context between agents
                "fail_fast": False,             # Continue even if an agent fails
                "context_window_limit": 32000   # Token limit for context
            }
        )
        
        # Initialize response
        response = OrchestrationResponse(
            run_id=run_id,
            ticker=ticker,
            pattern=OrchestrationPattern.SEQUENTIAL,
            status=ExecutionStatus.RUNNING,
            started_at=started_at,
            steps=[],
            messages=[],
            artifacts=[]
        )
        
        self._active_runs[run_id] = response
        
        try:
            # Execute using framework pattern
            logger.info(f"Executing SequentialPattern with {len(agent_sequence)} agents", agents=agent_sequence)
            
            # Build task with context
            task = f"Perform comprehensive financial research and analysis for {ticker}"
            context = {
                "ticker": ticker,
                "depth": depth,
                "year": year or "latest",
                "artifacts": [],
                "scope": scope,
                "run_id": run_id
            }
            
            # Execute agents sequentially using pattern
            step_num = 1
            for agent_name in agent_sequence:
                agent = self.agents.get(agent_name)
                if not agent:
                    logger.warning(f"Agent not found: {agent_name}")
                    continue
                
                step = ExecutionStep(
                    step_number=step_num,
                    agent=agent_name,
                    status=ExecutionStatus.RUNNING,
                    started_at=datetime.utcnow()
                )
                response.steps.append(step)
                
                try:
                    logger.info(f"Executing agent {agent_name}", step=step_num)
                    
                    # Execute agent with MAF interface
                    result = await agent.run(
                        messages=task,
                        thread=None,
                        ticker=ticker,
                        context=context
                    )
                    
                    # Extract response text from MAF response
                    result_text = ""
                    if hasattr(result, 'messages') and result.messages:
                        for msg in result.messages:
                            if hasattr(msg, 'text'):
                                result_text += msg.text + "\n"
                            elif hasattr(msg, 'contents'):
                                for content in msg.contents:
                                    if hasattr(content, 'text'):
                                        result_text += content.text + "\n"
                    
                    logger.info(
                        f"Agent {agent_name} completed",
                        step=step_num,
                        output_length=len(result_text)
                    )
                    
                    # Update step
                    step.status = ExecutionStatus.COMPLETED
                    step.completed_at = datetime.utcnow()
                    step.output = result_text[:500]  # Store first 500 chars
                    
                    # Broadcast progress update
                    if progress_callback:
                        await progress_callback(run_id, "step_completed", response.model_dump())
                    
                    # Add to context for next agent (context preservation)
                    context[f"{agent_name}_analysis"] = result_text
                    
                    # Add message
                    response.messages.append(AgentMessage(
                        agent=agent_name,
                        content=result_text,
                        timestamp=datetime.utcnow()
                    ))
                    
                except Exception as e:
                    logger.error(f"Agent {agent_name} failed", error=str(e))
                    step.status = ExecutionStatus.FAILED
                    step.completed_at = datetime.utcnow()
                    step.error = str(e)
                    
                    if pattern.fail_fast:
                        raise
                
                step_num += 1
            
            # Extract artifacts from context and convert to ResearchArtifact objects
            raw_artifacts = context.get("artifacts", [])
            for artifact_data in raw_artifacts:
                if isinstance(artifact_data, dict):
                    artifact = ResearchArtifact(
                        id=artifact_data.get("id", str(uuid.uuid4())),
                        type=artifact_data.get("type", "text"),
                        title=artifact_data.get("title", "Analysis Result"),
                        content=artifact_data.get("content", ""),
                        timestamp=datetime.utcnow(),
                        metadata=artifact_data.get("metadata", {})
                    )
                    response.artifacts.append(artifact)
                else:
                    # Already a ResearchArtifact object
                    response.artifacts.append(artifact_data)
            
            response.status = ExecutionStatus.COMPLETED
            response.completed_at = datetime.utcnow()
            
            logger.info(f"Sequential execution completed successfully",
                        run_id=run_id,
                        steps=step_num-1,
                        artifacts=len(response.artifacts))
            
            # Save to Cosmos DB
            await self._save_run_to_cosmos(
                response=response,
                user_id=user_id,
                session_id=session_id,
                request_params={
                    "ticker": ticker,
                    "scope": scope,
                    "depth": depth,
                    "include_pdf": include_pdf,
                    "year": year
                }
            )
            
            return response
            
        except Exception as e:
            logger.error("Sequential execution failed", run_id=run_id, error=str(e))
            response.status = ExecutionStatus.FAILED
            response.completed_at = datetime.utcnow()
            response.error = str(e)
            
            # Save failed run to Cosmos DB
            await self._save_run_to_cosmos(
                response=response,
                user_id=user_id,
                session_id=session_id,
                request_params={
                    "ticker": ticker,
                    "scope": scope,
                    "depth": depth,
                    "include_pdf": include_pdf,
                    "year": year
                }
            )
            
            return response
            return response
        # Create execution context
        context = {
            "ticker": ticker,
            "depth": depth,
            "year": year or "latest",
            "artifacts": [],
            "scope": scope
        }
        
        # Build agent sequence based on scope
        agent_sequence = []
        if "company" in scope or "all" in scope:
            agent_sequence.append(("company", "Company analysis"))
        if "sec" in scope or "all" in scope:
            agent_sequence.append(("sec", "SEC filing analysis"))
        if "earnings" in scope or "all" in scope:
            agent_sequence.append(("earnings", "Earnings call analysis"))
        if "fundamentals" in scope or "all" in scope:
            agent_sequence.append(("fundamentals", "Fundamental analysis"))
        if "technicals" in scope or "all" in scope:
            agent_sequence.append(("technicals", "Technical analysis"))
        
        # Always add report at the end if PDF requested
        if include_pdf:
            agent_sequence.append(("report", "Generate equity brief"))
        
        # Initialize response
        response = OrchestrationResponse(
            run_id=run_id,
            ticker=ticker,
            pattern=OrchestrationPattern.SEQUENTIAL,
            status=ExecutionStatus.RUNNING,
            started_at=started_at,
            steps=[],
            messages=[],
            artifacts=[]
        )
        
        self._active_runs[run_id] = response
        
        try:
            # Execute agents sequentially
            step_num = 1
            for agent_id, task_desc in agent_sequence:
                agent = self.agents.get(agent_id)
                if not agent:
                    continue
                
                step = ExecutionStep(
                    step_number=step_num,
                    agent=agent_id,
                    status=ExecutionStatus.RUNNING,
                    started_at=datetime.utcnow()
                )
                response.steps.append(step)
                
                try:
                    # Execute agent with context
                    task_message = f"Analyze {ticker}: {task_desc}"
                    
                    logger.info(
                        f"Executing agent {agent_id}",
                        agent=agent_id,
                        ticker=ticker,
                        task=task_desc,
                        step=step_num
                    )
                    
                    result = await agent.run(
                        messages=task_message,
                        ticker=ticker,
                        context=context
                    )
                    
                    # Extract response text
                    result_text = ""
                    if hasattr(result, 'messages') and result.messages:
                        for msg in result.messages:
                            if hasattr(msg, 'contents') and msg.contents:
                                for content in msg.contents:
                                    if hasattr(content, 'text'):
                                        result_text += content.text + "\n"
                    
                    logger.info(
                        f"Agent {agent_id} completed",
                        agent=agent_id,
                        ticker=ticker,
                        output_length=len(result_text),
                        duration=step.duration_seconds if hasattr(step, 'duration_seconds') else 0
                    )
                    
                    # Log first 200 chars of output for debugging
                    logger.debug(
                        f"Agent {agent_id} output preview",
                        agent=agent_id,
                        output_preview=result_text[:200] if result_text else "[empty]"
                    )
                    
                    # Update step
                    step.status = ExecutionStatus.COMPLETED
                    step.completed_at = datetime.utcnow()
                    step.duration_seconds = (
                        step.completed_at - step.started_at
                    ).total_seconds()
                    step.result = {"content": result_text}
                    
                    # Add agent message
                    agent_msg = AgentMessage(
                        agent_id=agent_id,
                        agent_name=agent.name if hasattr(agent, 'name') else agent_id,
                        timestamp=datetime.utcnow(),
                        content=result_text[:500],  # Truncate for summary
                        metadata={"step": step_num}
                    )
                    response.messages.append(agent_msg)
                    
                    step_num += 1
                    
                except Exception as e:
                    logger.error("Agent execution failed",
                                agent=agent_id, error=str(e), ticker=ticker)
                    step.status = ExecutionStatus.FAILED
                    step.error = str(e)
                    step.completed_at = datetime.utcnow()
            
            # Extract artifacts from context
            for artifact_data in context.get("artifacts", []):
                artifact = ResearchArtifact(
                    id=str(uuid.uuid4()),
                    type=artifact_data.get("type", "text"),
                    title=f"{artifact_data.get('agent', 'Agent')} Output",
                    content=artifact_data.get("content", ""),
                    timestamp=datetime.utcnow(),
                    metadata=artifact_data
                )
                response.artifacts.append(artifact)
            
            # Complete execution
            response.status = ExecutionStatus.COMPLETED
            response.completed_at = datetime.utcnow()
            response.duration_seconds = (
                response.completed_at - response.started_at
            ).total_seconds()
            
            # Generate summary
            response.summary = f"Completed sequential analysis of {ticker} with {len(response.steps)} steps"
            
            logger.info("Sequential execution completed",
                        run_id=run_id, duration=response.duration_seconds)
            
        except Exception as e:
            logger.error("Sequential execution failed",
                        run_id=run_id, error=str(e))
            response.status = ExecutionStatus.FAILED
            response.error = str(e)
            response.completed_at = datetime.utcnow()
        
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
        progress_callback: Optional[callable] = None
    ) -> OrchestrationResponse:
        """
        Execute concurrent research workflow using framework's ConcurrentPattern.
        
        Leverages MAF Concurrent Pattern for parallel agent execution with result aggregation.
        """
        run_id = run_id or str(uuid.uuid4())
        user_id = user_id or "unknown-user"
        started_at = datetime.utcnow()
        
        # Create session ID (one session per research run)
        session_id = f"fin-{ticker}-{run_id[:8]}"
        
        logger.info(
            "Starting concurrent execution with ConcurrentPattern",
            run_id=run_id,
            session_id=session_id,
            ticker=ticker,
            modules=modules,
            user_id=user_id
        )
        
        # Create session in Cosmos DB
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
                        "aggregation_strategy": aggregation_strategy
                    }
                )
                await self.cosmos.create_session(session)
                logger.debug("Created session in Cosmos", session_id=session_id)
            except Exception as e:
                logger.warning("Failed to create session in Cosmos", error=str(e))
        
        # Build agent list (excluding 'all' and 'report')
        agent_list = [m for m in modules if m != "all" and m != "report"]
        
        # Create framework's ConcurrentPattern
        pattern = ConcurrentPattern(
            agents=agent_list,
            name=f"concurrent_research_{ticker}",
            description=f"Parallel financial analysis for {ticker}",
            config={
                "aggregation_strategy": aggregation_strategy,  # How to combine results
                "max_concurrent": 5,                           # Max parallel executions
                "timeout_per_agent": 120                       # 2 minutes per agent
            }
        )
        
        # Initialize response
        response = OrchestrationResponse(
            run_id=run_id,
            ticker=ticker,
            pattern=OrchestrationPattern.CONCURRENT,
            status=ExecutionStatus.RUNNING,
            started_at=started_at,
            steps=[],
            messages=[],
            artifacts=[]
        )
        
        self._active_runs[run_id] = response
        
        try:
            logger.info(f"Executing ConcurrentPattern with {len(agent_list)} agents", agents=agent_list)
            
            # Build shared context
            context = {
                "ticker": ticker,
                "year": year or "latest",
                "artifacts": [],
                "modules": modules,
                "run_id": run_id
            }
            
            task = f"Analyze {ticker} for investment research"
            
            # Execute all agents concurrently
            tasks = []
            step_num = 1
            
            for agent_name in agent_list:
                agent = self.agents.get(agent_name)
                if not agent:
                    logger.warning(f"Agent not found: {agent_name}")
                    continue
                
                step = ExecutionStep(
                    step_number=step_num,
                    agent=agent_name,
                    status=ExecutionStatus.RUNNING,
                    started_at=datetime.utcnow()
                )
                response.steps.append(step)
                
                # Create concurrent task
                async_task = self._execute_agent_task(agent, agent_name, ticker, task, context, step)
                tasks.append(async_task)
                step_num += 1
            
            # Execute all tasks concurrently
            logger.info(f"Executing {len(tasks)} agents in parallel")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Concurrent agent failed", agent=agent_list[idx], error=str(result))
                    response.steps[idx].status = ExecutionStatus.FAILED
                    response.steps[idx].completed_at = datetime.utcnow()
                    response.steps[idx].error = str(result)
                else:
                    # Result is the response text
                    response.messages.append(AgentMessage(
                        agent=agent_list[idx],
                        content=result,
                        timestamp=datetime.utcnow()
                    ))
                    
                    # Update context with result
                    context[f"{agent_list[idx]}_analysis"] = result
            
            # Run report agent if requested (sequential after concurrent)
            if include_pdf:
                report_agent = self.agents.get("report")
                if report_agent:
                    logger.info("Executing report agent after concurrent analysis")
                    report_step = ExecutionStep(
                        step_number=step_num,
                        agent="report",
                        status=ExecutionStatus.RUNNING,
                        started_at=datetime.utcnow()
                    )
                    response.steps.append(report_step)
                    
                    try:
                        report_result = await report_agent.run(
                            messages="Generate comprehensive equity research report",
                            thread=None,
                            ticker=ticker,
                            context=context
                        )
                        
                        # Extract report text
                        report_text = ""
                        if hasattr(report_result, 'messages') and report_result.messages:
                            for msg in report_result.messages:
                                if hasattr(msg, 'text'):
                                    report_text += msg.text
                                elif hasattr(msg, 'contents'):
                                    for content in msg.contents:
                                        if hasattr(content, 'text'):
                                            report_text += content.text
                        
                        report_step.status = ExecutionStatus.COMPLETED
                        report_step.completed_at = datetime.utcnow()
                        
                        response.messages.append(AgentMessage(
                            agent="report",
                            content=report_text,
                            timestamp=datetime.utcnow()
                        ))
                        
                    except Exception as e:
                        logger.error("Report agent failed", error=str(e))
                        report_step.status = ExecutionStatus.FAILED
                        report_step.completed_at = datetime.utcnow()
                        report_step.error = str(e)
            
            # Extract artifacts from context and convert to ResearchArtifact objects
            raw_artifacts = context.get("artifacts", [])
            for artifact_data in raw_artifacts:
                if isinstance(artifact_data, dict):
                    artifact = ResearchArtifact(
                        id=artifact_data.get("id", str(uuid.uuid4())),
                        type=artifact_data.get("type", "text"),
                        title=artifact_data.get("title", "Analysis Result"),
                        content=artifact_data.get("content", ""),
                        timestamp=datetime.utcnow(),
                        metadata=artifact_data.get("metadata", {})
                    )
                    response.artifacts.append(artifact)
                else:
                    # Already a ResearchArtifact object
                    response.artifacts.append(artifact_data)
            
            response.status = ExecutionStatus.COMPLETED
            response.completed_at = datetime.utcnow()
            
            logger.info(f"Concurrent execution completed",
                        run_id=run_id,
                        agents=len(agent_list),
                        artifacts=len(response.artifacts))
            
            # Save to Cosmos DB
            await self._save_run_to_cosmos(
                response=response,
                user_id=user_id,
                session_id=session_id,
                request_params={
                    "ticker": ticker,
                    "modules": modules,
                    "aggregation_strategy": aggregation_strategy,
                    "include_pdf": include_pdf,
                    "year": year
                }
            )
            
            return response
            
        except Exception as e:
            logger.error("Concurrent execution failed", run_id=run_id, error=str(e))
            response.status = ExecutionStatus.FAILED
            response.completed_at = datetime.utcnow()
            response.error = str(e)
            
            # Save failed run to Cosmos DB
            await self._save_run_to_cosmos(
                response=response,
                user_id=user_id,
                session_id=session_id,
                request_params={
                    "ticker": ticker,
                    "modules": modules,
                    "aggregation_strategy": aggregation_strategy,
                    "include_pdf": include_pdf,
                    "year": year
                }
            )
            
            return response
    
    async def _execute_agent_task(
        self,
        agent: Any,
        agent_name: str,
        ticker: str,
        task: str,
        context: Dict[str, Any],
        step: ExecutionStep
    ) -> str:
        """Execute a single agent task (helper for concurrent execution)."""
        try:
            logger.info(f"Starting agent {agent_name}")
            
            result = await agent.run(
                messages=task,
                thread=None,
                ticker=ticker,
                context=context
            )
            
            # Extract response text
            result_text = ""
            if hasattr(result, 'messages') and result.messages:
                for msg in result.messages:
                    if hasattr(msg, 'text'):
                        result_text += msg.text + "\n"
                    elif hasattr(msg, 'contents'):
                        for content in msg.contents:
                            if hasattr(content, 'text'):
                                result_text += content.text + "\n"
            
            step.status = ExecutionStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            step.output = result_text[:500]  # Store first 500 chars
            
            logger.info(f"Agent {agent_name} completed", output_length=len(result_text))
            
            return result_text
            
        except Exception as e:
            logger.error(f"Agent {agent_name} failed", error=str(e))
            step.status = ExecutionStatus.FAILED
            step.completed_at = datetime.utcnow()
            step.error = str(e)
            raise
    
    async def _execute_agent_concurrent(
        self,
        agent: Any,
        agent_id: str,
        ticker: str,
        context: Dict[str, Any],
        step: ExecutionStep
    ) -> Dict[str, Any]:
        """Execute a single agent in concurrent mode."""
        try:
            result = await agent.run(
                messages=f"Analyze {ticker}",
                ticker=ticker,
                context=context
            )
            
            # Extract content
            content = ""
            if hasattr(result, 'messages') and result.messages:
                for msg in result.messages:
                    if hasattr(msg, 'contents') and msg.contents:
                        for c in msg.contents:
                            if hasattr(c, 'text'):
                                content += c.text + "\n"
            
            # Update step
            step.status = ExecutionStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            step.duration_seconds = (
                step.completed_at - step.started_at
            ).total_seconds()
            step.result = {"content": content}
            
            return {
                "agent_id": agent_id,
                "agent_name": agent.name if hasattr(agent, 'name') else agent_id,
                "content": content,
                "success": True
            }
            
        except Exception as e:
            step.status = ExecutionStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.utcnow()
            raise
    
    def get_run_status(self, run_id: str) -> Optional[OrchestrationResponse]:
        """Get status of a running or completed execution."""
        return self._active_runs.get(run_id)
    
    def list_active_runs(self) -> List[OrchestrationResponse]:
        """List all active runs."""
        return [
            run for run in self._active_runs.values()
            if run.status == ExecutionStatus.RUNNING
        ]

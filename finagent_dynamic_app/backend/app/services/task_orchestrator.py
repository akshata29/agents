"""Task orchestrator service for the financial research application."""

import uuid
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Sequence

import structlog

from ..maf import (
    MAFAgentFactory,
    MAFDynamicPlanner,
    MAFOrchestrator,
    PlanParsingError,
    PlanStep,
)

from ..agents import (
    CompanyAgent,
    EarningsAgent,
    ForecasterAgent,
    FundamentalsAgent,
    ReportAgent,
    SECAgent,
    SummarizerAgent,
    TechnicalsAgent,
)

from ..models.task_models import (
    InputTask,
    Plan,
    Step,
    AgentMessage,
    HumanFeedback,
    Session,
    StepStatus,
    PlanStatus,
    AgentType,
    DataType,
    HumanFeedbackStatus,
    PlanWithSteps,
    ActionRequest,
    ActionResponse,
)
from ..persistence.cosmos_memory import CosmosMemoryStore
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)


class TaskOrchestrator:
    """Coordinates planning and execution using Microsoft Agent Framework components."""

    def __init__(
        self,
        settings: Settings,
        cosmos_store: Optional[CosmosMemoryStore] = None,
    ):
        self.settings = settings

        self.agent_factory = MAFAgentFactory(self.settings)
        self.planning_agent = self.agent_factory.create_chat_agent(
            agent_type="planner",
            name="financial_planner",
        )
        self.orchestrator = MAFOrchestrator()

        self.cosmos = cosmos_store
        self.registered_agents: Dict[str, object] = {}

        self.available_agents = self._get_available_agents()

        logger.info(
            "TaskOrchestrator initialized",
            available_agents=list(self.available_agents.keys()),
        )

    async def initialize(self) -> None:
        logger.info("Initializing TaskOrchestrator")

        if self.cosmos is None:
            self.cosmos = CosmosMemoryStore(
                endpoint=self.settings.COSMOSDB_ENDPOINT,
                database_name=self.settings.COSMOSDB_DATABASE,
                container_name=self.settings.COSMOSDB_CONTAINER,
                tenant_id=self.settings.azure_tenant_id,
                client_id=self.settings.azure_client_id,
                client_secret=self.settings.azure_client_secret,
            )

        await self.cosmos.initialize()
        self._register_agents()

        logger.info("TaskOrchestrator initialization complete")

    async def shutdown(self) -> None:
        logger.info("Shutting down TaskOrchestrator")

        if self.cosmos:
            await self.cosmos.close()

        logger.info("TaskOrchestrator shutdown complete")

    def _register_agents(self) -> None:
        """Instantiate and register financial domain agents with the orchestrator."""
        if self.registered_agents:
            logger.debug("Agents already registered", agents=list(self.registered_agents))
            return

        chat_client = self.agent_factory.chat_client

        agents: Dict[str, object] = {
            AgentType.COMPANY.value: CompanyAgent(
                name=AgentType.COMPANY.value,
                chat_client=chat_client,
                model=self.settings.AZURE_OPENAI_DEPLOYMENT,
                fmp_api_key=self.settings.FMP_API_KEY,
                mcp_server_url=self.settings.YAHOO_FINANCE_MCP_URL,
            ),
            AgentType.SEC.value: SECAgent(
                name=AgentType.SEC.value,
                chat_client=chat_client,
                model=self.settings.AZURE_OPENAI_DEPLOYMENT,
                fmp_api_key=self.settings.FMP_API_KEY,
            ),
            AgentType.EARNINGS.value: EarningsAgent(
                name=AgentType.EARNINGS.value,
                chat_client=chat_client,
                model=self.settings.AZURE_OPENAI_DEPLOYMENT,
                fmp_api_key=self.settings.FMP_API_KEY,
            ),
            AgentType.FUNDAMENTALS.value: FundamentalsAgent(
                name=AgentType.FUNDAMENTALS.value,
                chat_client=chat_client,
                model=self.settings.AZURE_OPENAI_DEPLOYMENT,
                fmp_api_key=self.settings.FMP_API_KEY,
            ),
            AgentType.TECHNICALS.value: TechnicalsAgent(
                name=AgentType.TECHNICALS.value,
                chat_client=chat_client,
                model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            ),
            AgentType.FORECASTER.value: ForecasterAgent(
                name=AgentType.FORECASTER.value,
                chat_client=chat_client,
                model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            ),
            AgentType.SUMMARIZER.value: SummarizerAgent(
                name=AgentType.SUMMARIZER.value,
                chat_client=chat_client,
                model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            ),
            AgentType.REPORT.value: ReportAgent(
                name=AgentType.REPORT.value,
                chat_client=chat_client,
                model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            ),
        }

        self.orchestrator.register_agent(self.planning_agent.name, self.planning_agent)
        logger.info("Registered planning agent", agent_name=self.planning_agent.name)

        for agent_name, agent_instance in agents.items():
            self.orchestrator.register_agent(agent_name, agent_instance)
            self.registered_agents[agent_name] = agent_instance
            logger.info(
                "Registered financial agent",
                agent=agent_name,
                agent_class=type(agent_instance).__name__,
            )


    async def create_plan_from_objective(
        self,
        input_task: InputTask
    ) -> PlanWithSteps:
        """
        Create execution plan from user objective using the native MAF planner.
        
        Args:
            input_task: User's input task with objective and context
            
        Returns:
            PlanWithSteps: Created plan with steps, stored in CosmosDB
        """
        logger.info(
            "Creating plan from objective",
            description=input_task.description[:100],
            session_id=input_task.session_id
        )

        try:
            session_id = f"session-{uuid.uuid4().hex[:8]}"
            user_id = input_task.user_id or "default-user"

            extracted_ticker = await self._extract_ticker_from_text(input_task.description)
            ticker = input_task.ticker or extracted_ticker

            logger.info(
                "Ticker extraction",
                input_ticker=input_task.ticker,
                extracted_ticker=extracted_ticker,
                final_ticker=ticker,
            )

            session_metadata = {"objective": input_task.description[:200]}
            if ticker:
                session_metadata["ticker"] = ticker

            session = Session(
                id=session_id,
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.utcnow(),
                metadata=session_metadata,
            )
            await self.cosmos.create_session(session)
            logger.info("Created new session for research task", session_id=session_id, ticker=ticker)

            planning_rules = self._compose_planning_rules(input_task.description)
            planner = MAFDynamicPlanner(self.planning_agent, planning_rules=planning_rules)

            summary_type = input_task.depth or "executive"
            persona = "investment"

            try:
                plan_steps = await planner.generate_plan(
                    objective=input_task.description,
                    files_info=[],
                    summary_type=summary_type,
                    persona=persona,
                    ticker=ticker,
                )
            except PlanParsingError as parse_error:
                logger.error(
                    "Planner returned unparsable response",
                    error=str(parse_error),
                    objective=input_task.description[:100],
                )
                raise

            if not plan_steps:
                raise PlanParsingError("Planner returned no actionable steps")

            plan, steps = self._convert_plan_steps_to_models(
                plan_steps,
                input_task=input_task,
                session_id=session_id,
                user_id=user_id,
                ticker=ticker,
            )

            # Store plan and steps in Cosmos
            await self.cosmos.add_plan(plan)
            
            for step in steps:
                logger.info(
                    f"Saving step to Cosmos",
                    step_id=step.id,
                    action=step.action[:50],
                    agent=step.agent.value,
                    dependencies=step.dependencies,
                    tools=step.tools
                )
                await self.cosmos.add_step(step)

            logger.info(
                "Plan created and stored",
                plan_id=plan.id,
                steps_count=len(steps),
                session_id=plan.session_id
            )

            # Create PlanWithSteps for API response
            plan_with_steps = PlanWithSteps(
                id=plan.id,
                session_id=plan.session_id,
                user_id=plan.user_id,
                initial_goal=plan.initial_goal,
                summary=plan.summary,
                overall_status=plan.overall_status,
                human_clarification_request=plan.human_clarification_request,
                human_clarification_response=plan.human_clarification_response,
                total_steps=plan.total_steps,
                completed_steps=plan.completed_steps,
                failed_steps=plan.failed_steps,
                timestamp=plan.timestamp,
                ticker=plan.ticker,
                scope=plan.scope,
                steps=steps,
                steps_requiring_approval=sum(1 for s in steps if s.human_approval_status == HumanFeedbackStatus.REQUESTED)
            )

            return plan_with_steps

        except Exception as e:
            logger.error(
                "Failed to create plan",
                error=str(e),
                description=input_task.description[:100]
            )
            raise

    def _compose_planning_rules(self, objective: str) -> str:
        """Build the instruction block fed into the native planner."""
        agent_sections = []
        for agent_name, agent_info in self.available_agents.items():
            tools_desc = "\n    ".join(agent_info.get("tools_detailed", agent_info.get("tools", [])))
            agent_sections.append(
                f"- {agent_name}:\n    Description: {agent_info['description']}\n    Tools:\n    {tools_desc}"
            )

        objective_lower = objective.lower()

        if any(
            keyword in objective_lower
            for keyword in ["stock quote", "current price", "get quote", "stock price"]
        ) and not any(keyword in objective_lower for keyword in ["forecast", "predict"]):
            step_guidance = "Create ONLY 1 step to retrieve the requested stock price information."
        elif any(
            keyword in objective_lower
            for keyword in [
                "comprehensive",
                "full analysis",
                "detailed analysis",
                "deep research",
                "complete analysis",
            ]
        ):
            step_guidance = (
                "Create 5-8 steps for thorough analysis across multiple dimensions "
                "(data gathering, analysis, synthesis)."
            )
        elif any(
            keyword in objective_lower
            for keyword in ["predict", "forecast", "stock movement", "price prediction"]
        ):
            step_guidance = (
                "Create 2-4 steps: gather required data (news/financials/etc) and then "
                "perform the requested prediction/forecast."
            )
        elif "news" in objective_lower and any(
            keyword in objective_lower for keyword in ["sentiment", "summary", "analyze"]
        ):
            step_guidance = "Create 2 steps: (1) get news, (2) analyze or summarize as requested."
        elif any(
            keyword in objective_lower
            for keyword in [
                "get news",
                "get recommendation",
                "get financial",
                "company profile",
                "company info",
            ]
        ) and objective_lower.count("get") == 1:
            step_guidance = "Create ONLY 1-2 steps to retrieve the requested information."
        else:
            step_guidance = (
                "Create 2-3 focused steps that directly address the objective without "
                "adding unrequested analysis."
            )

        planning_rules = f"""
Financial Planning Rules:
1. {step_guidance}
2. Each step MUST specify the precise agent and the tool/function to invoke.
3. ONLY include steps that are explicitly required or clearly implied by the objective.
4. Use `Parameters: {{dependencies: [step_numbers]}}` for any step that relies on prior results.
5. Do NOT add comprehensive analysis unless the objective explicitly requests it.

Available Agents and Tools:
{chr(10).join(agent_sections)}

Formatting Requirements:
- Format every line exactly as: `Step N: <action>. Agent: <Agent_Name>. Tool: <tool_name>.`
- Include optional `Parameters: {{dependencies: [1,2], notes: "..."}}` only when needed.
- Use the exact Agent values shown above (e.g., Company_Agent, SEC_Agent).
- Keep the plan concise and strictly aligned to the user's request.
"""

        return planning_rules

    def _convert_plan_steps_to_models(
        self,
        plan_steps: List[PlanStep],
        *,
        input_task: InputTask,
        session_id: str,
        user_id: str,
        ticker: Optional[str],
    ) -> tuple[Plan, List[Step]]:
        """Convert parsed ``PlanStep`` objects into persisted Plan/Steps."""

        plan_id = str(uuid.uuid4())
        order_to_step_id: Dict[int, str] = {}
        pending_dependencies: Dict[str, List[int]] = {}
        steps: List[Step] = []

        for plan_step in sorted(plan_steps, key=lambda s: s.order):
            step_id = str(uuid.uuid4())
            order_to_step_id[plan_step.order] = step_id

            dependencies = self._extract_dependency_orders(plan_step.parameters)
            pending_dependencies[step_id] = dependencies

            tools = [plan_step.tool] if plan_step.tool else []
            required_artifacts = self._extract_required_artifacts(plan_step.parameters)

            step = Step(
                id=step_id,
                data_type=DataType.STEP,
                session_id=session_id,
                plan_id=plan_id,
                user_id=user_id,
                action=plan_step.action,
                agent=self._map_agent_name_to_type(plan_step.agent),
                status=StepStatus.PLANNED,
                order=plan_step.order,
                timestamp=datetime.utcnow(),
                dependencies=[],
                required_artifacts=required_artifacts,
                tools=tools,
            )
            steps.append(step)

        # Resolve dependency order numbers to actual step IDs
        for step in steps:
            dep_orders = pending_dependencies.get(step.id, [])
            resolved: List[str] = []
            for dep_order in dep_orders:
                dep_id = order_to_step_id.get(dep_order)
                if dep_id:
                    resolved.append(dep_id)
                else:
                    logger.warning(
                        "Unable to resolve dependency order",
                        step_id=step.id,
                        missing_order=dep_order,
                    )
            step.dependencies = resolved

        plan = Plan(
            id=plan_id,
            data_type=DataType.PLAN,
            session_id=session_id,
            user_id=user_id,
            initial_goal=input_task.description,
            overall_status=PlanStatus.IN_PROGRESS,
            total_steps=len(steps),
            completed_steps=0,
            failed_steps=0,
            ticker=ticker,
            scope=input_task.scope,
            timestamp=datetime.utcnow(),
        )

        return plan, steps

    @staticmethod
    def _extract_dependency_orders(parameters: Dict[str, Any]) -> List[int]:
        """Extract dependency orders from planner parameters."""
        raw = parameters.get("dependencies") or parameters.get("dependency")
        if not raw:
            return []

        if isinstance(raw, list):
            candidates = raw
        elif isinstance(raw, str):
            candidates = [part.strip() for part in raw.strip("[]").split(",") if part.strip()]
        else:
            candidates = [raw]

        orders: List[int] = []
        for item in candidates:
            try:
                orders.append(int(item))
            except (TypeError, ValueError):
                continue
        return orders

    @staticmethod
    def _extract_required_artifacts(parameters: Dict[str, Any]) -> List[str]:
        """Extract required artifact hints from planner parameters."""
        artifacts = parameters.get("required_artifacts") or parameters.get("artifacts")
        if not artifacts:
            return []
        if isinstance(artifacts, list):
            return [str(item) for item in artifacts]
        if isinstance(artifacts, str):
            return [item.strip() for item in artifacts.split(",") if item.strip()]
        return [str(artifacts)]

    async def get_plan_with_steps(
        self,
        plan_id: str,
        session_id: str
    ) -> Optional[PlanWithSteps]:
        """
        Retrieve plan with all its steps from CosmosDB.
        
        Args:
            plan_id: Plan identifier
            session_id: Session identifier (partition key)
            
        Returns:
            PlanWithSteps with full plan and step details, or None if not found
        """
        logger.info("Retrieving plan with steps", plan_id=plan_id)

        try:
            # Get plan from Cosmos
            plan = await self.cosmos.get_plan(plan_id, session_id)
            if not plan:
                logger.warning("Plan not found", plan_id=plan_id)
                return None

            # Get all steps for this plan
            steps = await self.cosmos.get_steps_by_plan(plan_id, session_id)

            # Create PlanWithSteps response
            plan_with_steps = PlanWithSteps(
                id=plan.id,
                initial_goal=plan.initial_goal,
                session_id=plan.session_id,
                user_id=plan.user_id,
                summary=plan.summary,
                overall_status=plan.overall_status,
                human_clarification_request=plan.human_clarification_request,
                human_clarification_response=plan.human_clarification_response,
                total_steps=plan.total_steps,
                completed_steps=plan.completed_steps,
                failed_steps=plan.failed_steps,
                timestamp=plan.timestamp,
                ticker=plan.ticker,
                scope=plan.scope,
                steps=steps
            )

            logger.info(
                "Plan retrieved",
                plan_id=plan_id,
                steps_count=len(steps)
            )

            return plan_with_steps

        except Exception as e:
            logger.error(
                "Failed to retrieve plan",
                error=str(e),
                plan_id=plan_id
            )
            raise

    async def handle_step_approval(
        self,
        feedback: HumanFeedback
    ) -> ActionResponse:
        """
        Handle human approval/rejection of a step and execute if approved.
        
        Args:
            feedback: Human feedback with approval/rejection decision
            
        Returns:
            ActionResponse with execution results or rejection reason
        """
        logger.info(
            "Processing step approval",
            step_id=feedback.step_id,
            approved=feedback.approved,
            session_id=feedback.session_id
        )

        try:
            # Get step from Cosmos
            step = await self.cosmos.get_step(feedback.step_id, feedback.session_id)
            if not step:
                raise ValueError(f"Step {feedback.step_id} not found")

            logger.info(
                "Step retrieved from Cosmos",
                step_id=step.id,
                agent=step.agent.value,
                dependencies=step.dependencies,
                num_dependencies=len(step.dependencies) if step.dependencies else 0,
                tools=step.tools
            )

            # Update step based on feedback
            if feedback.approved:
                # Execute the step using framework patterns
                result = await self._execute_step(step, feedback)
                
                # Update step status to completed
                step.status = StepStatus.COMPLETED
                step.agent_reply = str(result.result) if result.result else None
                
                await self.cosmos.update_step(step)

                logger.info(
                    "Step executed successfully",
                    step_id=step.id,
                    agent=step.agent.value  # Use agent.value to get string
                )

                # Check if all steps are complete and update plan status
                await self._update_plan_status_if_complete(step.plan_id, step.session_id)

                return result

            else:
                # Step was rejected
                step.status = StepStatus.REJECTED
                step.agent_reply = feedback.human_feedback or "Rejected by user"
                
                await self.cosmos.update_step(step)

                logger.info("Step rejected", step_id=step.id)

                # Check if all steps are complete/rejected and update plan status
                await self._update_plan_status_if_complete(step.plan_id, step.session_id)

                return ActionResponse(
                    step_id=step.id,
                    plan_id=step.plan_id,
                    session_id=feedback.session_id,
                    success=False,
                    result="Step rejected by user",
                    metadata={"feedback": feedback.human_feedback}
                )

        except Exception as e:
            logger.error(
                "Failed to handle step approval",
                error=str(e),
                step_id=feedback.step_id
            )
            raise

    async def _check_dependencies(self, step: Step) -> tuple[bool, str]:
        """
        Check if all dependencies for a step are met.
        
        Dependencies are considered met if they are either:
        - COMPLETED: Successfully executed
        - REJECTED: User chose to skip, but dependent step can still proceed if approved
        
        Args:
            step: Step to check dependencies for
            
        Returns:
            Tuple of (dependencies_met: bool, reason: str)
        """
        if not step.dependencies:
            return True, "No dependencies"
        
        unmet_dependencies = []
        rejected_dependencies = []
        
        for dep_id in step.dependencies:
            try:
                dep_step = await self.cosmos.get_step(dep_id, step.session_id)
                
                # Allow execution if dependency is completed OR rejected (user decision)
                if dep_step.status == StepStatus.COMPLETED:
                    continue  # Dependency met successfully
                elif dep_step.status == StepStatus.REJECTED:
                    rejected_dependencies.append(f"{dep_step.action[:50]}")
                    continue  # Dependency rejected, but allow user to proceed if they approve
                else:
                    # Dependency is still pending/planned/running
                    unmet_dependencies.append(f"{dep_step.action[:50]} (Status: {dep_step.status})")
                    
            except Exception as e:
                logger.warning(f"Could not find dependency step {dep_id}", error=str(e))
                unmet_dependencies.append(f"Unknown step {dep_id}")
        
        if unmet_dependencies:
            reason = f"Waiting for dependencies: {', '.join(unmet_dependencies)}"
            return False, reason
        
        # Log if proceeding with rejected dependencies
        if rejected_dependencies:
            logger.warning(
                "Step proceeding with rejected dependencies",
                step_id=step.id,
                rejected_deps=rejected_dependencies
            )
            return True, f"Proceeding despite {len(rejected_dependencies)} rejected dependency(ies)"
        
        return True, "All dependencies met"

    async def _get_dependency_artifacts(self, step: Step) -> Dict[str, Any]:
        """
        Collect artifacts from all dependency steps.
        
        Args:
            step: Step to collect dependency artifacts for
            
        Returns:
            Dictionary containing all artifacts from dependent steps
        """
        all_artifacts = []
        
        logger.info(
            f"Collecting dependency artifacts for step {step.id}",
            num_dependencies=len(step.dependencies),
            dependency_ids=step.dependencies
        )
        
        for dep_id in step.dependencies:
            try:
                dep_step = await self.cosmos.get_step(dep_id)
                logger.info(
                    f"Processing dependency step {dep_id}",
                    dep_action=dep_step.action[:50],
                    dep_agent=dep_step.agent.value,
                    dep_status=dep_step.status,
                    has_reply=bool(dep_step.agent_reply),
                    dep_tools=dep_step.tools
                )
                
                # Get messages from the dependency step that contain artifacts
                messages = await self.cosmos.get_messages(
                    session_id=dep_step.session_id,
                    plan_id=dep_step.plan_id,
                    step_id=dep_id
                )
                
                logger.info(f"Found {len(messages)} messages for dependency step {dep_id}")
                
                # Extract artifacts from messages
                for msg in messages:
                    if msg.metadata and "artifact" in msg.metadata:
                        all_artifacts.append(msg.metadata["artifact"])
                        logger.info(f"Found artifact in message metadata")
                
                # Also include the step's result as an artifact
                if dep_step.agent_reply:
                    artifact = {
                        "type": "step_result",
                        "step_id": dep_id,
                        "agent": dep_step.agent.value,
                        "action": dep_step.action,
                        "content": dep_step.agent_reply,
                        "tools": dep_step.tools
                    }
                    all_artifacts.append(artifact)
                    logger.info(
                        f"Added step result as artifact",
                        agent=dep_step.agent.value,
                        tools=dep_step.tools,
                        content_length=len(dep_step.agent_reply)
                    )
                    
            except Exception as e:
                logger.error(f"Could not retrieve artifacts from dependency step {dep_id}", error=str(e), exc_info=True)
        
        logger.info(
            f"Total artifacts collected",
            num_artifacts=len(all_artifacts),
            step_id=step.id
        )
        
        return {"dependency_artifacts": all_artifacts}

    def _is_synthesis_agent(self, step: Step) -> bool:
        """
        Determine if this step is using a synthesis agent that needs comprehensive context.
        Synthesis agents (Forecaster, Report, Summarizer) analyze and combine outputs from multiple previous steps.
        
        Args:
            step: Step to check
            
        Returns:
            True if this is a synthesis agent
        """
        synthesis_agents = [AgentType.FORECASTER, AgentType.REPORT, AgentType.SUMMARIZER]
        is_synthesis = step.agent in synthesis_agents
        
        logger.info(
            f"Checking if synthesis agent",
            step_id=step.id,
            agent=step.agent.value,
            is_synthesis=is_synthesis
        )
        
        return is_synthesis

    async def _get_session_context(self, step: Step) -> Dict[str, Any]:
        """
        Collect outputs from ALL previous completed steps in the session.
        This is used for synthesis agents (Forecaster, Report) that need comprehensive context.
        
        Args:
            step: Current step being executed
            
        Returns:
            Dictionary containing all previous step results
        """
        logger.info(
            f"Collecting session context for synthesis agent",
            step_id=step.id,
            agent=step.agent.value,
            plan_id=step.plan_id
        )
        
        # Get all steps in the plan
        all_steps = await self.cosmos.get_steps_by_plan(step.plan_id, step.session_id)
        
        # Filter to completed steps that come before this step
        previous_steps = [
            s for s in all_steps 
            if s.status == StepStatus.COMPLETED and s.order < step.order
        ]
        
        logger.info(
            f"Found {len(previous_steps)} previous completed steps",
            step_id=step.id,
            current_order=step.order,
            all_steps_count=len(all_steps)
        )
        
        # Collect all outputs
        session_artifacts = []
        for prev_step in sorted(previous_steps, key=lambda s: s.order):
            if prev_step.agent_reply:
                artifact = {
                    "type": "step_result",
                    "step_id": prev_step.id,
                    "step_order": prev_step.order,
                    "agent": prev_step.agent.value,
                    "action": prev_step.action,
                    "content": prev_step.agent_reply,
                    "tools": prev_step.tools or []
                }
                session_artifacts.append(artifact)
                logger.info(
                    f"Added session context from step {prev_step.order}",
                    agent=prev_step.agent.value,
                    tools=prev_step.tools,
                    content_length=len(prev_step.agent_reply),
                    content_preview=prev_step.agent_reply[:100] if prev_step.agent_reply else ""
                )
        
        logger.info(
            f"Total session artifacts collected for synthesis",
            num_artifacts=len(session_artifacts),
            step_id=step.id
        )
        
        return {"session_context": session_artifacts}

    async def _execute_step(
        self,
        step: Step,
        feedback: HumanFeedback
    ) -> ActionResponse:
        """
        Execute a single plan step using native MAF agents.

        Execution strategy:
        - Prefer direct calls to the agent's ``process`` helper for single-agent work.
        - When collaboration is required, orchestrate a shared workflow via ``MAFOrchestrator``.
        - Fall back to a sequential workflow for agents that do not expose ``process``.

        Args:
            step: Step to execute
            feedback: User feedback with optional additional context

        Returns:
            ActionResponse with execution results
        """
        logger.info(
            "Executing step",
            step_id=step.id,
            agent=step.agent.value,
            description=step.action[:100],
            dependencies=step.dependencies,
            num_dependencies=len(step.dependencies) if step.dependencies else 0,
            tools=step.tools
        )

        try:
            # Check if dependencies are met
            deps_met, dep_reason = await self._check_dependencies(step)
            if not deps_met:
                logger.warning(
                    "Step dependencies not met",
                    step_id=step.id,
                    reason=dep_reason
                )
                return ActionResponse(
                    step_id=step.id,
                    plan_id=step.plan_id,
                    session_id=feedback.session_id,
                    success=False,
                    result=f"Cannot execute step: {dep_reason}",
                    metadata={"dependencies_unmet": True, "reason": dep_reason}
                )
            
            agent_name = step.agent.value
            agent_instance = self.registered_agents.get(agent_name)
            if agent_instance is None:
                try:
                    agent_instance = self.orchestrator.get_agent(agent_name)
                except KeyError:
                    agent_instance = None

            logger.info(
                "Resolved agent for execution",
                agent_name=agent_name,
                agent_class=type(agent_instance).__name__ if agent_instance else "None",
                has_process_method=bool(agent_instance and hasattr(agent_instance, "process")),
            )
            
            # Build task description and context with ticker
            task, context = await self._build_task_and_context_from_step(step, feedback)
            
            # Add comprehensive context based on agent type
            if self._is_synthesis_agent(step):
                # Synthesis agents (Forecaster, Report) need ALL previous step outputs
                session_ctx = await self._get_session_context(step)
                context.update(session_ctx)
                logger.info(
                    "Added comprehensive session context for synthesis agent",
                    step_id=step.id,
                    agent=step.agent.value,
                    num_session_artifacts=len(session_ctx.get("session_context", []))
                )
            elif step.dependencies:
                # Regular agents only need explicit dependency artifacts
                dep_artifacts = await self._get_dependency_artifacts(step)
                context.update(dep_artifacts)
                logger.info(
                    "Added dependency artifacts to context",
                    step_id=step.id,
                    num_artifacts=len(dep_artifacts.get("dependency_artifacts", []))
                )
            
            logger.info(
                "Task and context built for step execution",
                step_id=step.id,
                ticker=context.get('ticker'),
                context_keys=list(context.keys())
            )

            # Get tools for the agent(s) involved
            tools = self._get_tools_for_step(step)
            if tools and "requested_tools" not in context:
                context["requested_tools"] = tools

            # Determine if step requires multi-agent collaboration
            requires_collaboration = self._requires_multi_agent_collaboration(step)
            
            # Update step status to EXECUTING and add progress message
            step.status = StepStatus.EXECUTING
            await self.cosmos.update_step(step)
            logger.info(
                "Step status updated to EXECUTING",
                step_id=step.id,
                status=step.status
            )
            
            # Store progress message
            progress_message = AgentMessage(
                id=str(uuid.uuid4()),
                data_type=DataType.MESSAGE,
                session_id=feedback.session_id,
                user_id=step.user_id,
                plan_id=step.plan_id,
                step_id=step.id,
                content=f"🔄 {agent_name} is analyzing {context.get('ticker', 'data')}...",
                source=step.agent.value,
                message_type="progress",
                created_at=datetime.utcnow(),
                metadata={"progress": True}
            )
            await self.cosmos.add_message(progress_message)
            logger.info(
                "Progress message stored",
                step_id=step.id,
                message_id=progress_message.id,
                content_preview=progress_message.content[:50]
            )
            
            if not requires_collaboration and agent_instance and hasattr(agent_instance, "process"):
                logger.info(
                    "Executing via direct agent.process call",
                    agent_name=agent_name,
                    ticker=context.get("ticker"),
                    task_preview=task[:100],
                )
                result_text = await agent_instance.process(task, context)
                result = SimpleNamespace(
                    result=result_text or "",
                    metadata={
                        "mode": "direct_process",
                        "agent": agent_name,
                        "tools": tools,
                    },
                )
            else:
                if requires_collaboration:
                    workflow_agents = self._select_collaborating_agents(step)
                    logger.info(
                        "Executing collaborative workflow",
                        agents=workflow_agents,
                        step_id=step.id,
                    )
                    result = await self._execute_via_workflow(
                        workflow_agents,
                        task,
                        context,
                        concurrent=True,
                    )
                else:
                    logger.info(
                        "Executing via sequential workflow fallback",
                        agent_name=agent_name,
                        step_id=step.id,
                    )
                    result = await self._execute_via_workflow(
                        [agent_name],
                        task,
                        context,
                        concurrent=False,
                    )

            if tools and hasattr(result, "metadata") and isinstance(result.metadata, dict):
                result.metadata.setdefault("tools", tools)

            # Store agent message in Cosmos
            message = AgentMessage(
                id=str(uuid.uuid4()),
                data_type=DataType.MESSAGE,
                session_id=feedback.session_id,
                user_id=step.user_id,  # Add user_id
                plan_id=step.plan_id,
                step_id=step.id,
                content=str(result.result),
                source=step.agent.value,  # Use 'source' not 'agent_name'
                message_type="action_response",
                created_at=datetime.utcnow(),
                metadata={
                    "execution_context": result.metadata if hasattr(result, "metadata") else {}
                }
            )

            await self.cosmos.add_message(message)
            
            # Update step status to COMPLETED
            step.status = StepStatus.COMPLETED
            await self.cosmos.update_step(step)

            logger.info(
                "Step execution completed",
                step_id=step.id,
                agent=step.agent.value  # Use agent.value
            )

            return ActionResponse(
                step_id=step.id,
                plan_id=step.plan_id,
                session_id=feedback.session_id,
                success=True,
                result=str(result.result) if hasattr(result, 'result') else "Execution completed",
                metadata={"message_id": message.id}
            )

        except Exception as e:
            logger.error(
                "Step execution failed",
                error=str(e),
                step_id=step.id,
                agent=step.agent.value  # Use agent.value
            )

            # Store error message
            error_message = AgentMessage(
                id=str(uuid.uuid4()),
                data_type=DataType.MESSAGE,
                session_id=feedback.session_id,
                user_id=step.user_id,  # Add user_id
                plan_id=step.plan_id,
                step_id=step.id,
                content=f"Error: {str(e)}",
                source=step.agent.value,  # Use 'source' not 'agent_name'
                message_type="error",
                created_at=datetime.utcnow(),
                metadata={"error": True}
            )

            await self.cosmos.add_message(error_message)
            
            # Update step status to FAILED
            step.status = StepStatus.FAILED
            await self.cosmos.update_step(step)

            return ActionResponse(
                step_id=step.id,
                plan_id=step.plan_id,
                session_id=feedback.session_id,
                success=False,
                result=None,
                error=str(e)
            )

    async def _execute_via_workflow(
        self,
        agent_names: Sequence[str],
        task: str,
        context: Dict[str, Any],
        *,
        concurrent: bool,
    ) -> SimpleNamespace:
        """Run a MAF workflow for the supplied agents and return a result namespace."""

        if not agent_names:
            raise ValueError("At least one agent is required to execute a workflow")

        prompt = self._build_workflow_prompt(task, context)
        logger.info(
            "Starting workflow execution",
            agents=list(agent_names),
            concurrent=concurrent and len(agent_names) > 1,
            prompt_preview=prompt[:200],
        )

        if concurrent and len(agent_names) > 1:
            workflow_result = await self.orchestrator.run_concurrent(agent_names, prompt)
        else:
            workflow_result = await self.orchestrator.run_sequential(agent_names, prompt)

        text = workflow_result.last_text()
        logger.info(
            "Workflow execution finished",
            agents=list(agent_names),
            result_length=len(text) if text else 0,
        )

        return SimpleNamespace(
            result=text or "",
            metadata={
                "mode": "workflow",
                "agents": list(agent_names),
                "concurrent": concurrent and len(agent_names) > 1,
            },
        )

    def _build_workflow_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Render a rich prompt that includes task details and contextual artifacts."""

        lines = [
            "Collaborative Research Task:",
            task.strip(),
            "",
        ]

        ticker = context.get("ticker")
        scope = context.get("scope") or context.get("objective_scope")

        if ticker:
            lines.append(f"Ticker: {ticker}")
        if scope:
            lines.append(f"Scope: {scope}")

        additional_keys = {
            key: value
            for key, value in context.items()
            if key not in {"ticker", "scope", "objective_scope", "dependency_artifacts", "session_context"}
            and not isinstance(value, (list, dict))
        }

        if additional_keys:
            lines.append("Context Attributes:")
            for key, value in additional_keys.items():
                lines.append(f"- {key}: {value}")

        artifacts: List[Dict[str, Any]] = []
        artifacts.extend(context.get("dependency_artifacts") or [])
        artifacts.extend(context.get("session_context") or [])

        if artifacts:
            lines.append("")
            lines.append("Relevant Prior Findings:")
            for artifact in artifacts:
                artifact_type = artifact.get("type") or artifact.get("agent") or "artifact"
                content = artifact.get("content") or artifact.get("summary") or ""
                truncated = content[:400] + ("..." if content and len(content) > 400 else "")
                lines.append(f"- {artifact_type}: {truncated}")

        lines.append("")
        lines.append("Please collaborate to produce a concise, data-backed response.")

        return "\n".join(lines)

    async def _update_plan_status_if_complete(self, plan_id: str, session_id: str) -> None:
        """
        Check if all steps in a plan are complete and update plan status accordingly.
        
        Args:
            plan_id: The plan ID to check
            session_id: The session ID
        """
        try:
            logger.info("Checking plan status for completion", plan_id=plan_id, session_id=session_id)
            
            # Get the plan
            plan = await self.cosmos.get_plan(plan_id, session_id)
            if not plan:
                logger.warning("Plan not found for status update", plan_id=plan_id)
                return
            
            # Get all steps for this plan
            steps = await self.cosmos.get_steps_by_plan(plan_id, session_id)
            if not steps:
                logger.warning("No steps found for plan", plan_id=plan_id)
                return
            
            # Count step statuses
            total_steps = len(steps)
            completed_steps = sum(1 for s in steps if s.status == StepStatus.COMPLETED)
            failed_steps = sum(1 for s in steps if s.status == StepStatus.FAILED)
            rejected_steps = sum(1 for s in steps if s.status == StepStatus.REJECTED)
            
            logger.info("Step status breakdown", 
                       plan_id=plan_id,
                       total=total_steps,
                       completed=completed_steps,
                       failed=failed_steps,
                       rejected=rejected_steps)
            
            # Calculate finished steps (terminal states: completed, failed, or rejected)
            finished_steps = completed_steps + failed_steps + rejected_steps
            
            # Update plan metadata
            plan.total_steps = total_steps
            plan.completed_steps = completed_steps
            plan.failed_steps = failed_steps
            
            # Determine overall plan status
            if finished_steps == total_steps:
                # All steps have reached a terminal state
                if failed_steps > 0 and completed_steps == 0:
                    # All steps failed (none completed) - mark as FAILED
                    plan.overall_status = PlanStatus.FAILED
                    logger.info("Plan failed - all steps failed", plan_id=plan_id, failed=failed_steps)
                else:
                    # At least some steps completed, or mix of completed/rejected - mark as COMPLETED
                    plan.overall_status = PlanStatus.COMPLETED
                    logger.info("Plan completed", 
                              plan_id=plan_id, 
                              completed=completed_steps,
                              rejected=rejected_steps,
                              failed=failed_steps,
                              total=total_steps)
            # else: keep IN_PROGRESS if there are still pending steps
            
            # Update the plan in Cosmos
            await self.cosmos.update_plan(plan)
            
            logger.info("Plan status updated", 
                       plan_id=plan_id, 
                       status=plan.overall_status,
                       completed=completed_steps,
                       total=total_steps)
            
        except Exception as e:
            logger.error("Failed to update plan status", plan_id=plan_id, error=str(e))

    async def _build_task_and_context_from_step(
        self,
        step: Step,
        feedback: HumanFeedback
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build task description and context for agent execution.
        
        Args:
            step: Step to execute
            feedback: User feedback with optional context
            
        Returns:
            Tuple of (task description string, context dictionary with ticker/scope/previous_results)
        """
        task_parts = []
        context = {}
        
        # Try to get plan context for ticker/scope information
        try:
            plan = await self.cosmos.get_plan(step.plan_id, step.session_id)
            if plan:
                # Add ticker to context if available
                if plan.ticker:
                    context['ticker'] = plan.ticker
                    task_parts.append(f"Stock Ticker: {plan.ticker}")
                
                # Add scope context if available
                if plan.scope:
                    context['scope'] = plan.scope
                    task_parts.append(f"Analysis Scope: {', '.join(plan.scope)}")
                
                # Add separator if we added context
                if task_parts:
                    task_parts.append("")  # Empty line for separation
        except Exception as e:
            logger.warning(f"Could not fetch plan context: {str(e)}")
        
        # For Report agent, gather all previous step results
        if step.agent == AgentType.REPORT:
            try:
                # Get all messages for this plan from previous steps
                all_messages = await self.cosmos.get_messages_by_plan(step.plan_id)
                
                # Filter to only action_response messages (agent outputs)
                previous_results = []
                for msg in all_messages:
                    if msg.message_type == "action_response" and msg.step_id != step.id:
                        previous_results.append({
                            "agent": msg.source,
                            "content": msg.content
                        })
                
                if previous_results:
                    context['previous_results'] = previous_results
                    logger.info(
                        "Added previous results to Report agent context",
                        result_count=len(previous_results),
                        agents=[r['agent'] for r in previous_results]
                    )
            except Exception as e:
                logger.warning(f"Could not fetch previous results for Report agent: {str(e)}")
        
        # Add the main action
        task_parts.append(step.action)

        # Add user feedback/clarification if provided
        if feedback.human_feedback:
            task_parts.append(f"\nUser feedback: {feedback.human_feedback}")

        task_description = "\n".join(task_parts)
        
        logger.info(
            "Built task and context",
            step_id=step.id,
            ticker=context.get('ticker'),
            has_scope=bool(context.get('scope'))
        )
        
        return task_description, context

    def _get_tools_for_step(self, step: Step) -> List[str]:
        """
        Get the list of tools available for a step based on the agent(s) involved.
        
        Args:
            step: The step to get tools for
            
        Returns:
            List of tool names
        """
        # Get tools for the primary agent
        agent_name = step.agent.value
        agent_info = self.available_agents.get(agent_name, {})
        tools = agent_info.get("tools", [])
        
        # If collaboration is required, also include tools from other agents
        if self._requires_multi_agent_collaboration(step):
            # Get all agents that might collaborate
            collaborating_agents = self._select_collaborating_agents(step)
            for collab_agent_name in collaborating_agents:
                if collab_agent_name != agent_name:
                    collab_agent_info = self.available_agents.get(collab_agent_name, {})
                    collab_tools = collab_agent_info.get("tools", [])
                    tools.extend(collab_tools)
            
            # Deduplicate tools
            tools = list(set(tools))
        
        logger.info(
            f"Tools for step",
            step_id=step.id,
            agent=agent_name,
            tools=tools
        )
        
        return tools


    def _get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get available agents and their capabilities with detailed tool information."""
        # Import agents to get their tool info
        from ..agents.company_agent import CompanyAgent
        from ..agents.forecaster_agent import ForecasterAgent
        
        company_tools = CompanyAgent.get_tools_info()
        company_tools_list = [f"{name}: {info['description']}" for name, info in company_tools.items()]
        
        forecaster_tools = ForecasterAgent.get_tools_info()
        forecaster_tools_list = [f"{name}: {info['description']}" for name, info in forecaster_tools.items()]
        
        return {
            AgentType.COMPANY.value: {
                "type": AgentType.COMPANY,
                "description": "Company intelligence via Yahoo Finance MCP Server and FMP API",
                "tools": list(company_tools.keys()),
                "tools_detailed": company_tools_list
            },
            AgentType.SEC.value: {
                "type": AgentType.SEC,
                "description": "SEC filings and regulatory document analysis",
                "tools": ["sec_filings", "form_10k", "form_10q"],
                "tools_detailed": ["sec_filings: Retrieve and analyze SEC filings"]
            },
            AgentType.EARNINGS.value: {
                "type": AgentType.EARNINGS,
                "description": "Earnings reports and call transcript analysis",
                "tools": ["earnings_data", "transcripts", "earnings_calendar"],
                "tools_detailed": ["transcripts: Analyze earnings call transcripts"]
            },
            AgentType.FUNDAMENTALS.value: {
                "type": AgentType.FUNDAMENTALS,
                "description": "Fundamental financial analysis and metrics",
                "tools": ["financial_ratios", "income_statement", "balance_sheet"],
                "tools_detailed": ["financial_ratios: Calculate and analyze financial ratios"]
            },
            AgentType.TECHNICALS.value: {
                "type": AgentType.TECHNICALS,
                "description": "Technical analysis and chart patterns",
                "tools": ["price_data", "indicators", "chart_patterns"],
                "tools_detailed": ["indicators: Calculate technical indicators"]
            },
            AgentType.FORECASTER.value: {
                "type": AgentType.FORECASTER,
                "description": "Stock price forecasting and prediction using sentiment analysis and trend prediction",
                "tools": list(forecaster_tools.keys()),
                "tools_detailed": forecaster_tools_list
            },
            AgentType.SUMMARIZER.value: {
                "type": AgentType.SUMMARIZER,
                "description": "Summarizes information and generates focused summaries from provided context. Use for sentiment analysis, news summaries, and data synthesis without additional structure",
                "tools": ["summarize_information", "generate_sentiment_summary", "create_news_summary", "synthesize_findings"],
                "tools_detailed": [
                    "summarize_information: Create concise summaries from context",
                    "generate_sentiment_summary: Analyze and summarize sentiment from news/data",
                    "create_news_summary: Summarize news articles",
                    "synthesize_findings: Combine insights from multiple sources"
                ]
            },
            AgentType.REPORT.value: {
                "type": AgentType.REPORT,
                "description": "Report generation, synthesis, and summarization of analysis from other agents. Use this for comprehensive research briefs and structured reports",
                "tools": ["document_generation", "data_aggregation", "summary_creation", "pattern_analysis"],
                "tools_detailed": [
                    "document_generation: Create comprehensive reports",
                    "data_aggregation: Combine data from multiple sources",
                    "pattern_analysis: Identify positive developments, concerns, and key factors from gathered data"
                ]
            }
        }
    
    async def _extract_ticker_from_text(self, text: str) -> Optional[str]:
        """
        Intelligently extract ticker symbol from text using LLM.
        Handles company names, ticker symbols, and various formats.
        
        Args:
            text: Input text that may contain a company name or ticker symbol
            
        Returns:
            Extracted ticker symbol or None
        """
        try:
            from agent_framework.azure import AzureOpenAIChatClient
            from agent_framework import ChatMessage, Role
            
            extraction_prompt = f"""Extract the stock ticker symbol from the following text. 
The text may contain:
- A ticker symbol (e.g., "TSLA", "AAPL", "MSFT")
- A company name (e.g., "Tesla", "Apple Inc.", "Microsoft Corporation")
- Both ticker and company name

If you find a ticker or company name, respond with ONLY the ticker symbol in uppercase.
If no company or ticker is mentioned, respond with "NONE".

Text: {text}

Ticker symbol (uppercase only):"""

            # Use Microsoft Agent Framework's AzureOpenAIChatClient
            chat_client = AzureOpenAIChatClient(
                endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
                api_key=self.settings.AZURE_OPENAI_API_KEY,
                deployment_name=self.settings.AZURE_OPENAI_DEPLOYMENT,
                api_version=self.settings.AZURE_OPENAI_API_VERSION
            )
            
            # Create messages for the chat
            messages = [
                ChatMessage(role=Role.SYSTEM, text="You are a financial assistant that extracts stock ticker symbols."),
                ChatMessage(role=Role.USER, text=extraction_prompt)
            ]
            
            # Call the chat client using get_response
            response = await chat_client.get_response(messages=messages, temperature=0, max_tokens=10)
            
            # Extract ticker from response (ChatResponse has .text property directly)
            ticker = response.text.strip().upper()
            
            # Validate response
            if ticker and ticker != "NONE" and 1 <= len(ticker) <= 5 and ticker.isalpha():
                logger.info(
                    "LLM extracted ticker from text",
                    ticker=ticker,
                    original_text=text[:100]
                )
                return ticker
            
            logger.info("No valid ticker extracted by LLM", text=text[:100], llm_response=ticker)
            return None
            
        except Exception as e:
            logger.error("Failed to extract ticker using LLM", error=str(e), text=text[:100], exc_info=True)
            return None

    def _get_available_tools(self) -> List[str]:
        """Get list of all available tools across agents."""
        tools = []
        for agent_info in self.available_agents.values():
            tools.extend(agent_info["tools"])
        return list(set(tools))  # Deduplicate

    def _infer_agent_from_description(self, description: str) -> str:
        """Infer agent name from step description."""
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ["company", "profile", "overview"]):
            return "company"
        elif any(keyword in description_lower for keyword in ["sec", "filing", "10-k", "10-q"]):
            return "sec"
        elif any(keyword in description_lower for keyword in ["earnings", "transcript", "call"]):
            return "earnings"
        elif any(keyword in description_lower for keyword in ["fundamental", "ratio", "financial"]):
            return "fundamentals"
        elif any(keyword in description_lower for keyword in ["technical", "chart", "indicator"]):
            return "technicals"
        elif any(keyword in description_lower for keyword in ["forecast", "predict", "stock movement", "stock price"]):
            return "forecaster"
        elif any(keyword in description_lower for keyword in ["sentiment", "summarize", "summary"]):
            return "summarizer"
        elif any(keyword in description_lower for keyword in ["report", "research brief", "comprehensive analysis"]):
            return "report"
            return "report"
        
        return "generic"  # Fallback

    def _map_agent_name_to_type(self, agent_name: Optional[str]) -> AgentType:
        """Map agent name to AgentType enum."""
        if not agent_name:
            return AgentType.GENERIC
        
        # Normalize agent name: lowercase and remove _Agent suffix
        normalized = agent_name.lower().replace("_agent", "").strip()
        
        # Also handle common variations
        normalized = normalized.replace("earningcall", "earnings")
        
        mapping = {
            "company": AgentType.COMPANY,
            "sec": AgentType.SEC,
            "earnings": AgentType.EARNINGS,
            "fundamentals": AgentType.FUNDAMENTALS,
            "technicals": AgentType.TECHNICALS,
            "forecaster": AgentType.FORECASTER,
            "summarizer": AgentType.SUMMARIZER,
            "report": AgentType.REPORT,
            "planner": AgentType.PLANNER,
            "generic": AgentType.GENERIC
        }
        
        agent_type = mapping.get(normalized, AgentType.GENERIC)
        
        if agent_type == AgentType.GENERIC and agent_name:
            logger.warning(f"Unknown agent name '{agent_name}' (normalized: '{normalized}'), defaulting to GENERIC")
        
        return agent_type

    def _requires_multi_agent_collaboration(self, step: Step) -> bool:
        """
        Determine if a step requires multi-agent collaboration.
        
        Collaboration indicators:
        - Keywords like "compare", "synthesize", "integrate", "correlate"
        - Analysis requiring multiple perspectives
        
        Note: Report agent does NOT require collaboration - it synthesizes
        existing results from previous steps via messages.
        """
        action_lower = step.action.lower()
        
        collaboration_keywords = [
            "compare", "contrast", "integrate", "correlate",
            "combine", "merge", "cross-reference", "reconcile", "validate against"
        ]
        
        # Check if action requires collaboration (but not for report agent)
        if step.agent != AgentType.REPORT and any(keyword in action_lower for keyword in collaboration_keywords):
            return True
        
        return False

    def _select_collaborating_agents(self, step: Step) -> List[str]:
        """
        Select which agents should collaborate on a step.
        
        Strategy:
        - Always include the assigned agent
        - Add relevant agents based on step content
        - Limit to 2-4 agents for focused discussion
        """
        agents = [step.agent.value]  # Start with assigned agent
        action_lower = step.action.lower()
        
        # Add company agent for company-specific data
        if "company" in action_lower or "profile" in action_lower:
            if AgentType.COMPANY.value not in agents:
                agents.append(AgentType.COMPANY.value)
        
        # Add fundamentals for financial analysis
        if any(word in action_lower for word in ["financial", "ratio", "metric", "valuation"]):
            if AgentType.FUNDAMENTALS.value not in agents:
                agents.append(AgentType.FUNDAMENTALS.value)
        
        # Add report agent for synthesis tasks - but don't add if it's already the assigned agent
        if step.agent == AgentType.REPORT or "synthesize" in action_lower:
            # Report agent is already in the list from step.agent.value, so skip
            pass
        
        # Limit to 4 agents maximum
        return agents[:4]


"""
Task Orchestrator Service

Bridges the Magentic Framework's orchestration patterns with our CosmosDB persistence layer.

Pattern Usage:
- Planning: ReActPattern via orchestrator.execute() - Iterative reasoning loop for 
  dynamic plan generation (Observe→Think→Act→Reflect)
- Execution: Multiple patterns based on step complexity:
  * HandoffPattern - For single-agent tasks with potential delegation
  * GroupChatPattern - For multi-agent collaboration on complex steps
  * ReActPattern - For steps requiring iterative reasoning

Implements the approval workflow for task execution with human-in-the-loop control.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import structlog

# Add framework to path - add parent directory so 'framework' can be imported as a package
import sys
from pathlib import Path
repo_root = Path(__file__).parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Framework imports
from framework.core.planning import DynamicPlanner, ExecutionPlan, PlanStep
from framework.patterns import GroupChatPattern, HandoffPattern, ReActPattern
from framework.core.orchestrator import MagenticOrchestrator
from framework.agents.factory import AgentFactory
from framework.config.settings import Settings as FrameworkSettings

# Local imports
from ..models.task_models import (
    InputTask, Plan, Step, AgentMessage, HumanFeedback, Session,
    StepStatus, PlanStatus, AgentType, DataType, HumanFeedbackStatus,
    PlanWithSteps, ActionRequest, ActionResponse
)
from ..persistence.cosmos_memory import CosmosMemoryStore
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)


class TaskOrchestrator:
    """
    Orchestrates task planning and execution using framework patterns.
    
    Architecture:
    - Planning Phase: ReActPattern for iterative reasoning and dynamic plan creation
    - Execution Phase: Pattern selection based on step requirements:
      * HandoffPattern: Single-agent tasks with potential delegation to specialists
      * GroupChatPattern: Multi-agent collaboration for complex analysis
      * ReActPattern: Steps requiring iterative reasoning and decision-making
    
    Responsibilities:
    - Create plans using ReActPattern via orchestrator
    - Execute approved steps using appropriate patterns (Handoff/GroupChat/ReAct)
    - Manage plan/step state in CosmosDB
    - Handle human-in-the-loop approval workflow
    """

    def __init__(
        self,
        settings: Settings,
        cosmos_store: Optional[CosmosMemoryStore] = None
    ):
        """Initialize task orchestrator with framework components."""
        self.settings = settings
        
        # Initialize framework components
        framework_settings = self._create_framework_settings()
        self.planner = DynamicPlanner(framework_settings)
        self.orchestrator = MagenticOrchestrator(framework_settings)
        
        # Initialize agent factory for creating agents
        self.agent_factory = AgentFactory(framework_settings)
        
        # Create planning agent
        self.planning_agent = self.agent_factory.create_agent(
            agent_type="planner",
            name="financial_planner"
        )
        
        # Initialize Cosmos persistence
        self.cosmos = cosmos_store
        
        # Available agents and their capabilities
        self.available_agents = self._get_available_agents()
        
        logger.info(
            "TaskOrchestrator initialized",
            available_agents=list(self.available_agents.keys())
        )

    async def initialize(self) -> None:
        """Initialize orchestrator and dependencies."""
        logger.info("Initializing TaskOrchestrator")
        
        # Initialize Cosmos if not provided
        if self.cosmos is None:
            self.cosmos = CosmosMemoryStore(
                endpoint=self.settings.COSMOSDB_ENDPOINT,
                database_name=self.settings.COSMOSDB_DATABASE,
                container_name=self.settings.COSMOSDB_CONTAINER,
                tenant_id=self.settings.azure_tenant_id,
                client_id=self.settings.azure_client_id,
                client_secret=self.settings.azure_client_secret
            )
            await self.cosmos.__aenter__()
        
        # Initialize framework orchestrator
        await self.orchestrator.initialize()
        
        # Register custom financial domain agent types with the factory
        self._register_custom_agent_types()
        
        # Register the planning agent with the orchestrator
        await self.orchestrator.agent_registry.register_agent(
            self.planning_agent.name,
            self.planning_agent
        )
        logger.info("Registered planning agent", agent_name=self.planning_agent.name)
        
        # Create and register all execution agents
        for agent_name, agent_info in self.available_agents.items():
            try:
                logger.info(f"Creating agent: {agent_name}", agent_type=agent_name)
                agent = self.agent_factory.create_agent(
                    agent_type=agent_name,  # Use the agent name as type (company, sec, etc.)
                    name=agent_name
                )
                logger.info(
                    f"Agent created successfully: {agent_name}",
                    agent_class=type(agent).__name__,
                    agent_instance=str(agent)[:100]
                )
                await self.orchestrator.agent_registry.register_agent(agent_name, agent)
                logger.info(f"Registered execution agent: {agent_name}", agent_class=type(agent).__name__)
            except Exception as e:
                logger.error(f"Failed to create/register agent: {agent_name}", error=str(e), exc_info=True)
        
        logger.info("TaskOrchestrator initialization complete")

    async def shutdown(self) -> None:
        """Shutdown orchestrator and cleanup resources."""
        logger.info("Shutting down TaskOrchestrator")
        
        if self.cosmos:
            await self.cosmos.__aexit__(None, None, None)
        
        await self.orchestrator.shutdown()
        
        logger.info("TaskOrchestrator shutdown complete")

    async def create_plan_from_objective(
        self,
        input_task: InputTask
    ) -> PlanWithSteps:
        """
        Create execution plan from user objective using framework's DynamicPlanner.
        
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
            # ALWAYS create a new session for each plan/research task
            session_id = f"session-{uuid.uuid4().hex[:8]}"
            user_id = input_task.user_id or "default-user"  # Use authenticated user_id
            
            # Extract ticker symbol from the objective intelligently
            extracted_ticker = await self._extract_ticker_from_text(input_task.description)
            
            # Use extracted ticker if not explicitly provided
            ticker = input_task.ticker or extracted_ticker
            
            logger.info(
                "Ticker extraction",
                input_ticker=input_task.ticker,
                extracted_ticker=extracted_ticker,
                final_ticker=ticker,
                objective=input_task.description[:100]
            )
            
            # Create new session
            session = Session(
                id=session_id,
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.utcnow(),
                metadata={
                    "ticker": ticker,
                    "objective": input_task.description[:200]  # Store truncated objective
                } if ticker else {"objective": input_task.description[:200]}
            )
            await self.cosmos.create_session(session)
            logger.info("Created new session for research task", session_id=session_id, ticker=ticker)

            # Prepare agent descriptions for the planner with detailed tool information
            agent_descriptions = []
            for agent_name, agent_info in self.available_agents.items():
                tools_desc = "\n    ".join(agent_info.get('tools_detailed', agent_info['tools']))
                agent_descriptions.append(
                    f"- {agent_name}:\n    Description: {agent_info['description']}\n    Available Tools:\n    {tools_desc}"
                )
            
            # Determine step guidance based on objective keywords
            objective_lower = input_task.description.lower()
            
            # Simple objectives (just stock quotes, prices, basic info)
            if any(keyword in objective_lower for keyword in ["stock quote", "current price", "get quote", "stock price"]) and "forecast" not in objective_lower and "predict" not in objective_lower:
                step_guidance = "Create ONLY 1 step to retrieve the requested stock price information"
            # Comprehensive analysis ONLY when explicitly requested
            elif any(keyword in objective_lower for keyword in ["comprehensive", "full analysis", "detailed analysis", "deep research", "complete analysis"]):
                step_guidance = "Create 5-8 steps for thorough analysis across multiple dimensions (data gathering, analysis, synthesis)"
            # Prediction/forecast requests need data + analysis
            elif any(keyword in objective_lower for keyword in ["predict", "forecast", "stock movement", "price prediction"]):
                step_guidance = "Create 2-4 steps: gather required data (news/financials/etc), then perform the requested prediction/forecast"
            # News + something else
            elif "news" in objective_lower and ("sentiment" in objective_lower or "summary" in objective_lower or "analyze" in objective_lower):
                step_guidance = "Create 2 steps: (1) get news, (2) analyze/summarize as requested"
            # Single data request
            elif any(keyword in objective_lower for keyword in ["get news", "get recommendation", "get financial", "company profile", "company info"]) and objective_lower.count("get") == 1:
                step_guidance = "Create ONLY 1-2 steps to retrieve the requested information"
            # Default: minimal steps
            else:
                step_guidance = "Create 2-3 steps that DIRECTLY address the objective - do NOT add unrequested analysis"
            
            # Create detailed planning prompt with tool-level specificity
            planning_task = f"""
            Create a focused financial analysis plan for: {input_task.description}
            
            ⚠️ CRITICAL PLANNING RULES:
            1. Create ONLY the steps explicitly mentioned or clearly required by the objective
            2. DO NOT assume the user wants comprehensive analysis unless they specifically ask for it
            3. DO NOT add extra data gathering, analysis, or prediction steps beyond what's requested
            4. If the objective mentions specific tasks (e.g., "get news", "analyze sentiment", "predict price"), create steps ONLY for those tasks
            5. Do NOT add recommendations, financial metrics, predictions, or other analysis unless the objective explicitly asks for them
            6. Keep the plan minimal and focused - only what's needed to accomplish the stated objective
            
            Available Agents and Their Tools:
            {chr(10).join(agent_descriptions)}
            
            CRITICAL FORMATTING RULES:
            - ALWAYS include "Dependencies: [...]" for steps that need data from previous steps
            - Data gathering steps (Step 1, 2, 3) have NO dependencies
            - Analysis/forecast steps (Step 4+) MUST have Dependencies listing previous steps
            - Format EXACTLY as: "Step N: Action. Agent: name. Function: tool. Dependencies: [1,2]"
            
            Requirements:
            1. {step_guidance}
            2. Each step MUST specify BOTH the agent AND the specific tool/function to use
            3. CRITICAL: Analysis/forecast steps MUST include "Dependencies: [step_numbers]"
            4. ONLY create steps that are explicitly or clearly implied by the objective
            
            EXACT FORMAT EXAMPLES (use as reference for formatting only - create steps based on YOUR objective):
            
            Example 1 - Simple request: "Get news for Microsoft"
            Step 1: Get latest company news for MSFT. Agent: company. Function: get_yahoo_finance_news
            
            Example 2 - News + Sentiment: "Get news and sentiment for Tesla"
            Step 1: Get latest company news for TSLA. Agent: company. Function: get_yahoo_finance_news
            Step 2: Analyze sentiment from news. Agent: report. Function: data_aggregation. Dependencies: [1]
            
            Example 3 - Stock prediction request: "Predict AAPL stock movement"
            Step 1: Get latest company news for AAPL. Agent: company. Function: get_yahoo_finance_news
            Step 2: Get analyst recommendations for AAPL. Agent: company. Function: get_recommendations
            Step 3: Predict stock price movement. Agent: forecaster. Function: predict_stock_movement. Dependencies: [1,2]
            
            RULES:
            - Use ONLY these exact agent names: company, sec, earnings, fundamentals, technicals, forecaster, report
            - Specify the exact function/tool from the Available Tools list above
            - Data gathering steps have NO Dependencies field
            - Analysis/forecast steps MUST have Dependencies: [step_numbers] listing which steps they need data from
            - NO meta-planning, headers, or separators - ONLY numbered action steps
            
            {"Ticker Symbol: " + input_task.ticker if input_task.ticker else ""}
            
            OUTPUT FORMAT - Return ONLY the numbered steps:
            Step 1: [Action]. Agent: agent_name. Function: tool_name
            Step 2: [Action]. Agent: agent_name. Function: tool_name  
            Step 3: [Action]. Agent: agent_name. Function: tool_name. Dependencies: [1,2]
            ...
            
            Remember: 
            - Follow the objective literally - do NOT add comprehensive analysis unless requested
            - Choose the right agent based on their description
            - Choose the right tool/function based on what data you need
            - Specify dependencies for steps that need data from previous steps
            - Be specific: "Function: get_recommendations" not just "get recommendations"
            """
            
            logger.info("Creating plan using planning agent", task=input_task.description[:100])
            
            # Use the planning agent directly to generate the plan
            from framework.agents.base import AgentMessage
            
            plan_message = AgentMessage(
                role="user",
                content=planning_task
            )
            
            # Agent.process() returns a string, not AgentResponse
            plan_text = await self.planning_agent.process(plan_message, context={})
            
            logger.info(
                "Plan generation completed",
                content_length=len(plan_text) if plan_text else 0
            )
            
            if not plan_text or len(plan_text.strip()) == 0:
                raise ValueError("Plan generation returned empty response")
            
            # Parse the plan from the response
            execution_plan = await self._parse_plan_from_text(plan_text, input_task)
            
            logger.info(
                "Execution plan created",
                plan_id=execution_plan.id,
                steps_count=len(execution_plan.steps)
            )

            # Convert framework ExecutionPlan to our Plan model
            plan, steps = self._convert_framework_plan_to_model(
                execution_plan,
                input_task,
                session_id,
                user_id,
                ticker  # Pass the extracted/provided ticker
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
        Execute a single step using the appropriate framework pattern.
        
        Pattern Selection Strategy:
        - HandoffPattern: Default for single-agent tasks (allows delegation if needed)
        - GroupChatPattern: For steps requiring multi-agent collaboration
        - ReActPattern: For complex reasoning tasks (future enhancement)
        
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
            
            # Get the actual agent instance from the registry
            agent_name = step.agent.value
            agent_instance = await self.orchestrator.agent_registry.get_agent(agent_name)
            
            logger.info(
                f"Retrieved agent from registry: {agent_name}",
                agent_class=type(agent_instance).__name__ if agent_instance else "None",
                agent_type=str(type(agent_instance)),
                has_mcp=hasattr(agent_instance, 'mcp_server_url') if agent_instance else False
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
            
            # For single-agent execution with our custom agents, call directly with context
            if not requires_collaboration and agent_instance and hasattr(agent_instance, 'process'):
                logger.info(
                    f"Calling agent.process() directly with context",
                    agent_name=agent_name,
                    ticker=context.get('ticker'),
                    context_dict=context,
                    task_preview=task[:100]
                )
                result_text = await agent_instance.process(task, context)
                logger.info(
                    f"Agent.process() returned",
                    agent_name=agent_name,
                    result_length=len(result_text) if result_text else 0
                )
                result = type('Result', (), {'result': result_text, 'metadata': {}})()
            else:
                # Use patterns for collaboration or generic agents
                if requires_collaboration:
                    # Use GroupChatPattern for multi-agent collaboration
                    pattern = self._create_groupchat_pattern(step)
                    logger.info("Using GroupChatPattern for multi-agent collaboration", step_id=step.id)
                else:
                    # Use HandoffPattern for single-agent with delegation capability
                    pattern = self._create_handoff_pattern(step)
                    logger.info("Using HandoffPattern for single-agent execution", step_id=step.id)

                # Execute via orchestrator
                result = await self.orchestrator.execute(
                    task=task,
                    pattern=pattern,
                    tools=tools,  # Pass agent-specific tools
                    metadata={
                        "step_id": step.id,
                        "plan_id": step.plan_id,
                        "session_id": feedback.session_id,
                        **context  # Include ticker and scope in metadata
                    }
                )

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
                    "execution_context": result.metadata if hasattr(result, 'metadata') else {}
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

    def _convert_framework_plan_to_model(
        self,
        execution_plan: ExecutionPlan,
        input_task: InputTask,
        session_id: str,
        user_id: str,
        ticker: Optional[str] = None
    ) -> tuple[Plan, List[Step]]:
        """
        Convert framework's ExecutionPlan to our Plan and Step models.
        
        Args:
            execution_plan: Framework's execution plan
            input_task: Original user input
            session_id: Session identifier
            user_id: User identifier
            ticker: Extracted ticker symbol
            
        Returns:
            Tuple of (Plan model, List of Step models)
        """
        plan_id = str(uuid.uuid4())
        
        # Convert framework steps to our Step models
        steps = []
        step_counter = 0
        for idx, framework_step in enumerate(execution_plan.steps):
            # Skip non-actionable steps (headers, separators, metadata)
            description = framework_step.description.strip()
            if not description or len(description) < 10:
                continue
            if description.startswith(('---', '**', '###', '#')) or description.endswith(':'):
                continue
            if description.lower().startswith(('required tools', 'dependencies', 'expected outcome')):
                continue
            
            step_counter += 1
            
            # Parse agent from description if in format "Action (Agent: agent_name)"
            agent_name = framework_step.agent
            action_text = description
            
            # Try to extract agent from parentheses like "(Agent: company)"
            import re
            agent_match = re.search(r'\(Agent:\s*(\w+)\)', description, re.IGNORECASE)
            if agent_match:
                agent_name = agent_match.group(1)
                # Remove the agent annotation from the action text
                action_text = re.sub(r'\s*\(Agent:\s*\w+\)', '', description).strip()
            
            # If still no agent, infer from description
            if not agent_name or agent_name.lower() in ['none', 'unknown', '']:
                agent_name = self._infer_agent_from_description(action_text)
            
            logger.debug(
                "Converting step",
                step_number=step_counter,
                action=action_text[:50],
                agent=agent_name,
                dependencies=framework_step.dependencies,
                tools=framework_step.tools
            )
            
            step = Step(
                id=framework_step.id,
                data_type=DataType.STEP,
                session_id=session_id,
                plan_id=plan_id,
                user_id=user_id,
                action=action_text,
                agent=self._map_agent_name_to_type(agent_name),
                status=StepStatus.PLANNED,
                order=step_counter,
                timestamp=datetime.utcnow(),
                dependencies=framework_step.dependencies,  # Preserve dependencies
                tools=framework_step.tools  # Preserve tools
            )
            steps.append(step)
        
        logger.info(
            "Converted plan steps",
            total_framework_steps=len(execution_plan.steps),
            filtered_steps=len(steps)
        )

        # Create Plan model (steps are stored separately in Cosmos)
        plan = Plan(
            id=plan_id,
            data_type=DataType.PLAN,
            session_id=session_id,
            user_id=user_id,
            initial_goal=input_task.description,
            overall_status=PlanStatus.IN_PROGRESS,  # Use IN_PROGRESS not PENDING_APPROVAL
            total_steps=len(steps),
            ticker=ticker,  # Use the extracted/provided ticker
            created_at=datetime.utcnow()
        )

        return plan, steps

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

    def _create_framework_settings(self) -> FrameworkSettings:
        """Create framework settings from app settings."""
        # Import ObservabilitySettings from framework
        from framework.config.settings import ObservabilitySettings
        
        # Create observability settings with disabled observability
        obs_settings = ObservabilitySettings(
            enabled=self.settings.observability_enabled,
            otlp_endpoint=self.settings.observability_otlp_endpoint,
            applicationinsights_connection_string=self.settings.applicationinsights_connection_string
        )
        
        return FrameworkSettings(
            azure_openai_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            azure_openai_api_version=self.settings.AZURE_OPENAI_API_VERSION,
            azure_openai_deployment=self.settings.AZURE_OPENAI_DEPLOYMENT,
            log_level=self.settings.LOG_LEVEL,
            observability=obs_settings
        )

    def _register_custom_agent_types(self) -> None:
        """Register custom financial domain agent types with the factory."""
        
        def create_financial_agent(name: str, config: Dict[str, Any]):
            """Factory function for creating financial domain agents."""
            logger.info(f"create_financial_agent called for: {name}", config_keys=list(config.keys()))
            
            # Import our actual custom agent classes
            try:
                from ..agents import (
                    CompanyAgent, SECAgent, EarningsAgent,
                    FundamentalsAgent, TechnicalsAgent, ReportAgent, ForecasterAgent, SummarizerAgent
                )
                logger.info(f"Successfully imported custom agent classes for {name}")
            except Exception as e:
                logger.error(f"Failed to import custom agent classes for {name}", error=str(e), exc_info=True)
                raise
            
            # Use the framework's AzureOpenAIChatClient for consistency
            from agent_framework.azure import AzureOpenAIChatClient
            
            try:
                azure_chat_client = AzureOpenAIChatClient(
                    endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
                    api_key=self.settings.AZURE_OPENAI_API_KEY,
                    deployment_name=self.settings.AZURE_OPENAI_DEPLOYMENT,
                    api_version=self.settings.AZURE_OPENAI_API_VERSION
                )
                logger.info(f"AzureOpenAIChatClient created for {name}")
            except Exception as e:
                logger.error(f"Failed to create AzureOpenAIChatClient for {name}", error=str(e), exc_info=True)
                raise
            
            # Map agent names to actual classes
            agent_classes = {
                "company": CompanyAgent,
                "sec": SECAgent,
                "earnings": EarningsAgent,
                "fundamentals": FundamentalsAgent,
                "technicals": TechnicalsAgent,
                "report": ReportAgent,
                "forecaster": ForecasterAgent,
                "summarizer": SummarizerAgent
            }
            
            # Normalize agent name (remove _Agent suffix if present)
            normalized_name = name.lower().replace("_agent", "")
            agent_class = agent_classes.get(normalized_name)
            
            if not agent_class:
                logger.warning(f"Unknown agent type: {name} (normalized: {normalized_name}), falling back to generic agent")
                from framework.agents.factory import MicrosoftAgentWrapper
                from agent_framework import ChatAgent
                
                chat_agent = ChatAgent(
                    name=name,
                    chat_client=self.agent_factory._chat_client,
                    description=config.get("description", f"Financial agent: {name}"),
                    instruction=self._get_agent_instructions(name, config)
                )
                
                return MicrosoftAgentWrapper(
                    name=name,
                    chat_agent=chat_agent,
                    description=config.get("description", ""),
                    settings=self.agent_factory.settings
                )
            
            # Create the actual specialized agent with proper configuration
            agent_params = {
                "name": f"{normalized_name.capitalize()}Agent",
                "description": config.get("description", ""),
                "chat_client": azure_chat_client,  # Pass chat_client instead of azure_client
                "model": self.settings.AZURE_OPENAI_DEPLOYMENT
            }
            
            # Add specific params for CompanyAgent
            if normalized_name == "company":
                agent_params["fmp_api_key"] = self.settings.FMP_API_KEY
                agent_params["mcp_server_url"] = self.settings.YAHOO_FINANCE_MCP_URL
                logger.info(
                    f"CompanyAgent params prepared",
                    fmp_key_set=bool(self.settings.FMP_API_KEY),
                    mcp_url=self.settings.YAHOO_FINANCE_MCP_URL
                )
            
            # Add FMP API key for agents that need it
            if normalized_name in ["fundamentals", "earnings", "sec"]:
                agent_params["fmp_api_key"] = self.settings.FMP_API_KEY
                logger.info(
                    f"{normalized_name.capitalize()}Agent params prepared",
                    fmp_key_set=bool(self.settings.FMP_API_KEY)
                )
            
            # Create the agent instance
            try:
                agent = agent_class(**agent_params)
                logger.info(
                    f"Created custom agent instance: {name}",
                    agent_class=agent_class.__name__,
                    agent_type=str(type(agent)),
                    has_mcp=hasattr(agent, 'mcp_server_url')
                )
                return agent
            except Exception as e:
                logger.error(
                    f"Failed to instantiate {agent_class.__name__}",
                    error=str(e),
                    agent_params=list(agent_params.keys()),
                    exc_info=True
                )
                raise
        
        # Register each custom agent type
        for agent_name, agent_info in self.available_agents.items():
            self.agent_factory.register_agent_type(
                agent_type=agent_name,
                factory_func=create_financial_agent,
                description=agent_info["description"]
            )
            logger.info(f"Registered custom agent type: {agent_name}")

    def _get_agent_instructions(self, agent_name: str, config: Dict[str, Any]) -> str:
        """Get specialized instructions for each agent type."""
        base_instruction = f"""You are a specialized financial analysis agent: {agent_name}.

Description: {config.get('description', '')}

Available Tools: {', '.join(config.get('tools', []))}

Your responsibilities:
"""
        
        # Map AgentType enum values to instructions (handle both enum values and lowercase)
        agent_key = agent_name.replace("_Agent", "").lower() if "_Agent" in agent_name else agent_name.lower()
        
        instructions = {
            "company": """
- Retrieve and analyze company profiles and market data
- Provide current stock quotes and trading information
- Analyze company overview, industry position, and competitive landscape
- Use company_profile, stock_quotes, and market_data tools
""",
            "sec": """
- Access and analyze SEC filings (10-K, 10-Q, 8-K)
- Extract key information from regulatory documents
- Identify material changes and risks disclosed in filings
- Use sec_filings, form_10k, and form_10q tools
""",
            "earningcall": """
- Analyze earnings reports and financial results
- Review earnings call transcripts for management insights
- Track earnings calendar and upcoming events
- Use earnings_data, transcripts, and earnings_calendar tools
""",
            "fundamentals": """
- Calculate and analyze financial ratios
- Review income statements and balance sheets
- Assess financial health and performance metrics
- Use financial_ratios, income_statement, and balance_sheet tools
""",
            "technicals": """
- Analyze price trends and chart patterns
- Calculate technical indicators (RSI, MACD, moving averages)
- Identify support/resistance levels and trading signals
- Use price_data, indicators, and chart_patterns tools
""",
            "report": """
- Synthesize information from multiple sources
- Generate comprehensive analysis reports
- Aggregate data and create clear summaries
- Use document_generation and data_aggregation tools
"""
        }
        
        return base_instruction + instructions.get(agent_key, "Provide specialized financial analysis.")


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

    def _create_handoff_pattern(self, step: Step) -> HandoffPattern:
        """Create HandoffPattern for single-agent execution with delegation."""
        available_agent_names = list(self.available_agents.keys())
        
        return HandoffPattern(
            agents=available_agent_names,
            initial_agent=step.agent.value,
            config={
                "handoff_strategy": "explicit",
                "max_handoffs": 3,
                "allow_return_handoffs": True,
                "handoff_instructions": (
                    "If the task requires expertise from another agent, "
                    "you can hand off to them. Otherwise, complete the task yourself."
                )
            }
        )

    def _create_groupchat_pattern(self, step: Step) -> GroupChatPattern:
        """Create GroupChatPattern for multi-agent collaboration."""
        # Determine which agents should participate
        participating_agents = self._select_collaborating_agents(step)
        
        return GroupChatPattern(
            agents=participating_agents,
            config={
                "manager_type": "auto",  # Let framework decide who speaks
                "max_iterations": 5,  # Allow back-and-forth discussion
                "allow_repeat_speakers": True,
                "termination_condition": "consensus"  # Stop when agents agree
            }
        )

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

    async def _parse_plan_from_text(self, plan_text: str, input_task: InputTask) -> ExecutionPlan:
        """
        Parse plan text from ReAct reasoning into ExecutionPlan.
        
        Extracts step descriptions, agent assignments, function names, and dependencies from the text.
        Supports formats:
        - New with deps: "Step 1: Action. Agent: agent_name. Function: function_name. Dependencies: [1,2]"
        - New: "Step 1: Action. Agent: agent_name. Function: function_name"
        - Old: "Step 1: Action (Agent: agent_name)"
        """
        import re
        
        # Log the raw plan text for debugging
        logger.info("Raw plan text from LLM", plan_text=plan_text[:500])
        
        # Extract the plan content (look for FINAL ANSWER section)
        if "FINAL ANSWER:" in plan_text.upper():
            plan_content = plan_text.split("FINAL ANSWER:")[-1].strip()
        else:
            plan_content = plan_text
        
        logger.info("Plan content after extraction", content=plan_content[:500])
        
        # Parse steps line by line to extract dependencies properly
        # Format: "Step N: Action. Agent: agent. Function: func. Dependencies: [1,2,3]"
        step_lines = [line.strip() for line in plan_content.split('\n') if line.strip().startswith('Step')]
        
        logger.info(
            f"Found {len(step_lines)} step lines in plan",
            step_lines_preview=[line[:100] for line in step_lines[:3]]
        )
        
        steps = []
        step_id_map = {}  # Map step number to step ID
        step_data = []  # Temporary storage for parsed step data
        
        # FIRST PASS: Create step IDs for all steps
        for line in step_lines:
            step_num_match = re.search(r'Step\s+(\d+):', line, re.IGNORECASE)
            if step_num_match:
                step_num = int(step_num_match.group(1))
                step_id = str(uuid.uuid4())
                step_id_map[step_num] = step_id
                logger.info(f"Pre-created step ID", step_num=step_num, step_id=step_id)
        
        # SECOND PASS: Parse step details with dependency resolution
        for line in step_lines:
            logger.info(f"Parsing line", line=line[:150])
            
            # Extract step number
            step_num_match = re.search(r'Step\s+(\d+):', line, re.IGNORECASE)
            if not step_num_match:
                logger.warning(f"Could not extract step number from line", line=line[:100])
                continue
            
            step_num = int(step_num_match.group(1))
            step_id = step_id_map[step_num]  # Use pre-created ID
            
            # Extract components with regex
            # Pattern with dependencies: "Agent: X. Function: Y. Dependencies: [...]"
            # Function name should NOT include trailing period
            full_pattern = r'Step\s+\d+:\s*(.+?)\.\s*Agent:\s*(\w+)\.\s*Function:\s*([^\.\s]+)(?:\.\s*Dependencies:\s*\[([^\]]+)\])?'
            match = re.search(full_pattern, line, re.IGNORECASE)
            
            if match:
                action = match.group(1).strip()
                agent = match.group(2).strip().lower()
                function = match.group(3).strip()
                deps_str = match.group(4)  # Can be None if no dependencies
                
                logger.info(
                    f"Regex matched successfully",
                    step_num=step_num,
                    action=action[:50],
                    agent=agent,
                    function=function,
                    deps_str=deps_str
                )
                
                # Parse dependencies
                dependencies = []
                if deps_str:
                    # Extract numbers from dependency string (e.g., "1,2,3" or "1, 2, 3")
                    dep_numbers = [int(d.strip()) for d in deps_str.split(',') if d.strip().isdigit()]
                    # Map step numbers to step IDs (now they all exist!)
                    dependencies = [step_id_map.get(num) for num in dep_numbers if num in step_id_map]
                    logger.info(
                        f"Resolved dependencies for step {step_num}",
                        dep_numbers=dep_numbers,
                        resolved_ids=dependencies
                    )
                
                logger.info(
                    f"Parsed step {step_num}",
                    action=action[:80],
                    agent=agent,
                    function=function,
                    num_dependencies=len(dependencies)
                )
                
                # Include function in description
                description = f"{action}. Function: {function}"
                
                step = PlanStep(
                    id=step_id,
                    description=description,
                    agent=agent,
                    tools=[function],
                    dependencies=dependencies,
                    status="pending"
                )
                steps.append(step)
            else:
                # Try old format without Function
                old_pattern = r'Step\s+\d+:\s*(.+?)\s*\(Agent:\s*(\w+)\)'
                old_match = re.search(old_pattern, line, re.IGNORECASE)
                
                if old_match:
                    action = old_match.group(1).strip()
                    agent = old_match.group(2).strip().lower()
                    
                    logger.info(f"Parsed step {step_num} (old format)", action=action[:80], agent=agent)
                    
                    step = PlanStep(
                        id=step_id,
                        description=action,
                        agent=agent,
                        tools=[],
                        dependencies=[],
                        status="pending"
                    )
                    steps.append(step)
        
        logger.info(f"Parsed {len(steps)} steps from planning result")
        
        # Create ExecutionPlan
        execution_plan = ExecutionPlan(
            id=str(uuid.uuid4()),
            description=input_task.description,
            steps=steps,
            status="draft",
            metadata={"ticker": input_task.ticker} if input_task.ticker else {}
        )
        
        return execution_plan

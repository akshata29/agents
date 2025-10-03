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
            agent = self.agent_factory.create_agent(
                agent_type=agent_name,  # Use the agent name as type (company, sec, etc.)
                name=agent_name
            )
            await self.orchestrator.agent_registry.register_agent(agent_name, agent)
            logger.info("Registered execution agent", agent_name=agent_name)
        
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
            user_id = "default-user"  # Since InputTask doesn't have user_id
            
            # Create new session
            session = Session(
                id=session_id,
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.utcnow(),
                metadata={
                    "ticker": input_task.ticker,
                    "objective": input_task.description[:200]  # Store truncated objective
                } if input_task.ticker else {"objective": input_task.description[:200]}
            )
            await self.cosmos.create_session(session)
            logger.info("Created new session for research task", session_id=session_id, ticker=input_task.ticker)

            # Prepare agent descriptions for the planner
            agent_descriptions = []
            for agent_name, agent_info in self.available_agents.items():
                agent_descriptions.append(
                    f"- {agent_name}: {agent_info['description']} (tools: {', '.join(agent_info['tools'])})"
                )
            
            # Create detailed planning prompt with clear output format
            planning_task = f"""
            Create a comprehensive financial analysis plan for: {input_task.description}
            
            Available Agents and Their Capabilities:
            {chr(10).join(agent_descriptions)}
            
            Requirements:
            1. Break down the analysis into 6-8 logical, actionable steps
            2. Each step MUST be in EXACTLY this format: "Step N: [Specific Action] (Agent: agent_name)"
            3. IMPORTANT: Use ONLY these exact agent names: company, sec, earnings, fundamentals, technicals, report
            4. Example: "Step 1: Retrieve latest quarterly earnings report (Agent: company)"
            5. Example: "Step 2: Analyze SEC filings and 10-K reports (Agent: sec)"
            6. Assign each step to the most appropriate agent based on their capabilities listed above
            7. Consider the logical flow and dependencies between steps
            8. Focus on actionable research tasks that produce concrete outputs
            9. NO meta-planning, headers, or separators - ONLY numbered action steps
            
            {"Ticker Symbol: " + input_task.ticker if input_task.ticker else ""}
            
            OUTPUT FORMAT - Return ONLY the numbered steps, nothing else:
            Step 1: [Action] (Agent: agent_name)
            Step 2: [Action] (Agent: agent_name)
            ...
            
            Remember: agent_name must be one of: company, sec, earnings, fundamentals, technicals, report
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
                user_id
            )

            # Store plan and steps in Cosmos
            await self.cosmos.add_plan(plan)
            
            for step in steps:
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

                return result

            else:
                # Step was rejected
                step.status = StepStatus.REJECTED
                step.agent_reply = feedback.human_feedback or "Rejected by user"
                
                await self.cosmos.update_step(step)

                logger.info("Step rejected", step_id=step.id)

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
            agent=step.agent.value,  # Use agent.value
            description=step.action[:100]  # Use 'action' not 'description'
        )

        try:
            # Build task description with context (ticker, scope, etc.)
            task = await self._build_task_from_step(step, feedback)

            # Get tools for the agent(s) involved
            tools = self._get_tools_for_step(step)

            # Determine if step requires multi-agent collaboration
            requires_collaboration = self._requires_multi_agent_collaboration(step)
            
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
                    "session_id": feedback.session_id
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

            return ActionResponse(
                step_id=step.id,
                plan_id=step.plan_id,
                session_id=feedback.session_id,
                success=False,
                result=None,
                error=str(e)
            )

    def _convert_framework_plan_to_model(
        self,
        execution_plan: ExecutionPlan,
        input_task: InputTask,
        session_id: str,
        user_id: str
    ) -> tuple[Plan, List[Step]]:
        """
        Convert framework's ExecutionPlan to our Plan and Step models.
        
        Args:
            execution_plan: Framework's execution plan
            input_task: Original user input
            session_id: Session identifier
            user_id: User identifier
            
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
                agent=agent_name
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
                created_at=datetime.utcnow()
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
            ticker=input_task.ticker,
            created_at=datetime.utcnow()
        )

        return plan, steps

    async def _build_task_from_step(
        self,
        step: Step,
        feedback: HumanFeedback
    ) -> str:
        """
        Build task description for agent execution with context.
        
        Args:
            step: Step to execute
            feedback: User feedback with optional context
            
        Returns:
            Task description string with ticker and scope context
        """
        task_parts = []
        
        # Try to get plan context for ticker/scope information
        try:
            plan = await self.cosmos.get_plan(step.plan_id, step.session_id)
            if plan:
                # Add ticker context if available
                if plan.ticker:
                    task_parts.append(f"Stock Ticker: {plan.ticker}")
                
                # Add scope context if available
                if plan.scope:
                    task_parts.append(f"Analysis Scope: {', '.join(plan.scope)}")
                
                # Add separator if we added context
                if task_parts:
                    task_parts.append("")  # Empty line for separation
        except Exception as e:
            logger.warning(f"Could not fetch plan context: {str(e)}")
        
        # Add the main action
        task_parts.append(step.action)

        # Add user feedback/clarification if provided
        if feedback.human_feedback:
            task_parts.append(f"\nUser feedback: {feedback.human_feedback}")

        return "\n".join(task_parts)

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
            from framework.agents.factory import MicrosoftAgentWrapper
            from agent_framework import ChatAgent
            
            # Create Microsoft Agent Framework ChatAgent
            chat_agent = ChatAgent(
                name=name,
                chat_client=self.agent_factory._chat_client,
                description=config.get("description", f"Financial agent: {name}"),
                instruction=self._get_agent_instructions(name, config)
            )
            
            # Wrap in our BaseAgent interface
            return MicrosoftAgentWrapper(
                name=name,
                chat_agent=chat_agent,
                description=config.get("description", ""),
                settings=self.agent_factory.settings
            )
        
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
        """Get available agents and their capabilities."""
        return {
            AgentType.COMPANY.value: {
                "type": AgentType.COMPANY,
                "description": "Company profile and market data analysis",
                "tools": ["company_profile", "stock_quotes", "market_data"]
            },
            AgentType.SEC.value: {
                "type": AgentType.SEC,
                "description": "SEC filings and regulatory document analysis",
                "tools": ["sec_filings", "form_10k", "form_10q"]
            },
            AgentType.EARNINGS.value: {
                "type": AgentType.EARNINGS,
                "description": "Earnings reports and call transcript analysis",
                "tools": ["earnings_data", "transcripts", "earnings_calendar"]
            },
            AgentType.FUNDAMENTALS.value: {
                "type": AgentType.FUNDAMENTALS,
                "description": "Fundamental financial analysis and metrics",
                "tools": ["financial_ratios", "income_statement", "balance_sheet"]
            },
            AgentType.TECHNICALS.value: {
                "type": AgentType.TECHNICALS,
                "description": "Technical analysis and chart patterns",
                "tools": ["price_data", "indicators", "chart_patterns"]
            },
            AgentType.REPORT.value: {
                "type": AgentType.REPORT,
                "description": "Report generation and synthesis",
                "tools": ["document_generation", "data_aggregation"]
            }
        }

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
        elif any(keyword in description_lower for keyword in ["report", "summary", "synthesis"]):
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
        - Report generation that needs multiple data sources
        - Analysis requiring multiple perspectives
        """
        action_lower = step.action.lower()
        
        collaboration_keywords = [
            "compare", "contrast", "synthesize", "integrate", "correlate",
            "combine", "merge", "cross-reference", "reconcile", "validate against"
        ]
        
        # Check if action requires collaboration
        if any(keyword in action_lower for keyword in collaboration_keywords):
            return True
        
        # Report steps often need multiple agents
        if step.agent == AgentType.REPORT and any(word in action_lower for word in ["comprehensive", "detailed", "complete"]):
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
            if "company" not in agents:
                agents.append("company")
        
        # Add fundamentals for financial analysis
        if any(word in action_lower for word in ["financial", "ratio", "metric", "valuation"]):
            if "fundamentals" not in agents:
                agents.append("fundamentals")
        
        # Add report agent for synthesis tasks
        if step.agent == AgentType.REPORT or "synthesize" in action_lower:
            if "report" not in agents:
                agents.append("report")
        
        # Limit to 4 agents maximum
        return agents[:4]

    async def _parse_plan_from_text(self, plan_text: str, input_task: InputTask) -> ExecutionPlan:
        """
        Parse plan text from ReAct reasoning into ExecutionPlan.
        
        Extracts step descriptions and agent assignments from the text.
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
        
        # Parse steps using regex - match entire lines
        # Match patterns like: "Step 1: Action (Agent: agent_name)"
        step_pattern = r'Step\s+\d+:\s*(.+?)\s*\(Agent:\s*(\w+)\)'
        matches = re.findall(step_pattern, plan_content, re.IGNORECASE)
        
        logger.info(f"Regex matches found: {len(matches)}")
        
        steps = []
        for idx, (action, agent) in enumerate(matches):
            logger.info(f"Parsed step {idx + 1}", action=action.strip()[:80], agent=agent)
            step = PlanStep(
                id=str(uuid.uuid4()),
                description=f"{action.strip()} (Agent: {agent})",
                agent=agent.lower(),
                tools=[],
                dependencies=[],
                status="pending"
            )
            steps.append(step)
        
        logger.info(f"Parsed {len(steps)} steps from ReAct planning result")
        
        # Create ExecutionPlan
        execution_plan = ExecutionPlan(
            id=str(uuid.uuid4()),
            description=input_task.description,
            steps=steps,
            status="draft",
            metadata={"ticker": input_task.ticker} if input_task.ticker else {}
        )
        
        return execution_plan

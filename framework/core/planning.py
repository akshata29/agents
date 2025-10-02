"""
Dynamic Planner - ReAct Pattern and Adaptive Planning Engine

Implements the ReAct (Reasoning + Acting) pattern with dynamic plan updating,
backtracking capabilities, and intelligent tool selection for complex problem solving.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from ..agents.base import BaseAgent
from ..config.settings import Settings
from ..mcp_integration.client import MCPClient


logger = structlog.get_logger(__name__)


class ReasoningType(str, Enum):
    """Types of reasoning steps."""
    OBSERVATION = "observation"
    THOUGHT = "thought"
    ACTION = "action"
    REFLECTION = "reflection"
    PLANNING = "planning"


class ReasoningStep(BaseModel):
    """A single step in the reasoning process."""
    step_number: int
    type: ReasoningType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error: Optional[str] = None

    class Config:
        use_enum_values = True


class PlanStep(BaseModel):
    """A step in an execution plan."""
    id: str
    description: str
    agent: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    """A complete execution plan with steps and dependencies."""
    id: str
    description: str
    steps: List[PlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "draft"  # draft, executing, completed, failed
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReActResult(BaseModel):
    """Result of a ReAct execution."""
    task: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    iterations: int = 0
    reasoning_trace: List[ReasoningStep] = Field(default_factory=list)
    plan: Optional[ExecutionPlan] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DynamicPlanner:
    """
    Dynamic planner implementing ReAct pattern with adaptive planning.
    
    Provides intelligent reasoning, action selection, and plan adaptation
    for complex problem-solving scenarios.
    """

    def __init__(
        self,
        settings: Settings,
        mcp_client: Optional[MCPClient] = None
    ):
        """Initialize the dynamic planner."""
        self.settings = settings
        self.mcp_client = mcp_client
        
        # Planning configuration
        self.max_iterations = 10
        self.backtrack_threshold = 3
        
        # Execution tracking
        self._active_plans: Dict[str, ExecutionPlan] = {}
        self._plan_lock = asyncio.Lock()
        
        # Agent reference (if needed)
        self._agent: Optional[BaseAgent] = None
        
        # Configuration
        self.max_reasoning_steps = getattr(settings, 'max_reasoning_steps', 50)
        self.reasoning_timeout = getattr(settings, 'reasoning_timeout', 300)  # 5 minutes
        self.enable_backtracking = getattr(settings, 'enable_backtracking', True)
        
        logger.info("DynamicPlanner initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the dynamic planner and cleanup resources."""
        logger.info("Shutting down DynamicPlanner")
        # Cancel any active plans
        async with self._plan_lock:
            self._active_plans.clear()
        logger.info("DynamicPlanner shutdown complete")

    async def create_plan(
        self,
        task: str,
        agent: BaseAgent,
        available_tools: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """
        Create an execution plan for a given task.
        
        Args:
            task: Task description
            agent: Planning agent
            available_tools: Available MCP tools
            constraints: Planning constraints
            
        Returns:
            Execution plan
        """
        logger.info("Creating execution plan", task=task[:100])
        
        # Generate plan using the planning agent
        planning_prompt = self._create_planning_prompt(task, available_tools, constraints)
        
        try:
            # Get plan from agent
            plan_response = await agent.process(planning_prompt)
            
            # Parse the plan response into structured plan
            execution_plan = await self._parse_plan_response(plan_response, task)
            
            logger.info(
                "Execution plan created",
                plan_id=execution_plan.id,
                steps=len(execution_plan.steps)
            )
            
            return execution_plan
            
        except Exception as e:
            logger.error("Failed to create execution plan", error=str(e))
            raise

    async def execute_react_loop(
        self,
        task: str,
        agent: BaseAgent,
        tools: Optional[List[str]] = None,
        max_iterations: int = 10,
        initial_plan: Optional[ExecutionPlan] = None
    ) -> ReActResult:
        """
        Execute a ReAct (Reasoning + Acting) loop.
        
        Args:
            task: Task to execute
            agent: Reasoning agent
            tools: Available MCP tools
            max_iterations: Maximum iterations
            initial_plan: Optional initial plan
            
        Returns:
            ReAct execution result
        """
        start_time = datetime.utcnow()
        reasoning_trace = []
        current_plan = initial_plan
        
        logger.info(
            "Starting ReAct execution",
            task=task[:100],
            max_iterations=max_iterations
        )
        
        try:
            for iteration in range(max_iterations):
                logger.debug(f"ReAct iteration {iteration + 1}/{max_iterations}")
                
                # Observation step
                observation = await self._observe_current_state(
                    task, reasoning_trace, current_plan
                )
                reasoning_trace.append(ReasoningStep(
                    step_number=len(reasoning_trace) + 1,
                    type=ReasoningType.OBSERVATION,
                    content=observation
                ))
                
                # Reasoning/Thought step
                thought = await self._generate_thought(
                    task, agent, reasoning_trace, tools
                )
                
                # Check if agent is None
                if agent is None:
                    raise ValueError("Agent is required for ReAct execution")
                
                reasoning_trace.append(ReasoningStep(
                    step_number=len(reasoning_trace) + 1,
                    type=ReasoningType.THOUGHT,
                    content=thought
                ))
                
                # Check if task is complete
                if await self._is_task_complete(thought, task):
                    final_result = await self._extract_final_result(reasoning_trace)
                    return ReActResult(
                        task=task,
                        success=True,
                        result=final_result,
                        iterations=iteration + 1,
                        reasoning_trace=reasoning_trace,
                        plan=current_plan,
                        execution_time=(datetime.utcnow() - start_time).total_seconds()
                    )
                
                # Action step
                action_result = await self._execute_action(
                    thought, agent, tools, reasoning_trace
                )
                
                reasoning_trace.append(ReasoningStep(
                    step_number=len(reasoning_trace) + 1,
                    type=ReasoningType.ACTION,
                    content=action_result.get("description", ""),
                    success=action_result.get("success", False),
                    error=action_result.get("error"),
                    metadata=action_result
                ))
                
                # Plan adaptation if needed
                if not action_result.get("success", False) and self.enable_backtracking:
                    current_plan = await self._adapt_plan(
                        current_plan, reasoning_trace, task, agent
                    )
            
            # Max iterations reached
            return ReActResult(
                task=task,
                success=False,
                error="Maximum iterations reached without completion",
                iterations=max_iterations,
                reasoning_trace=reasoning_trace,
                plan=current_plan,
                execution_time=(datetime.utcnow() - start_time).total_seconds()
            )
            
        except Exception as e:
            logger.error("ReAct execution failed", error=str(e))
            return ReActResult(
                task=task,
                success=False,
                error=str(e),
                iterations=len(reasoning_trace),
                reasoning_trace=reasoning_trace,
                plan=current_plan,
                execution_time=(datetime.utcnow() - start_time).total_seconds()
            )

    async def adapt_plan(
        self,
        plan: ExecutionPlan,
        new_information: str,
        agent: BaseAgent
    ) -> ExecutionPlan:
        """
        Adapt an existing plan based on new information.
        
        Args:
            plan: Current execution plan
            new_information: New information to incorporate
            agent: Planning agent
            
        Returns:
            Updated execution plan
        """
        logger.info("Adapting execution plan", plan_id=plan.id)
        
        adaptation_prompt = f"""
        Current Plan: {plan.description}
        
        Plan Steps:
        {self._format_plan_steps(plan.steps)}
        
        New Information: {new_information}
        
        Please adapt the plan to incorporate this new information. 
        Consider which steps need modification, addition, or removal.
        """
        
        try:
            adaptation_response = await agent.process(adaptation_prompt)
            updated_plan = await self._parse_plan_adaptation(
                plan, adaptation_response
            )
            
            updated_plan.updated_at = datetime.utcnow()
            
            logger.info(
                "Plan adapted",
                plan_id=plan.id,
                original_steps=len(plan.steps),
                updated_steps=len(updated_plan.steps)
            )
            
            return updated_plan
            
        except Exception as e:
            logger.error("Failed to adapt plan", error=str(e))
            return plan  # Return original plan if adaptation fails

    async def validate_plan(
        self,
        plan: ExecutionPlan,
        agent: BaseAgent
    ) -> Tuple[bool, List[str]]:
        """
        Validate an execution plan for feasibility and completeness.
        
        Args:
            plan: Execution plan to validate
            agent: Validation agent
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        validation_prompt = f"""
        Please validate the following execution plan:
        
        Task: {plan.description}
        
        Steps:
        {self._format_plan_steps(plan.steps)}
        
        Check for:
        1. Logical step ordering
        2. Dependency consistency
        3. Resource availability
        4. Potential bottlenecks
        5. Missing steps
        
        Provide a validation assessment.
        """
        
        try:
            validation_response = await agent.process(validation_prompt)
            is_valid, issues = await self._parse_validation_response(validation_response)
            
            logger.info(
                "Plan validation completed",
                plan_id=plan.id,
                is_valid=is_valid,
                issues_count=len(issues)
            )
            
            return is_valid, issues
            
        except Exception as e:
            logger.error("Plan validation failed", error=str(e))
            return False, [f"Validation error: {str(e)}"]

    # Private methods

    def _create_planning_prompt(
        self,
        task: str,
        available_tools: Optional[List[str]],
        constraints: Optional[Dict[str, Any]]
    ) -> str:
        """Create a prompt for plan generation."""
        tools_section = ""
        if available_tools:
            tools_section = f"\nAvailable Tools: {', '.join(available_tools)}"
        
        constraints_section = ""
        if constraints:
            constraints_section = f"\nConstraints: {constraints}"
        
        return f"""
        Create a detailed execution plan for the following task:
        
        Task: {task}
        {tools_section}
        {constraints_section}
        
        Break down the task into specific, actionable steps with clear dependencies.
        Each step should specify:
        1. Description of what needs to be done
        2. Required tools or agents
        3. Dependencies on other steps
        4. Expected outcome
        
        Provide a structured plan in a clear format.
        """

    async def _parse_plan_response(
        self, 
        response: str, 
        task: str
    ) -> ExecutionPlan:
        """Parse agent response into execution plan."""
        # Simplified parsing - in production, use more sophisticated parsing
        plan_id = f"plan_{datetime.utcnow().timestamp()}"
        
        steps = []
        lines = response.split('\n')
        
        for i, line in enumerate(lines):
            if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '*')):
                step = PlanStep(
                    id=f"step_{i}",
                    description=line.strip(),
                    status="pending"
                )
                steps.append(step)
        
        return ExecutionPlan(
            id=plan_id,
            description=task,
            steps=steps,
            status="draft"
        )

    async def _observe_current_state(
        self,
        task: str,
        reasoning_trace: List[ReasoningStep],
        current_plan: Optional[ExecutionPlan]
    ) -> str:
        """Observe the current state for ReAct iteration."""
        observations = [
            f"Task: {task}",
            f"Completed reasoning steps: {len(reasoning_trace)}"
        ]
        
        if current_plan:
            completed_steps = [s for s in current_plan.steps if s.status == "completed"]
            pending_steps = [s for s in current_plan.steps if s.status == "pending"]
            
            observations.extend([
                f"Plan progress: {len(completed_steps)}/{len(current_plan.steps)} steps completed",
                f"Next pending steps: {len(pending_steps)}"
            ])
        
        if reasoning_trace:
            last_step = reasoning_trace[-1]
            observations.append(f"Last step result: {'Success' if last_step.success else 'Failed'}")
        
        return " | ".join(observations)

    async def _generate_thought(
        self,
        task: str,
        agent: BaseAgent,
        reasoning_trace: List[ReasoningStep],
        tools: Optional[List[str]]
    ) -> str:
        """Generate a reasoning thought using the agent."""
        context = self._format_reasoning_context(task, reasoning_trace, tools)
        
        thought_prompt = f"""
        Based on the current context, what should be the next reasoning step?
        
        Context:
        {context}
        
        Provide your reasoning about what to do next to make progress on the task.
        """
        
        return await agent.process(thought_prompt)

    async def _is_task_complete(self, thought: str, task: str) -> bool:
        """Check if the task is complete based on the current thought."""
        # Simple completion detection - can be enhanced with ML models
        completion_indicators = [
            "task complete", "finished", "done", "accomplished",
            "final result", "conclusion", "completed successfully"
        ]
        
        thought_lower = thought.lower()
        return any(indicator in thought_lower for indicator in completion_indicators)

    async def _extract_final_result(self, reasoning_trace: List[ReasoningStep]) -> str:
        """Extract the final result from reasoning trace."""
        # Look for the last successful action or thought
        for step in reversed(reasoning_trace):
            if step.success and step.type in [ReasoningType.ACTION, ReasoningType.THOUGHT]:
                return step.content
        
        return "Task completed, but no explicit result found"

    async def _execute_action(
        self,
        thought: str,
        agent: BaseAgent,
        tools: Optional[List[str]],
        reasoning_trace: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Execute an action based on the current thought."""
        # Determine the action from the thought
        action_prompt = f"""
        Based on this reasoning: {thought}
        
        What specific action should be taken? Choose from:
        1. Use a tool (specify which tool and how)
        2. Request more information
        3. Make a decision or conclusion
        4. Refine the approach
        
        Provide the specific action and its details.
        """
        
        try:
            action_description = await agent.process(action_prompt)
            
            # Execute the action (simplified - can be enhanced with actual tool execution)
            result = await self._perform_action(action_description, tools)
            
            return {
                "description": action_description,
                "result": result,
                "success": True
            }
            
        except Exception as e:
            return {
                "description": f"Action execution failed: {str(e)}",
                "error": str(e),
                "success": False
            }

    async def _perform_action(
        self, 
        action_description: str, 
        tools: Optional[List[str]]
    ) -> str:
        """Perform the actual action (placeholder for tool execution)."""
        # Simplified action execution - integrate with MCP tools in production
        if tools and self.mcp_client:
            # Try to match action with available tools
            for tool in tools:
                if tool.lower() in action_description.lower():
                    # Execute MCP tool (placeholder)
                    return f"Executed tool '{tool}' with action: {action_description}"
        
        return f"Action simulated: {action_description}"

    async def _adapt_plan(
        self,
        current_plan: Optional[ExecutionPlan],
        reasoning_trace: List[ReasoningStep],
        task: str,
        agent: BaseAgent
    ) -> ExecutionPlan:
        """Adapt the current plan based on reasoning trace."""
        if not current_plan:
            # Create new plan
            return await self.create_plan(task, agent)
        
        # Analyze failures and adapt
        failed_steps = [step for step in reasoning_trace if not step.success]
        
        if failed_steps:
            failure_info = " | ".join([f"Step {s.step_number}: {s.error or 'Unknown error'}" for s in failed_steps])
            return await self.adapt_plan(current_plan, f"Failures encountered: {failure_info}", agent)
        
        return current_plan

    def _format_reasoning_context(
        self,
        task: str,
        reasoning_trace: List[ReasoningStep],
        tools: Optional[List[str]]
    ) -> str:
        """Format reasoning context for prompts."""
        context_parts = [f"Task: {task}"]
        
        if tools:
            context_parts.append(f"Available tools: {', '.join(tools)}")
        
        if reasoning_trace:
            context_parts.append("Recent reasoning steps:")
            for step in reasoning_trace[-3:]:  # Last 3 steps
                status = "✓" if step.success else "✗"
                context_parts.append(f"{status} {step.type}: {step.content[:100]}...")
        
        return "\n".join(context_parts)

    def _format_plan_steps(self, steps: List[PlanStep]) -> str:
        """Format plan steps for display."""
        formatted = []
        for i, step in enumerate(steps, 1):
            status_icon = {"pending": "⏸️", "running": "▶️", "completed": "✅", "failed": "❌", "skipped": "⏭️"}.get(step.status, "❓")
            formatted.append(f"{i}. {status_icon} {step.description}")
            
            if step.dependencies:
                formatted.append(f"   Dependencies: {', '.join(step.dependencies)}")
        
        return "\n".join(formatted)

    async def _parse_plan_adaptation(
        self,
        original_plan: ExecutionPlan,
        adaptation_response: str
    ) -> ExecutionPlan:
        """Parse plan adaptation response."""
        # Simplified adaptation parsing - enhance for production
        adapted_plan = original_plan.model_copy()
        adapted_plan.updated_at = datetime.utcnow()
        
        # Basic parsing to identify new or modified steps
        lines = adaptation_response.split('\n')
        for line in lines:
            if 'add step' in line.lower() or 'new step' in line.lower():
                new_step = PlanStep(
                    id=f"step_{len(adapted_plan.steps)}",
                    description=line.strip(),
                    status="pending"
                )
                adapted_plan.steps.append(new_step)
        
        return adapted_plan

    async def _parse_validation_response(
        self, 
        validation_response: str
    ) -> Tuple[bool, List[str]]:
        """Parse validation response."""
        # Simplified validation parsing
        is_valid = "valid" in validation_response.lower() and "invalid" not in validation_response.lower()
        
        # Extract issues (simplified)
        issues = []
        lines = validation_response.split('\n')
        for line in lines:
            if any(word in line.lower() for word in ['issue', 'problem', 'error', 'missing', 'concern']):
                issues.append(line.strip())
        
        return is_valid, issues
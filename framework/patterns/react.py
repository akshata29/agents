"""
ReAct (Reasoning + Acting) Pattern

Implementation of the ReAct pattern for dynamic reasoning and action execution
with plan adaptation, backtracking, and intelligent tool selection.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum

from ..core.orchestrator import OrchestrationPattern


class ReActStepType(str, Enum):
    """Types of steps in ReAct execution."""
    OBSERVATION = "observation"
    THOUGHT = "thought"  
    ACTION = "action"
    REFLECTION = "reflection"
    PLANNING = "planning"


class ReActStep(BaseModel):
    """A single step in ReAct execution."""
    step_number: int
    type: ReActStepType
    content: str
    tool_used: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ReActPattern(OrchestrationPattern):
    """
    ReAct (Reasoning + Acting) orchestration pattern implementation.
    
    Implements the ReAct loop: Observation → Thought → Action → Reflection
    with dynamic planning, tool selection, and backtracking capabilities.
    """
    
    # ReAct-specific configuration as Pydantic fields
    reasoning_agent: str = Field(description="Primary reasoning agent for ReAct loop")
    max_iterations: int = Field(default=10, description="Maximum ReAct loop iterations")
    max_reasoning_steps: int = Field(default=50, description="Maximum reasoning steps per iteration")
    enable_backtracking: bool = Field(default=True, description="Enable backtracking on failures")
    enable_reflection: bool = Field(default=True, description="Enable reflection after actions")
    action_timeout: int = Field(default=60, description="Timeout for action execution in seconds")
    require_final_answer: bool = Field(default=True, description="Require explicit final answer")
    completion_keywords: List[str] = Field(
        default_factory=lambda: ["final answer", "conclusion", "completed", "finished", "done"],
        description="Keywords indicating task completion"
    )
    max_consecutive_failures: int = Field(default=3, description="Maximum consecutive action failures before stopping")
    backtrack_on_failure: bool = Field(default=True, description="Backtrack when action fails")
    
    def __init__(
        self,
        agent: str,
        name: str = "react",
        description: str = "",
        tools: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize ReAct pattern.
        
        Args:
            agent: Primary reasoning agent
            name: Pattern name
            description: Pattern description
            tools: Available MCP tools for actions
            config: Optional pattern configuration
        """
        # Extract ReAct-specific config
        _config = config or {}
        max_iterations = _config.get("max_iterations", 10)
        max_reasoning_steps = _config.get("max_reasoning_steps", 50)
        enable_backtracking = _config.get("enable_backtracking", True)
        enable_reflection = _config.get("enable_reflection", True)
        action_timeout = _config.get("action_timeout", 60)
        require_final_answer = _config.get("require_final_answer", True)
        completion_keywords = _config.get("completion_keywords", [
            "final answer", "conclusion", "completed", "finished", "done"
        ])
        max_consecutive_failures = _config.get("max_consecutive_failures", 3)
        backtrack_on_failure = _config.get("backtrack_on_failure", True)
        
        super().__init__(
            name=name,
            description=description or f"ReAct pattern with {agent} agent",
            agents=[agent],  # ReAct uses a single reasoning agent
            tools=tools or [],
            config=_config,
            reasoning_agent=agent,
            max_iterations=max_iterations,
            max_reasoning_steps=max_reasoning_steps,
            enable_backtracking=enable_backtracking,
            enable_reflection=enable_reflection,
            action_timeout=action_timeout,
            require_final_answer=require_final_answer,
            completion_keywords=completion_keywords,
            max_consecutive_failures=max_consecutive_failures,
            backtrack_on_failure=backtrack_on_failure
        )

    def validate(self) -> tuple[bool, List[str]]:
        """Validate the ReAct pattern configuration."""
        issues = []
        
        if not self.reasoning_agent:
            issues.append("No reasoning agent specified for ReAct pattern")
        
        if self.max_iterations < 1:
            issues.append("max_iterations must be at least 1")
        
        if self.max_iterations > 100:
            issues.append("max_iterations should not exceed 100 for performance reasons")
        
        if self.max_reasoning_steps < 5:
            issues.append("max_reasoning_steps should be at least 5")
        
        if self.action_timeout < 5:
            issues.append("action_timeout should be at least 5 seconds")
        
        if self.max_consecutive_failures < 1:
            issues.append("max_consecutive_failures must be at least 1")
        
        return len(issues) == 0, issues

    def get_execution_plan(self) -> Dict[str, Any]:
        """Get execution plan for this ReAct pattern."""
        return {
            "pattern": self.name,
            "type": "react",
            "reasoning_agent": self.reasoning_agent,
            "available_tools": self.tools,
            "max_iterations": self.max_iterations,
            "estimated_time": self.max_iterations * 45,  # 45 seconds per iteration estimate
            "config": {
                "max_reasoning_steps": self.max_reasoning_steps,
                "enable_backtracking": self.enable_backtracking,
                "enable_reflection": self.enable_reflection,
                "action_timeout": self.action_timeout,
                "require_final_answer": self.require_final_answer,
                "max_consecutive_failures": self.max_consecutive_failures
            }
        }

    def should_continue_iteration(
        self, 
        iteration: int, 
        reasoning_steps: List[ReActStep],
        consecutive_failures: int
    ) -> tuple[bool, str]:
        """
        Determine if ReAct should continue to next iteration.
        
        Returns:
            Tuple of (should_continue, reason)
        """
        # Check max iterations
        if iteration >= self.max_iterations:
            return False, f"Maximum iterations reached ({self.max_iterations})"
        
        # Check max reasoning steps
        if len(reasoning_steps) >= self.max_reasoning_steps:
            return False, f"Maximum reasoning steps reached ({self.max_reasoning_steps})"
        
        # Check consecutive failures
        if consecutive_failures >= self.max_consecutive_failures:
            return False, f"Maximum consecutive failures reached ({self.max_consecutive_failures})"
        
        # Check for completion indicators
        if self.is_task_complete(reasoning_steps):
            return False, "Task completion detected"
        
        return True, "Continue reasoning"

    def is_task_complete(self, reasoning_steps: List[ReActStep]) -> bool:
        """Check if the task is complete based on reasoning steps."""
        if not reasoning_steps:
            return False
        
        # Look for completion keywords in recent thoughts
        recent_steps = reasoning_steps[-3:]  # Check last 3 steps
        
        for step in recent_steps:
            if step.type == ReActStepType.THOUGHT:
                step_content_lower = step.content.lower()
                
                # Check for completion keywords
                for keyword in self.completion_keywords:
                    if keyword in step_content_lower:
                        return True
                
                # Check for explicit completion patterns
                completion_patterns = [
                    "the answer is",
                    "i have completed",
                    "task is finished",
                    "no further action needed",
                    "ready to conclude"
                ]
                
                for pattern in completion_patterns:
                    if pattern in step_content_lower:
                        return True
        
        return False

    def extract_final_answer(self, reasoning_steps: List[ReActStep]) -> Optional[str]:
        """Extract the final answer from reasoning steps."""
        if not reasoning_steps:
            return None
        
        # Look for final answer in reverse order
        for step in reversed(reasoning_steps):
            if step.type in [ReActStepType.THOUGHT, ReActStepType.REFLECTION]:
                content_lower = step.content.lower()
                
                # Look for final answer patterns
                final_answer_patterns = [
                    "final answer:",
                    "the answer is:",
                    "conclusion:",
                    "result:",
                    "solution:"
                ]
                
                for pattern in final_answer_patterns:
                    if pattern in content_lower:
                        # Extract text after the pattern
                        start_idx = content_lower.find(pattern)
                        if start_idx >= 0:
                            start_idx += len(pattern)
                            return step.content[start_idx:].strip()
                
                # If this is a successful final step, use its content
                if step.success and any(keyword in content_lower for keyword in self.completion_keywords):
                    return step.content
        
        # If no explicit final answer found, return the last successful step
        for step in reversed(reasoning_steps):
            if step.success and step.content.strip():
                return step.content
        
        return None

    def select_next_action(
        self, 
        task: str,
        reasoning_steps: List[ReActStep],
        available_tools: List[str]
    ) -> Dict[str, Any]:
        """
        Select the next action based on current reasoning state.
        
        Returns action specification dict.
        """
        if not reasoning_steps:
            return {
                "type": "observation",
                "description": "Initial task observation",
                "tool": None
            }
        
        last_step = reasoning_steps[-1]
        
        # Determine next step based on last step type
        if last_step.type == ReActStepType.OBSERVATION:
            return {
                "type": "thought",
                "description": "Analyze observation and plan next steps",
                "tool": None
            }
        
        elif last_step.type == ReActStepType.THOUGHT:
            # If thought indicates completion, do reflection
            if self.is_task_complete([last_step]):
                return {
                    "type": "reflection",
                    "description": "Reflect on task completion",
                    "tool": None
                }
            
            # Otherwise, determine appropriate action
            thought_content_lower = last_step.content.lower()
            
            # Look for tool usage intentions
            for tool in available_tools:
                if tool.lower() in thought_content_lower:
                    return {
                        "type": "action",
                        "description": f"Execute {tool} tool",
                        "tool": tool
                    }
            
            # Default to general action
            return {
                "type": "action",
                "description": "Execute necessary action based on reasoning",
                "tool": self._select_best_tool(thought_content_lower, available_tools)
            }
        
        elif last_step.type == ReActStepType.ACTION:
            if self.enable_reflection and len(reasoning_steps) % 3 == 0:
                return {
                    "type": "reflection",
                    "description": "Reflect on recent actions and progress",
                    "tool": None
                }
            else:
                return {
                    "type": "observation",
                    "description": "Observe results of previous action",
                    "tool": None
                }
        
        elif last_step.type == ReActStepType.REFLECTION:
            return {
                "type": "observation",
                "description": "Observe current state after reflection",
                "tool": None
            }
        
        # Default fallback
        return {
            "type": "thought",
            "description": "Continue reasoning about the task",
            "tool": None
        }

    def should_backtrack(
        self, 
        reasoning_steps: List[ReActStep], 
        consecutive_failures: int
    ) -> bool:
        """Determine if backtracking should be performed."""
        if not self.enable_backtracking:
            return False
        
        if consecutive_failures < 2:
            return False
        
        # Look for patterns that indicate backtracking might help
        recent_failures = [step for step in reasoning_steps[-5:] if not step.success]
        
        # If more than half of recent steps failed, consider backtracking
        return len(recent_failures) > 2

    def find_backtrack_point(self, reasoning_steps: List[ReActStep]) -> int:
        """Find the appropriate point to backtrack to."""
        if len(reasoning_steps) < 3:
            return 0
        
        # Look for the last successful thought or observation
        for i in range(len(reasoning_steps) - 1, -1, -1):
            step = reasoning_steps[i]
            if (step.success and 
                step.type in [ReActStepType.THOUGHT, ReActStepType.OBSERVATION] and
                i < len(reasoning_steps) - 1):  # Not the current step
                return i
        
        # Fallback: backtrack to 1/3 of the way through
        return max(0, len(reasoning_steps) // 3)

    def generate_backtrack_context(
        self, 
        original_steps: List[ReActStep], 
        backtrack_point: int
    ) -> str:
        """Generate context for backtracking."""
        failed_attempts = original_steps[backtrack_point:]
        
        failure_summary = []
        for step in failed_attempts:
            if not step.success:
                failure_summary.append(f"- {step.type}: {step.error or 'Failed without specific error'}")
        
        context = f"""
        Previous approach encountered issues. Backtracking from step {backtrack_point + 1}.
        
        Failed attempts:
        {chr(10).join(failure_summary)}
        
        Let's try a different approach from this point.
        """
        
        return context.strip()

    def calculate_progress(self, reasoning_steps: List[ReActStep]) -> float:
        """Calculate reasoning progress (0.0 to 1.0)."""
        if not reasoning_steps:
            return 0.0
        
        # Base progress on step count and success rate
        step_progress = min(len(reasoning_steps) / self.max_reasoning_steps, 1.0)
        
        # Factor in success rate
        successful_steps = sum(1 for step in reasoning_steps if step.success)
        success_rate = successful_steps / len(reasoning_steps) if reasoning_steps else 0
        
        # Check for task completion
        if self.is_task_complete(reasoning_steps):
            return 1.0
        
        # Combined progress metric
        return (step_progress * 0.7) + (success_rate * 0.3)

    # Private helper methods

    def _select_best_tool(self, thought_content: str, available_tools: List[str]) -> Optional[str]:
        """Select the best tool based on thought content."""
        if not available_tools:
            return None
        
        # Simple keyword matching - can be enhanced with ML models
        tool_scores = {}
        
        for tool in available_tools:
            score = 0
            tool_lower = tool.lower()
            
            # Direct mentions
            if tool_lower in thought_content:
                score += 10
            
            # Related keywords (simplified)
            tool_keywords = {
                "web_search": ["search", "find", "look up", "google", "internet"],
                "file_operations": ["file", "read", "write", "save", "load"],
                "database": ["database", "query", "sql", "data"],
                "api_client": ["api", "request", "call", "http"]
            }
            
            keywords = tool_keywords.get(tool_lower, [])
            for keyword in keywords:
                if keyword in thought_content:
                    score += 3
            
            if score > 0:
                tool_scores[tool] = score
        
        # Return tool with highest score
        if tool_scores:
            return max(tool_scores.items(), key=lambda x: x[1])[0]
        
        # Default to first available tool
        return available_tools[0] if available_tools else None

    def __str__(self) -> str:
        """String representation of the pattern."""
        return f"ReActPattern(agent={self.reasoning_agent}, tools={len(self.tools)}, max_iterations={self.max_iterations})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"ReActPattern("
            f"name='{self.name}', "
            f"agent='{self.reasoning_agent}', "
            f"tools={self.tools}, "
            f"max_iterations={self.max_iterations}, "
            f"enable_backtracking={self.enable_backtracking})"
        )
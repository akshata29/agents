"""
Sequential Orchestration Pattern

Implementation of sequential agent execution where agents work in a defined order,
each building on the previous agent's output with full context preservation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..core.orchestrator import OrchestrationPattern


class SequentialPattern(OrchestrationPattern):
    """
    Sequential orchestration pattern implementation.
    
    Executes agents in a predefined order where each agent receives
    the full conversation context and adds its contribution.
    """
    
    # Sequential-specific configuration as Pydantic fields
    preserve_context: bool = Field(default=True, description="Whether to preserve conversation context between agents")
    fail_fast: bool = Field(default=False, description="Whether to stop execution on first agent failure")
    context_window_limit: int = Field(default=32000, description="Maximum context window size in tokens")
    
    def __init__(
        self,
        agents: List[str],
        name: str = "sequential",
        description: str = "",
        tools: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize sequential pattern.
        
        Args:
            agents: List of agent names in execution order
            name: Pattern name
            description: Pattern description
            tools: Optional MCP tools to use
            config: Optional pattern configuration
        """
        # Extract sequential-specific config
        _config = config or {}
        preserve_context = _config.get("preserve_context", True)
        fail_fast = _config.get("fail_fast", False)
        context_window_limit = _config.get("context_window_limit", 32000)
        
        super().__init__(
            name=name,
            description=description or f"Sequential execution of {len(agents)} agents",
            agents=agents,
            tools=tools,
            config=_config,
            preserve_context=preserve_context,
            fail_fast=fail_fast,
            context_window_limit=context_window_limit
        )

    def validate(self) -> tuple[bool, List[str]]:
        """Validate the sequential pattern configuration."""
        issues = []
        
        if not self.agents:
            issues.append("No agents specified for sequential pattern")
        
        if len(self.agents) < 2:
            issues.append("Sequential pattern requires at least 2 agents")
        
        # Check for duplicate agents (warning, not error)
        duplicates = []
        seen = set()
        for agent in self.agents:
            if agent in seen:
                duplicates.append(agent)
            else:
                seen.add(agent)
        
        if duplicates:
            issues.append(f"Duplicate agents found: {duplicates}")
        
        return len(issues) == 0, issues

    def get_execution_plan(self) -> Dict[str, Any]:
        """Get execution plan for this sequential pattern."""
        steps = []
        
        for i, agent in enumerate(self.agents):
            step = {
                "step_number": i + 1,
                "agent": agent,
                "description": f"Execute {agent} agent",
                "depends_on": [i] if i > 0 else [],
                "parallel": False
            }
            steps.append(step)
        
        return {
            "pattern": self.name,
            "type": "sequential",
            "steps": steps,
            "total_steps": len(steps),
            "estimated_time": len(self.agents) * 30,  # 30 seconds per agent estimate
            "config": {
                "preserve_context": self.preserve_context,
                "fail_fast": self.fail_fast,
                "context_window_limit": self.context_window_limit
            }
        }

    def adapt_for_context_limit(self, current_context_size: int) -> 'SequentialPattern':
        """Adapt pattern if context size exceeds limits."""
        if current_context_size < self.context_window_limit:
            return self
        
        # Create adapted pattern with context summarization
        adapted_config = self.config.copy()
        adapted_config["enable_summarization"] = True
        adapted_config["summarize_after_steps"] = 2
        
        return SequentialPattern(
            agents=self.agents,
            name=self.name,
            description=f"{self.description} (adapted for context limits)",
            tools=self.tools,
            config=adapted_config
        )

    def get_agent_for_step(self, step_number: int) -> Optional[str]:
        """Get the agent for a specific step number (1-based)."""
        if 1 <= step_number <= len(self.agents):
            return self.agents[step_number - 1]
        return None

    def get_next_agent(self, current_agent: str) -> Optional[str]:
        """Get the next agent in the sequence."""
        try:
            current_index = self.agents.index(current_agent)
            if current_index < len(self.agents) - 1:
                return self.agents[current_index + 1]
        except ValueError:
            pass
        return None

    def get_previous_agent(self, current_agent: str) -> Optional[str]:
        """Get the previous agent in the sequence."""
        try:
            current_index = self.agents.index(current_agent)
            if current_index > 0:
                return self.agents[current_index - 1]
        except ValueError:
            pass
        return None

    def is_final_agent(self, agent: str) -> bool:
        """Check if the given agent is the final agent in the sequence."""
        return self.agents and self.agents[-1] == agent

    def calculate_progress(self, completed_agents: List[str]) -> float:
        """Calculate completion progress (0.0 to 1.0)."""
        if not self.agents:
            return 1.0
        
        completed_count = 0
        for agent in completed_agents:
            if agent in self.agents:
                completed_count += 1
        
        return min(completed_count / len(self.agents), 1.0)

    def get_remaining_agents(self, completed_agents: List[str]) -> List[str]:
        """Get list of remaining agents to execute."""
        completed_set = set(completed_agents)
        return [agent for agent in self.agents if agent not in completed_set]

    def __str__(self) -> str:
        """String representation of the pattern."""
        return f"SequentialPattern(agents={self.agents}, tools={self.tools or []})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"SequentialPattern("
            f"name='{self.name}', "
            f"agents={self.agents}, "
            f"tools={self.tools}, "
            f"preserve_context={self.preserve_context}, "
            f"fail_fast={self.fail_fast})"
        )
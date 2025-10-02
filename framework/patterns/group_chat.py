"""
Group Chat Orchestration Pattern

Wrapper around Microsoft Agent Framework's GroupChat pattern where multiple agents
collaborate in a managed conversation, with agent selection handled by a GroupChatManager.
"""

from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field

from ..core.orchestrator import OrchestrationPattern


class GroupChatPattern(OrchestrationPattern):
    """
    Group Chat orchestration pattern implementation.
    
    Wraps MAF's GroupChat pattern where multiple agents participate in a
    managed conversation. A GroupChatManager selects which agent speaks next
    based on the conversation history.
    
    This pattern is ideal for:
    - Multi-perspective analysis
    - Collaborative problem solving
    - Round-robin discussions
    - Dynamic agent selection based on context
    """
    
    # Group chat-specific configuration as Pydantic fields
    manager_type: str = Field(
        default="round_robin",
        description="Type of group chat manager: 'round_robin' or 'custom'"
    )
    max_iterations: int = Field(
        default=40,
        description="Maximum number of conversation turns"
    )
    require_consensus: bool = Field(
        default=False,
        description="Whether all agents must agree before completing"
    )
    selection_strategy: Optional[str] = Field(
        default=None,
        description="Custom agent selection strategy: 'expertise', 'availability', etc."
    )
    
    def __init__(
        self,
        agents: List[str],
        name: str = "group_chat",
        description: str = "",
        tools: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize group chat pattern.
        
        Args:
            agents: List of agent names participating in the group chat
            name: Pattern name
            description: Pattern description
            tools: Optional MCP tools to use
            config: Optional pattern configuration with:
                - manager_type: 'round_robin' (default) or 'custom'
                - max_iterations: Maximum conversation turns (default: 40)
                - require_consensus: Whether all agents must agree (default: False)
                - selection_strategy: Custom selection strategy (optional)
                - termination_condition: Custom termination function (optional)
        """
        # Extract group chat-specific config
        _config = config or {}
        manager_type = _config.get("manager_type", "round_robin")
        max_iterations = _config.get("max_iterations", 40)
        require_consensus = _config.get("require_consensus", False)
        selection_strategy = _config.get("selection_strategy")
        
        super().__init__(
            name=name,
            pattern_type="group_chat",
            agents=agents,
            description=description or "Group chat pattern with managed agent selection",
            tools=tools,
            config=config,
            manager_type=manager_type,
            max_iterations=max_iterations,
            require_consensus=require_consensus,
            selection_strategy=selection_strategy
        )
    
    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the group chat pattern.
        
        This implementation delegates to MAF's GroupChat pattern via the
        orchestrator's execution engine.
        
        Args:
            input_data: Initial conversation prompt or task
            context: Optional execution context
            
        Returns:
            Conversation history with all agent contributions
        """
        # The actual execution is handled by the orchestrator
        # which will use MAF's AgentWorkflowBuilder.CreateGroupChatBuilderWith()
        return await self._execute_with_orchestrator(input_data, context)
    
    def validate(self) -> bool:
        """
        Validate the group chat configuration.
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        if len(self.agents) < 2:
            raise ValueError("Group chat requires at least 2 agents")
        
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        
        if self.manager_type not in ["round_robin", "custom"]:
            raise ValueError("manager_type must be 'round_robin' or 'custom'")
        
        return True
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of group chat configuration."""
        return {
            "pattern_type": "group_chat",
            "participants": self.agents,
            "manager_type": self.manager_type,
            "max_iterations": self.max_iterations,
            "require_consensus": self.require_consensus,
            "selection_strategy": self.selection_strategy,
            "expected_turns": f"Up to {self.max_iterations}",
            "agent_count": len(self.agents)
        }


class RoundRobinManager:
    """
    Round-robin group chat manager.
    
    Selects agents in a circular order, ensuring each agent gets equal
    opportunities to participate.
    """
    
    def __init__(
        self,
        agents: List[str],
        max_iterations: int = 40,
        should_terminate_func: Optional[Callable] = None
    ):
        """
        Initialize round-robin manager.
        
        Args:
            agents: List of agent names
            max_iterations: Maximum conversation turns
            should_terminate_func: Optional custom termination function
        """
        self.agents = agents
        self.max_iterations = max_iterations
        self.should_terminate_func = should_terminate_func
        self.current_index = 0
        self.iteration_count = 0
    
    def select_next_agent(self, history: List[Any]) -> str:
        """
        Select next agent in round-robin fashion.
        
        Args:
            history: Conversation history
            
        Returns:
            Name of next agent to speak
        """
        agent = self.agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.agents)
        self.iteration_count += 1
        return agent
    
    def should_terminate(self, history: List[Any]) -> bool:
        """
        Determine if conversation should terminate.
        
        Args:
            history: Conversation history
            
        Returns:
            True if should terminate, False otherwise
        """
        # Check custom termination function first
        if self.should_terminate_func:
            if self.should_terminate_func(self, history):
                return True
        
        # Default: terminate after max iterations
        return self.iteration_count >= self.max_iterations
    
    def reset(self):
        """Reset manager state for new conversation."""
        self.current_index = 0
        self.iteration_count = 0


# Example usage patterns
EXAMPLE_ROUND_ROBIN_CONFIG = {
    "manager_type": "round_robin",
    "max_iterations": 10,
    "require_consensus": False
}

EXAMPLE_CUSTOM_MANAGER_CONFIG = {
    "manager_type": "custom",
    "max_iterations": 20,
    "selection_strategy": "expertise",
    "require_consensus": True
}

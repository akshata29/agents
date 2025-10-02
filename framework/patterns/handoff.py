"""
Handoff Orchestration Pattern

Wrapper around Microsoft Agent Framework's Handoff pattern where agents can
dynamically delegate work to specialized agents based on the conversation context.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from enum import Enum

from ..core.orchestrator import OrchestrationPattern


class HandoffStrategy(str, Enum):
    """Strategy for determining handoff behavior."""
    EXPLICIT = "explicit"  # Agents explicitly decide to handoff
    AUTOMATIC = "automatic"  # System determines handoffs based on expertise
    HYBRID = "hybrid"  # Combination of both


class HandoffPattern(OrchestrationPattern):
    """
    Handoff orchestration pattern implementation.
    
    Wraps MAF's Handoff pattern where the current agent can hand off
    the conversation to another specialized agent. The next agent is
    selected by the current agent through tool calling.
    
    This pattern is ideal for:
    - Triage and routing scenarios
    - Specialized expertise routing
    - Dynamic delegation based on conversation
    - Customer service escalation
    """
    
    # Handoff-specific configuration as Pydantic fields
    initial_agent: str = Field(description="Agent that receives initial input")
    handoff_strategy: str = Field(
        default="explicit",
        description="Handoff strategy: 'explicit', 'automatic', or 'hybrid'"
    )
    allow_return_handoffs: bool = Field(
        default=True,
        description="Whether agents can hand back to previous agents"
    )
    max_handoffs: int = Field(
        default=10,
        description="Maximum number of handoffs allowed"
    )
    handoff_instructions: Optional[str] = Field(
        default=None,
        description="Custom instructions for how agents should perform handoffs"
    )
    
    def __init__(
        self,
        agents: List[str],
        initial_agent: str,
        handoff_relationships: Optional[Dict[str, List[str]]] = None,
        name: str = "handoff",
        description: str = "",
        tools: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize handoff pattern.
        
        Args:
            agents: List of all agent names in the handoff network
            initial_agent: Agent that receives the initial input
            handoff_relationships: Dict mapping agent names to lists of agents they can handoff to.
                                 If None, all agents can handoff to all others.
            name: Pattern name
            description: Pattern description
            tools: Optional MCP tools to use
            config: Optional pattern configuration with:
                - handoff_strategy: 'explicit' (default), 'automatic', or 'hybrid'
                - allow_return_handoffs: Whether agents can hand back (default: True)
                - max_handoffs: Maximum handoffs allowed (default: 10)
                - handoff_instructions: Custom handoff instructions (optional)
        """
        if initial_agent not in agents:
            raise ValueError(f"Initial agent '{initial_agent}' must be in agents list")
        
        # Extract handoff-specific config
        _config = config or {}
        handoff_strategy = _config.get("handoff_strategy", "explicit")
        allow_return_handoffs = _config.get("allow_return_handoffs", True)
        max_handoffs = _config.get("max_handoffs", 10)
        handoff_instructions = _config.get("handoff_instructions")
        
        # Store handoff relationships
        self.handoff_relationships = handoff_relationships or self._create_full_mesh(agents)
        
        super().__init__(
            name=name,
            pattern_type="handoff",
            agents=agents,
            description=description or "Handoff pattern with dynamic agent delegation",
            tools=tools,
            config=config,
            initial_agent=initial_agent,
            handoff_strategy=handoff_strategy,
            allow_return_handoffs=allow_return_handoffs,
            max_handoffs=max_handoffs,
            handoff_instructions=handoff_instructions
        )
    
    def _create_full_mesh(self, agents: List[str]) -> Dict[str, List[str]]:
        """
        Create full mesh handoff network where every agent can handoff to every other agent.
        
        Args:
            agents: List of agent names
            
        Returns:
            Dict mapping each agent to list of all other agents
        """
        return {agent: [other for other in agents if other != agent] for agent in agents}
    
    def add_handoff(self, from_agent: str, to_agent: str, reason: Optional[str] = None):
        """
        Add a handoff relationship.
        
        Args:
            from_agent: Agent that can initiate the handoff
            to_agent: Agent that can receive the handoff
            reason: Optional reason for this handoff path
        """
        if from_agent not in self.agents:
            raise ValueError(f"Agent '{from_agent}' not in agent list")
        if to_agent not in self.agents:
            raise ValueError(f"Agent '{to_agent}' not in agent list")
        
        if from_agent not in self.handoff_relationships:
            self.handoff_relationships[from_agent] = []
        
        if to_agent not in self.handoff_relationships[from_agent]:
            self.handoff_relationships[from_agent].append(to_agent)
    
    def add_bidirectional_handoff(self, agent1: str, agent2: str):
        """
        Add bidirectional handoff relationship.
        
        Args:
            agent1: First agent
            agent2: Second agent
        """
        self.add_handoff(agent1, agent2)
        self.add_handoff(agent2, agent1)
    
    def get_available_handoffs(self, current_agent: str) -> List[str]:
        """
        Get list of agents that current agent can handoff to.
        
        Args:
            current_agent: Current agent name
            
        Returns:
            List of agent names available for handoff
        """
        return self.handoff_relationships.get(current_agent, [])
    
    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the handoff pattern.
        
        This implementation delegates to MAF's Handoff pattern via the
        orchestrator's execution engine.
        
        Args:
            input_data: Initial conversation prompt or task
            context: Optional execution context
            
        Returns:
            Final agent's response after all handoffs
        """
        # The actual execution is handled by the orchestrator
        # which will use MAF's AgentWorkflowBuilder.CreateHandoffBuilderWith()
        return await self._execute_with_orchestrator(input_data, context)
    
    def validate(self) -> bool:
        """
        Validate the handoff configuration.
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        if len(self.agents) < 2:
            raise ValueError("Handoff pattern requires at least 2 agents")
        
        if self.initial_agent not in self.agents:
            raise ValueError(f"Initial agent '{self.initial_agent}' not in agents list")
        
        if self.max_handoffs < 1:
            raise ValueError("max_handoffs must be at least 1")
        
        if self.handoff_strategy not in ["explicit", "automatic", "hybrid"]:
            raise ValueError("handoff_strategy must be 'explicit', 'automatic', or 'hybrid'")
        
        # Validate handoff relationships
        for from_agent, to_agents in self.handoff_relationships.items():
            if from_agent not in self.agents:
                raise ValueError(f"Handoff source agent '{from_agent}' not in agents list")
            for to_agent in to_agents:
                if to_agent not in self.agents:
                    raise ValueError(f"Handoff target agent '{to_agent}' not in agents list")
        
        return True
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of handoff configuration."""
        # Calculate handoff graph statistics
        total_handoffs = sum(len(targets) for targets in self.handoff_relationships.values())
        avg_handoffs_per_agent = total_handoffs / len(self.agents) if self.agents else 0
        
        return {
            "pattern_type": "handoff",
            "initial_agent": self.initial_agent,
            "total_agents": len(self.agents),
            "handoff_strategy": self.handoff_strategy,
            "max_handoffs": self.max_handoffs,
            "allow_return_handoffs": self.allow_return_handoffs,
            "total_handoff_paths": total_handoffs,
            "avg_handoffs_per_agent": round(avg_handoffs_per_agent, 2),
            "handoff_network": self.handoff_relationships
        }
    
    def visualize_handoff_graph(self) -> str:
        """
        Create a text visualization of the handoff graph.
        
        Returns:
            Text representation of handoff relationships
        """
        lines = [f"Handoff Network (Initial: {self.initial_agent}):"]
        lines.append("=" * 50)
        
        for from_agent, to_agents in sorted(self.handoff_relationships.items()):
            if to_agents:
                targets = ", ".join(to_agents)
                lines.append(f"  {from_agent} → {targets}")
            else:
                lines.append(f"  {from_agent} → (no handoffs)")
        
        return "\n".join(lines)


# Helper functions for common handoff patterns

def create_triage_pattern(
    triage_agent: str,
    specialist_agents: List[str],
    allow_specialist_collaboration: bool = False
) -> HandoffPattern:
    """
    Create a triage handoff pattern where one agent routes to specialists.
    
    Args:
        triage_agent: Agent that receives initial input and routes
        specialist_agents: List of specialist agent names
        allow_specialist_collaboration: Whether specialists can handoff to each other
        
    Returns:
        Configured HandoffPattern
    """
    all_agents = [triage_agent] + specialist_agents
    relationships = {
        triage_agent: specialist_agents.copy()
    }
    
    # Specialists can return to triage
    for specialist in specialist_agents:
        relationships[specialist] = [triage_agent]
    
    # If collaboration allowed, specialists can handoff to each other
    if allow_specialist_collaboration:
        for specialist in specialist_agents:
            relationships[specialist].extend([s for s in specialist_agents if s != specialist])
    
    return HandoffPattern(
        agents=all_agents,
        initial_agent=triage_agent,
        handoff_relationships=relationships,
        name="triage_handoff",
        description="Triage pattern with specialist routing"
    )


def create_escalation_pattern(agent_levels: List[List[str]]) -> HandoffPattern:
    """
    Create an escalation handoff pattern with multiple support levels.
    
    Args:
        agent_levels: List of lists, where each inner list contains agents at that level.
                     Example: [['tier1_a', 'tier1_b'], ['tier2_a'], ['tier3']]
        
    Returns:
        Configured HandoffPattern
    """
    all_agents = [agent for level in agent_levels for agent in level]
    relationships = {}
    
    for level_idx, level_agents in enumerate(agent_levels):
        for agent in level_agents:
            # Can handoff within same level
            relationships[agent] = [other for other in level_agents if other != agent]
            
            # Can escalate to next level
            if level_idx < len(agent_levels) - 1:
                relationships[agent].extend(agent_levels[level_idx + 1])
            
            # Can de-escalate to previous level
            if level_idx > 0:
                relationships[agent].extend(agent_levels[level_idx - 1])
    
    return HandoffPattern(
        agents=all_agents,
        initial_agent=agent_levels[0][0],  # Start at first agent of first level
        handoff_relationships=relationships,
        name="escalation_handoff",
        description="Escalation pattern with support tiers"
    )


# Example usage patterns
EXAMPLE_TRIAGE_CONFIG = {
    "handoff_strategy": "explicit",
    "allow_return_handoffs": True,
    "max_handoffs": 5
}

EXAMPLE_ESCALATION_CONFIG = {
    "handoff_strategy": "hybrid",
    "allow_return_handoffs": True,
    "max_handoffs": 10,
    "handoff_instructions": "Escalate only when current level cannot resolve the issue."
}

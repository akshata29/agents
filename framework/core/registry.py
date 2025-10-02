"""
Agent Registry - Dynamic Agent Management and Discovery

Provides centralized registry for agent discovery, registration, and lifecycle management.
Supports both built-in and dynamically loaded agents with metadata and health tracking.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from ..agents.base import BaseAgent
from ..config.settings import Settings


logger = structlog.get_logger(__name__)


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    AVAILABLE = "available"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class AgentCapability(BaseModel):
    """Agent capability definition."""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_tools: List[str] = Field(default_factory=list)


class AgentMetadata(BaseModel):
    """Comprehensive agent metadata."""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    capabilities: List[AgentCapability] = Field(default_factory=list)
    status: AgentStatus = AgentStatus.AVAILABLE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    error_count: int = 0
    health_score: float = 1.0
    configuration: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class AgentRegistration(BaseModel):
    """Agent registration information."""
    metadata: AgentMetadata
    agent: Any  # BaseAgent instance - using Any to avoid Pydantic schema issues
    health_check: Optional[Callable[[], bool]] = None
    last_health_check: Optional[datetime] = None
    health_check_interval: int = 300  # 5 minutes
    
    class Config:
        arbitrary_types_allowed = True


class AgentRegistry:
    """
    Centralized registry for agent management and discovery.
    
    Provides dynamic agent registration, discovery, health monitoring,
    and lifecycle management capabilities.
    """

    def __init__(self, settings: Settings):
        """Initialize the agent registry."""
        self.settings = settings
        self._agents: Dict[str, AgentRegistration] = {}
        self._capabilities_index: Dict[str, Set[str]] = {}
        self._tags_index: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        
        logger.info("AgentRegistry initialized")

    async def initialize(self) -> None:
        """Initialize the registry and start health monitoring."""
        logger.info("Initializing AgentRegistry")
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("AgentRegistry initialization complete")

    async def shutdown(self) -> None:
        """Shutdown the registry and cleanup resources."""
        logger.info("Shutting down AgentRegistry")
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup agents
        async with self._lock:
            for registration in self._agents.values():
                if hasattr(registration.agent, 'cleanup'):
                    try:
                        await registration.agent.cleanup()
                    except Exception as e:
                        logger.warning(
                            "Error during agent cleanup",
                            agent=registration.metadata.name,
                            error=str(e)
                        )
            
            self._agents.clear()
            self._capabilities_index.clear()
            self._tags_index.clear()
        
        logger.info("AgentRegistry shutdown complete")

    async def register_agent(
        self,
        name: str,
        agent: BaseAgent,
        metadata: Optional[AgentMetadata] = None,
        health_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Register an agent with the registry.
        
        Args:
            name: Agent name (must be unique)
            agent: Agent instance
            metadata: Optional agent metadata
            health_check: Optional health check function
            
        Returns:
            Agent ID
        """
        async with self._lock:
            if name in self._agents:
                raise ValueError(f"Agent already registered: {name}")
            
            # Create metadata if not provided
            if metadata is None:
                metadata = AgentMetadata(
                    id=f"agent_{name}_{datetime.utcnow().timestamp()}",
                    name=name,
                    description=f"Agent: {name}",
                    tags=["builtin"] if hasattr(agent, '_builtin') else ["custom"]
                )
            
            # Create registration
            registration = AgentRegistration(
                metadata=metadata,
                agent=agent,
                health_check=health_check
            )
            
            # Store registration
            self._agents[name] = registration
            
            # Update indexes
            self._update_capability_index(name, metadata.capabilities)
            self._update_tags_index(name, metadata.tags)
            
            logger.info(
                "Agent registered",
                agent_id=metadata.id,
                name=name,
                capabilities=len(metadata.capabilities),
                tags=metadata.tags
            )
            
            return metadata.id

    async def unregister_agent(self, name: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            name: Agent name
            
        Returns:
            True if agent was unregistered, False if not found
        """
        async with self._lock:
            if name not in self._agents:
                return False
            
            registration = self._agents[name]
            
            # Cleanup agent if possible
            if hasattr(registration.agent, 'cleanup'):
                try:
                    await registration.agent.cleanup()
                except Exception as e:
                    logger.warning("Error during agent cleanup", agent=name, error=str(e))
            
            # Remove from indexes
            self._remove_from_capability_index(name, registration.metadata.capabilities)
            self._remove_from_tags_index(name, registration.metadata.tags)
            
            # Remove registration
            del self._agents[name]
            
            logger.info("Agent unregistered", name=name)
            return True

    async def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent instance or None if not found
        """
        async with self._lock:
            registration = self._agents.get(name)
            if registration:
                # Update usage statistics
                registration.metadata.last_used = datetime.utcnow()
                registration.metadata.usage_count += 1
                return registration.agent
            return None

    async def get_agent_metadata(self, name: str) -> Optional[AgentMetadata]:
        """Get agent metadata by name."""
        async with self._lock:
            registration = self._agents.get(name)
            return registration.metadata if registration else None

    async def list_agents(
        self,
        status: Optional[AgentStatus] = None,
        tags: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None
    ) -> List[AgentMetadata]:
        """
        List agents with optional filtering.
        
        Args:
            status: Filter by agent status
            tags: Filter by tags (AND operation)
            capabilities: Filter by capabilities (AND operation)
            
        Returns:
            List of matching agent metadata
        """
        async with self._lock:
            results = []
            
            for registration in self._agents.values():
                metadata = registration.metadata
                
                # Filter by status
                if status and metadata.status != status:
                    continue
                
                # Filter by tags (all must match)
                if tags and not all(tag in metadata.tags for tag in tags):
                    continue
                
                # Filter by capabilities (all must be present)
                if capabilities:
                    agent_caps = {cap.name for cap in metadata.capabilities}
                    if not all(cap in agent_caps for cap in capabilities):
                        continue
                
                results.append(metadata)
            
            return results

    async def search_agents_by_capability(self, capability: str) -> List[str]:
        """
        Search for agents that have a specific capability.
        
        Args:
            capability: Capability name to search for
            
        Returns:
            List of agent names
        """
        async with self._lock:
            return list(self._capabilities_index.get(capability, set()))

    async def search_agents_by_tag(self, tag: str) -> List[str]:
        """
        Search for agents that have a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of agent names
        """
        async with self._lock:
            return list(self._tags_index.get(tag, set()))

    async def get_available_agents(self) -> List[str]:
        """Get list of available agents."""
        available = await self.list_agents(status=AgentStatus.AVAILABLE)
        return [metadata.name for metadata in available]

    async def update_agent_status(self, name: str, status: AgentStatus) -> bool:
        """
        Update an agent's status.
        
        Args:
            name: Agent name
            status: New status
            
        Returns:
            True if updated successfully, False if agent not found
        """
        async with self._lock:
            registration = self._agents.get(name)
            if registration:
                old_status = registration.metadata.status
                registration.metadata.status = status
                
                logger.debug(
                    "Agent status updated",
                    agent=name,
                    old_status=old_status,
                    new_status=status
                )
                return True
            return False

    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        async with self._lock:
            total_agents = len(self._agents)
            status_counts = {}
            
            for registration in self._agents.values():
                status = registration.metadata.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            total_usage = sum(
                reg.metadata.usage_count for reg in self._agents.values()
            )
            
            total_errors = sum(
                reg.metadata.error_count for reg in self._agents.values()
            )
            
            avg_health = sum(
                reg.metadata.health_score for reg in self._agents.values()
            ) / total_agents if total_agents > 0 else 0
            
            return {
                "total_agents": total_agents,
                "status_counts": status_counts,
                "total_usage": total_usage,
                "total_errors": total_errors,
                "average_health_score": avg_health,
                "capabilities_count": len(self._capabilities_index),
                "tags_count": len(self._tags_index)
            }

    # Private methods

    def _update_capability_index(self, agent_name: str, capabilities: List[AgentCapability]):
        """Update the capabilities index."""
        for capability in capabilities:
            if capability.name not in self._capabilities_index:
                self._capabilities_index[capability.name] = set()
            self._capabilities_index[capability.name].add(agent_name)

    def _remove_from_capability_index(self, agent_name: str, capabilities: List[AgentCapability]):
        """Remove agent from capabilities index."""
        for capability in capabilities:
            if capability.name in self._capabilities_index:
                self._capabilities_index[capability.name].discard(agent_name)
                if not self._capabilities_index[capability.name]:
                    del self._capabilities_index[capability.name]

    def _update_tags_index(self, agent_name: str, tags: List[str]):
        """Update the tags index."""
        for tag in tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = set()
            self._tags_index[tag].add(agent_name)

    def _remove_from_tags_index(self, agent_name: str, tags: List[str]):
        """Remove agent from tags index."""
        for tag in tags:
            if tag in self._tags_index:
                self._tags_index[tag].discard(agent_name)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]

    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in health check loop", error=str(e))

    async def _perform_health_checks(self):
        """Perform health checks on registered agents."""
        current_time = datetime.utcnow()
        
        async with self._lock:
            for name, registration in self._agents.items():
                try:
                    # Skip if health check not due
                    if (registration.last_health_check and 
                        (current_time - registration.last_health_check).seconds < registration.health_check_interval):
                        continue
                    
                    # Perform health check
                    if registration.health_check:
                        is_healthy = registration.health_check()
                        
                        if is_healthy:
                            registration.metadata.health_score = min(
                                registration.metadata.health_score + 0.1, 1.0
                            )
                            if registration.metadata.status == AgentStatus.ERROR:
                                registration.metadata.status = AgentStatus.AVAILABLE
                        else:
                            registration.metadata.health_score = max(
                                registration.metadata.health_score - 0.2, 0.0
                            )
                            registration.metadata.error_count += 1
                            if registration.metadata.health_score < 0.5:
                                registration.metadata.status = AgentStatus.ERROR
                    
                    registration.last_health_check = current_time
                    
                except Exception as e:
                    logger.warning(
                        "Health check failed for agent",
                        agent=name,
                        error=str(e)
                    )
                    registration.metadata.error_count += 1
                    registration.metadata.health_score = max(
                        registration.metadata.health_score - 0.3, 0.0
                    )
                    registration.metadata.status = AgentStatus.ERROR
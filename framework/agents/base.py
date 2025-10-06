"""
Base Agent Class

Abstract base class for all agents in the Foundation Framework.
Provides common interface and functionality for agent implementations.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

from ..config.settings import Settings


logger = structlog.get_logger(__name__)


class AgentMessage(BaseModel):
    """Standard message format for agent communication."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    role: str = "assistant"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Standard response format from agents."""
    
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time: float = 0.0
    tokens_used: Optional[int] = None


class AgentCapability(BaseModel):
    """Represents an agent capability."""
    
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    examples: List[str] = Field(default_factory=list)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the framework.
    
    Provides common interface and functionality that all agents must implement,
    including message processing, capability management, and lifecycle hooks.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        settings: Optional[Settings] = None,
        **kwargs
    ):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name (must be unique)
            description: Agent description
            settings: Framework settings
            **kwargs: Additional agent-specific parameters
        """
        self.name = name
        self.description = description or f"Agent: {name}"
        self.settings = settings or Settings()
        
        # Agent state
        self.id = str(uuid4())
        self.created_at = datetime.utcnow()
        self.is_initialized = False
        self.is_busy = False
        
        # Statistics
        self.message_count = 0
        self.error_count = 0
        self.total_processing_time = 0.0
        
        # Capabilities
        self._capabilities: Dict[str, AgentCapability] = {}
        
        logger.info(
            "Agent created",
            agent_id=self.id,
            name=self.name,
            description=self.description
        )

    async def initialize(self) -> None:
        """
        Initialize the agent.
        
        Called once before the agent starts processing messages.
        Subclasses can override to perform agent-specific initialization.
        """
        if self.is_initialized:
            return
        
        logger.info("Initializing agent", agent_id=self.id, name=self.name)
        
        # Perform base initialization
        await self._initialize_capabilities()
        
        # Call subclass initialization
        await self._on_initialize()
        
        self.is_initialized = True
        
        logger.info("Agent initialized", agent_id=self.id, name=self.name)

    async def cleanup(self) -> None:
        """
        Cleanup agent resources.
        
        Called when the agent is being shut down or removed.
        Subclasses can override to perform agent-specific cleanup.
        """
        logger.info("Cleaning up agent", agent_id=self.id, name=self.name)
        
        # Call subclass cleanup
        await self._on_cleanup()
        
        # Reset state
        self.is_initialized = False
        self.is_busy = False
        
        logger.info("Agent cleanup complete", agent_id=self.id, name=self.name)

    async def process(
        self,
        message: Union[str, AgentMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a message and return the response.
        
        Args:
            message: Input message (string or AgentMessage)
            context: Optional context for processing
            
        Returns:
            Response string
        """
        start_time = datetime.utcnow()
        
        # Ensure agent is initialized
        if not self.is_initialized:
            await self.initialize()
        
        # Convert string to AgentMessage if needed
        if isinstance(message, str):
            agent_message = AgentMessage(content=message)
        else:
            agent_message = message
        
        # Check if agent is busy (optional concurrency control)
        if self.is_busy and not getattr(self, '_allow_concurrent', False):
            raise RuntimeError(f"Agent {self.name} is busy processing another request")
        
        try:
            self.is_busy = True
            self.message_count += 1
            
            logger.debug(
                "Processing message",
                agent_id=self.id,
                agent_name=self.name,
                message_length=len(agent_message.content)
            )
            
            # Call the agent-specific processing logic
            response = await self._process_message(agent_message, context or {})
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.total_processing_time += processing_time
            
            logger.debug(
                "Message processed",
                agent_id=self.id,
                agent_name=self.name,
                processing_time=processing_time,
                response_length=len(response.content)
            )
            
            return response.content
            
        except Exception as e:
            self.error_count += 1
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.error(
                "Error processing message",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                processing_time=processing_time,
                exc_info=True
            )
            
            # Return error message or re-raise based on configuration
            if getattr(self.settings.agents, 'return_errors_as_messages', False):
                return f"Error processing message: {str(e)}"
            else:
                raise
            
        finally:
            self.is_busy = False

    async def get_capabilities(self) -> List[AgentCapability]:
        """Get list of agent capabilities."""
        return list(self._capabilities.values())

    async def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability."""
        return capability_name in self._capabilities

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        avg_processing_time = (
            self.total_processing_time / self.message_count 
            if self.message_count > 0 else 0
        )
        
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "is_initialized": self.is_initialized,
            "is_busy": self.is_busy,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.message_count, 1),
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_processing_time,
            "capabilities_count": len(self._capabilities)
        }

    # Abstract methods that subclasses must implement

    @abstractmethod
    async def _process_message(
        self,
        message: AgentMessage,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """
        Process a message and return a response.
        
        This is the main processing method that subclasses must implement.
        
        Args:
            message: The message to process
            context: Processing context
            
        Returns:
            Agent response
        """
        pass

    # Optional lifecycle hooks for subclasses

    async def _on_initialize(self) -> None:
        """
        Called during agent initialization.
        
        Subclasses can override to perform custom initialization.
        """
        pass

    async def _on_cleanup(self) -> None:
        """
        Called during agent cleanup.
        
        Subclasses can override to perform custom cleanup.
        """
        pass

    # Protected helper methods

    async def _initialize_capabilities(self) -> None:
        """Initialize agent capabilities."""
        # Base capabilities that all agents have
        base_capabilities = [
            AgentCapability(
                name="message_processing",
                description="Process text messages and return responses",
                parameters={"input": "text", "output": "text"}
            ),
            AgentCapability(
                name="status_reporting",
                description="Report agent status and statistics",
                parameters={"output": "dict"}
            )
        ]
        
        for capability in base_capabilities:
            self._capabilities[capability.name] = capability
        
        # Call subclass capability initialization
        await self._register_capabilities()

    async def _register_capabilities(self) -> None:
        """
        Register agent-specific capabilities.
        
        Subclasses can override to add their own capabilities.
        """
        pass

    def _add_capability(self, capability: AgentCapability) -> None:
        """Add a capability to the agent."""
        self._capabilities[capability.name] = capability
        
        logger.debug(
            "Capability added",
            agent_id=self.id,
            agent_name=self.name,
            capability=capability.name
        )

    def _remove_capability(self, capability_name: str) -> bool:
        """Remove a capability from the agent."""
        if capability_name in self._capabilities:
            del self._capabilities[capability_name]
            
            logger.debug(
                "Capability removed",
                agent_id=self.id,
                agent_name=self.name,
                capability=capability_name
            )
            return True
        return False

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"Agent(name={self.name}, id={self.id[:8]}...)"

    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (
            f"Agent(name='{self.name}', id='{self.id}', "
            f"description='{self.description}', "
            f"initialized={self.is_initialized}, "
            f"capabilities={len(self._capabilities)})"
        )
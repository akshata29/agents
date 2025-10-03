"""
Abstract base interface for memory/persistence storage.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.models.task_models import AgentMessage, Plan, Session, Step


class MemoryStoreBase(ABC):
    """Abstract base class for memory/persistence storage."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the memory store (e.g., connect to database)."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources."""
        pass
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    @abstractmethod
    async def create_session(self, session: Session) -> None:
        """Create a new session."""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        pass
    
    @abstractmethod
    async def update_session(self, session: Session) -> None:
        """Update an existing session."""
        pass
    
    # ========================================================================
    # Plan Management
    # ========================================================================
    
    @abstractmethod
    async def add_plan(self, plan: Plan) -> None:
        """Add a new plan."""
        pass
    
    @abstractmethod
    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by ID."""
        pass
    
    @abstractmethod
    async def get_plan_by_session(self, session_id: str) -> Optional[Plan]:
        """Retrieve the plan for a given session."""
        pass
    
    @abstractmethod
    async def get_all_plans(self, user_id: str, limit: int = 10) -> List[Plan]:
        """Retrieve all plans for a user."""
        pass
    
    @abstractmethod
    async def update_plan(self, plan: Plan) -> None:
        """Update an existing plan."""
        pass
    
    # ========================================================================
    # Step Management
    # ========================================================================
    
    @abstractmethod
    async def add_step(self, step: Step) -> None:
        """Add a new step."""
        pass
    
    @abstractmethod
    async def get_step(self, step_id: str, session_id: str) -> Optional[Step]:
        """Retrieve a step by ID."""
        pass
    
    @abstractmethod
    async def get_steps_by_plan(self, plan_id: str) -> List[Step]:
        """Retrieve all steps for a plan."""
        pass
    
    @abstractmethod
    async def update_step(self, step: Step) -> None:
        """Update an existing step."""
        pass
    
    # ========================================================================
    # Message Management
    # ========================================================================
    
    @abstractmethod
    async def add_message(self, message: AgentMessage) -> None:
        """Add a new agent message."""
        pass
    
    @abstractmethod
    async def get_messages_by_session(self, session_id: str) -> List[AgentMessage]:
        """Retrieve all messages for a session."""
        pass
    
    @abstractmethod
    async def get_messages_by_plan(self, plan_id: str) -> List[AgentMessage]:
        """Retrieve all messages for a plan."""
        pass
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    @abstractmethod
    async def query_items(
        self,
        query: str,
        parameters: List[Dict[str, Any]],
        model_class: type
    ) -> List[Any]:
        """Execute a custom query and return results as model instances."""
        pass

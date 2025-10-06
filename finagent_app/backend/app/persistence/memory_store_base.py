"""
Abstract base interface for research run persistence.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.persistence_models import ResearchRun, ResearchSession


class MemoryStoreBase(ABC):
    """Abstract base class for research run persistence."""
    
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
    async def create_session(self, session: ResearchSession) -> None:
        """Create a new research session."""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """Retrieve a session by ID."""
        pass
    
    @abstractmethod
    async def update_session(self, session: ResearchSession) -> None:
        """Update an existing session."""
        pass
    
    @abstractmethod
    async def get_all_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[ResearchSession]:
        """Retrieve all sessions, optionally filtered by user."""
        pass
    
    # ========================================================================
    # Research Run Management
    # ========================================================================
    
    @abstractmethod
    async def add_run(self, run: ResearchRun) -> None:
        """Add a new research run."""
        pass
    
    @abstractmethod
    async def get_run(self, run_id: str) -> Optional[ResearchRun]:
        """Retrieve a research run by ID."""
        pass
    
    @abstractmethod
    async def update_run(self, run: ResearchRun) -> None:
        """Update an existing research run."""
        pass
    
    @abstractmethod
    async def get_runs_by_session(self, session_id: str) -> List[ResearchRun]:
        """Retrieve all runs for a session."""
        pass
    
    @abstractmethod
    async def get_runs_by_user(self, user_id: str, limit: int = 50) -> List[ResearchRun]:
        """Retrieve all runs for a user."""
        pass
    
    @abstractmethod
    async def get_runs_by_ticker(self, ticker: str, user_id: Optional[str] = None, limit: int = 20) -> List[ResearchRun]:
        """Retrieve all runs for a specific ticker, optionally filtered by user."""
        pass

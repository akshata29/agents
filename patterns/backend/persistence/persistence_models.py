"""
Persistence Data Models for Pattern Executions

Models for storing pattern execution sessions and runs in Cosmos DB.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class PatternSession(BaseModel):
    """Represents a pattern execution session."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    data_type: str = Field(default="session")
    session_id: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PatternExecution(BaseModel):
    """Represents a single pattern execution run."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    data_type: str = Field(default="pattern_execution")
    
    # Identifiers
    execution_id: str  # Execution ID from the workflow
    session_id: str
    user_id: str
    
    # Pattern parameters
    pattern: str  # sequential, parallel, router, enhanced_capabilities
    task: str  # Original task/objective
    
    # Execution status
    status: str = "running"  # running, completed, failed, cancelled
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None  # in seconds
    
    # Progress tracking
    progress: float = 0.0
    current_task: Optional[str] = None
    completed_tasks: List[str] = Field(default_factory=list)
    failed_tasks: List[str] = Field(default_factory=list)
    
    # Results and outputs
    result: Optional[Any] = None  # Final result
    agent_outputs: List[Dict[str, Any]] = Field(default_factory=list)  # Agent activities
    
    # Error handling
    error_message: Optional[str] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

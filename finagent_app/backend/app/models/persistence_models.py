"""
Persistence models for storing research runs in Cosmos DB.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResearchRun(BaseModel):
    """
    Stored research run in Cosmos DB.
    
    Maps to OrchestrationResponse but optimized for persistence.
    """
    # Cosmos DB fields
    id: str  # Same as run_id
    run_id: str
    session_id: str  # Partition key - group runs by session
    user_id: str  # User who initiated the run
    data_type: str = "research_run"  # For filtering in Cosmos queries
    
    # Research details
    ticker: str
    pattern: str  # sequential, concurrent, handoff, group_chat
    status: str  # pending, running, completed, failed, cancelled
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None  # Duration in seconds
    
    # Request parameters
    request_params: Dict[str, Any] = Field(default_factory=dict)  # Store original request
    
    # Results summary (store key info, not full details)
    summary: Optional[str] = None
    investment_thesis: Optional[str] = None
    key_risks: Optional[List[str]] = None
    pdf_url: Optional[str] = None
    
    # Execution metadata
    steps_count: int = 0
    messages_count: int = 0
    artifacts_count: int = 0
    error: Optional[str] = None
    
    # Full response (store as JSON blob)
    full_response: Optional[Dict[str, Any]] = None  # Complete OrchestrationResponse
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class ResearchSession(BaseModel):
    """
    Research session grouping multiple runs.
    """
    # Cosmos DB fields
    id: str  # Same as session_id
    session_id: str  # Partition key
    user_id: str
    data_type: str = "session"
    
    # Session details
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

"""
Persistence Data Models for Advisor Productivity Application

Models for storing advisor sessions in Cosmos DB.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class AdvisorSession(BaseModel):
    """Represents an advisor-client conversation session."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    data_type: str = Field(default="advisor_session")
    session_id: str
    user_id: str = "default_advisor"  # Can be expanded for multi-user support
    
    # Session metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Session status
    status: str = "active"  # active, completed, archived
    
    # Transcript data
    transcript: List[Dict[str, Any]] = Field(default_factory=list)  # List of transcript segments
    total_words: int = 0
    exchange_count: int = 0
    
    # Analytics data
    sentiment_data: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    entities: Optional[Dict[str, Any]] = None
    
    # Summary data (multi-persona)
    summaries: Optional[Dict[str, Dict[str, Any]]] = None  # {persona: summary_data}
    
    # Key metrics
    client_name: Optional[str] = None
    advisor_name: Optional[str] = None
    investment_readiness_score: Optional[float] = None
    risk_tolerance: Optional[str] = None
    key_topics: List[str] = Field(default_factory=list)
    key_phrases: List[str] = Field(default_factory=list)
    
    # Decisions and actions
    decisions_count: int = 0
    action_items_count: int = 0
    
    # Technical metadata
    audio_quality: Optional[str] = None
    transcription_confidence: Optional[float] = None
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionSearchResult(BaseModel):
    """Lightweight model for session list/search results."""
    
    session_id: str
    created_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    status: str
    client_name: Optional[str]
    advisor_name: Optional[str]
    exchange_count: int
    investment_readiness_score: Optional[float]
    key_topics: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

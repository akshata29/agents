"""
Persistence Data Models for Deep Research Application

Models for storing research sessions and runs in Cosmos DB.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class ResearchSession(BaseModel):
    """Represents a deep research session."""
    
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


class ResearchRun(BaseModel):
    """Represents a single deep research execution run."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    data_type: str = Field(default="research_run")
    
    # Identifiers
    run_id: str  # Execution ID from the workflow
    session_id: str
    user_id: str
    
    # Research parameters
    topic: str
    depth: str = "comprehensive"
    max_sources: int = 10
    include_citations: bool = True
    execution_mode: str = "workflow"  # workflow, code, or maf-workflow
    
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
    total_tasks: int = 0
    
    # Results and outputs
    research_report: Optional[str] = None  # Final report markdown
    summary: Optional[str] = None
    sources_analyzed: int = 0
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Technical details
    orchestration_pattern: Optional[str] = None
    framework: Optional[str] = None  # Framework name (e.g., "Foundation Framework")
    workflow_engine: Optional[str] = None  # Workflow engine type
    workflow_graph: Optional[Dict[str, Any]] = None  # For MAF workflow
    task_results: Dict[str, Any] = Field(default_factory=dict)  # Results from each task
    execution_details: Optional[Dict[str, Any]] = None  # Complete execution monitor details (tasks, outputs, timeline)
    
    # Error handling
    error_message: Optional[str] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

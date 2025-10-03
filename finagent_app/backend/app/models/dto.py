"""
Data Transfer Objects for Financial Research API
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Import from framework
try:
    from agent_framework.core.orchestrator import ExecutionStatus
    from agent_framework.patterns import SequentialPattern, ConcurrentPattern, HandoffPattern
except ImportError:
    # Fallback
    class ExecutionStatus(str, Enum):
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"


class OrchestrationPattern(str, Enum):
    """Orchestration patterns for API."""
    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    HANDOFF = "handoff"
    GROUP_CHAT = "group_chat"


class ResearchDepth(str, Enum):
    """Research depth levels."""
    STANDARD = "standard"
    DEEP = "deep"
    COMPREHENSIVE = "comprehensive"


class ResearchModule(str, Enum):
    """Available research modules."""
    COMPANY = "company"
    SEC = "sec"
    EARNINGS = "earnings"
    FUNDAMENTALS = "fundamentals"
    TECHNICALS = "technicals"
    ALL = "all"


class ExecutionStatus(str, Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============= Request Models =============

class SequentialResearchRequest(BaseModel):
    """Request for sequential research execution."""
    ticker: str = Field(..., description="Stock ticker symbol", example="MSFT")
    scope: List[ResearchModule] = Field(
        default=[ResearchModule.SEC, ResearchModule.EARNINGS, 
                 ResearchModule.FUNDAMENTALS, ResearchModule.TECHNICALS],
        description="Research modules to include"
    )
    depth: ResearchDepth = Field(
        default=ResearchDepth.STANDARD,
        description="Research depth level"
    )
    include_pdf: bool = Field(
        default=True,
        description="Generate PDF equity brief"
    )
    year: Optional[str] = Field(
        default=None,
        description="Year for SEC/earnings data (default: latest)"
    )


class ConcurrentResearchRequest(BaseModel):
    """Request for concurrent research execution."""
    ticker: str = Field(..., description="Stock ticker symbol")
    modules: List[ResearchModule] = Field(
        default=[ResearchModule.SEC, ResearchModule.EARNINGS,
                 ResearchModule.FUNDAMENTALS, ResearchModule.TECHNICALS],
        description="Research modules to run concurrently"
    )
    aggregation_strategy: Literal["merge", "weighted", "consensus"] = Field(
        default="merge",
        description="Strategy for aggregating concurrent results"
    )
    include_pdf: bool = Field(default=True)
    year: Optional[str] = None


class HandoffResearchRequest(BaseModel):
    """Request for handoff research execution."""
    ticker: str = Field(..., description="Stock ticker symbol")
    initial_agent: str = Field(..., description="Initial agent to start with")
    question: Optional[str] = Field(
        default=None,
        description="Specific research question"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Initial context for handoff"
    )
    max_handoffs: int = Field(default=10, description="Maximum handoff iterations")


class GroupChatRequest(BaseModel):
    """Request for group chat research execution."""
    ticker: str = Field(..., description="Stock ticker symbol")
    question: str = Field(..., description="Research question or hypothesis")
    participants: Optional[List[str]] = Field(
        default=None,
        description="Agent participants (default: all financial agents)"
    )
    max_turns: int = Field(default=40, description="Maximum conversation turns")
    require_consensus: bool = Field(
        default=False,
        description="Require consensus before concluding"
    )


# ============= Response Models =============

class AgentMessage(BaseModel):
    """Individual agent message in conversation."""
    agent: str  # Agent name/id
    timestamp: datetime
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    artifacts: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResearchArtifact(BaseModel):
    """Research artifact (report, chart, data)."""
    id: str
    type: str  # Changed from Literal to str to accept any artifact type
    title: str
    content: Any
    module: Optional[ResearchModule] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionStep(BaseModel):
    """Individual execution step in orchestration."""
    step_number: int
    agent: str
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    output: Optional[str] = None  # Short output preview
    error: Optional[str] = None


class OrchestrationResponse(BaseModel):
    """Response for orchestration execution."""
    run_id: str
    ticker: str
    pattern: OrchestrationPattern
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Execution details
    steps: List[ExecutionStep] = Field(default_factory=list)
    messages: List[AgentMessage] = Field(default_factory=list)
    artifacts: List[ResearchArtifact] = Field(default_factory=list)
    
    # Results
    summary: Optional[str] = None
    investment_thesis: Optional[str] = None
    key_risks: Optional[List[str]] = None
    pdf_url: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class AgentHealthResponse(BaseModel):
    """Agent health status."""
    agent_id: str
    agent_name: str
    status: Literal["healthy", "degraded", "unhealthy"]
    tools_available: List[str]
    last_execution: Optional[datetime] = None
    error_rate: float = 0.0
    avg_response_time: Optional[float] = None


class SystemStatusResponse(BaseModel):
    """Overall system status."""
    status: Literal["operational", "degraded", "down"]
    agents: List[AgentHealthResponse]
    active_executions: int
    mcp_connected: bool
    storage_connected: bool
    timestamp: datetime


# ============= WebSocket Messages =============

class WSMessageType(str, Enum):
    """WebSocket message types."""
    STATUS_UPDATE = "status_update"
    AGENT_MESSAGE = "agent_message"
    STEP_COMPLETE = "step_complete"
    ARTIFACT_CREATED = "artifact_created"
    EXECUTION_COMPLETE = "execution_complete"
    ERROR = "error"


class WSMessage(BaseModel):
    """WebSocket message."""
    type: WSMessageType
    run_id: str
    timestamp: datetime
    data: Dict[str, Any]

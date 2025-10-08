"""
Task orchestration data models for advisor_productivity_app.

These models support advisor session management, real-time transcription,
sentiment analysis, recommendation generation, and compliance tracking
using the Microsoft Agent Framework patterns.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class DataType(str, Enum):
    """Type identifier for documents in CosmosDB."""
    SESSION = "session"
    PLAN = "plan"
    STEP = "step"
    MESSAGE = "message"
    TRANSCRIPT = "transcript"
    SENTIMENT = "sentiment"
    RECOMMENDATION = "recommendation"
    SUMMARY = "summary"
    ENTITY = "entity"


class AgentType(str, Enum):
    """Available agent types in the advisor productivity system."""
    PLANNER = "Planner_Agent"
    SPEECH_TRANSCRIPTION = "SpeechTranscription_Agent"
    SENTIMENT = "Sentiment_Agent"
    RECOMMENDATION = "Recommendation_Agent"
    SUMMARIZER = "Summarizer_Agent"
    ENTITY_PII = "EntityPII_Agent"
    GENERIC = "Generic_Agent"
    HUMAN = "Human_Agent"
    GROUP_CHAT_MANAGER = "GroupChatManager"


class SessionType(str, Enum):
    """Type of advisory session."""
    LIVE = "live"  # Real-time conversation
    RECORDED = "recorded"  # Pre-recorded audio
    REPLAY = "replay"  # Reviewing past session


class StepStatus(str, Enum):
    """Status of a step in a plan."""
    PLANNED = "planned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStatus(str, Enum):
    """Status of an overall plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpeakerType(str, Enum):
    """Speaker identification."""
    ADVISOR = "advisor"
    CLIENT = "client"
    UNKNOWN = "unknown"


class SentimentType(str, Enum):
    """Overall sentiment classification."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class RecommendationType(str, Enum):
    """Types of investment recommendations."""
    PORTFOLIO_ALLOCATION = "portfolio_allocation"
    RISK_MITIGATION = "risk_mitigation"
    TAX_OPTIMIZATION = "tax_optimization"
    RETIREMENT_PLANNING = "retirement_planning"
    REBALANCING = "rebalancing"
    PRODUCT_SUGGESTION = "product_suggestion"
    GENERAL_ADVICE = "general_advice"


class EntityType(str, Enum):
    """Types of entities extracted from conversation."""
    COMPANY = "company"
    SECURITY = "security"
    AMOUNT = "amount"
    DATE = "date"
    PERCENTAGE = "percentage"
    PRODUCT = "product"  # Financial products like 401k, IRA, etc.
    ACCOUNT = "account"
    PERSON = "person"  # PII
    LOCATION = "location"  # PII
    PHONE = "phone"  # PII
    SSN = "ssn"  # PII
    OTHER = "other"


# ============================================================================
# Base Models
# ============================================================================

class BaseDataModel(BaseModel):
    """Base model for all Cosmos DB documents."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Session(BaseDataModel):
    """Represents an advisor-client session."""
    
    data_type: Literal[DataType.SESSION] = Field(default=DataType.SESSION)
    session_id: str
    user_id: str  # Advisor ID
    
    # Session details
    session_type: SessionType = SessionType.LIVE
    client_name: Optional[str] = None  # May be redacted for privacy
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    last_active: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: Optional[int] = None
    
    # Session metadata
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Transcript Models
# ============================================================================

class TranscriptSegment(BaseDataModel):
    """A single segment of transcribed speech."""
    
    data_type: Literal[DataType.TRANSCRIPT] = Field(default=DataType.TRANSCRIPT)
    session_id: str
    user_id: str
    
    # Transcript content
    text: str
    speaker: SpeakerType
    confidence: float  # 0-1 confidence score from Speech API
    
    # Timing
    start_time_seconds: float
    end_time_seconds: float
    
    # Metadata
    language: str = "en-US"
    audio_quality: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Sentiment Models
# ============================================================================

class SentimentAnalysis(BaseDataModel):
    """Sentiment analysis results for a transcript segment or session."""
    
    data_type: Literal[DataType.SENTIMENT] = Field(default=DataType.SENTIMENT)
    session_id: str
    user_id: str
    transcript_segment_id: Optional[str] = None  # If analyzing a segment
    
    # Overall sentiment
    overall_sentiment: SentimentType
    confidence_score: float  # 0-1
    
    # Investment-specific emotions (0-1 scale)
    emotions: Dict[str, float] = Field(default_factory=dict)
    # Examples: confidence, concern, excitement, confusion, risk_averse, risk_seeking
    
    # Investment readiness indicators
    investment_readiness: Optional[float] = None  # 0-1 scale
    risk_tolerance_indicator: Optional[str] = None  # conservative, moderate, aggressive
    decision_readiness: Optional[float] = None  # 0-1, willingness to make decisions
    
    # Metadata
    analyzed_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Recommendation Models
# ============================================================================

class InvestmentRecommendation(BaseDataModel):
    """AI-generated investment recommendation."""
    
    data_type: Literal[DataType.RECOMMENDATION] = Field(default=DataType.RECOMMENDATION)
    session_id: str
    user_id: str
    
    # Recommendation details
    recommendation_type: RecommendationType
    suggestion: str  # The actual recommendation text
    rationale: str  # Why this recommendation makes sense
    confidence: float  # 0-1 confidence score
    
    # Risk and priority
    risk_level: str  # low, moderate, high
    priority: str  # low, medium, high
    
    # Context
    based_on_segments: List[str] = Field(default_factory=list)  # Transcript segment IDs
    sentiment_context: Optional[Dict[str, Any]] = None
    
    # Compliance
    compliance_notes: List[str] = Field(default_factory=list)
    requires_disclosure: bool = False
    
    # Status
    status: str = "pending"  # pending, approved, dismissed, acted_upon
    advisor_action: Optional[str] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Summary Models
# ============================================================================

class SessionSummary(BaseDataModel):
    """Comprehensive summary of an advisor-client session."""
    
    data_type: Literal[DataType.SUMMARY] = Field(default=DataType.SUMMARY)
    session_id: str
    user_id: str
    
    # Summary content
    summary: str  # Main summary text
    key_points: List[str] = Field(default_factory=list)
    action_items: List[Dict[str, Any]] = Field(default_factory=list)
    decisions_made: List[str] = Field(default_factory=list)
    client_commitments: List[str] = Field(default_factory=list)
    follow_ups: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Persona-specific summaries
    advisor_summary: Optional[str] = None
    compliance_summary: Optional[str] = None
    client_summary: Optional[str] = None
    
    # Summary metadata
    summary_type: str = "detailed"  # brief, detailed, comprehensive
    persona: str = "advisor"  # advisor, compliance, client
    
    # Related data
    recommendations_referenced: List[str] = Field(default_factory=list)
    entities_mentioned: List[str] = Field(default_factory=list)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Entity Models
# ============================================================================

class ExtractedEntity(BaseDataModel):
    """Entity extracted from conversation with PII handling."""
    
    data_type: Literal[DataType.ENTITY] = Field(default=DataType.ENTITY)
    session_id: str
    user_id: str
    transcript_segment_id: Optional[str] = None
    
    # Entity details
    entity_type: EntityType
    text: str  # Original or redacted text
    normalized_value: Optional[str] = None  # Standardized form (e.g., ticker symbols)
    
    # PII handling
    is_pii: bool = False
    redacted: bool = False
    original_text: Optional[str] = None  # Only stored if PII and needs audit trail
    
    # Context
    context: Optional[str] = None  # Surrounding text for context
    confidence: Optional[float] = None
    
    # Compliance tagging
    compliance_tags: List[str] = Field(default_factory=list)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Plan & Step Models (for orchestration)
# ============================================================================

class Plan(BaseDataModel):
    """
    Represents a high-level plan for advisor session analysis.
    Generated by the Planner Agent.
    """
    
    data_type: Literal[DataType.PLAN] = Field(default=DataType.PLAN)
    session_id: str
    user_id: str
    
    # Plan details
    initial_goal: str
    summary: Optional[str] = None
    overall_status: PlanStatus = PlanStatus.PENDING
    
    # Metadata
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    metadata: Optional[Dict[str, Any]] = None


class Step(BaseDataModel):
    """
    Represents a single step in an analysis plan, assigned to a specific agent.
    """
    
    data_type: Literal[DataType.STEP] = Field(default=DataType.STEP)
    plan_id: str
    session_id: str
    user_id: str
    
    # Step details
    action: str  # What the agent should do
    agent: AgentType  # Which agent is responsible
    status: StepStatus = StepStatus.PLANNED
    
    # Execution results
    agent_reply: Optional[str] = None
    error_message: Optional[str] = None
    
    # Ordering
    order: Optional[int] = None
    
    # Dependencies
    dependencies: List[str] = Field(default_factory=list)
    required_artifacts: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    
    # Step-specific parameters
    parameters: Optional[Dict[str, Any]] = None


class AgentMessage(BaseDataModel):
    """
    Represents a message in the agent conversation history.
    """
    
    data_type: Literal[DataType.MESSAGE] = Field(default=DataType.MESSAGE)
    session_id: str
    user_id: str
    plan_id: str
    step_id: Optional[str] = None
    
    # Message content
    content: str
    source: str  # Agent name or "Human"
    target: Optional[str] = None
    
    # Message type/metadata
    message_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Request/Response Models (for API)
# ============================================================================

class StartSessionRequest(BaseModel):
    """Request to start a new advisor session."""
    
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    session_type: SessionType = SessionType.LIVE
    client_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TranscriptionRequest(BaseModel):
    """Request to transcribe audio segment."""
    
    session_id: str
    audio_data: Optional[bytes] = None
    audio_url: Optional[str] = None


class SentimentAnalysisRequest(BaseModel):
    """Request for sentiment analysis."""
    
    session_id: str
    transcript_segment_id: Optional[str] = None
    text: Optional[str] = None


class RecommendationRequest(BaseModel):
    """Request for investment recommendations."""
    
    session_id: str
    context: Optional[Dict[str, Any]] = None
    sentiment_data: Optional[Dict[str, Any]] = None


class SummaryRequest(BaseModel):
    """Request for session summarization."""
    
    session_id: str
    summary_type: str = "detailed"  # brief, detailed, comprehensive
    persona: str = "advisor"  # advisor, compliance, client


class EntityExtractionRequest(BaseModel):
    """Request for entity extraction and PII detection."""
    
    session_id: str
    text: str
    redact_pii: bool = True


class ActionRequest(BaseModel):
    """Request sent to an agent to perform an action."""
    
    step_id: str
    plan_id: str
    session_id: str
    action: str
    agent: AgentType
    context: Optional[Dict[str, Any]] = None


class ActionResponse(BaseModel):
    """Response from an agent after executing an action."""
    
    step_id: str
    plan_id: str
    session_id: str
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PlanWithSteps(BaseModel):
    """Plan with all its steps."""
    
    id: str
    session_id: str
    user_id: str
    initial_goal: str
    summary: Optional[str] = None
    overall_status: PlanStatus
    total_steps: int
    completed_steps: int
    failed_steps: int
    timestamp: datetime
    steps: List[Step] = Field(default_factory=list)


class SessionListItem(BaseModel):
    """Summary item for session list view."""
    
    session_id: str
    user_id: str
    session_type: SessionType
    created_at: datetime
    duration_seconds: Optional[int] = None
    transcript_segments: int = 0
    recommendations: int = 0
    status: str = "active"


class ExecutionStatusResponse(BaseModel):
    """Real-time execution status response."""
    
    plan_id: str
    session_id: str
    overall_status: PlanStatus
    current_step: Optional[str] = None
    current_agent: Optional[str] = None
    completed_steps: int
    total_steps: int
    progress_percentage: float
    recent_messages: List[str] = Field(default_factory=list)


class SessionAnalyticsResponse(BaseModel):
    """Analytics data for a session."""
    
    session_id: str
    
    # Talk time analytics
    advisor_talk_time_seconds: float = 0
    client_talk_time_seconds: float = 0
    total_talk_time_seconds: float = 0
    
    # Sentiment analytics
    overall_sentiment: Optional[SentimentType] = None
    sentiment_trend: List[Dict[str, Any]] = Field(default_factory=list)
    investment_readiness_avg: Optional[float] = None
    
    # Recommendation analytics
    total_recommendations: int = 0
    recommendations_by_type: Dict[str, int] = Field(default_factory=dict)
    high_priority_recommendations: int = 0
    
    # Entity analytics
    total_entities: int = 0
    pii_detected: int = 0
    entities_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Key topics
    key_topics: List[str] = Field(default_factory=list)
    decisions_count: int = 0
    action_items_count: int = 0


class ExportRequest(BaseModel):
    """Request to export session results."""
    
    session_id: str
    format: Literal["markdown", "pdf", "json"]
    include_transcript: bool = True
    include_sentiment: bool = True
    include_recommendations: bool = True
    include_summary: bool = True
    redact_pii: bool = True

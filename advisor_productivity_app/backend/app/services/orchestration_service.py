"""
Orchestration Service for Advisor Productivity

Coordinates all agents and manages the complete workflow lifecycle.
Handles real-time updates, agent coordination, and session management.

Uses Microsoft Agent Framework (MAF) Concurrent Pattern for parallel agent execution.
"""

from typing import Dict, Any, Optional, List
import asyncio
import json
from datetime import datetime
import structlog
import sys
from pathlib import Path

# Add framework to path
repo_root = Path(__file__).parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Framework imports
from framework.core.orchestrator import MagenticOrchestrator
from framework.core.registry import AgentRegistry, AgentMetadata, AgentCapability as RegistryCapability
from framework.config.settings import Settings as FrameworkSettings

from ..agents.speech_transcription_agent import SpeechTranscriptionAgent
from ..agents.sentiment_agent import InvestmentSentimentAgent
from ..agents.recommendation_agent import InvestmentRecommendationAgent
from ..agents.summarization_agent import InvestmentSummarizationAgent
from ..agents.entity_pii_agent import EntityPIIAgent
from ..agents.planner_agent import PlannerAgent
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)


class OrchestrationService:
    """
    Orchestration service that coordinates all agents for advisor productivity.
    
    Responsibilities:
    - Manage agent lifecycle using MAF orchestrator
    - Coordinate concurrent agent execution using MAF patterns
    - Handle data flow between agents
    - Manage session state
    - Provide unified interface for frontend
    
    Uses MAF Concurrent Pattern for parallel processing of:
    - Sentiment analysis
    - Entity/PII extraction  
    - Recommendation generation
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Initialize framework components
        framework_settings = self._create_framework_settings()
        self.orchestrator = MagenticOrchestrator(framework_settings)
        
        # Initialize all agents
        self.transcription_agent = SpeechTranscriptionAgent(settings)
        self.sentiment_agent = InvestmentSentimentAgent(settings)
        self.recommendation_agent = InvestmentRecommendationAgent(settings)
        self.summarization_agent = InvestmentSummarizationAgent(settings)
        self.entity_pii_agent = EntityPIIAgent(settings)
        self.planner_agent = PlannerAgent(settings)
        
        # Session storage
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("OrchestrationService initialized with MAF orchestrator")
    
    def _create_framework_settings(self) -> FrameworkSettings:
        """Create framework settings from app settings."""
        # Framework Settings expects nested structure with azure_openai sub-object
        return FrameworkSettings(
            azure_openai={
                "endpoint": self.settings.azure_openai_endpoint,
                "api_key": self.settings.azure_openai_api_key,
                "chat_deployment_name": self.settings.azure_openai_deployment,
                "api_version": self.settings.azure_openai_api_version
            }
        )
    
    async def initialize(self):
        """Initialize orchestrator and register agents."""
        await self.orchestrator.initialize()
        await self._register_agents()
        logger.info("OrchestrationService initialized and agents registered")
    
    async def _register_agents(self):
        """Register all agents with the MAF orchestrator."""
        # Register sentiment agent
        await self.orchestrator.agent_registry.register_agent(
            name="sentiment",
            agent=self.sentiment_agent,
            metadata=AgentMetadata(
                id="sentiment",
                name="sentiment",
                description="Investment sentiment analysis agent",
                capabilities=[
                    RegistryCapability(
                        name="sentiment_analysis",
                        description="Analyze sentiment and emotions",
                        parameters={},
                        required_tools=[]
                    )
                ]
            )
        )
        
        # Register entity/PII agent
        await self.orchestrator.agent_registry.register_agent(
            name="entity_pii",
            agent=self.entity_pii_agent,
            metadata=AgentMetadata(
                id="entity_pii",
                name="entity_pii",
                description="Entity extraction and PII detection agent",
                capabilities=[
                    RegistryCapability(
                        name="entity_extraction",
                        description="Extract entities and detect PII",
                        parameters={},
                        required_tools=[]
                    )
                ]
            )
        )
        
        # Register recommendation agent
        await self.orchestrator.agent_registry.register_agent(
            name="recommendations",
            agent=self.recommendation_agent,
            metadata=AgentMetadata(
                id="recommendations",
                name="recommendations",
                description="Investment recommendation generation agent",
                capabilities=[
                    RegistryCapability(
                        name="recommendation_generation",
                        description="Generate investment recommendations",
                        parameters={},
                        required_tools=[]
                    )
                ]
            )
        )
        
        logger.info("All agents registered with MAF orchestrator")
    
    async def create_session(
        self,
        session_id: str,
        workflow_type: str = "standard_advisor_session",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new session.
        
        Args:
            session_id: Unique session identifier
            workflow_type: Type of workflow to execute
            config: Optional configuration overrides
        
        Returns:
            Session information
        """
        try:
            if session_id in self.sessions:
                raise ValueError(f"Session {session_id} already exists")
            
            # Initialize session state
            session = {
                "session_id": session_id,
                "workflow_type": workflow_type,
                "status": "created",
                "created_at": datetime.utcnow().isoformat(),
                "config": config or {},
                "data": {
                    "transcript": [],
                    "sentiment": None,
                    "recommendations": [],
                    "entities": None,
                    "summary": None
                },
                "agents_status": {
                    "transcription": "idle",
                    "sentiment": "idle",
                    "recommendations": "idle",
                    "entity_pii": "idle",
                    "summary": "idle"
                }
            }
            
            self.sessions[session_id] = session
            
            logger.info(
                "Session created",
                session_id=session_id,
                workflow_type=workflow_type
            )
            
            return {
                "session_id": session_id,
                "status": "created",
                "workflow_type": workflow_type,
                "created_at": session["created_at"]
            }
        
        except Exception as e:
            logger.error("Error creating session", error=str(e), exc_info=True)
            raise
    
    async def start_session(self, session_id: str) -> Dict[str, Any]:
        """
        Start a session and begin workflow execution.
        
        Args:
            session_id: Session to start
        
        Returns:
            Session status
        """
        try:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.sessions[session_id]
            session["status"] = "active"
            session["started_at"] = datetime.utcnow().isoformat()
            
            logger.info("Session started", session_id=session_id)
            
            return {
                "session_id": session_id,
                "status": "active",
                "started_at": session["started_at"]
            }
        
        except Exception as e:
            logger.error("Error starting session", error=str(e), exc_info=True)
            raise
    
    async def process_transcript_chunk(
        self,
        session_id: str,
        text: str,
        speaker: Optional[str] = None,
        is_final: bool = False
    ) -> Dict[str, Any]:
        """
        Process a new transcript chunk using MAF Concurrent Pattern.
        
        Triggers parallel execution of:
        - Sentiment analysis
        - Entity/PII extraction
        - (Optional) Recommendation generation
        
        Args:
            session_id: Session identifier
            text: Transcript text
            speaker: Speaker identifier
            is_final: Whether this is a final transcript
        
        Returns:
            Processing results
        """
        try:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.sessions[session_id]
            
            # Add to transcript
            transcript_entry = {
                "text": text,
                "speaker": speaker or "Unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "is_final": is_final
            }
            session["data"]["transcript"].append(transcript_entry)
            
            # Get full transcript for analysis
            full_transcript = " ".join([t["text"] for t in session["data"]["transcript"]])
            
            # Only process if we have enough content (minimum 5 words to ensure meaningful analysis)
            word_count = len(full_transcript.split())
            if word_count >= 5:
                logger.info(
                    "Triggering concurrent agent processing",
                    session_id=session_id,
                    transcript_length=len(full_transcript),
                    word_count=word_count
                )
                
                # **USE MAF CONCURRENT PATTERN** - Execute all agents in parallel!
                task = f"""Analyze this investment advisor conversation:

Transcript: {full_transcript}

Speaker: {speaker or 'Unknown'}

Provide comprehensive analysis including sentiment, entities, and any compliance concerns."""
                
                # Execute concurrent pattern with sentiment and recommendations agents
                # NOTE: Using direct agent.run() calls with asyncio.gather() instead of ConcurrentBuilder
                #       ConcurrentBuilder has known issues with message aggregation
                try:
                    # Get agent instances
                    sentiment_agent = await self.orchestrator.agent_registry.get_agent("sentiment")
                    recommendations_agent = await self.orchestrator.agent_registry.get_agent("recommendations")
                    
                    # Execute all agents concurrently using asyncio.gather()
                    logger.info("Executing agents in parallel with asyncio.gather")
                    
                    results = await asyncio.gather(
                        sentiment_agent.run(messages=task),
                        recommendations_agent.run(messages=task),
                        return_exceptions=True
                    )
                    
                    # Build concurrent_result in expected format
                    concurrent_result = {
                        "pattern": "concurrent",
                        "task": task,
                        "agents": ["sentiment", "recommendations"],
                        "results": []
                    }
                    
                    agent_names = ["sentiment", "recommendations"]
                    for idx, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Agent {agent_names[idx]} failed", error=str(result))
                            concurrent_result["results"].append({
                                "agent": agent_names[idx],
                                "content": "",
                                "error": str(result)
                            })
                        else:
                            # Extract text from AgentRunResponse
                            result_text = ""
                            if hasattr(result, 'messages') and result.messages:
                                result_text = result.messages[0].text if result.messages else ""
                            
                            logger.info(f"Agent {agent_names[idx]} completed", output_length=len(result_text))
                            concurrent_result["results"].append({
                                "agent": agent_names[idx],
                                "content": result_text
                            })
                    
                    logger.info(
                        "Concurrent execution completed",
                        session_id=session_id,
                        agents=concurrent_result.get("agents", []),
                        result_count=len(concurrent_result.get("results", []))
                    )
                except Exception as e:
                    logger.error(
                        "Concurrent execution failed",
                        session_id=session_id,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True
                    )
                    # Continue without agent processing
                    return {
                        "session_id": session_id,
                        "transcript_length": len(session["data"]["transcript"]),
                        "error": f"Agent processing failed: {str(e)}"
                    }
                
                # Parse results from concurrent execution
                # concurrent_result["results"] is a list of {"agent": agent_id, "content": output}
                # Content is JSON string from MAF agents
                for result in concurrent_result.get("results", []):
                    agent_id = result.get("agent")
                    content = result.get("content")
                    
                    # Parse JSON content from MAF agents
                    try:
                        if isinstance(content, str):
                            parsed_content = json.loads(content)
                        else:
                            parsed_content = content
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON from {agent_id}, using raw content", session_id=session_id)
                        parsed_content = content
                    
                    if agent_id == "sentiment":
                        session["data"]["sentiment"] = parsed_content
                        session["agents_status"]["sentiment"] = "completed"
                        logger.info("✓ Sentiment analysis completed", session_id=session_id)
                    
                    elif agent_id == "entity_pii":
                        session["data"]["entities"] = parsed_content
                        session["agents_status"]["entity_pii"] = "completed"
                        logger.info("✓ Entity/PII extraction completed", session_id=session_id)
                    
                    elif agent_id == "recommendations":
                        # Parse recommendations from content
                        session["data"]["recommendations"] = parsed_content
                        session["agents_status"]["recommendations"] = "completed"
                        logger.info("✓ Recommendations generated", session_id=session_id)
                
                return {
                    "session_id": session_id,
                    "transcript_length": len(session["data"]["transcript"]),
                    "sentiment_updated": session["data"]["sentiment"] is not None,
                    "entities_updated": session["data"]["entities"] is not None,
                    "recommendations_updated": session["data"]["recommendations"] is not None,
                    "concurrent_pattern": True,
                    "agents_executed": concurrent_result.get("agents", [])
                }
            else:
                # Not enough content yet - log this
                logger.debug(
                    "Transcript too short for agent processing",
                    session_id=session_id,
                    word_count=word_count,
                    threshold=5,
                    transcript=full_transcript[:100]
                )
            
            # Not enough content yet
            return {
                "session_id": session_id,
                "transcript_length": len(session["data"]["transcript"]),
                "sentiment_updated": False,
                "entities_updated": False,
                "recommendations_updated": False,
                "message": "Waiting for more content (minimum 10 words)"
            }
        
        except Exception as e:
            logger.error("Error processing transcript", error=str(e), exc_info=True)
            raise
    
    async def generate_recommendations(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Generate investment recommendations for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Recommendations
        """
        try:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.sessions[session_id]
            full_transcript = " ".join([t["text"] for t in session["data"]["transcript"]])
            
            session["agents_status"]["recommendations"] = "processing"
            
            recommendations = await self.recommendation_agent.run({
                "text": full_transcript,
                "sentiment_data": session["data"]["sentiment"]
            })
            
            session["data"]["recommendations"] = recommendations.get("recommendations", [])
            session["agents_status"]["recommendations"] = "completed"
            
            return {
                "session_id": session_id,
                "recommendations": session["data"]["recommendations"],
                "count": len(session["data"]["recommendations"])
            }
        
        except Exception as e:
            logger.error("Error generating recommendations", error=str(e), exc_info=True)
            raise
    
    async def generate_summary(
        self,
        session_id: str,
        personas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate session summary.
        
        Args:
            session_id: Session identifier
            personas: List of personas for summary
        
        Returns:
            Summaries
        """
        try:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.sessions[session_id]
            full_transcript = " ".join([t["text"] for t in session["data"]["transcript"]])
            
            session["agents_status"]["summary"] = "processing"
            
            personas = personas or ["advisor", "compliance", "client"]
            summaries = []
            
            for persona in personas:
                summary = await self.summarization_agent.run({
                    "text": full_transcript,
                    "persona": persona,
                    "summary_type": "detailed"
                })
                summaries.append(summary)
            
            session["data"]["summary"] = summaries
            session["agents_status"]["summary"] = "completed"
            
            return {
                "session_id": session_id,
                "summaries": summaries,
                "personas": personas
            }
        
        except Exception as e:
            logger.error("Error generating summary", error=str(e), exc_info=True)
            raise
    
    async def end_session(
        self,
        session_id: str,
        auto_summary: bool = True
    ) -> Dict[str, Any]:
        """
        End a session and generate final outputs.
        
        Args:
            session_id: Session to end
            auto_summary: Whether to auto-generate summary
        
        Returns:
            Session summary
        """
        try:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.sessions[session_id]
            session["status"] = "ended"
            session["ended_at"] = datetime.utcnow().isoformat()
            
            # Generate summary if requested
            if auto_summary and not session["data"]["summary"]:
                await self.generate_summary(session_id)
            
            logger.info("Session ended", session_id=session_id)
            
            return {
                "session_id": session_id,
                "status": "ended",
                "ended_at": session["ended_at"],
                "data": session["data"],
                "agents_status": session["agents_status"]
            }
        
        except Exception as e:
            logger.error("Error ending session", error=str(e), exc_info=True)
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return self.sessions.get(session_id)
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions."""
        return list(self.sessions.values())
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current session status.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session status information
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        return {
            "session_id": session_id,
            "status": session["status"],
            "workflow_type": session["workflow_type"],
            "agents_status": session["agents_status"],
            "data_summary": {
                "transcript_chunks": len(session["data"]["transcript"]),
                "has_sentiment": session["data"]["sentiment"] is not None,
                "recommendations_count": len(session["data"]["recommendations"]),
                "has_entities": session["data"]["entities"] is not None,
                "has_summary": session["data"]["summary"] is not None
            },
            "created_at": session["created_at"],
            "started_at": session.get("started_at"),
            "ended_at": session.get("ended_at")
        }

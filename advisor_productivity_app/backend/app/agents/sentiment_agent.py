"""
Investment Sentiment Analysis Agent

Performs comprehensive sentiment analysis on investment advisor-client conversations.
Specialized for financial advisory context with investment-specific emotions and metrics.
MAF-compatible agent implementation.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncIterable
from datetime import datetime
from pathlib import Path
import structlog

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread

from openai import AsyncAzureOpenAI

from ..models.task_models import (
    SentimentAnalysis,
    SentimentType
)

logger = structlog.get_logger(__name__)


class InvestmentSentimentAgent(BaseAgent):
    """
    MAF-compatible agent for investment-focused sentiment analysis.
    
    Specialized Capabilities:
    - Investment-specific emotion detection (confidence, concern, excitement, confusion, risk_averse, risk_seeking)
    - Investment readiness scoring (0-1 scale indicating propensity to invest)
    - Advisor-client dynamics analysis
    - Risk tolerance assessment
    - Decision confidence tracking
    - Compliance concern detection
    """
    
    def __init__(self, settings, name: str = "investment_sentiment", description: str = "Analyzes investment conversation sentiment and emotional dynamics"):
        """Initialize the investment sentiment analysis agent."""
        super().__init__(name=name, description=description)
        
        self.app_settings = settings
        
        # Initialize Azure OpenAI client
        self.client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT
        
        # Investment-specific emotion categories
        self.investment_emotions = [
            "confidence",      # High confidence in investment decisions
            "concern",         # Worry or apprehension about risks
            "excitement",      # Enthusiasm about opportunities
            "confusion",       # Uncertainty or lack of understanding
            "risk_averse",     # Conservative, safety-focused
            "risk_seeking",    # Aggressive, growth-focused
            "cautious",        # Careful, measured approach
            "optimistic",      # Positive outlook on markets/investments
            "pessimistic",     # Negative outlook, bearish sentiment
            "anxious",         # Stress about market volatility or losses
            "satisfied",       # Content with current portfolio/strategy
            "frustrated"       # Dissatisfaction with performance or options
        ]
        
        logger.info(
            f"Initialized {self.name}",
            investment_emotions=len(self.investment_emotions)
        )
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "investment_sentiment_analysis",
            "emotion_detection",
            "investment_readiness_scoring",
            "risk_tolerance_assessment",
            "advisor_client_dynamics",
            "decision_confidence_tracking"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent - REQUIRED by MAF."""
        logger.info(f"🚀 InvestmentSentimentAgent.run() called with messages={type(messages)}, kwargs={list(kwargs.keys())}")
        try:
            # Normalize messages
            normalized_messages = self._normalize_messages(messages)
            logger.info(f"📝 Normalized to {len(normalized_messages)} messages")
            
            # Extract content from last message
            last_message = normalized_messages[-1] if normalized_messages else None
            content = last_message.text if last_message and hasattr(last_message, 'text') else ""
            logger.info(f"📄 Extracted content length: {len(content)}")
            
            # Allow override from kwargs
            content = kwargs.get("content", content)
            session_id = kwargs.get("session_id")
            speaker = kwargs.get("speaker")
            
            if not content or len(content.strip()) == 0:
                logger.warning("⚠️ No content provided, returning error response")
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: No content provided for sentiment analysis")]
                    )]
                )
            
            # Perform investment sentiment analysis
            result = await self.analyze_investment_sentiment(
                content=content,
                session_id=session_id,
                speaker=speaker,
                context=kwargs
            )
            
            # Return result as ChatMessage
            result_text = json.dumps(result, ensure_ascii=False, default=str)
            logger.info(f"✅ Returning AgentRunResponse with {len(result_text)} chars")
            response = AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            logger.info(f"📦 Response object created: {type(response)}, messages count: {len(response.messages)}")
            logger.info(f"🔍 Verifying response.messages: {response.messages}")
            logger.info(f"🔍 Response.messages[0].role: {response.messages[0].role if response.messages else 'NO MESSAGES'}")
            logger.info(f"🔍 Response.messages[0].text: {response.messages[0].text[:100] if response.messages and hasattr(response.messages[0], 'text') else 'NO TEXT'}")
            return response
            
        except Exception as e:
            logger.error(f"Error in investment sentiment analysis", error=str(e), exc_info=True)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=f"Error: {str(e)}")]
                )]
            )
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Stream responses - REQUIRED by MAF."""
        result = await self.run(messages, thread=thread, **kwargs)
        
        for message in result.messages:
            yield AgentRunResponseUpdate(
                messages=[message]
            )
    
    def _normalize_messages(
        self, 
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None
    ) -> list[ChatMessage]:
        """Normalize various message formats to list of ChatMessage."""
        if messages is None:
            return []
        
        if isinstance(messages, str):
            return [ChatMessage(role=Role.USER, contents=[TextContent(text=messages)])]
        
        if isinstance(messages, ChatMessage):
            return [messages]
        
        if isinstance(messages, list):
            normalized = []
            for msg in messages:
                if isinstance(msg, str):
                    normalized.append(ChatMessage(role=Role.USER, contents=[TextContent(text=msg)]))
                elif isinstance(msg, ChatMessage):
                    normalized.append(msg)
            return normalized
        
        return []
    
    async def analyze_investment_sentiment(
        self,
        content: str,
        session_id: Optional[str] = None,
        speaker: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of investment conversation content.
        
        Args:
            content: Transcribed text to analyze
            session_id: Optional session identifier
            speaker: Optional speaker identifier (advisor/client)
            context: Additional context (transcript history, etc.)
            
        Returns:
            Dictionary containing investment sentiment analysis
        """
        logger.info(
            "Analyzing investment sentiment",
            content_length=len(content),
            session_id=session_id,
            speaker=speaker
        )
        
        try:
            # Build specialized prompt
            prompt = self._build_investment_sentiment_prompt(
                content=content,
                speaker=speaker,
                context=context
            )
            
            # Call Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert investment sentiment analyst specializing in financial advisor-client conversations. 
You understand investment psychology, risk tolerance, and decision-making dynamics. 
Analyze conversations with focus on investment readiness, emotional state, and advisor-client dynamics.
Provide structured JSON output."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Enhance with metadata
            result["metadata"] = {
                "session_id": session_id,
                "speaker": speaker,
                "analyzed_at": datetime.utcnow().isoformat(),
                "content_length": len(content),
                "agent": self.name
            }
            
            logger.info(
                "Investment sentiment analysis completed",
                overall_sentiment=result.get("overall_sentiment"),
                investment_readiness=result.get("investment_readiness_score"),
                risk_tolerance=result.get("risk_tolerance")
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze investment sentiment", error=str(e), exc_info=True)
            raise
    
    def _build_investment_sentiment_prompt(
        self,
        content: str,
        speaker: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build specialized prompt for investment sentiment analysis."""
        
        speaker_context = ""
        if speaker:
            speaker_context = f"\n\nSpeaker: {speaker}"
        
        conversation_history = ""
        if context and context.get('conversation_history'):
            history = context.get('conversation_history', [])
            if len(history) > 0:
                recent = history[-3:]  # Last 3 exchanges for context
                conversation_history = f"""

Recent Conversation Context:
{json.dumps(recent, indent=2)}
"""
        
        prompt = f"""Analyze the investment sentiment in the following conversation segment.{speaker_context}{conversation_history}

Current Segment:
{content}

Provide comprehensive investment-focused sentiment analysis in this JSON structure:

{{
    "overall_sentiment": "positive|negative|neutral|mixed",
    "sentiment_type": "confident|concerned|excited|confused|cautious|optimistic|pessimistic|anxious",
    "sentiment_score": <float between -1.0 (very negative) and 1.0 (very positive)>,
    "confidence": <float between 0.0 and 1.0>,
    
    "investment_emotions": [
        {{
            "emotion": "confidence|concern|excitement|confusion|risk_averse|risk_seeking|cautious|optimistic|pessimistic|anxious|satisfied|frustrated",
            "intensity": <float between 0.0 and 1.0>,
            "evidence": "Brief quote or phrase supporting this emotion"
        }}
    ],
    
    "investment_readiness": {{
        "score": <float between 0.0 (not ready) and 1.0 (very ready)>,
        "reasoning": "Explanation of readiness assessment",
        "indicators": ["indicator1", "indicator2"],
        "concerns": ["concern1", "concern2"]
    }},
    
    "risk_tolerance": {{
        "level": "conservative|moderate|aggressive|very_aggressive",
        "score": <float between 0.0 (very conservative) and 1.0 (very aggressive)>,
        "evidence": ["evidence1", "evidence2"]
    }},
    
    "decision_confidence": {{
        "level": "high|medium|low",
        "score": <float between 0.0 and 1.0>,
        "factors": ["factor1", "factor2"]
    }},
    
    "advisor_client_dynamics": {{
        "trust_level": "high|medium|low",
        "engagement": "high|medium|low",
        "alignment": "aligned|partially_aligned|misaligned",
        "concerns_raised": ["concern1", "concern2"],
        "questions_asked": ["question1", "question2"]
    }},
    
    "key_phrases": ["phrase1", "phrase2", "phrase3"],
    
    "compliance_flags": [
        {{
            "type": "pressure|unrealistic_expectations|risk_mismatch|suitability_concern",
            "severity": "high|medium|low",
            "description": "Brief description"
        }}
    ],
    
    "insights": "2-3 sentence summary of key sentiment insights relevant to investment decision-making",
    
    "recommendations": [
        "action_or_consideration_1",
        "action_or_consideration_2"
    ]
}}

IMPORTANT INVESTMENT-SPECIFIC GUIDANCE:
1. Investment Readiness: Assess how ready the client is to make investment decisions (0.0 = needs education, 0.5 = considering, 1.0 = ready to act)
2. Risk Tolerance: Evaluate based on language about volatility, returns, safety, growth appetite
3. Decision Confidence: Detect hesitation, certainty, need for more information
4. Compliance: Flag any pressure tactics, unrealistic return expectations, or risk mismatches
5. Emotions: Focus on investment-specific emotions (confidence, concern, excitement about opportunities, etc.)

Base your analysis strictly on the content provided. Be objective and evidence-based."""
        
        return prompt
    
    async def analyze_conversation_flow(
        self,
        segments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze sentiment progression across multiple conversation segments.
        Detects trends, shifts, and patterns over the conversation timeline.
        
        Args:
            segments: List of {text, speaker, timestamp, sentiment} dictionaries
            
        Returns:
            Analysis of sentiment flow and progression
        """
        logger.info(
            "Analyzing conversation sentiment flow",
            segment_count=len(segments)
        )
        
        try:
            # Prepare segments summary
            segments_summary = []
            for i, seg in enumerate(segments):
                segments_summary.append({
                    "position": i + 1,
                    "speaker": seg.get("speaker", "unknown"),
                    "text_preview": seg.get("text", "")[:100],
                    "sentiment": seg.get("sentiment", {})
                })
            
            prompt = f"""Analyze the sentiment progression across this investment conversation.

Conversation Segments ({len(segments)} total):
{json.dumps(segments_summary, indent=2)}

Provide analysis in JSON format:
{{
    "sentiment_progression": "improving|declining|stable|volatile",
    "overall_trajectory": "Description of how sentiment evolves",
    
    "key_turning_points": [
        {{
            "segment_position": <int>,
            "description": "What changed",
            "impact": "positive|negative|neutral"
        }}
    ],
    
    "client_sentiment_trend": {{
        "direction": "improving|declining|stable",
        "investment_readiness_trend": "increasing|decreasing|stable",
        "confidence_trend": "growing|weakening|stable"
    }},
    
    "advisor_effectiveness": {{
        "rapport_building": "effective|needs_improvement",
        "concern_addressing": "effective|needs_improvement",
        "explanation_clarity": "clear|unclear",
        "recommendations": ["recommendation1", "recommendation2"]
    }},
    
    "risk_factors": [
        "Any red flags or concerns in the conversation flow"
    ],
    
    "insights": "Summary of sentiment progression insights"
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in analyzing conversation dynamics and sentiment progression in investment advisory contexts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            logger.info(
                "Conversation flow analysis completed",
                progression=result.get("sentiment_progression")
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze conversation flow", error=str(e), exc_info=True)
            raise
    
    async def detect_compliance_concerns(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect potential compliance concerns in conversation content.
        
        Focus areas:
        - Sales pressure or coercion
        - Unrealistic return promises
        - Risk/suitability mismatches
        - Inadequate disclosure
        - Churning indicators
        
        Args:
            content: Conversation text
            context: Additional context
            
        Returns:
            List of detected compliance concerns
        """
        logger.info("Analyzing compliance concerns")
        
        try:
            prompt = f"""Analyze this investment conversation for potential compliance concerns.

Conversation:
{content}

Identify any compliance red flags in JSON format:
{{
    "concerns": [
        {{
            "type": "sales_pressure|unrealistic_returns|risk_mismatch|inadequate_disclosure|churning|suitability|other",
            "severity": "critical|high|medium|low",
            "description": "Detailed description of the concern",
            "evidence": "Quote or phrase from conversation",
            "recommendation": "Suggested action or follow-up"
        }}
    ],
    "overall_risk_level": "critical|high|medium|low|none",
    "requires_review": true|false,
    "summary": "Brief summary of compliance posture"
}}

COMPLIANCE FOCUS AREAS:
1. Sales Pressure: Aggressive tactics, time pressure, fear-based selling
2. Unrealistic Returns: Promises of guaranteed returns, downplaying risks
3. Risk Mismatch: Recommending unsuitable products for client profile
4. Inadequate Disclosure: Failing to explain fees, risks, or product features
5. Churning: Excessive trading to generate commissions
6. Suitability: Product recommendations misaligned with client needs/goals

Be thorough but balanced. Flag genuine concerns, not routine advisory discussions."""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a compliance expert specializing in investment advisory regulations. Identify potential violations or concerning patterns."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for compliance
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            concerns = result.get("concerns", [])
            
            logger.info(
                "Compliance analysis completed",
                concern_count=len(concerns),
                risk_level=result.get("overall_risk_level"),
                requires_review=result.get("requires_review")
            )
            
            return concerns
            
        except Exception as e:
            logger.error(f"Failed to detect compliance concerns", error=str(e), exc_info=True)
            raise
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for the planner."""
        return {
            "agent_name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "investment_emotions": self.investment_emotions,
            "output_formats": ["json", "summary"],
            "specialized_features": [
                "investment_readiness_scoring",
                "risk_tolerance_assessment",
                "compliance_concern_detection",
                "conversation_flow_analysis"
            ]
        }

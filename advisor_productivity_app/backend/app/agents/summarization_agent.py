"""
Investment Summarization Agent

Creates comprehensive summaries of investment advisor-client sessions with
action items, decisions, and persona-based views.
MAF-compatible agent implementation.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Literal, AsyncIterable
from datetime import datetime
from pathlib import Path
import structlog

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread

from openai import AsyncAzureOpenAI

from ..models.task_models import (
    SessionSummary
)

logger = structlog.get_logger(__name__)


class InvestmentSummarizationAgent(BaseAgent):
    """
    MAF-compatible agent for investment session summarization.
    
    Capabilities:
    - Session-wide conversation summarization
    - Action item extraction
    - Key decisions and commitments tracking
    - Persona-based summaries (advisor, compliance, client)
    - Integration with sentiment and recommendation data
    - Follow-up recommendations
    """
    
    def __init__(self, settings, name: str = "investment_summarization", description: str = "Creates comprehensive investment session summaries"):
        """Initialize the investment summarization agent."""
        super().__init__(name=name, description=description)
        
        self.app_settings = settings
        
        # Initialize Azure OpenAI client
        self.client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT
        
        # Summary types
        self.summary_types = ["brief", "detailed", "comprehensive"]
        
        # Personas
        self.personas = ["advisor", "compliance", "client", "general"]
        
        logger.info(
            f"Initialized {self.name}",
            summary_types=len(self.summary_types),
            personas=len(self.personas)
        )
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "session_summarization",
            "action_item_extraction",
            "decision_tracking",
            "commitment_tracking",
            "persona_based_summaries",
            "follow_up_recommendations"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent - REQUIRED by MAF."""
        try:
            # Extract context from kwargs
            session_id = kwargs.get("session_id")
            transcript_segments = kwargs.get("transcript_segments", [])
            sentiment_data = kwargs.get("sentiment_data")
            recommendations = kwargs.get("recommendations")
            summary_type = kwargs.get("summary_type", "detailed")
            persona = kwargs.get("persona", "advisor")
            
            if not transcript_segments:
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: No transcript segments provided")]
                    )]
                )
            
            # Generate summary
            result = await self.generate_session_summary(
                transcript_segments=transcript_segments,
                sentiment_data=sentiment_data,
                recommendations=recommendations,
                session_id=session_id,
                summary_type=summary_type,
                persona=persona,
                context=kwargs
            )
            
            # Return result as ChatMessage
            result_text = json.dumps(result, ensure_ascii=False, default=str)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            
        except Exception as e:
            logger.error(f"Error in session summarization", error=str(e), exc_info=True)
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
    
    async def generate_session_summary(
        self,
        transcript_segments: List[Dict[str, Any]],
        sentiment_data: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        summary_type: str = "detailed",
        persona: str = "advisor",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive session summary.
        
        Args:
            transcript_segments: List of conversation segments with text, speaker, timestamp
            sentiment_data: Aggregated sentiment analysis results
            recommendations: Generated recommendations
            session_id: Optional session identifier
            summary_type: Level of detail (brief, detailed, comprehensive)
            persona: Target audience (advisor, compliance, client, general)
            context: Additional context
            
        Returns:
            Dictionary containing comprehensive summary
        """
        logger.info(
            "Generating session summary",
            session_id=session_id,
            segment_count=len(transcript_segments),
            summary_type=summary_type,
            persona=persona,
            has_sentiment=bool(sentiment_data),
            has_recommendations=bool(recommendations)
        )
        
        try:
            # Build full transcript from segments
            full_transcript = self._build_transcript_from_segments(transcript_segments)
            
            # Build summary prompt
            prompt = self._build_summary_prompt(
                transcript=full_transcript,
                transcript_segments=transcript_segments,
                sentiment_data=sentiment_data,
                recommendations=recommendations,
                summary_type=summary_type,
                persona=persona
            )
            
            # Call Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_persona_system_message(persona)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,  # Moderate creativity for summaries
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Enhance with metadata
            result["metadata"] = {
                "session_id": session_id,
                "generated_at": datetime.utcnow().isoformat(),
                "summary_type": summary_type,
                "persona": persona,
                "segment_count": len(transcript_segments),
                "has_sentiment_data": bool(sentiment_data),
                "has_recommendations": bool(recommendations),
                "agent": self.name
            }
            
            logger.info(
                "Session summary generated",
                key_points=len(result.get("key_points", [])),
                action_items=len(result.get("action_items", [])),
                decisions=len(result.get("decisions_made", []))
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate session summary", error=str(e), exc_info=True)
            raise
    
    def _build_transcript_from_segments(
        self,
        segments: List[Dict[str, Any]]
    ) -> str:
        """Build formatted transcript from segments."""
        transcript_lines = []
        
        for segment in segments:
            speaker = segment.get("speaker", "Unknown")
            text = segment.get("text", "")
            timestamp = segment.get("timestamp", "")
            
            if timestamp:
                transcript_lines.append(f"[{timestamp}] {speaker}: {text}")
            else:
                transcript_lines.append(f"{speaker}: {text}")
        
        return "\n\n".join(transcript_lines)
    
    def _build_summary_prompt(
        self,
        transcript: str,
        transcript_segments: List[Dict[str, Any]],
        sentiment_data: Optional[Dict[str, Any]],
        recommendations: Optional[Dict[str, Any]],
        summary_type: str,
        persona: str
    ) -> str:
        """Build specialized prompt for investment session summary."""
        
        # Build sentiment context section
        sentiment_section = ""
        if sentiment_data:
            sentiment_section = f"""

SENTIMENT ANALYSIS INSIGHTS:
The following sentiment data was collected throughout the conversation:
{json.dumps(sentiment_data, indent=2, default=str)}

Use this sentiment analysis to:
- Assess the client's emotional journey and investment readiness
- Identify concerns, confidence levels, and decision-making patterns
- Understand risk tolerance indicators
- Track engagement and trust-building moments
"""
        
        # Build recommendations section
        recommendations_section = ""
        if recommendations:
            recommendations_section = f"""

INVESTMENT RECOMMENDATIONS GENERATED:
The following recommendations were created based on the conversation:
{json.dumps(recommendations, indent=2, default=str)}

Incorporate these recommendations into your summary by:
- Noting which recommendations align with discussed topics
- Highlighting client reactions to investment suggestions
- Tracking recommendation acceptance, questions, or concerns
- Identifying next steps for recommendation follow-through
"""
        
        # Determine detail level
        if summary_type == "brief":
            detail_guidance = "Provide a concise 2-3 paragraph summary focusing on the most critical points."
        elif summary_type == "detailed":
            detail_guidance = "Provide a comprehensive summary covering all important aspects of the conversation."
        else:  # comprehensive
            detail_guidance = "Provide an exhaustive summary with detailed coverage of all discussion points, decisions, and nuances."
        
        prompt = f"""Generate a comprehensive summary of this investment advisor-client session.

CONVERSATION TRANSCRIPT ({len(transcript_segments)} segments):
{transcript}
{sentiment_section}
{recommendations_section}

SUMMARY REQUIREMENTS:
- Summary Type: {summary_type}
- Target Persona: {persona}
- {detail_guidance}

IMPORTANT: Integrate the sentiment analysis and recommendations data above into your summary. 
The summary should reflect how the client's emotional state, investment readiness, and risk 
tolerance evolved throughout the conversation, and how the generated recommendations align 
with the discussion topics and client needs.

Provide the summary in this JSON structure:

{{
    "summary": "Main narrative summary of the session",
    
    "key_points": [
        "Key point 1",
        "Key point 2",
        "Key point 3"
    ],
    
    "action_items": [
        {{
            "action": "Specific action to be taken",
            "responsible": "advisor|client|both",
            "deadline": "timeframe or specific date",
            "priority": "high|medium|low",
            "details": "Additional context"
        }}
    ],
    
    "decisions_made": [
        {{
            "decision": "What was decided",
            "rationale": "Why this decision was made",
            "impact": "Expected impact or outcome"
        }}
    ],
    
    "client_commitments": [
        {{
            "commitment": "What client committed to",
            "timeline": "When they committed to do it",
            "notes": "Additional context"
        }}
    ],
    
    "topics_discussed": [
        {{
            "topic": "Topic name",
            "summary": "Brief summary of discussion",
            "key_insights": ["insight1", "insight2"]
        }}
    ],
    
    "recommendations_reviewed": [
        {{
            "recommendation": "Investment recommendation discussed",
            "client_response": "How client responded",
            "status": "accepted|considering|declined|deferred",
            "next_steps": "What happens next"
        }}
    ],
    
    "sentiment_progression": {{
        "initial_state": "Client's emotional state at start",
        "final_state": "Client's emotional state at end",
        "key_shifts": ["Notable changes in sentiment or readiness"],
        "overall_trajectory": "improving|declining|stable",
        "investment_readiness_score": "Numeric score from sentiment analysis if available",
        "dominant_emotions": ["Top emotions observed during session"]
    }},
    
    "risk_tolerance_assessment": {{
        "assessed_level": "conservative|moderate|aggressive|very_aggressive",
        "evidence": ["Supporting observations from conversation and sentiment data"],
        "confidence": "high|medium|low",
        "consistency": "Whether stated preferences align with emotional indicators"
    }},
    
    "analytics_summary": {{
        "sentiment_insights": "How sentiment analysis informed understanding of the client",
        "recommendation_alignment": "How well recommendations matched client needs and discussion",
        "emotional_indicators": "Key emotional states that influenced the conversation",
        "readiness_factors": "What contributed to or hindered investment readiness"
    }},
    
    "investment_readiness": {{
        "current_level": "Description of client readiness",
        "factors": ["Factors affecting readiness"],
        "recommendations": ["Steps to improve readiness if needed"]
    }},
    
    "follow_ups": [
        {{
            "topic": "Follow-up topic",
            "purpose": "Why this follow-up is needed",
            "suggested_timeline": "When to follow up",
            "preparation_needed": "What to prepare"
        }}
    ],
    
    "compliance_notes": [
        "Any compliance-relevant observations, disclosures made, or concerns"
    ],
    
    "advisor_notes": "Private notes for the advisor (not for client)",
    
    "client_summary": "Simplified summary suitable for sharing with client",
    
    "next_meeting_agenda": [
        "Suggested topic 1",
        "Suggested topic 2"
    ]
}}

PERSONA-SPECIFIC GUIDANCE:

{self._get_persona_guidance(persona)}

Be thorough, accurate, and professional. Base all insights on the actual conversation content."""
        
        return prompt
    
    def _get_persona_system_message(self, persona: str) -> str:
        """Get system message tailored to persona."""
        
        if persona == "advisor":
            return """You are an AI assistant helping financial advisors summarize client meetings.
Focus on actionable insights, follow-ups, and advisor-relevant details.
Include both strategic and tactical information.
Highlight areas requiring attention or follow-up."""
        
        elif persona == "compliance":
            return """You are an AI assistant helping compliance officers review advisor-client interactions.
Focus on regulatory compliance, suitability, disclosures, and risk assessment.
Highlight any potential compliance concerns or required documentation.
Ensure all recommendations align with suitability standards."""
        
        elif persona == "client":
            return """You are an AI assistant creating client-friendly meeting summaries.
Use clear, jargon-free language.
Focus on what the client needs to know and do.
Make action items and next steps crystal clear."""
        
        else:  # general
            return """You are an AI assistant creating balanced, comprehensive meeting summaries.
Provide objective, factual summaries suitable for general documentation.
Include all relevant details without bias toward any specific audience."""
    
    def _get_persona_guidance(self, persona: str) -> str:
        """Get specific guidance for persona."""
        
        if persona == "advisor":
            return """
ADVISOR FOCUS:
- What does the advisor need to do next?
- What client concerns need addressing?
- What opportunities were identified?
- What research or preparation is needed?
- What products/strategies to explore further?
- Client relationship insights
"""
        
        elif persona == "compliance":
            return """
COMPLIANCE FOCUS:
- Were all disclosures properly made?
- Is there alignment between recommendations and client suitability?
- Were any high-risk products discussed with appropriate context?
- Are there any pressure tactics or concerning language?
- Is documentation complete?
- Are there any regulatory red flags?
"""
        
        elif persona == "client":
            return """
CLIENT FOCUS:
- What did we agree on?
- What am I supposed to do next?
- What is my advisor doing for me?
- What should I expect?
- Keep it simple and actionable
- No financial jargon
"""
        
        else:  # general
            return """
GENERAL FOCUS:
- Comprehensive but balanced
- All stakeholders' perspectives
- Complete documentation
- Objective tone
"""
    
    async def generate_persona_summaries(
        self,
        transcript_segments: List[Dict[str, Any]],
        sentiment_data: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate summaries for all personas in parallel.
        
        Returns:
            Dictionary with keys: advisor, compliance, client, general
        """
        logger.info("Generating multi-persona summaries", session_id=session_id)
        
        # Generate all persona summaries in parallel
        tasks = []
        for persona in self.personas:
            task = self.generate_session_summary(
                transcript_segments=transcript_segments,
                sentiment_data=sentiment_data,
                recommendations=recommendations,
                session_id=session_id,
                summary_type="detailed",
                persona=persona
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Build result dictionary
        persona_summaries = {}
        for persona, result in zip(self.personas, results):
            persona_summaries[persona] = result
        
        logger.info(
            "Multi-persona summaries generated",
            persona_count=len(persona_summaries)
        )
        
        return persona_summaries
    
    async def extract_action_items(
        self,
        transcript_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract action items from transcript.
        
        Focus on concrete, actionable tasks with clear ownership.
        """
        logger.info("Extracting action items")
        
        transcript = self._build_transcript_from_segments(transcript_segments)
        
        prompt = f"""Analyze this investment advisor-client conversation and extract all action items.

Conversation:
{transcript}

Identify and return action items in JSON format:
{{
    "action_items": [
        {{
            "action": "Specific, actionable task",
            "responsible": "advisor|client|both",
            "deadline": "Timeframe or date",
            "priority": "high|medium|low",
            "context": "Why this action is needed",
            "dependencies": ["Any prerequisites"],
            "success_criteria": "How to know it's done"
        }}
    ]
}}

GUIDELINES:
- Only include concrete, actionable items (not vague intentions)
- Assign clear responsibility
- Include realistic deadlines
- Prioritize based on urgency and importance
- Provide enough context for follow-through"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant specialized in extracting actionable tasks from conversations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for extraction
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            action_items = result.get("action_items", [])
            
            logger.info(
                "Action items extracted",
                count=len(action_items)
            )
            
            return action_items
            
        except Exception as e:
            logger.error("Failed to extract action items", error=str(e), exc_info=True)
            raise
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for the planner."""
        return {
            "agent_name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "summary_types": self.summary_types,
            "personas": self.personas,
            "output_formats": ["json"],
            "specialized_features": [
                "persona_based_summaries",
                "action_item_extraction",
                "decision_tracking",
                "sentiment_integration",
                "recommendation_integration"
            ]
        }

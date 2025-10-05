"""
Sentiment Analysis Agent

Performs comprehensive sentiment analysis on extracted content.
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

logger = structlog.get_logger(__name__)


class SentimentAgent(BaseAgent):
    """
    MAF-compatible agent for sentiment analysis of extracted content.
    
    Capabilities:
    - Multi-dimensional sentiment analysis (positive, negative, neutral)
    - Emotion detection
    - Tone analysis
    - Speaker/section-based sentiment tracking
    - Confidence scoring
    """
    
    def __init__(self, settings, name: str = "sentiment", description: str = "Analyzes sentiment, emotions, and tone in content"):
        """Initialize the sentiment analysis agent."""
        super().__init__(name=name, description=description)
        
        self.app_settings = settings
        
        # Initialize Azure OpenAI client
        self.client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT
        
        logger.info(f"Initialized {self.name}")
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "sentiment_analysis",
            "emotion_detection",
            "tone_analysis"
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
            # Normalize messages
            normalized_messages = self._normalize_messages(messages)
            
            # Extract content from last message
            last_message = normalized_messages[-1] if normalized_messages else None
            content = last_message.text if last_message and hasattr(last_message, 'text') else ""
            
            # Allow override from kwargs
            content = kwargs.get("content", content)
            
            if not content or len(content.strip()) == 0:
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: No content provided for sentiment analysis")]
                    )]
                )
            
            # Perform sentiment analysis
            result = await self.analyze_sentiment(content, kwargs)
            
            # Return result as ChatMessage
            result_text = json.dumps(result, ensure_ascii=False)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis", error=str(e), exc_info=True)
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
    
    async def analyze_sentiment(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of given content.
        
        Args:
            content: Text content to analyze
            context: Additional context (file type, metadata, etc.)
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        logger.info("Analyzing sentiment", content_length=len(content))
        
        try:
            # Build prompt for sentiment analysis
            prompt = self._build_sentiment_prompt(content, context)
            
            # Call Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert sentiment analyst. Analyze the given content and provide comprehensive sentiment insights in JSON format."
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
            
            logger.info("Sentiment analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze sentiment", error=str(e))
            raise
    
    def _build_sentiment_prompt(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for sentiment analysis."""
        
        context_info = ""
        if context:
            context_info = f"\n\nContext: {context.get('file_type', 'Unknown')} content"
        
        prompt = f"""Analyze the sentiment of the following content and provide a comprehensive analysis in JSON format.{context_info}

Content:
{content}

Provide your analysis in the following JSON structure:
{{
    "overall_sentiment": "positive|negative|neutral|mixed",
    "sentiment_score": <float between -1.0 and 1.0>,
    "confidence": <float between 0.0 and 1.0>,
    "emotions": [
        {{
            "emotion": "joy|sadness|anger|fear|surprise|disgust|trust|anticipation",
            "intensity": <float between 0.0 and 1.0>
        }}
    ],
    "tone": "formal|informal|professional|casual|enthusiastic|somber",
    "key_phrases": ["phrase1", "phrase2", "phrase3"],
    "sentiment_by_section": [
        {{
            "section": "introduction|main|conclusion",
            "sentiment": "positive|negative|neutral",
            "score": <float>
        }}
    ],
    "insights": "Brief summary of sentiment insights"
}}

Focus on providing accurate, nuanced analysis."""
        
        return prompt
    
    async def analyze_conversation_sentiment(
        self,
        transcription: str,
        speaker_diarization: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment in a conversation with speaker tracking.
        
        Args:
            transcription: Full conversation transcription
            speaker_diarization: Speaker information if available
            
        Returns:
            Dictionary containing conversation sentiment analysis
        """
        logger.info("Analyzing conversation sentiment")
        
        try:
            prompt = f"""Analyze the sentiment of the following conversation. Track sentiment for different speakers if distinguishable.

Conversation:
{transcription}

{"Speaker Diarization: " + str(speaker_diarization) if speaker_diarization else ""}

Provide analysis in JSON format:
{{
    "overall_sentiment": "positive|negative|neutral|mixed",
    "sentiment_score": <float between -1.0 and 1.0>,
    "speakers": [
        {{
            "speaker_id": "speaker1|speaker2",
            "sentiment": "positive|negative|neutral",
            "emotions": ["emotion1", "emotion2"],
            "key_points": ["point1", "point2"]
        }}
    ],
    "conversation_dynamics": {{
        "tone_shift": "improved|declined|stable",
        "engagement_level": "high|medium|low",
        "conflict_detected": true|false
    }},
    "insights": "Summary of conversation sentiment"
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in conversation analysis and sentiment detection."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            logger.info("Conversation sentiment analysis completed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze conversation sentiment", error=str(e))
            raise
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for the planner."""
        return {
            "agent_name": self.name,
            "description": self.description,
            "capabilities": [
                "sentiment_analysis",
                "emotion_detection",
                "tone_analysis",
                "conversation_sentiment",
                "speaker_tracking"
            ],
            "output_formats": ["json", "summary"]
        }

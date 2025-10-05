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
    
    def _chunk_content(self, content: str, max_chunk_tokens: int = 30000) -> List[str]:
        """
        Split large content into manageable chunks for processing.
        Uses approximate token count (4 chars ≈ 1 token).
        
        Args:
            content: Text to chunk
            max_chunk_tokens: Maximum tokens per chunk
            
        Returns:
            List of content chunks
        """
        # Approximate: 4 characters ≈ 1 token
        max_chars = max_chunk_tokens * 4
        
        if len(content) <= max_chars:
            return [content]
        
        # Split by paragraphs first (double newlines)
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # If single paragraph is too large, split it further
            if para_length > max_chars:
                # If we have accumulated content, save it
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split large paragraph by sentences
                sentences = para.split('. ')
                para_chunk = []
                para_chunk_len = 0
                
                for sentence in sentences:
                    if para_chunk_len + len(sentence) > max_chars and para_chunk:
                        chunks.append('. '.join(para_chunk) + '.')
                        para_chunk = [sentence]
                        para_chunk_len = len(sentence)
                    else:
                        para_chunk.append(sentence)
                        para_chunk_len += len(sentence)
                
                if para_chunk:
                    chunks.append('. '.join(para_chunk))
            
            # Regular paragraph processing
            elif current_length + para_length > max_chars:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        # Add remaining content
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        logger.info(f"Split content into {len(chunks)} chunks", 
                   total_chars=len(content),
                   avg_chunk_size=len(content) // len(chunks) if chunks else 0)
        
        return chunks
    
    async def analyze_sentiment(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of given content.
        Uses map-reduce pattern for large documents.
        
        Args:
            content: Text content to analyze
            context: Additional context (file type, metadata, objective, etc.)
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        logger.info(
            "Analyzing sentiment",
            content_length=len(content),
            has_objective=bool(context and context.get('objective_context'))
        )
        
        try:
            # Check if content needs chunking (>100k characters ≈ 25k tokens)
            if len(content) > 100000:
                logger.info("Large content detected, using map-reduce pattern")
                return await self._analyze_sentiment_with_map_reduce(content, context)
            
            # Standard sentiment analysis for smaller content
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
    
    async def _analyze_sentiment_with_map_reduce(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use map-reduce pattern for large documents.
        Step 1 (Map): Analyze sentiment in each chunk
        Step 2 (Aggregate): Collect all sentiment data
        Step 3 (Reduce): Synthesize comprehensive sentiment analysis
        """
        # Step 1: Split into chunks
        chunks = self._chunk_content(content, max_chunk_tokens=30000)
        logger.info(f"Processing {len(chunks)} chunks via map-reduce")
        
        # Extract objective context if available
        objective_context = context.get('objective_context') if context else None
        
        # Step 2: Analyze sentiment in each chunk (Map phase)
        chunk_sentiments = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Analyzing sentiment in chunk {i+1}/{len(chunks)}")
            
            # Build prompt with objective context for each chunk
            objective_guidance = ""
            if objective_context:
                objective_guidance = f"""

IMPORTANT - Keep in mind the user's objective:
{objective_context}

While analyzing sentiment in this section, pay special attention to aspects relevant to the above objective."""
            
            prompt = f"""Analyze the sentiment of this section from a larger document. Provide detailed sentiment metrics in JSON format.{objective_guidance}

Document Section:
{chunk[:50000]}

Provide analysis in this JSON structure:
{{
    "section_sentiment": "positive|negative|neutral|mixed",
    "sentiment_score": <float between -1.0 and 1.0>,
    "confidence": <float between 0.0 and 1.0>,
    "dominant_emotions": ["emotion1", "emotion2"],
    "tone": "formal|informal|professional|etc",
    "key_sentiment_phrases": ["phrase1", "phrase2"],
    "sentiment_shifts": ["any notable changes in sentiment"]
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert sentiment analyst. Analyze sentiment accurately and provide structured JSON output."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            chunk_result = json.loads(response.choices[0].message.content)
            chunk_sentiments.append(chunk_result)
        
        # Step 3: Aggregate findings from all chunks
        logger.info(f"Aggregating sentiment data from {len(chunk_sentiments)} chunks")
        
        all_emotions = []
        all_phrases = []
        all_shifts = []
        sentiment_scores = []
        confidence_scores = []
        tones = []
        
        for chunk_data in chunk_sentiments:
            if 'sentiment_score' in chunk_data:
                sentiment_scores.append(chunk_data['sentiment_score'])
            if 'confidence' in chunk_data:
                confidence_scores.append(chunk_data['confidence'])
            if 'dominant_emotions' in chunk_data:
                all_emotions.extend(chunk_data['dominant_emotions'])
            if 'key_sentiment_phrases' in chunk_data:
                all_phrases.extend(chunk_data['key_sentiment_phrases'])
            if 'sentiment_shifts' in chunk_data:
                all_shifts.extend(chunk_data['sentiment_shifts'])
            if 'tone' in chunk_data:
                tones.append(chunk_data['tone'])
        
        # Calculate aggregate metrics
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Determine overall sentiment
        if avg_sentiment > 0.3:
            overall_sentiment = "positive"
        elif avg_sentiment < -0.3:
            overall_sentiment = "negative"
        elif -0.1 <= avg_sentiment <= 0.1:
            overall_sentiment = "neutral"
        else:
            overall_sentiment = "mixed"
        
        # Step 4: Synthesize comprehensive analysis (Reduce phase)
        logger.info("Synthesizing final sentiment analysis")
        
        # Build synthesis context
        synthesis_context = {
            "chunk_count": len(chunks),
            "chunk_sentiments": chunk_sentiments,
            "avg_sentiment_score": avg_sentiment,
            "overall_sentiment": overall_sentiment,
            "all_emotions": list(set(all_emotions)),
            "all_phrases": all_phrases[:20],  # Top 20 phrases
            "sentiment_shifts": all_shifts,
            "tones": list(set(tones))
        }
        
        objective_guidance = ""
        if objective_context:
            objective_guidance = f"""

CRITICAL - Align with the user's objective:
{objective_context}

Ensure your sentiment insights directly support understanding this objective."""
        
        synthesis_prompt = f"""You have analyzed sentiment across {len(chunks)} sections of a large document. 

Aggregate Data:
{json.dumps(synthesis_context, indent=2)}

Synthesize a comprehensive sentiment analysis that:
1. Provides an overall sentiment assessment
2. Identifies key emotions and their intensity
3. Describes the dominant tone
4. Highlights significant sentiment patterns or shifts
5. Provides actionable insights{objective_guidance}

Return your analysis in this JSON structure:
{{
    "overall_sentiment": "positive|negative|neutral|mixed",
    "sentiment_score": <float between -1.0 and 1.0>,
    "confidence": <float between 0.0 and 1.0>,
    "emotions": [
        {{
            "emotion": "emotion_name",
            "intensity": <float between 0.0 and 1.0>
        }}
    ],
    "tone": "description of overall tone",
    "key_phrases": ["phrase1", "phrase2", "phrase3"],
    "sentiment_by_section": [
        {{
            "section": "beginning|middle|end",
            "sentiment": "positive|negative|neutral",
            "score": <float>
        }}
    ],
    "sentiment_progression": "description of how sentiment evolves through document",
    "insights": "comprehensive summary of sentiment analysis with key takeaways",
    "metadata": {{
        "processing_method": "map_reduce",
        "chunks_processed": {len(chunks)},
        "total_length": {len(content)}
    }}
}}"""
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert sentiment analyst. Synthesize comprehensive insights from chunk-level sentiment data."
                },
                {
                    "role": "user",
                    "content": synthesis_prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        final_result = json.loads(response.choices[0].message.content)
        
        logger.info(
            "Map-reduce sentiment analysis completed",
            chunks_processed=len(chunks),
            overall_sentiment=final_result.get('overall_sentiment')
        )
        
        return final_result
    
    def _build_sentiment_prompt(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for sentiment analysis with objective awareness."""
        
        context_info = ""
        if context:
            file_type = context.get('file_type', 'Unknown')
            context_info = f"\n\nContext: {file_type} content"
        
        objective_guidance = ""
        if context and context.get('objective_context'):
            objective_guidance = f"""

IMPORTANT - Keep in mind the user's objective:
{context.get('objective_context')}

While analyzing sentiment, pay special attention to aspects relevant to the above objective."""
        
        prompt = f"""Analyze the sentiment of the following content and provide a comprehensive analysis in JSON format.{context_info}{objective_guidance}

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

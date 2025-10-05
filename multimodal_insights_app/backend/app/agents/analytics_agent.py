"""
Analytics Agent

Performs dynamic, context-aware analytics on extracted content.
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


class AnalyticsAgent(BaseAgent):
    """
    MAF-compatible agent for dynamic analytics and insight extraction.
    
    Capabilities:
    - Context-aware analytics
    - Pattern recognition
    - Product/service analysis
    - Recommendation extraction
    - Next-best-action identification
    - Trend analysis
    - Custom analytical frameworks
    """
    
    def __init__(self, settings, name: str = "analytics", description: str = "Performs dynamic, context-aware analytics and insight extraction"):
        """Initialize the analytics agent."""
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
            "pattern_recognition",
            "product_analysis",
            "recommendation_extraction",
            "next_best_action",
            "trend_analysis"
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
            analysis_focus = kwargs.get("analysis_focus")
            
            if not content or len(content.strip()) == 0:
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: No content provided for analytics")]
                    )]
                )
            
            # Perform analytics
            result = await self.analyze(content, analysis_focus, kwargs)
            
            # Return result as ChatMessage
            result_text = json.dumps(result, ensure_ascii=False)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            
        except Exception as e:
            logger.error(f"Error in analytics", error=str(e), exc_info=True)
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
    
    async def analyze(
        self,
        content: str,
        analysis_focus: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analytics on content.
        
        Args:
            content: Content to analyze
            analysis_focus: Specific areas to focus on (e.g., ["products", "sentiment", "recommendations"])
            context: Additional context (file type, metadata, etc.)
            
        Returns:
            Dictionary containing analytical insights
        """
        logger.info(
            "Performing analytics",
            content_length=len(content),
            focus_areas=analysis_focus
        )
        
        try:
            # Check if content needs chunking (>100k characters ≈ 25k tokens)
            if len(content) > 100000:
                logger.info("Large content detected, using map-reduce pattern")
                return await self._analyze_with_map_reduce(content, analysis_focus, context)
            
            # Standard analytics for smaller content
            prompt = self._build_analytics_prompt(content, analysis_focus, context)
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert analyst skilled at extracting insights, identifying patterns, and providing actionable recommendations from various types of content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
                max_tokens=3000
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Add metadata
            result["analysis_metadata"] = {
                "focus_areas": analysis_focus or ["general"],
                "content_length": len(content),
                "context_type": context.get("file_type") if context else "unknown"
            }
            
            logger.info("Analytics completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to perform analytics", error=str(e))
            raise
    
    async def _analyze_with_map_reduce(
        self,
        content: str,
        analysis_focus: Optional[List[str]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use map-reduce pattern for large documents.
        Step 1 (Map): Analyze each chunk
        Step 2 (Reduce): Synthesize findings into final analysis
        """
        # Step 1: Split into chunks
        chunks = self._chunk_content(content, max_chunk_tokens=30000)
        logger.info(f"Processing {len(chunks)} chunks via map-reduce")
        
        # Step 2: Analyze each chunk (Map phase)
        chunk_analyses = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Analyzing chunk {i+1}/{len(chunks)}")
            
            # Build prompt with objective context
            objective_guidance = ""
            if context and context.get("objective_context"):
                objective_guidance = f"""

IMPORTANT - Keep in mind the user's objective:
{context.get('objective_context')}

While analyzing this section, focus on insights relevant to the above objective."""
            
            focus_text = ', '.join(analysis_focus) if analysis_focus else 'general insights'
            
            prompt = f"""Analyze this section of a larger document. Extract key insights, patterns, and findings.
Focus on: {focus_text}{objective_guidance}

Document Section:
{chunk[:50000]}

Provide your analysis in JSON format with these fields:
- key_insights: Array of important findings
- patterns: Array of identified patterns or trends
- recommendations: Array of actionable suggestions
- metrics: Object with any quantitative findings"""  # Extra safety limit
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert analyst. Extract insights and patterns from document sections."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            chunk_analyses.append(json.loads(response.choices[0].message.content))
        
        # Step 3: Synthesize findings (Reduce phase)
        logger.info(f"Synthesizing {len(chunk_analyses)} chunk analyses")
        
        # Combine all findings
        combined_findings = {
            "key_insights": [],
            "patterns": [],
            "recommendations": [],
            "metrics": {}
        }
        
        for analysis in chunk_analyses:
            if "key_insights" in analysis:
                combined_findings["key_insights"].extend(analysis["key_insights"])
            if "patterns" in analysis:
                combined_findings["patterns"].extend(analysis["patterns"])
            if "recommendations" in analysis:
                combined_findings["recommendations"].extend(analysis["recommendations"])
            if "metrics" in analysis:
                combined_findings["metrics"].update(analysis["metrics"])
        
        # Final synthesis
        objective_guidance = ""
        if context and context.get("objective_context"):
            objective_guidance = f"""

CRITICAL - User's Original Objective:
{context.get('objective_context')}

Your final analysis MUST align with and address all requirements in the above objective.
Structure your response to cover all requested analysis areas and provide insights that directly support the objective."""
        
        synthesis_prompt = f"""You are synthesizing analytics from multiple document sections. Create a cohesive final analysis.

Combined findings from {len(chunk_analyses)} sections:
{json.dumps(combined_findings, indent=2)}{objective_guidance}

Create a comprehensive final analysis that:
1. Identifies the most important insights across all sections
2. Recognizes overarching patterns and trends
3. Provides prioritized, actionable recommendations
4. Eliminates redundancy while preserving key findings
5. Directly addresses the user's objective requirements

Format your response as JSON with these sections:
- executive_summary: High-level overview aligned with objective
- key_findings: Most important insights (prioritized)
- patterns_identified: Trends and patterns across the document
- recommendations: Actionable next steps
- risk_areas: Potential concerns or risks (if applicable)
- metrics: Any quantitative findings"""
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert analyst creating final synthesis reports."
                },
                {
                    "role": "user",
                    "content": synthesis_prompt
                }
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
            max_tokens=3000
        )
        
        result = json.loads(response.choices[0].message.content)
        result["analysis_metadata"] = {
            "focus_areas": analysis_focus or ["general"],
            "content_length": len(content),
            "context_type": context.get("file_type") if context else "unknown",
            "processing_method": "map_reduce",
            "chunks_processed": len(chunks)
        }
        
        return result
    
    async def analyze_conversation(
        self,
        transcription: str,
        analysis_goals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a conversation for specific insights.
        
        Args:
            transcription: Conversation transcription
            analysis_goals: What to analyze (e.g., ["products", "pain_points", "next_actions"])
            
        Returns:
            Dictionary containing conversation analytics
        """
        logger.info("Analyzing conversation")
        
        goals_text = "general conversation analysis"
        if analysis_goals:
            goals_text = ", ".join(analysis_goals)
        
        try:
            prompt = f"""Analyze the following conversation and provide comprehensive insights focusing on: {goals_text}

Conversation:
{transcription}

Provide your analysis in JSON format with the following structure:
{{
    "key_topics": [
        {{
            "topic": "topic name",
            "importance": "high|medium|low",
            "mentions": <count>,
            "summary": "brief summary"
        }}
    ],
    "products_services_mentioned": [
        {{
            "name": "product/service name",
            "context": "how it was discussed",
            "sentiment": "positive|negative|neutral"
        }}
    ],
    "pain_points": [
        {{
            "pain_point": "description",
            "severity": "high|medium|low",
            "potential_solution": "suggested solution"
        }}
    ],
    "recommendations": [
        {{
            "recommendation": "what was recommended",
            "rationale": "why it was recommended",
            "priority": "high|medium|low"
        }}
    ],
    "next_best_actions": [
        {{
            "action": "specific action to take",
            "timeline": "immediate|short-term|long-term",
            "expected_outcome": "what this achieves"
        }}
    ],
    "customer_needs": [
        "need 1",
        "need 2"
    ],
    "opportunities": [
        "opportunity 1",
        "opportunity 2"
    ],
    "risks_concerns": [
        "risk/concern 1",
        "risk/concern 2"
    ],
    "insights": "Overall analytical insights and patterns"
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert business analyst specializing in conversation analysis and customer insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
                max_tokens=3000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            logger.info("Conversation analytics completed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze conversation", error=str(e))
            raise
    
    async def extract_patterns(
        self,
        content: str,
        pattern_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract patterns from content.
        
        Args:
            content: Content to analyze
            pattern_types: Types of patterns to look for
            
        Returns:
            Dictionary containing identified patterns
        """
        logger.info("Extracting patterns")
        
        pattern_focus = pattern_types or ["themes", "trends", "anomalies"]
        
        try:
            prompt = f"""Identify and extract patterns from the following content. Focus on: {', '.join(pattern_focus)}

Content:
{content}

Provide your analysis in JSON format:
{{
    "recurring_themes": [
        {{
            "theme": "theme name",
            "frequency": "high|medium|low",
            "significance": "description"
        }}
    ],
    "trends": [
        {{
            "trend": "trend description",
            "direction": "increasing|decreasing|stable",
            "impact": "description"
        }}
    ],
    "anomalies": [
        {{
            "anomaly": "unusual finding",
            "context": "where it appears",
            "significance": "why it matters"
        }}
    ],
    "correlations": [
        {{
            "correlation": "relationship between X and Y",
            "strength": "strong|moderate|weak"
        }}
    ],
    "insights": "Summary of pattern analysis"
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in pattern recognition and data analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            logger.info("Pattern extraction completed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract patterns", error=str(e))
            raise
    
    def _build_analytics_prompt(
        self,
        content: str,
        analysis_focus: Optional[List[str]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for analytics."""
        
        focus_areas = analysis_focus or ["general insights"]
        context_info = ""
        if context:
            context_info = f"\n\nContext: {context.get('file_type', 'Unknown')} content"
        
        # Check for objective context to align analytics
        objective_text = ""
        if context and context.get("objective_context"):
            objective_text = f"""

IMPORTANT - User's Original Objective:
{context.get('objective_context')}

Your analysis MUST align with and address all key points, analysis areas, and requirements specified in the above objective.
Extract and analyze data specifically requested in the objective, maintaining the same structure and level of detail."""
        
        prompt = f"""Perform comprehensive analytics on the following content. Focus on: {', '.join(focus_areas)}{context_info}{objective_text}

Content:
{content}

Provide your analysis in JSON format with the following structure:
{{
    "executive_summary": "High-level overview of key findings{' aligned with objective requirements' if objective_text else ''}",
    "key_insights": [
        {{
            "insight": "specific insight",
            "supporting_evidence": "evidence from content",
            "importance": "high|medium|low"
        }}
    ],
    "metrics": {{
        "quantitative_findings": ["finding 1", "finding 2"],
        "qualitative_findings": ["finding 1", "finding 2"]
    }},
    "segments": [
        {{
            "segment": "identified segment/category",
            "characteristics": ["char1", "char2"],
            "insights": "segment-specific insights"
        }}
    ],
    "actionable_recommendations": [
        {{
            "recommendation": "specific recommendation",
            "rationale": "why this is recommended",
            "expected_impact": "anticipated outcome",
            "priority": "high|medium|low"
        }}
    ],
    "risks_opportunities": {{
        "risks": ["risk 1", "risk 2"],
        "opportunities": ["opportunity 1", "opportunity 2"]
    }},
    "conclusion": "Overall analytical conclusion"
}}

Be thorough, specific, and data-driven in your analysis{' that directly addresses the objective' if objective_text else ''}."""
        
        return prompt
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for the planner."""
        return {
            "agent_name": self.name,
            "description": self.description,
            "capabilities": [
                "comprehensive_analytics",
                "conversation_analysis",
                "pattern_extraction",
                "product_analysis",
                "sentiment_analytics",
                "recommendation_generation",
                "next_best_action_identification",
                "trend_analysis"
            ],
            "analysis_types": [
                "general",
                "conversation",
                "pattern",
                "business",
                "customer"
            ]
        }

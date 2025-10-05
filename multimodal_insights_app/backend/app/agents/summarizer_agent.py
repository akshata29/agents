"""
Summarizer Agent

Provides flexible summarization with persona-based customization.
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

logger = structlog.get_logger(__name__)


class SummarizerAgent(BaseAgent):
    """
    MAF-compatible agent for flexible content summarization.
    
    Capabilities:
    - Multi-level summaries (brief, detailed, comprehensive)
    - Persona-based summaries (executive, technical, general)
    - Multi-document synthesis
    - Key points extraction
    - Customizable formats
    """
    
    def __init__(self, settings, name: str = "summarizer", description: str = "Creates flexible summaries with persona-based customization"):
        """Initialize the summarizer agent."""
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
            "brief_summary",
            "detailed_summary",
            "comprehensive_summary",
            "persona_customization"
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
            summary_type = kwargs.get("summary_type", "detailed")
            persona = kwargs.get("persona", "general")
            focus_areas = kwargs.get("focus_areas")
            objective_context = kwargs.get("objective_context")
            
            if not content or len(content.strip()) == 0:
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: No content provided for summarization")]
                    )]
                )
            
            # Perform summarization
            result = await self.summarize(
                content, 
                summary_type, 
                persona, 
                focus_areas,
                objective_context
            )
            
            # Return result as ChatMessage
            result_text = json.dumps(result, ensure_ascii=False)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            
        except Exception as e:
            logger.error(f"Error in summarization", error=str(e), exc_info=True)
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
    
    async def summarize(
        self,
        content: str,
        summary_type: Literal["brief", "detailed", "comprehensive"] = "detailed",
        persona: Literal["executive", "technical", "general"] = "general",
        focus_areas: Optional[List[str]] = None,
        objective_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate summary of content using map-reduce for large documents.
        
        Args:
            content: Content to summarize
            summary_type: Level of detail
            persona: Target audience persona
            focus_areas: Specific areas to focus on
            objective_context: Original user objective to align with
            
        Returns:
            Dictionary containing summary and metadata
        """
        logger.info(
            "Generating summary",
            summary_type=summary_type,
            persona=persona,
            content_length=len(content),
            has_objective=bool(objective_context)
        )
        
        try:
            # Check if content needs chunking (>100k characters ≈ 25k tokens)
            if len(content) > 100000:
                logger.info("Large content detected, using map-reduce pattern")
                return await self._summarize_with_map_reduce(
                    content, summary_type, persona, focus_areas, objective_context
                )
            
            # Standard summarization for smaller content
            prompt = self._build_summary_prompt(
                content,
                summary_type,
                persona,
                focus_areas,
                objective_context
            )
            
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
                temperature=0.5,
                max_tokens=self._get_max_tokens_for_type(summary_type)
            )
            
            summary_text = response.choices[0].message.content
            
            result = {
                "summary": summary_text,
                "summary_type": summary_type,
                "persona": persona,
                "focus_areas": focus_areas or [],
                "original_length": len(content),
                "summary_length": len(summary_text),
                "compression_ratio": len(summary_text) / len(content) if content else 0
            }
            
            logger.info("Summary generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate summary", error=str(e))
            raise
    
    async def _summarize_with_map_reduce(
        self,
        content: str,
        summary_type: str,
        persona: str,
        focus_areas: Optional[List[str]],
        objective_context: Optional[str]
    ) -> Dict[str, Any]:
        """
        Use map-reduce pattern for large documents.
        Step 1 (Map): Summarize each chunk
        Step 2 (Reduce): Combine chunk summaries into final summary
        """
        # Step 1: Split into chunks
        chunks = self._chunk_content(content, max_chunk_tokens=30000)
        logger.info(f"Processing {len(chunks)} chunks via map-reduce")
        
        # Step 2: Summarize each chunk (Map phase)
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Summarizing chunk {i+1}/{len(chunks)}")
            
            # Build prompt with objective context for each chunk
            objective_guidance = ""
            if objective_context:
                objective_guidance = f"""

IMPORTANT - Keep in mind the user's objective:
{objective_context}

While summarizing this section, extract information relevant to the above objective."""
            
            focus_guidance = ""
            if focus_areas:
                focus_guidance = f"\n\nFocus on: {', '.join(focus_areas)}"
            
            prompt = f"""Summarize this section of a larger document. Focus on key points and maintain important details.{objective_guidance}{focus_guidance}

Document Section:
{chunk[:50000]}"""  # Extra safety limit
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise document summarizer. Extract key information while maintaining accuracy."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            chunk_summaries.append(response.choices[0].message.content)
        
        # Step 3: Combine summaries (Reduce phase)
        logger.info(f"Combining {len(chunk_summaries)} chunk summaries")
        combined = "\n\n---\n\n".join(chunk_summaries)
        
        # Final synthesis
        final_prompt = self._build_summary_prompt(
            combined,
            summary_type,
            persona,
            focus_areas,
            objective_context,
            is_synthesis=True
        )
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": self._get_persona_system_message(persona)
                },
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],
            temperature=0.5,
            max_tokens=self._get_max_tokens_for_type(summary_type)
        )
        
        summary_text = response.choices[0].message.content
        
        return {
            "summary": summary_text,
            "summary_type": summary_type,
            "persona": persona,
            "focus_areas": focus_areas or [],
            "original_length": len(content),
            "summary_length": len(summary_text),
            "compression_ratio": len(summary_text) / len(content) if content else 0,
            "processing_method": "map_reduce",
            "chunks_processed": len(chunks)
        }
    
    async def create_multiple_summaries(
        self,
        content: str,
        summary_configs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple summaries with different configurations.
        
        Args:
            content: Content to summarize
            summary_configs: List of configuration dicts with keys:
                - summary_type
                - persona
                - focus_areas (optional)
                
        Returns:
            List of summary results
        """
        logger.info(
            "Generating multiple summaries",
            count=len(summary_configs)
        )
        
        tasks = []
        for config in summary_configs:
            task = self.summarize(
                content,
                summary_type=config.get("summary_type", "detailed"),
                persona=config.get("persona", "general"),
                focus_areas=config.get("focus_areas")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any exceptions
        summaries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Summary {i} failed", error=str(result))
            else:
                summaries.append(result)
        
        return summaries
    
    async def synthesize_multi_document(
        self,
        documents: List[Dict[str, str]],
        synthesis_goal: str
    ) -> Dict[str, Any]:
        """
        Synthesize insights from multiple documents.
        
        Args:
            documents: List of dicts with 'title' and 'content'
            synthesis_goal: What to focus on in synthesis
            
        Returns:
            Dictionary containing synthesized summary
        """
        logger.info(
            "Synthesizing multiple documents",
            document_count=len(documents)
        )
        
        try:
            # Build combined prompt
            docs_text = "\n\n---\n\n".join([
                f"Document: {doc.get('title', 'Untitled')}\n{doc.get('content', '')}"
                for doc in documents
            ])
            
            prompt = f"""Synthesize the following documents to provide insights on: {synthesis_goal}

{docs_text}

Provide a comprehensive synthesis that:
1. Identifies common themes and patterns
2. Highlights unique insights from each document
3. Provides an integrated analysis
4. Draws meaningful conclusions"""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert analyst skilled at synthesizing insights from multiple sources."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            synthesis = response.choices[0].message.content
            
            result = {
                "synthesis": synthesis,
                "document_count": len(documents),
                "synthesis_goal": synthesis_goal
            }
            
            logger.info("Multi-document synthesis completed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to synthesize documents", error=str(e))
            raise
    
    def _build_summary_prompt(
        self,
        content: str,
        summary_type: str,
        persona: str,
        focus_areas: Optional[List[str]],
        objective_context: Optional[str] = None,
        is_synthesis: bool = False
    ) -> str:
        """Build prompt for summarization."""
        
        length_guidance = {
            "brief": "1-2 paragraphs",
            "detailed": "3-5 paragraphs with key sections",
            "comprehensive": "Detailed multi-section summary covering all aspects requested in the objective"
        }
        
        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nFocus specifically on: {', '.join(focus_areas)}"
        
        objective_text = ""
        if objective_context:
            objective_text = f"""

IMPORTANT - User's Original Objective:
{objective_context}

Your summary MUST align with and address all key points, analysis areas, and requirements specified in the above objective. 
Structure your response to cover each section requested, maintain the same level of detail, and include all requested outputs."""
        
        if is_synthesis:
            prompt = f"""You are synthesizing multiple section summaries into a final cohesive summary.

The following are summaries of different sections of a large document:

{content}

Create a unified, well-structured {summary_type} summary ({length_guidance.get(summary_type, 'appropriate length')}).{focus_text}{objective_text}

Ensure the final summary:
1. Integrates insights from all sections coherently
2. Maintains logical flow and structure
3. Eliminates redundancy while preserving important details
4. Addresses all aspects of the user's objective"""
        else:
            prompt = f"""Summarize the following content.

Length: {length_guidance.get(summary_type, "moderate")}
Audience: {persona}
{focus_text}{objective_text}

Content:
{content}

Provide a clear, well-structured summary appropriate for the specified audience{' that fully addresses the objective requirements' if objective_context else ''}."""
        
        return prompt
    
    def _get_persona_system_message(self, persona: str) -> str:
        """Get system message for persona."""
        messages = {
            "executive": "You are a business analyst creating summaries for C-level executives. Focus on strategic insights, key decisions, and business impact.",
            "technical": "You are a technical writer creating summaries for engineers and technical professionals. Include technical details, methodologies, and implementation aspects.",
            "general": "You are a skilled communicator creating summaries for a general audience. Use clear language and explain concepts accessibly."
        }
        return messages.get(persona, messages["general"])
    
    def _get_max_tokens_for_type(self, summary_type: str) -> int:
        """Get max tokens based on summary type."""
        tokens = {
            "brief": 500,
            "detailed": 1500,
            "comprehensive": 3000
        }
        return tokens.get(summary_type, 1500)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for the planner."""
        return {
            "agent_name": self.name,
            "description": self.description,
            "capabilities": [
                "brief_summary",
                "detailed_summary",
                "comprehensive_summary",
                "persona_based_summary",
                "multi_document_synthesis",
                "key_points_extraction"
            ],
            "personas": ["executive", "technical", "general"],
            "summary_types": ["brief", "detailed", "comprehensive"]
        }

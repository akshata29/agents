"""
Summarizer Agent - Focused on creating concise summaries from provided context

Microsoft Agent Framework compliant agent for summarization tasks.
Does NOT add extra structure or analysis - just summarizes what's provided.
"""

from typing import Any, Dict, List, Optional
import structlog

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentThread

logger = structlog.get_logger(__name__)


class SummarizerAgent(BaseAgent):
    """
    Agent specialized in summarizing information based on context and instructions.
    Does NOT add extra structure or analysis - just summarizes what's provided.
    """
    
    SYSTEM_PROMPT = """You are a focused summarization specialist. Your role is to create concise, 
clear summaries based on the context and instructions provided.

CRITICAL RULES:
- Provide ONLY what is requested - do not add extra sections or structure
- If asked for "sentiment summary", focus ONLY on sentiment analysis
- If asked for "news summary", focus ONLY on summarizing the news
- Do NOT add Company Overview, Investment Highlights, or other unrequested sections
- Keep summaries brief, factual, and to the point
- Base your summary strictly on the provided context

Be concise, focused, and directly address the summarization task."""

    def __init__(
        self,
        name: str = "SummarizerAgent",
        description: str = "Summarization and synthesis specialist",
        chat_client: Any = None,
        model: str = "gpt-4o"
    ):
        """Initialize Summarizer Agent."""
        logger.info(
            "SummarizerAgent.__init__ called",
            name=name,
            has_chat_client=chat_client is not None,
            model=model
        )
        
        super().__init__(name=name, description=description)
        
        # Store custom attributes
        self.chat_client = chat_client
        self.model = model
        self.system_prompt = self.SYSTEM_PROMPT
        
        logger.info(
            "SummarizerAgent initialized",
            agent_name=self.name
        )
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "summarize_information",
            "generate_sentiment_summary",
            "create_news_summary",
            "synthesize_findings",
            "aggregate_data"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """
        Execute summarization task (MAF required method).
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional context (task, session_context, dependency_artifacts, etc.)
            
        Returns:
            AgentRunResponse containing the summary
        """
        # Normalize input messages to a list
        normalized_messages = self._normalize_messages(messages)
        
        if not normalized_messages:
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text="Hello! I'm a summarization agent. Please provide context to summarize.")]
            )
            return AgentRunResponse(messages=[response_message])
        
        # Get context from kwargs
        context = kwargs.get("context", {})
        
        # Extract task from last message
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        
        logger.info(
            "SummarizerAgent starting",
            task=task[:200],
            has_session_context=bool(context.get("session_context")),
            has_dependency_artifacts=bool(context.get("dependency_artifacts")),
            context_keys=list(context.keys())
        )
        
        try:
            # Build the summary prompt with context
            summary_prompt = self._build_summary_prompt(task, context)
            
            # Create messages for the LLM
            chat_messages = [
                ChatMessage(role=Role.SYSTEM, contents=[TextContent(text=self.system_prompt)]),
                ChatMessage(role=Role.USER, contents=[TextContent(text=summary_prompt)])
            ]
            
            # Call the chat client
            if not self.chat_client:
                error_msg = "No chat client configured for SummarizerAgent"
                logger.error(error_msg)
                return AgentRunResponse(messages=[
                    ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=f"Error: {error_msg}")])
                ])
            
            logger.info("Calling chat client for summary generation")
            response = await self.chat_client.get_response(messages=chat_messages, temperature=0.3, max_tokens=2000)
            
            summary_text = response.text if hasattr(response, 'text') else str(response)
            
            logger.info(
                "Summary generated successfully",
                summary_length=len(summary_text)
            )
            
            # Return the response
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text=summary_text)]
            )
            
            return AgentRunResponse(messages=[response_message])
            
        except Exception as e:
            error_msg = f"Error generating summary: {str(e)}"
            logger.error("SummarizerAgent error", error=str(e), exc_info=True)
            
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text=error_msg)]
            )
            return AgentRunResponse(messages=[response_message])
    
    def _normalize_messages(
        self, messages: str | ChatMessage | list[str] | list[ChatMessage] | None
    ) -> list[ChatMessage]:
        """Normalize various message formats to a list of ChatMessage objects."""
        if messages is None:
            return []
        
        # If already a list
        if isinstance(messages, list):
            result = []
            for msg in messages:
                if isinstance(msg, ChatMessage):
                    result.append(msg)
                elif isinstance(msg, str):
                    result.append(ChatMessage(role=Role.USER, contents=[TextContent(text=msg)]))
            return result
        
        # Single ChatMessage
        if isinstance(messages, ChatMessage):
            return [messages]
        
        # Single string
        if isinstance(messages, str):
            return [ChatMessage(role=Role.USER, contents=[TextContent(text=messages)])]
        
        return []
    
    def _build_summary_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """
        Build the prompt for summarization based on available context.
        
        Priority:
        1. session_context (all previous steps) - for synthesis tasks
        2. dependency_artifacts (direct dependencies)
        3. artifacts (legacy)
        """
        company_name = context.get("company_name", "the company")
        
        prompt_parts = [
            f"TASK: {task}",
            f"COMPANY: {company_name}",
            "",
            "INSTRUCTIONS:",
            "- Provide a concise, focused summary that directly addresses the task",
            "- DO NOT add extra sections, structure, or analysis beyond what's requested",
            "- If asked for 'sentiment summary', focus ONLY on sentiment analysis",
            "- If asked for 'news summary', focus ONLY on summarizing the news",
            "- Keep it brief and to the point",
            "",
        ]
        
        # Priority 1: Check for session_context (all previous steps)
        session_context = context.get("session_context", [])
        if session_context:
            logger.info(f"Using session_context with {len(session_context)} previous steps")
            prompt_parts.append("CONTEXT FROM PREVIOUS STEPS:")
            prompt_parts.append("")
            
            for step_data in session_context:
                step_num = step_data.get("step_number", "?")
                agent = step_data.get("agent", "unknown")
                action = step_data.get("action", "unknown action")
                tools = step_data.get("tools", [])
                output = step_data.get("output", "")
                
                prompt_parts.append(f"Step {step_num} ({agent} - {action}):")
                if tools:
                    prompt_parts.append(f"Tools used: {', '.join(tools)}")
                prompt_parts.append(f"{output}")
                prompt_parts.append("")
            
            prompt_parts.append("---")
            prompt_parts.append("")
        
        # Priority 2: Check for dependency_artifacts (direct dependencies)
        elif context.get("dependency_artifacts"):
            dependency_artifacts = context.get("dependency_artifacts", [])
            logger.info(f"Using dependency_artifacts with {len(dependency_artifacts)} dependencies")
            prompt_parts.append("CONTEXT FROM DEPENDENCIES:")
            prompt_parts.append("")
            
            for artifact in dependency_artifacts:
                agent = artifact.get("agent", "unknown")
                action = artifact.get("action", "")
                content = artifact.get("content", "")
                tools = artifact.get("tools", [])
                
                prompt_parts.append(f"From {agent} ({action}):")
                if tools:
                    prompt_parts.append(f"Tools used: {', '.join(tools)}")
                prompt_parts.append(f"{content}")
                prompt_parts.append("")
            
            prompt_parts.append("---")
            prompt_parts.append("")
        
        # Priority 3: Legacy artifacts
        elif context.get("artifacts"):
            artifacts = context.get("artifacts", [])
            logger.info(f"Using legacy artifacts with {len(artifacts)} items")
            prompt_parts.append("CONTEXT:")
            prompt_parts.append("")
            
            for artifact in artifacts:
                if isinstance(artifact, dict):
                    content = artifact.get("content", str(artifact))
                else:
                    content = str(artifact)
                prompt_parts.append(content)
                prompt_parts.append("")
            
            prompt_parts.append("---")
            prompt_parts.append("")
        else:
            logger.warning("No context found - generating summary with minimal information")
            prompt_parts.append("CONTEXT: No additional context provided.")
            prompt_parts.append("")
        
        # Final instruction
        prompt_parts.append("SUMMARY:")
        prompt_parts.append("Based on the context above, provide a clear and concise summary that addresses the task.")
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def get_tools_info() -> Dict[str, Dict[str, str]]:
        """Get information about available tools/functions for this agent."""
        return {
            "summarize_information": {
                "description": "Create concise summaries from provided context",
                "parameters": "context: str, task: str"
            },
            "generate_sentiment_summary": {
                "description": "Analyze and summarize sentiment from news/data",
                "parameters": "context: str, company: str"
            },
            "create_news_summary": {
                "description": "Summarize news articles and market updates",
                "parameters": "news_data: str, company: str"
            },
            "synthesize_findings": {
                "description": "Combine insights from multiple sources into a coherent summary",
                "parameters": "context: str, sources: list"
            }
        }
    
    async def process(self, task: str, context: Dict[str, Any] = None) -> str:
        """
        Legacy method for YAML-based workflow compatibility.
        This is called by the orchestrator with the context dict.
        """
        context = context or {}
        logger.info(
            "SummarizerAgent.process() called",
            task=task[:100] if task else "None",
            context_keys=list(context.keys()),
            has_session_context=bool(context.get("session_context")),
            has_dependency_artifacts=bool(context.get("dependency_artifacts")),
            agent_name=self.name
        )
        
        # Pass context via kwargs so run() can access it
        response = await self.run(messages=task, thread=None, context=context)
        result = response.messages[-1].text if response.messages else ""
        logger.info(
            "SummarizerAgent.process() completed",
            result_length=len(result),
            agent_name=self.name
        )
        return result



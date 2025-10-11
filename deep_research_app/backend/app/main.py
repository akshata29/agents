"""
Deep Research Backend API

FastAPI backend for the Deep Research application using MAF.
Provides REST and WebSocket endpoints for workflow execution, monitoring, and real-time updates.
"""

import asyncio
import os
import sys
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncIterable, Sequence, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import structlog
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[INFO] Loaded environment from {env_path}")
else:
    print(f"[WARNING] No .env file found at {env_path}")

# Add framework to path - add the parent directory that contains 'framework' package
framework_parent = Path(__file__).parent.parent.parent.parent
if str(framework_parent) not in sys.path:
    sys.path.insert(0, str(framework_parent))

# Now import from local MAF utilities
from app.maf import (
    WorkflowEngine,
    WorkflowStatus,
    TaskStatus,
    MagenticOrchestrator,
    AgentRegistry,
    ObservabilityService,
    MCPClient,
    Settings,
)

# Import our advanced services
from app.services.advanced_prompting_service import AdvancedPromptingService

# Microsoft Agent Framework imports
from agent_framework import (
    BaseAgent, AgentRunResponse, AgentRunResponseUpdate,
    AgentThread, ChatMessage, Role, TextContent
)

# Azure OpenAI and Tavily imports
from openai import AzureOpenAI
from tavily import TavilyClient

# Import services
from .services.tavily_search_service import (
    TavilySearchService,
    Source,
    ensure_sources_dict,
)
from .services.export_service import ExportService, get_export_service
from .services.file_handler import FileHandler
from .services.document_intelligence_service import DocumentIntelligenceService
from .services.document_research_service import DocumentResearchService

# Import configuration
from .config.research_config import (
    DEPTH_CONFIGS, DEPTH_PROMPTS,
    get_depth_config, get_depth_prompts, get_research_aspects
)

# Import validation service
from .services.research_validation import get_validator, ValidationResult

# Import MAF workflow module
from . import maf_workflow

# Import advanced research techniques
from .advanced_research import (
    assess_source_quality, filter_sources_by_tier,
    analyze_research_gaps, multi_perspective_analysis,
    fact_check_claims, SourceTier, PerspectiveRole
)
# Import routers
from app.routers import sessions
from app.routers import files as files_router

logger = structlog.get_logger(__name__)

# Global state
workflow_engine: Optional[WorkflowEngine] = None
agent_registry: Optional[AgentRegistry] = None
orchestrator: Optional[MagenticOrchestrator] = None
active_executions: Dict[str, Dict[str, Any]] = {}
websocket_connections: List[WebSocket] = []

# File handling services
file_handler: Optional[FileHandler] = None
doc_intelligence: Optional[DocumentIntelligenceService] = None
doc_research_service: Optional[DocumentResearchService] = None


# Helper function to prepare document context
async def prepare_document_context(document_ids: List[str]) -> Optional[Dict[str, Any]]:
    """Prepare document context for research from selected document IDs."""
    if not document_ids or not doc_research_service:
        return None

    try:
        logger.info("Preparing document context", document_count=len(document_ids))

        # Get document statistics
        stats = await doc_research_service.get_document_stats(document_ids)

        # Retrieve all document content
        document_sources: List[Dict[str, Any]] = []
        document_context_parts: List[str] = []

        for doc_id in document_ids:
            doc_source = await doc_research_service._get_document_source(doc_id, "")
            if doc_source:
                document_sources.extend(ensure_sources_dict(doc_source["sources"]))
                document_context_parts.append(doc_source["context"])

        # Combine document context
        document_context = "\n\n---\n\n".join(document_context_parts) if document_context_parts else ""
        logger.info(
            "Document context prepared",
            total_documents=len(document_ids),
            total_pages=stats.get("total_pages", 0),
            total_words=stats.get("total_words", 0),
            context_length=len(document_context),
        )

        return {
            "document_context": document_context,
            "document_sources": document_sources,
            "document_stats": stats,
        }

    except Exception as e:
        logger.error("Failed to prepare document context", error=str(e))
        return None


# Serialization helpers
def sanitize_for_json(value: Any) -> Any:
    """Recursively convert values into JSON-serializable structures."""
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            if key == "raw_response":
                continue
            cleaned[key] = sanitize_for_json(item)
        return cleaned

    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_json(item) for item in value]

    if isinstance(value, AgentRunResponse):
        if hasattr(value, "model_dump"):
            return sanitize_for_json(value.model_dump())
        if hasattr(value, "dict"):
            return sanitize_for_json(value.dict())
        return str(value)

    if isinstance(value, AgentRunResponseUpdate):
        if hasattr(value, "model_dump"):
            return sanitize_for_json(value.model_dump())
        if hasattr(value, "dict"):
            return sanitize_for_json(value.dict())
        return str(value)

    if hasattr(value, "isoformat") and callable(getattr(value, "isoformat")):
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


# Custom Agent Classes
class AIResearchAgent(BaseAgent):
    """AI-powered research agent using Azure OpenAI (Microsoft Agent Framework compliant)."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        azure_client: AzureOpenAI,
        model: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        # Initialize Microsoft Agent Framework's BaseAgent
        super().__init__(name=name, description=description)
        
        # Store our custom attributes
        self.agent_id = agent_id
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent and return a complete response.
        
        This is the required method for Microsoft Agent Framework compatibility.
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional keyword arguments
            
        Returns:
            AgentRunResponse containing the agent's reply
        """
        # Normalize input messages to a list
        normalized_messages = self._normalize_messages(messages)
        
        if not normalized_messages:
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text="Hello! I'm an AI research agent. How can I help you?")]
            )
        else:
            # Get context from kwargs
            context = kwargs.get('context', {})
            
            # Process the last message
            last_message = normalized_messages[-1]
            message_content = last_message.text if hasattr(last_message, 'text') else str(last_message)
            
            # Build prompt with context
            prompt = self._build_prompt(message_content, context)
            
            try:
                # Call Azure OpenAI
                response = await asyncio.to_thread(
                    self.azure_client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                result_text = response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"AI processing failed", agent=self.agent_id, error=str(e))
                result_text = f"AI error: {str(e)}"
            
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text=result_text)]
            )
        
        # Notify thread of new messages if provided
        if thread:
            await self._notify_thread_of_new_messages(thread, normalized_messages, response_message)
        
        return AgentRunResponse(messages=[response_message])
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Execute the agent and yield streaming response updates.
        
        This is the required method for Microsoft Agent Framework compatibility.
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional keyword arguments
            
        Yields:
            AgentRunResponseUpdate objects containing chunks of the response
        """
        # For now, implement non-streaming version by yielding complete response
        # Future: Implement true streaming with Azure OpenAI streaming API
        response = await self.run(messages, thread=thread, **kwargs)
        
        # Yield the complete response as a single update
        for message in response.messages:
            if message.contents:
                for content in message.contents:
                    if isinstance(content, TextContent):
                        yield AgentRunResponseUpdate(
                            contents=[content],
                            role=Role.ASSISTANT
                        )
    
    def _build_prompt(self, message: str, context: Dict[str, Any]) -> str:
        """Build context-aware prompt."""
        prompt_parts = [message]
        for key, value in context.items():
            if key not in ['task', 'agent_id'] and value:
                prompt_parts.append(f"\n{key.replace('_', ' ').title()}: {value}")
        return "\n".join(prompt_parts)
    
    async def process(self, message, context: Dict[str, Any] = None) -> str:
        """Legacy method for YAML-based workflow compatibility."""
        context = context or {}
        
        # Handle both string and AgentMessage object
        if hasattr(message, 'content'):
            # It's an AgentMessage object
            task = message.content
        else:
            # It's a string
            task = str(message)
        
        response = await self.run(messages=task, thread=None, context=context)
        return response.messages[-1].text if response.messages else ""


class TavilySearchAgent(BaseAgent):
    """Research agent with Tavily web search capabilities (Microsoft Agent Framework compliant)."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        tavily_client: TavilyClient,
        azure_client: AzureOpenAI,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        # Initialize Microsoft Agent Framework's BaseAgent
        super().__init__(name=name, description=description)
        
        # Store our custom attributes
        self.agent_id = agent_id
        self.tavily = tavily_client
        self.azure_client = azure_client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent and return a complete response.
        
        This is the required method for Microsoft Agent Framework compatibility.
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional keyword arguments
            
        Returns:
            AgentRunResponse containing the agent's reply
        """
        # Normalize input messages to a list
        normalized_messages = self._normalize_messages(messages)
        
        if not normalized_messages:
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text="Hello! I'm a research agent with web search capabilities. What would you like me to research?")]
            )
        else:
            # Get context from kwargs
            context = kwargs.get('context', {})
            
            # Process the last message
            last_message = normalized_messages[-1]
            message_content = last_message.text if hasattr(last_message, 'text') else str(last_message)
            
            try:
                # Use the message content as the task
                task = message_content
                
                # Build search query - extract concise query from potentially long instructions
                # Tavily has a 400 character limit, so we need to be smart about this
                if len(task) > 350:
                    # Use AI to extract the core search query from verbose instructions
                    query_extraction_response = await asyncio.to_thread(
                        self.azure_client.chat.completions.create,
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "Extract a concise search query (max 300 chars) from the user's research request. Return ONLY the search query, nothing else."},
                            {"role": "user", "content": f"Extract search query from: {task[:800]}"}
                        ],
                        temperature=0.3,  # Lower temperature for extraction task
                        max_tokens=100  # Short output for query extraction
                    )
                    search_query = query_extraction_response.choices[0].message.content.strip()
                    # Safety check - if still too long, truncate intelligently
                    if len(search_query) > 350:
                        # Try to find the actual topic after common phrases
                        for phrase in ["related to:", "regarding:", "about:", "on:"]:
                            if phrase in search_query.lower():
                                search_query = search_query.split(phrase, 1)[1].strip()
                                break
                        search_query = search_query[:350]
                else:
                    search_query = task.strip()
                
                if not search_query:
                    raise ValueError("Empty search query")
                
                logger.info(f"🔍 Tavily search query ({len(search_query)} chars): {search_query[:100]}...")
                
                # Perform web search
                search_results = await asyncio.to_thread(
                    self.tavily.search,
                    query=search_query,
                    max_results=context.get('max_sources', 5)
                )
                
                # Synthesize with AI
                sources_text = "\n\n".join([
                    f"Source: {r['title']}\nURL: {r['url']}\n{r['content']}"
                    for r in search_results.get('results', [])
                ])
                
                synthesis_prompt = f"""Based on the following web search results, {task}

Search Results:
{sources_text}

Provide a comprehensive, well-structured response."""
                
                response = await asyncio.to_thread(
                    self.azure_client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert researcher who synthesizes information from multiple sources."},
                        {"role": "user", "content": synthesis_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                result_text = response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"Research processing failed", agent=self.agent_id, error=str(e))
                result_text = f"Research error: {str(e)}"
            
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text=result_text)]
            )
        
        # Notify thread of new messages if provided
        if thread:
            await self._notify_thread_of_new_messages(thread, normalized_messages, response_message)
        
        return AgentRunResponse(messages=[response_message])
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Execute the agent and yield streaming response updates.
        
        This is the required method for Microsoft Agent Framework compatibility.
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional keyword arguments
            
        Yields:
            AgentRunResponseUpdate objects containing chunks of the response
        """
        # For now, implement non-streaming version by yielding complete response
        # Future: Implement true streaming with Azure OpenAI streaming API
        response = await self.run(messages, thread=thread, **kwargs)
        
        # Yield the complete response as a single update
        for message in response.messages:
            if message.contents:
                for content in message.contents:
                    if isinstance(content, TextContent):
                        yield AgentRunResponseUpdate(
                            contents=[content],
                            role=Role.ASSISTANT
                        )
    
    async def process(self, message, context: Dict[str, Any] = None) -> str:
        """Legacy method for YAML-based workflow compatibility."""
        context = context or {}
        
        # Handle both string and AgentMessage object
        if hasattr(message, 'content'):
            # It's an AgentMessage object
            task = message.content
        else:
            # It's a string
            task = str(message)
        
        response = await self.run(messages=task, thread=None, context=context)
        return response.messages[-1].text if response.messages else ""


async def setup_research_agents(agent_registry: AgentRegistry, settings: Settings):
    """Setup AI-powered research agents."""
    logger.info("Setting up research agents")
    
    # Get credentials from environment
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "chat4o")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if not all([azure_endpoint, azure_api_key]):
        logger.warning("Azure OpenAI credentials not found, agents may not work properly")
        return
    
    # Initialize clients
    azure_client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    )
    
    tavily_client = TavilyClient(api_key=tavily_api_key) if tavily_api_key else None
    
    # Register agents
    try:
        planner = AIResearchAgent(
            agent_id="planner",
            name="Research Planner",
            description="AI agent that creates comprehensive research plans",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="You are an expert research planner. Create detailed, actionable research plans."
        )
        await agent_registry.register_agent("planner", planner)
        logger.info("Registered agent", agent_id="planner")
    except ValueError:
        logger.info("Agent already registered", agent_id="planner")
    
    if tavily_client:
        try:
            researcher = TavilySearchAgent(
                agent_id="researcher",
                name="Web Researcher",
                description="AI agent that performs web research",
                tavily_client=tavily_client,
                azure_client=azure_client,
                model=azure_deployment
            )
            await agent_registry.register_agent("researcher", researcher)
            logger.info("Registered agent", agent_id="researcher")
        except ValueError:
            logger.info("Agent already registered", agent_id="researcher")
    
    try:
        writer = AIResearchAgent(
            agent_id="writer",
            name="Report Writer",
            description="AI agent that writes research reports",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="You are an expert research writer. Create clear, comprehensive reports."
        )
        await agent_registry.register_agent("writer", writer)
        logger.info("Registered agent", agent_id="writer")
    except ValueError:
        logger.info("Agent already registered", agent_id="writer")
    
    try:
        reviewer = AIResearchAgent(
            agent_id="reviewer",
            name="Report Editor",
            description="AI agent that enhances and refines research reports",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="You are an expert research editor. Your job is to take research content and enhance it - improve clarity, fix formatting, ensure logical flow, add structure, but PRESERVE all the research findings and content. Return the IMPROVED REPORT, not feedback on it."
        )
        await agent_registry.register_agent("reviewer", reviewer)
        logger.info("Registered agent", agent_id="reviewer")
    except ValueError:
        logger.info("Agent already registered", agent_id="reviewer")
    
    try:
        summarizer = AIResearchAgent(
            agent_id="summarizer",
            name="Executive Summarizer",
            description="AI agent that extracts key insights and creates executive summary",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="You are an expert at extracting key insights from research reports and creating compelling executive summaries. Return a concise 2-3 paragraph executive summary of the KEY FINDINGS, not meta-commentary about the report quality."
        )
        await agent_registry.register_agent("summarizer", summarizer)
        logger.info("Registered agent", agent_id="summarizer")
    except ValueError:
        logger.info("Agent already registered", agent_id="summarizer")
    
    logger.info("Research agents setup complete")


async def execute_research_programmatically(
    agent_registry: AgentRegistry,
    orchestrator_instance: MagenticOrchestrator,
    execution_id: str,
    topic: str,
    depth: str,
    max_sources: int,
    include_citations: bool,
    document_context_data: Optional[Dict[str, Any]] = None,
    model_deployment: Optional[str] = None
) -> Dict[str, Any]:
    """Execute research using programmatic orchestration with native MAF builders.

    This implementation now relies on the local ``app.maf`` orchestrator to
    orchestrate sequential and concurrent phases without the legacy shim classes.

    Args:
        document_context_data: Optional document context with document_context,
            document_sources, and document_stats
    """
    results = {}
    
    # Extract document context if available
    document_context = ""
    document_sources = []
    has_documents = False
    
    if document_context_data:
        document_context = document_context_data.get("document_context", "")
        document_sources = document_context_data.get("document_sources", [])
        has_documents = len(document_context) > 0
        logger.info(
            f"📄 Research will include document context",
            doc_words=document_context_data.get("document_stats", {}).get("total_words", 0),
            doc_pages=document_context_data.get("document_stats", {}).get("total_pages", 0)
        )
    
    try:
        # ============================================================
        # PHASE 4: Model Selection by Depth
        # ============================================================
        # Get optimal model configuration for this depth
        from .services.azure_openai_deployment_service import get_deployment_service
        from .services.model_config_service import ModelConfigService
        
        model_config = None
        try:
            subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
            resource_group = os.getenv("AZURE_AI_FOUNDRY_RESOURCE_GROUP")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            account_name = endpoint.split("//")[1].split(".")[0] if "//" in endpoint else ""
            
            if all([subscription_id, resource_group, account_name]):
                async with get_deployment_service(subscription_id, resource_group, account_name) as service:
                    summary = await service.get_deployments_summary()
                    chat_models = summary.get("chat_models", [])
                
                config_service = ModelConfigService(available_deployments=chat_models)
                model_config = config_service.get_model_config_for_depth(depth)
                
                logger.info(
                    f"🤖 Model selected for {depth} depth: {model_config.model_name} "
                    f"(deployment={model_config.deployment_name}, temp={model_config.temperature}, "
                    f"tokens={model_config.max_tokens})"
                )
            else:
                logger.warning("Azure deployment config incomplete, using defaults")
        except Exception as e:
            logger.warning(f"Failed to fetch model config, using defaults: {e}")
        
        # Fallback to default if model selection failed
        if not model_config:
            from .services.model_config_service import ModelConfig
            model_config = ModelConfig(
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                model_name="gpt-4o",
                temperature=0.7 if depth == "exhaustive" else 0.5,
                max_tokens=8000 if depth == "exhaustive" else 4000,
                use_reasoning_model=False
            )
            logger.info(f"Using fallback model: {model_config.model_name}")
        
        # Allow frontend to override model selection
        if model_deployment and model_deployment != model_config.deployment_name:
            logger.info(f"🎯 User override: Using model deployment '{model_deployment}' instead of '{model_config.deployment_name}'")
            model_config.deployment_name = model_deployment
        
        # Get depth configuration
        depth_config = DEPTH_CONFIGS.get(depth, DEPTH_CONFIGS["comprehensive"])
        logger.info(f"🎯 Research depth: {depth}", config=depth_config)
        
        # Override max_sources with depth-specific value
        max_sources = depth_config["max_sources"]
        num_aspects = depth_config["research_aspects"]
        
        # Get depth-specific prompts
        planner_prompt_template = DEPTH_PROMPTS[depth]["planner"]
        researcher_instructions = DEPTH_PROMPTS[depth]["researcher"]
        writer_instructions = DEPTH_PROMPTS[depth]["writer"]
        
        # Leverage local MAF patterns
        # Phase 1: Sequential Planning using sequential workflow
        logger.info("Code-based execution: Phase 1 - Sequential Planning (sequential workflow)")
        logger.info("sequential_task_start", phase=1, task="planning", agent="planner")

        # Update progress: Phase 1 starting
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = f"Phase 1: Research Planning ({depth} mode)"
            active_executions[execution_id]["progress"] = 10.0
            active_executions[execution_id]["completed_tasks"] = []

        # Use depth-specific planning prompt
        planner_prompt = planner_prompt_template.format(topic=topic)
        planner_prompt += f"\n\nTarget: {depth_config['detail_level']} analysis"
        planner_prompt += f"\nMax sources: {max_sources}"
        planner_prompt += f"\nReport length: {depth_config['report_min_words']}-{depth_config['report_max_words']} words"

        planning_context = await orchestrator_instance.execute(
            task=planner_prompt,
            pattern="sequential",
            agents=["planner"],
            metadata={
                "name": "research_planning",
                "description": f"Create {depth_config['detail_level']} research plan",
                "config": {"preserve_context": True},
            },
        )

        # Extract research plan with better error handling
        research_plan = ""
        if planning_context and planning_context.result:
            logger.info(
                f"Planning context result structure: {planning_context.result.keys() if isinstance(planning_context.result, dict) else type(planning_context.result)}"
            )

            # Try summary field first (it contains the complete response)
            if "summary" in planning_context.result:
                research_plan = planning_context.result.get("summary", "")
            # Try results list (contains agent responses)
            elif "results" in planning_context.result:
                responses = planning_context.result.get("results", [])
                if responses and len(responses) > 0:
                    # Results is a list of dicts with 'agent' and 'content' keys
                    research_plan = responses[0].get("content", "")
            # Try direct content field
            elif "content" in planning_context.result:
                research_plan = planning_context.result.get("content", "")

            if not research_plan:
                logger.warning(
                    f"⚠️ No research plan content found. Full result keys: {planning_context.result.keys()}"
                )
        else:
            logger.warning("⚠️ Planning context or result is None")

        results["research_plan"] = research_plan
        logger.info(
            "sequential_task_completed", phase=1, task="planning", result_length=len(str(research_plan))
        )

        # Update progress: Phase 1 complete
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = "Phase 2: Concurrent Investigation"
            active_executions[execution_id]["progress"] = 35.0
            active_executions[execution_id]["completed_tasks"].append("Phase 1: Planning")
        
        # Phase 2: Multi-Query Research Execution (Deep Research Pattern)
        logger.info("Code-based execution: Phase 2 - Multi-Query Deep Research")
        logger.info("deep_research_start", phase=2, depth=depth, max_sources=max_sources)
        
        # Initialize Tavily search service
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        
        tavily_service = TavilySearchService(api_key=tavily_api_key)
        
        # Initialize Azure OpenAI client for multi-pass refinement and advanced features
        azure_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Calculate queries per aspect based on depth
        # Total sources = queries_per_aspect * results_per_query * num_aspects
        # Example: exhaustive (50 sources) = 5 queries * 2 results * 5 aspects = 50 sources
        queries_per_aspect_map = {
            "quick": 1,      # 1 query * 5 results * 2 aspects = 10 sources
            "standard": 2,   # 2 queries * 3 results * 3 aspects = 18 sources  
            "comprehensive": 2,  # 2 queries * 5 results * 5 aspects = 50 sources
            "exhaustive": 2  # 2 queries * 5 results * 5 aspects = 50 sources
        }
        
        results_per_query_map = {
            "quick": 5,
            "standard": 3,
            "comprehensive": 5,
            "exhaustive": 5
        }
        
        queries_per_aspect = queries_per_aspect_map.get(depth, 2)
        results_per_query = results_per_query_map.get(depth, 5)
        
        # Define research aspects based on depth
        all_research_aspects = [
            ("core_concepts", "Core concepts and fundamental definitions", "Research the core concepts, fundamental definitions, and basic principles. Focus on authoritative sources."),
            ("current_state", "Current state and recent developments", "Investigate the current state, recent developments, and latest trends. Focus on publications from the last 2-3 years."),
            ("applications", "Practical applications and use cases", "Research practical applications, use cases, and real-world implementations. Include examples and case studies."),
            ("challenges", "Challenges and limitations", "Investigate the challenges, limitations, criticisms, and potential risks. Include counterarguments."),
            ("future_trends", "Future trends and predictions", "Research future trends, predictions, and emerging directions. Focus on expert opinions and forecasts.")
        ]
        
        # Select aspects based on depth
        research_aspects = all_research_aspects[:num_aspects]
        logger.info(f"🔬 Executing {num_aspects} research aspects with {queries_per_aspect} queries each")
        
        # Generate queries for each aspect using AI
        async def generate_queries_for_aspect(aspect_key: str, aspect_title: str, aspect_description: str):
            """Generate multiple search queries for a research aspect."""
            logger.info(f"Generating queries for aspect: {aspect_key}")
            
            query_generation_prompt = f"""Generate {queries_per_aspect} specific, focused search queries to research the following aspect of "{topic}":

Aspect: {aspect_title}
Description: {aspect_description}

Requirements:
- Each query should be specific and searchable (under 300 characters)
- Queries should cover different angles of this aspect
- Make queries focused enough to get quality results
- Return ONLY a JSON array of query strings, nothing else

Example format:
["query 1", "query 2"]
"""
            
            # NOTE: Use the outer azure_client and model_config from execute_research_programmatically scope
            
            response = await asyncio.to_thread(
                azure_client.chat.completions.create,
                model=model_config.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a research query generator. Return only valid JSON."},
                    {"role": "user", "content": query_generation_prompt}
                ],
                temperature=model_config.temperature,
                max_tokens=500  # Keep lower for query generation
            )
            
            queries_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            try:
                if "```json" in queries_text:
                    queries_text = queries_text.split("```json")[1].split("```")[0].strip()
                elif "```" in queries_text:
                    queries_text = queries_text.split("```")[1].split("```")[0].strip()
                
                queries = json.loads(queries_text)
                if not isinstance(queries, list):
                    queries = [topic + " " + aspect_title]
            except:
                queries = [topic + " " + aspect_title]
            
            return (aspect_key, aspect_title, queries[:queries_per_aspect])
        
        # Generate all queries
        all_aspect_queries = await asyncio.gather(
            *[generate_queries_for_aspect(key, title, desc) for key, title, desc in research_aspects],
            return_exceptions=True
        )
        
        # Execute searches and aggregate findings
        aggregated_findings = {}
        
        for aspect_data in all_aspect_queries:
            if isinstance(aspect_data, Exception):
                logger.error("Query generation failed", error=str(aspect_data))
                continue
            
            aspect_key, aspect_title, queries = aspect_data
            aspect_findings = []
            aspect_sources = []
            
            logger.info(f"🔍 Researching {aspect_key} with {len(queries)} queries")
            
            for query_idx, query in enumerate(queries):
                try:
                    # Perform Tavily search
                    search_results = await tavily_service.search_and_format(
                        query=query,
                        research_goal=aspect_title,
                        max_results=results_per_query
                    )
                    
                    context = search_results["context"]
                    sources = search_results["sources"]
                    
                    logger.info(f"📚 Search returned {len(sources)} sources for query: {query[:50]}...")
                    
                    # Combine web search context with document context
                    combined_context = context
                    if has_documents and document_context:
                        combined_context = f"""## Uploaded Research Documents

{document_context}

---

## Web Search Results

{context}"""
                        logger.info(f"📄 Combined document and web context for query")
                    
                    # Create synthesis prompt (with Chain-of-Thought for exhaustive)
                    if depth == "exhaustive":
                        # Use Chain-of-Thought prompting for deeper analysis
                        prompting_service = AdvancedPromptingService()
                        synthesis_prompt = prompting_service.get_chain_of_thought_prompt(
                            topic=topic,
                            query=query,
                            context=combined_context,  # Use combined context
                            prompt_type="synthesis"
                        )
                        logger.info(f"🧠 Using Chain-of-Thought prompting for query: {query[:50]}...")
                    else:
                        # Standard synthesis for other depths
                        source_types = "web search results"
                        if has_documents:
                            source_types = "uploaded research documents and web search results"
                        
                        synthesis_prompt = f"""Based on the following {source_types} for "{query}":

<CONTEXT>
{combined_context}
</CONTEXT>

Extract key learnings and insights. Be concise but information-dense.
Include citations using [1], [2] format from the context above.
Focus on factual information, metrics, and specific details.
{f"Pay special attention to insights from uploaded documents." if has_documents else ""}"""
                    
                    # NOTE: Use the outer azure_client and model_config from execute_research_programmatically scope
                    
                    # Synthesize findings
                    synthesis_response = await asyncio.to_thread(
                        azure_client.chat.completions.create,
                        model=model_config.deployment_name,
                        messages=[
                            {"role": "system", "content": "You are an expert researcher who synthesizes information from sources with proper citations."},
                            {"role": "user", "content": synthesis_prompt}
                        ],
                        temperature=model_config.temperature,
                        max_tokens=model_config.max_tokens
                    )
                    
                    findings = synthesis_response.choices[0].message.content
                    aspect_findings.append(f"Query: {query}\n{findings}")
                    aspect_sources.extend(sources)
                    
                    logger.info(f"✅ Query {query_idx+1}/{len(queries)} completed", sources_count=len(sources))
                    
                except Exception as e:
                    logger.error(f"Search failed for query: {query}", error=str(e))
                    aspect_findings.append(f"Query: {query}\nError: {str(e)}")
            
            # Aggregate findings for this aspect
            aggregated_findings[aspect_key] = {
                "title": aspect_title,
                "findings": "\n\n".join(aspect_findings),
                "sources": aspect_sources,  # Store actual sources, not just count
                "sources_count": len(aspect_sources)
            }
            
            logger.info(f"✅ Aspect {aspect_key} completed", 
                       total_sources=len(aspect_sources),
                       aspect_sources_details=f"{len(aspect_sources)} sources collected")
        
        # Store aggregated findings in results
        for key, data in aggregated_findings.items():
            results[key] = data["findings"]
        
        # Collect all sources (web + documents)
        all_web_sources = []
        for data in aggregated_findings.values():
            all_web_sources.extend(data["sources"])
        
        # Add document sources to results
        if has_documents and document_sources:
            results["document_sources"] = document_sources
            results["total_document_sources"] = len(document_sources)
            logger.info(f"📄 Added {len(document_sources)} document sources to results")
        
        # Update progress: Phase 2 complete
        total_sources_count = len(all_web_sources) + len(document_sources)
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = "Phase 3: Synthesizing Findings"
            active_executions[execution_id]["progress"] = 50.0
            active_executions[execution_id]["completed_tasks"] = [
                "Phase 1: Research Planning",
                f"Phase 2: Deep Research ({total_sources_count} sources: {len(all_web_sources)} web + {len(document_sources)} documents)"
            ]
        
        # Phase 3-6: Sequential Processing using sequential workflow
        logger.info("Code-based execution: Phase 3-6 - Sequential Processing (sequential workflow)")
        logger.info("sequential_task_start", phase=3, task="synthesis_validation_finalization", agents=["writer", "reviewer", "summarizer"])
        
        # Build comprehensive context for remaining phases with depth-specific instructions
        research_sections = []
        all_sources = []
        
        for key in aggregated_findings.keys():
            if key in results:
                section_title = aggregated_findings[key]["title"]
                sources_count = aggregated_findings[key]["sources_count"]
                research_sections.append(f"{section_title} ({sources_count} sources):\n{results[key]}\n")
                # Collect all sources
                aspect_sources_list = aggregated_findings[key].get("sources", [])
                logger.info(f"📋 Collecting sources for {key}: {len(aspect_sources_list)} sources")
                all_sources.extend(aspect_sources_list)
        
        logger.info(f"📚 Total sources collected from all aspects: {len(all_sources)}")
        
        # Deduplicate sources by URL
        unique_sources = []
        seen_urls = set()
        for source in all_sources:
            source_url = source.url if hasattr(source, 'url') else source.get('url', '')
            if source_url and source_url not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(source_url)
        
        logger.info(f"🔗 After deduplication: {len(unique_sources)} unique sources")
        
        # ============================================================
        # EXHAUSTIVE MODE: Multi-Pass Refinement with Gap Analysis
        # ============================================================
        if depth == "exhaustive" and depth_config.get("synthesis_iterations", 1) > 1:
            logger.info("🔄 EXHAUSTIVE MODE: Starting multi-pass refinement")
            
            num_iterations = depth_config["synthesis_iterations"]
            iteration_findings = []
            iteration_sources = list(unique_sources)  # Start with deduplicated sources
            
            for iteration in range(1, num_iterations):
                logger.info(f"📊 Refinement Iteration {iteration}/{num_iterations-1}")
                
                # Update progress
                if execution_id in active_executions:
                    active_executions[execution_id]["current_task"] = f"Iteration {iteration}: Gap Analysis"
                    active_executions[execution_id]["progress"] = 50.0 + (iteration / num_iterations) * 20.0
                
                # Synthesize current findings for gap analysis
                current_findings = "\n\n".join([results.get(key, "") for key in aggregated_findings.keys()])
                
                # Analyze gaps
                gap_analysis_result = await analyze_research_gaps(
                    topic=topic,
                    iteration=iteration,
                    previous_findings=current_findings,
                    previous_sources=iteration_sources,
                    azure_client=azure_client,
                    model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "chat4o")
                )
                
                iteration_findings.append({
                    "iteration": iteration,
                    "gap_analysis": gap_analysis_result["gap_analysis"],
                    "source_quality": gap_analysis_result["source_quality"]
                })
                
                logger.info(
                    f"Gap analysis iteration {iteration}",
                    source_tiers=gap_analysis_result["source_quality"]
                )
                
                # Extract recommended queries from gap analysis
                gap_text = gap_analysis_result["gap_analysis"]
                if "RECOMMENDED_QUERIES:" in gap_text:
                    # Simple extraction - in production would use more robust parsing
                    queries_section = gap_text.split("RECOMMENDED_QUERIES:")[1]
                    if "SOURCE_QUALITY_NEEDS:" in queries_section:
                        queries_section = queries_section.split("SOURCE_QUALITY_NEEDS:")[0]
                    
                    # Execute additional searches based on gap analysis
                    logger.info(f"🔍 Iteration {iteration}: Executing gap-filling searches")
                    
                    # Parse queries (simplified - assumes bullet format)
                    gap_queries = [
                        line.strip().lstrip('-').strip() 
                        for line in queries_section.split('\n') 
                        if line.strip() and line.strip().startswith('-')
                    ][:3]  # Limit to 3 queries per iteration
                    
                    for gap_query in gap_queries:
                        if gap_query:
                            try:
                                gap_search_results, gap_sources = await tavily_service.search_and_format(
                                    gap_query,
                                    max_results=3
                                )
                                iteration_sources.extend(gap_sources)
                                logger.info(f"  Gap search: {gap_query[:50]}... → {len(gap_sources)} sources")
                            except Exception as e:
                                logger.error(f"Gap search failed", query=gap_query, error=str(e))
                
                # Update progress
                if execution_id in active_executions:
                    active_executions[execution_id]["current_task"] = f"Iteration {iteration}: Additional Research"
                    active_executions[execution_id]["progress"] = 50.0 + ((iteration + 0.5) / num_iterations) * 20.0
            
            # Deduplicate iteration sources
            unique_iteration_sources = []
            seen_urls = set()
            for source in iteration_sources:
                source_url = source.url if hasattr(source, 'url') else source.get('url', '')
                if source_url and source_url not in seen_urls:
                    unique_iteration_sources.append(source)
                    seen_urls.add(source_url)
            
            # Replace unique_sources with refined sources
            unique_sources = unique_iteration_sources
            
            # Store iteration details in results
            results["refinement_iterations"] = iteration_findings
            results["total_iterations"] = num_iterations
            
            logger.info(
                f"✅ Multi-pass refinement completed",
                iterations=num_iterations - 1,
                final_sources=len(unique_sources)
            )
            
            # Update progress
            if execution_id in active_executions:
                active_executions[execution_id]["completed_tasks"].append(
                    f"Multi-pass Refinement ({num_iterations-1} iterations, {len(unique_sources)} total sources)"
                )
        
        # Format sources list
            if source_url and source_url not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(source_url)
        
        logger.info(f"🔗 After deduplication: {len(unique_sources)} unique sources")
        
        # Format sources list
        sources_list = "\n".join([
            f"[{idx+1}] {source.title if hasattr(source, 'title') else source.get('title', 'Untitled')}\n    {source.url if hasattr(source, 'url') else source.get('url', '')}"
            for idx, source in enumerate(unique_sources)
        ])
        
        logger.info(f"📝 Formatted {len(unique_sources)} sources for context")
        logger.info(f"📄 Sources list preview (first 500 chars): {sources_list[:500]}...")
        
        comprehensive_context = f"""Research Topic: {topic}

Research Depth: {depth} ({depth_config['detail_level']} analysis)
Target Length: {depth_config['report_min_words']}-{depth_config['report_max_words']} words

Research Plan:
{research_plan}

Research Findings:
{"".join(research_sections)}

Sources ({len(unique_sources)} total):
{sources_list}

==============================================
INSTRUCTIONS FOR WRITER AGENT (FIRST AGENT):
==============================================
{writer_instructions}

YOUR TASK: Write the COMPLETE, FULL-LENGTH RESEARCH REPORT about "{topic}" using the research findings above.

CRITICAL REQUIREMENTS:
1. Write a FULL REPORT of {depth_config['report_min_words']}-{depth_config['report_max_words']} words
2. DO NOT write just a summary - write the ENTIRE comprehensive report
3. Include ALL sections specified in the structure above
4. Each section should be substantive and detailed
5. Use the research findings provided to populate each section
6. Include analysis, evidence, examples, and insights
7. Write in a scholarly, professional tone

MANDATORY SOURCES SECTION:
You MUST include a complete "## Sources" or "## References" section at the END of your report.
List ALL {len(unique_sources)} sources provided above using this exact format:

## Sources

[1] Source Title
    URL

[2] Source Title  
    URL

(etc. for all {len(unique_sources)} sources)

DO NOT skip the sources section. It is MANDATORY.

==============================================
INSTRUCTIONS FOR EDITOR AGENT (SECOND AGENT):
==============================================
Take the research report from the writer and enhance it - improve clarity, structure, and flow while preserving all content.
Return the ENHANCED REPORT, not commentary about it.
CRITICAL: The Sources/References section MUST be preserved in full. Do not remove or modify the sources.

INSTRUCTIONS FOR SUMMARIZER AGENT:
Extract and present the key findings from the research report in a concise executive summary.
Return the SUMMARY OF FINDINGS, not an evaluation of report quality."""
        
        logger.info(f"📤 Sending context to agents with {len(unique_sources)} sources in Sources section")
        logger.info(f"📊 Context length: {len(comprehensive_context)} characters")
        
        logger.info("🚀 Executing sequential synthesis pipeline (writer → reviewer → summarizer)...")
        final_context = await orchestrator_instance.execute(
            task=comprehensive_context,
            pattern="sequential",
            agents=["writer", "reviewer", "summarizer"],
            metadata={
                "name": "synthesis_validation_finalization",
                "description": f"Sequential synthesis ({depth} depth), validation, and summarization",
                "config": {"preserve_context": True, "fail_fast": False},
            },
        )
        logger.info("✅ Sequential execution completed")
        
        # Extract results from sequential execution with better error handling
        if final_context and final_context.result:
            logger.info(f"Final context result structure: {final_context.result.keys() if isinstance(final_context.result, dict) else type(final_context.result)}")
            
            # Log the full result for debugging
            logger.info(f"📋 Full final_context.result keys: {list(final_context.result.keys()) if isinstance(final_context.result, dict) else 'Not a dict'}")
            if isinstance(final_context.result, dict) and "results" in final_context.result:
                logger.info(f"📋 Number of agent responses: {len(final_context.result['results'])}")
                for idx, resp in enumerate(final_context.result["results"]):
                    agent_name = resp.get("agent", f"agent_{idx}")
                    content_length = len(resp.get("content", ""))
                    content_preview = resp.get("content", "")[:200]
                    logger.info(f"  Agent {idx} ({agent_name}): {content_length} chars - Preview: {content_preview}...")
            
            # Priority: Use individual agent results (more granular)
            if "results" in final_context.result:
                responses = final_context.result["results"]
                logger.info(f"Got {len(responses)} responses from final phases")
                
                # Extract individual agent responses
                if len(responses) >= 1:
                    writer_output = responses[0].get("content", "")
                    if writer_output:
                        results["draft_report"] = writer_output
                        logger.info(f"📝 Writer output: {len(writer_output)} characters")
                
                if len(responses) >= 2:
                    reviewer_output = responses[1].get("content", "")
                    if reviewer_output:
                        # Reviewer enhances the report, this should be the final version
                        results["final_report"] = reviewer_output
                        logger.info(f"✨ Reviewer output (final): {len(reviewer_output)} characters")
                
                if len(responses) >= 3:
                    summarizer_output = responses[2].get("content", "")
                    if summarizer_output:
                        results["executive_summary"] = summarizer_output
                        logger.info(f"📊 Summarizer output: {len(summarizer_output)} characters")
                
                # If reviewer didn't produce output, use writer's draft as final
                if "final_report" not in results and "draft_report" in results:
                    results["final_report"] = results["draft_report"]
                    logger.warning("⚠️ No reviewer output, using draft as final report")
                
                logger.info("sequential_phases_completed", phases=[3, 4, 5], 
                           draft_length=len(results.get("draft_report", "")),
                           final_length=len(results.get("final_report", "")),
                           summary_length=len(results.get("executive_summary", "")))
            
            # Fallback: Use summary field only if no individual results
            elif "summary" in final_context.result:
                final_summary = final_context.result.get("summary", "")
                logger.warning(f"⚠️ No individual results, using summary field ({len(final_summary)} chars)")
                results["draft_report"] = final_summary
                results["final_report"] = final_summary
                results["executive_summary"] = final_summary
            
            else:
                logger.warning(f"⚠️ No 'results' or 'summary' key in final_context.result. Keys: {final_context.result.keys()}")
        else:
            logger.warning(f"⚠️ Final context or result is None")
        
        # Update progress: All phases complete
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = None
            active_executions[execution_id]["progress"] = 90.0
            active_executions[execution_id]["completed_tasks"] = [
                "Phase 1: Research Planning (sequential)",
                f"Phase 2: Multi-Query Deep Research ({len(unique_sources)} unique sources)",
                "Phase 3-6: Synthesis, Validation, Finalization, Summarization (sequential)"
            ]
        
        # ============================================================
        # ADVANCED AI: Self-Refinement Loop (Comprehensive/Exhaustive)
        # ============================================================
        prompting_service = AdvancedPromptingService()
        
        if prompting_service.should_use_refinement(depth):
            refinement_iterations = prompting_service.get_refinement_iterations(depth)
            logger.info(f"🔄 Starting Self-Refinement Loop: {refinement_iterations} iterations")
            
            final_report = results.get("final_report", results.get("draft_report", ""))
            
            if final_report:
                for iteration in range(refinement_iterations):
                    logger.info(f"🔄 Refinement Iteration {iteration + 1}/{refinement_iterations}")
                    
                    if execution_id in active_executions:
                        active_executions[execution_id]["current_task"] = f"Self-Refinement {iteration + 1}/{refinement_iterations}"
                        active_executions[execution_id]["progress"] = 90.0 + (iteration / refinement_iterations) * 5.0
                    
                    # Step 1: Critique the current draft
                    critique_prompt = prompting_service.get_critique_prompt(final_report)
                    
                    critique_response = await asyncio.to_thread(
                        azure_client.chat.completions.create,
                        model=model_config.deployment_name,
                        messages=[
                            {"role": "system", "content": "You are an expert research critic providing detailed, constructive feedback."},
                            {"role": "user", "content": critique_prompt}
                        ],
                        temperature=model_config.temperature,
                        max_tokens=model_config.max_tokens // 2  # Use half tokens for critique
                    )
                    
                    critique = critique_response.choices[0].message.content
                    logger.info(f"📝 Critique generated: {len(critique)} characters")
                    
                    # Step 2: Generate improvement suggestions
                    improvement_prompt = prompting_service.get_improvement_prompt(final_report, critique)
                    
                    improvement_response = await asyncio.to_thread(
                        azure_client.chat.completions.create,
                        model=model_config.deployment_name,
                        messages=[
                            {"role": "system", "content": "You are a research improvement strategist providing actionable enhancement plans."},
                            {"role": "user", "content": improvement_prompt}
                        ],
                        temperature=model_config.temperature,
                        max_tokens=model_config.max_tokens // 2
                    )
                    
                    improvements = improvement_response.choices[0].message.content
                    logger.info(f"💡 Improvements suggested: {len(improvements)} characters")
                    
                    # Step 3: Revise the draft
                    revision_prompt = prompting_service.get_revision_prompt(final_report, improvements)
                    
                    revision_response = await asyncio.to_thread(
                        azure_client.chat.completions.create,
                        model=model_config.deployment_name,
                        messages=[
                            {"role": "system", "content": "You are an expert research writer revising drafts based on improvement plans."},
                            {"role": "user", "content": revision_prompt}
                        ],
                        temperature=model_config.temperature,
                        max_tokens=model_config.max_tokens
                    )
                    
                    revised_report = revision_response.choices[0].message.content
                    
                    # Quality check: Only use revision if it's substantive
                    if revised_report and len(revised_report) > len(final_report) * 0.8:
                        logger.info(f"✅ Revision accepted: {len(revised_report)} characters (was {len(final_report)})")
                        final_report = revised_report
                        results["final_report"] = revised_report
                        results[f"refinement_{iteration + 1}"] = {
                            "critique": critique,
                            "improvements": improvements,
                            "revised_length": len(revised_report)
                        }
                    else:
                        logger.warning(f"⚠️ Revision rejected (too short or empty)")
                
                logger.info(f"✅ Self-Refinement Complete: Final report length = {len(final_report)} characters")
        
        # ============================================================
        # VALIDATION: Research Quality Assessment
        # ============================================================
        # Validate research quality for comprehensive/exhaustive modes
        if depth in ["comprehensive", "exhaustive"]:
            logger.info("🔍 Validating research quality")
            
            if execution_id in active_executions:
                active_executions[execution_id]["current_task"] = "Quality Validation"
                active_executions[execution_id]["progress"] = 91.0
            
            # Get the final report for validation
            final_report = results.get("final_report", results.get("draft_report", ""))
            
            if final_report:
                validator = get_validator()
                validation_result = await validator.validate_research_quality(
                    report=final_report,
                    depth=depth,
                    sources=unique_sources,
                    metadata={
                        "research_aspects": depth_config.get("research_aspects", 0),
                        "max_sources": depth_config.get("max_sources", 0)
                    }
                )
                
                results["validation"] = {
                    "passed": validation_result.passed,
                    "score": validation_result.score,
                    "issues": validation_result.issues,
                    "warnings": validation_result.warnings,
                    "metrics": validation_result.metrics
                }
                
                logger.info("✅ Research validation completed", 
                           passed=validation_result.passed,
                           score=f"{validation_result.score:.2f}",
                           issues_count=len(validation_result.issues),
                           warnings_count=len(validation_result.warnings))
                
                # Log validation details
                if validation_result.issues:
                    logger.warning("⚠️ Validation issues", issues=validation_result.issues)
                if validation_result.warnings:
                    logger.info("📋 Validation warnings", warnings=validation_result.warnings)
                
                # ============================================================
                # MULTI-PASS REFINEMENT: Iterative Quality Improvement
                # ============================================================
                # Trigger refinement if validation fails (score < 0.75)
                if not validation_result.passed and validation_result.score < 0.75:
                    max_refinement_passes = 3 if depth == "comprehensive" else 5
                    refinement_pass = 0
                    
                    logger.info("🔄 Initiating multi-pass refinement", 
                               max_passes=max_refinement_passes,
                               current_score=f"{validation_result.score:.2f}")
                    
                    while refinement_pass < max_refinement_passes and not validation_result.passed:
                        refinement_pass += 1
                        
                        if execution_id in active_executions:
                            active_executions[execution_id]["current_task"] = f"Refinement Pass {refinement_pass}/{max_refinement_passes}"
                            active_executions[execution_id]["progress"] = 91.0 + (refinement_pass / max_refinement_passes) * 4.0
                        
                        logger.info(f"🔧 Refinement pass {refinement_pass}/{max_refinement_passes}")
                        
                        # Build refinement context from validation results
                        refinement_context = f"""
# Research Quality Issues Detected

## Validation Score: {validation_result.score:.2f}

## Critical Issues:
{chr(10).join(['- ' + issue for issue in validation_result.issues]) if validation_result.issues else 'None'}

## Warnings:
{chr(10).join(['- ' + warning for warning in validation_result.warnings]) if validation_result.warnings else 'None'}

## Quality Metrics:
{chr(10).join([f'- {k}: {v}' for k, v in validation_result.metrics.items()])}

## Current Report:
{final_report}

## Available Sources ({len(unique_sources)}):
{chr(10).join([f"- [{s.get('title', 'Untitled')}]({s.get('url', 'No URL')}) - {s.get('source_type', 'Unknown type')}" for s in unique_sources[:10]])}
{'... and ' + str(len(unique_sources) - 10) + ' more sources' if len(unique_sources) > 10 else ''}

## Instructions:
Please refine the research report to address the above issues. Focus on:
1. Meeting word count targets ({depth_config['report_min_words']}-{depth_config['report_max_words']} words)
2. Including more high-quality citations from available sources
3. Improving structural depth with required sections
4. Enhancing analysis depth with critical thinking
5. Leveraging source quality (prioritize peer-reviewed, government, and news sources)

Provide an improved version that maintains accuracy while addressing validation gaps.
"""
                        
                        # Create refinement agent (enhance reviewer capabilities)
                        try:
                            refinement_result = await orchestrator.execute_agent(
                                agent_name="reviewer",
                                input_message=refinement_context,
                                context={
                                    "task_type": "research_refinement",
                                    "depth": depth,
                                    "refinement_pass": refinement_pass,
                                    "validation_issues": validation_result.issues,
                                    "current_report": final_report,
                                    "sources": unique_sources
                                },
                                execution_id=execution_id
                            )
                            
                            refined_report = refinement_result.get("output", "")
                            
                            if refined_report and len(refined_report) > len(final_report) * 0.8:
                                # Update final report with refined version
                                final_report = refined_report
                                results["final_report"] = refined_report
                                
                                # Re-validate the refined report
                                validation_result = await validator.validate_research_quality(
                                    report=refined_report,
                                    depth=depth,
                                    sources=unique_sources,
                                    metadata={
                                        "research_aspects": depth_config.get("research_aspects", 0),
                                        "max_sources": depth_config.get("max_sources", 0),
                                        "refinement_pass": refinement_pass
                                    }
                                )
                                
                                logger.info(f"✨ Refinement pass {refinement_pass} completed",
                                           new_score=f"{validation_result.score:.2f}",
                                           passed=validation_result.passed)
                                
                                # Update validation results
                                results["validation"] = {
                                    "passed": validation_result.passed,
                                    "score": validation_result.score,
                                    "issues": validation_result.issues,
                                    "warnings": validation_result.warnings,
                                    "metrics": validation_result.metrics,
                                    "refinement_passes": refinement_pass
                                }
                                
                                # Break if validation passes or score improved significantly
                                if validation_result.passed:
                                    logger.info("🎯 Validation passed after refinement!")
                                    break
                                    
                            else:
                                logger.warning(f"⚠️ Refinement pass {refinement_pass} produced insufficient output, skipping")
                                break
                                
                        except Exception as e:
                            logger.error(f"❌ Refinement pass {refinement_pass} failed", error=str(e))
                            break
                    
                    # Log final refinement status
                    if validation_result.passed:
                        logger.info("✅ Multi-pass refinement successful", 
                                   final_score=f"{validation_result.score:.2f}",
                                   passes_used=refinement_pass)
                    else:
                        logger.warning("⚠️ Refinement completed without passing validation",
                                      final_score=f"{validation_result.score:.2f}",
                                      passes_used=refinement_pass)
        
        # ============================================================
        # EXHAUSTIVE MODE: Multi-Perspective Analysis & Fact-Checking
        # ============================================================
        if depth == "exhaustive" and depth_config.get("enable_multi_perspective"):
            logger.info("🎭 EXHAUSTIVE MODE: Multi-perspective analysis")
            
            # Update progress
            if execution_id in active_executions:
                active_executions[execution_id]["current_task"] = "Multi-Perspective Analysis"
                active_executions[execution_id]["progress"] = 92.0
            
            # Get the final report for analysis
            final_report = results.get("final_report", results.get("draft_report", ""))
            
            if final_report:
                # Run multi-perspective analysis
                perspectives = await multi_perspective_analysis(
                    report=final_report,
                    azure_client=azure_client,
                    model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "chat4o")
                )
                
                results["multi_perspective_analysis"] = perspectives
                logger.info("✅ Multi-perspective analysis completed", 
                           perspectives=list(perspectives.keys()))
        
        if depth == "exhaustive" and depth_config.get("enable_fact_checking"):
            logger.info("✓ EXHAUSTIVE MODE: Fact-checking layer")
            
            # Update progress
            if execution_id in active_executions:
                active_executions[execution_id]["current_task"] = "Fact-Checking"
                active_executions[execution_id]["progress"] = 95.0
            
            # Get the final report for fact-checking
            final_report = results.get("final_report", results.get("draft_report", ""))
            
            if final_report:
                # Run fact-checking
                fact_check_results = await fact_check_claims(
                    report=final_report,
                    sources=unique_sources,
                    azure_client=azure_client,
                    model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "chat4o"),
                    tavily_search_service=tavily_service
                )
                
                results["fact_check"] = fact_check_results
                logger.info("✅ Fact-checking completed",
                           claims_analyzed=fact_check_results["sources_analyzed"])
        
        # Source Quality Assessment (for all modes)
        logger.info("📊 Assessing source quality")
        source_assessments = [assess_source_quality(s) for s in unique_sources]
        source_quality_summary = {
            "tier_1_count": len([a for a in source_assessments if a.tier.value == "peer_reviewed"]),
            "tier_2_count": len([a for a in source_assessments if a.tier.value == "primary_source"]),
            "tier_3_count": len([a for a in source_assessments if a.tier.value == "reputable_media"]),
            "tier_4_count": len([a for a in source_assessments if a.tier.value == "general_web"]),
            "average_quality_score": sum(a.score for a in source_assessments) / len(source_assessments) if source_assessments else 0
        }
        results["source_quality"] = source_quality_summary
        logger.info("Source quality distribution", **source_quality_summary)
        
        # Final progress update
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = None
            active_executions[execution_id]["progress"] = 100.0
            
            # Update completed tasks based on what was actually run
            completed_tasks = [
                "Phase 1: Research Planning (sequential)",
                f"Phase 2: Multi-Query Deep Research ({len(unique_sources)} unique sources)",
                "Phase 3-6: Synthesis, Validation, Finalization, Summarization (sequential)"
            ]
            
            if "refinement_iterations" in results:
                completed_tasks.append(f"Multi-pass Refinement ({results['total_iterations']-1} iterations)")
            if "multi_perspective_analysis" in results:
                completed_tasks.append("Multi-Perspective Analysis (Technical/Business/Critical)")
            if "fact_check" in results:
                completed_tasks.append("Fact-Checking Layer")
            
            active_executions[execution_id]["completed_tasks"] = completed_tasks
        
        # Store sources in results for API response (convert Source objects to dicts)
        results["sources"] = [
            {
                "title": source.title if hasattr(source, 'title') else source.get('title', 'Untitled'),
                "url": source.url if hasattr(source, 'url') else source.get('url', ''),
                "content": source.content if hasattr(source, 'content') else source.get('content', '')
            }
            for source in unique_sources
        ]
        results["sources_count"] = len(unique_sources)
        
        logger.info("Code-based execution completed successfully using framework patterns", 
                   total_sources=len(unique_sources))
        return results
        
    except Exception as e:
        logger.error(f"Code-based execution failed", error=str(e))
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application."""
    global workflow_engine, agent_registry, orchestrator
    global file_handler, doc_intelligence, doc_research_service
    
    # Startup
    logger.info("Starting Deep Research Backend API")
    
    # Initialize framework components
    settings = Settings()
    agent_registry = AgentRegistry(settings)
    observability = ObservabilityService(settings)
    await observability.initialize()
    mcp_client = MCPClient(settings)
    orchestrator = MagenticOrchestrator(settings, agent_registry=agent_registry, observability=observability)
    
    # Initialize workflow engine
    workflow_engine = WorkflowEngine(
        settings=settings,
        agent_registry=agent_registry,
        observability=observability,
        mcp_client=mcp_client
    )
    
    # Initialize file handling services
    try:
        file_handler = FileHandler(
            azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
            azure_client_id=os.getenv("AZURE_CLIENT_ID"),
            azure_client_secret=os.getenv("AZURE_CLIENT_SECRET"),
            azure_blob_storage_name=os.getenv("AZURE_BLOB_STORAGE_NAME"),
            azure_storage_container=os.getenv("AZURE_STORAGE_CONTAINER", "research-documents"),
            upload_directory=str(backend_dir / "uploads"),
            data_directory=str(backend_dir / "data")
        )
        await file_handler.initialize()
        logger.info("File handler initialized")
        
        # Initialize Document Intelligence service
        doc_intelligence = DocumentIntelligenceService(
            endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            key=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
            azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
            azure_client_id=os.getenv("AZURE_CLIENT_ID"),
            azure_client_secret=os.getenv("AZURE_CLIENT_SECRET"),
            azure_blob_storage_name=os.getenv("AZURE_BLOB_STORAGE_NAME")
        )
        logger.info("Document Intelligence service initialized")
        
        # Initialize Tavily service for document research service
        tavily_service = TavilySearchService(api_key=os.getenv("TAVILY_API_KEY"))
        
        # Initialize Document Research service
        doc_research_service = DocumentResearchService(
            file_handler=file_handler,
            tavily_service=tavily_service
        )
        logger.info("Document research service initialized")
        
        # Wire up file router dependencies
        files_router.set_services(file_handler, doc_intelligence)
        
    except Exception as e:
        logger.warning(f"Failed to initialize file handling services: {e}. File upload features will not be available.")
    
    # Setup research agents
    await setup_research_agents(agent_registry, settings)
    
    # Register the deep research workflow from local app folder
    app_dir = Path(__file__).parent.parent.parent
    workflow_path = app_dir / "workflows" / "deep_research.yaml"
        
    logger.info(f"Loading workflow from {workflow_path}")
    await workflow_engine.register_workflow(str(workflow_path))
    
    # Initialize Cosmos DB connection for session persistence
    try:
        from app.persistence.cosmos_memory import get_cosmos_store
        cosmos = get_cosmos_store()
        await cosmos.initialize()
        logger.info("Cosmos DB connection initialized for session persistence")
    except Exception as e:
        logger.warning(f"Failed to initialize Cosmos DB: {e}. Session persistence will not be available.")
    
    logger.info("Deep Research Backend API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Deep Research Backend API")
    if file_handler:
        await file_handler.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Deep Research API",
    description="Backend API for Deep Research application using Foundation Framework",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(sessions.router)
app.include_router(files_router.router)


# Request/Response Models
class ResearchRequest(BaseModel):
    """Request to start a research workflow."""
    topic: str = Field(..., description="The research topic or question")
    depth: str = Field(default="comprehensive", description="Research depth: quick, standard, comprehensive, exhaustive")
    max_sources: int = Field(default=10, description="Maximum number of sources to analyze")
    include_citations: bool = Field(default=True, description="Include citations in the report")
    execution_mode: str = Field(
        default="workflow", 
        description="Execution mode: workflow (declarative YAML), code (programmatic patterns), or maf-workflow (MAF graph-based)"
    )
    session_id: Optional[str] = Field(default=None, description="Optional session ID to use existing session")
    model_deployment: Optional[str] = Field(default=None, description="Optional: Override automatic model selection with specific deployment name")
    document_ids: List[str] = Field(
        default_factory=list,
        description="List of document IDs to include in research context"
    )


class ResearchResponse(BaseModel):
    """Response for research workflow initiation."""
    execution_id: str
    status: str
    message: str
    execution_mode: str
    orchestration_pattern: str


class ExecutionStatusResponse(BaseModel):
    """Execution status response."""
    execution_id: str
    status: str
    progress: float
    current_task: Optional[str] = None
    completed_tasks: List[str] = []
    failed_tasks: List[str] = []
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Technical details


class WorkflowInfoResponse(BaseModel):
    """Workflow configuration information."""
    name: str
    version: str
    description: str
    variables: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    total_tasks: int
    max_parallel_tasks: int
    timeout: int
    orchestration_pattern: str
    execution_modes: List[str]


# API Endpoints

@app.get("/api")
async def root():
    """Root API endpoint - returns API information."""
    return {
        "service": "Deep Research API",
        "version": "1.0.0",
        "status": "running",
        "framework": "Foundation Framework"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "workflow_engine": "ready" if workflow_engine else "initializing"
    }


@app.get("/api/workflow/info", response_model=WorkflowInfoResponse)
async def get_workflow_info():
    """Get workflow configuration information."""
    if not workflow_engine:
        raise HTTPException(status_code=503, detail="Workflow engine not initialized")
    
    workflow_def = await workflow_engine.get_workflow("deep_research_workflow")
    if not workflow_def:
        raise HTTPException(status_code=404, detail="Deep research workflow not found")
    
    # Extract task information with dependencies
    tasks_info = []
    for task in workflow_def.tasks:
        # task.type is already a string from the workflow definition
        task_type = task.type if isinstance(task.type, str) else task.type.value
        
        task_info = {
            "id": task.id,
            "name": task.name,
            "type": task_type,
            "description": task.description or "",
            "agent": task.agent if task_type == "agent" else None,
            "depends_on": task.depends_on or [],
            "timeout": task.timeout,
            "parallel": len(task.depends_on or []) > 0 and task.depends_on[0] != "sequential"
        }
        tasks_info.append(task_info)
    
    # Extract variable information
    variables_info = [
        {
            "name": var.name,
            "type": var.type,
            "default": var.default,
            "required": var.required,
            "description": var.description
        }
        for var in workflow_def.variables
    ]
    
    return WorkflowInfoResponse(
        name=workflow_def.name,
        version=workflow_def.version,
        description=workflow_def.description,
        variables=variables_info,
        tasks=tasks_info,
        total_tasks=len(workflow_def.tasks),
        max_parallel_tasks=workflow_def.max_parallel_tasks or 5,
        timeout=workflow_def.timeout or 3600,
        orchestration_pattern="Hybrid (Sequential → Concurrent → Sequential)",
        execution_modes=["workflow", "code", "maf-workflow"]
    )


@app.get("/api/documents/available")
async def get_available_documents(user_id: Optional[str] = None):
    """
    Get list of available processed documents for research.
    
    Args:
        user_id: Optional user ID filter
    
    Returns:
        List of available documents with metadata
    """
    if not doc_research_service:
        raise HTTPException(
            status_code=503,
            detail="Document research service not initialized"
        )
    
    try:
        documents = await doc_research_service.get_available_documents(user_id=user_id)
        
        return {
            "success": True,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        logger.error("Failed to get available documents", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available documents: {str(e)}"
        )


@app.post("/api/research/start", response_model=ResearchResponse)
async def start_research(request: ResearchRequest, req: Request, background_tasks: BackgroundTasks):
    """Start a new research workflow execution."""
    if not workflow_engine or not agent_registry:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        # Extract authenticated user (for session tracking)
        from app.auth.auth_utils import get_authenticated_user_details
        user_details = get_authenticated_user_details(req.headers)
        user_id = user_details.get("user_principal_id", "dev-user@localhost")
        
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        # Ensure session exists in Cosmos DB (create if doesn't exist)
        session_id = request.session_id
        run_id = None
        try:
            from app.persistence.cosmos_memory import get_cosmos_store
            from app.models.persistence_models import ResearchSession, ResearchRun
            from datetime import timezone
            
            cosmos = get_cosmos_store()
            await cosmos.initialize()
            
            # Ensure session exists
            if session_id:
                existing_session = await cosmos.get_session(session_id)
                if not existing_session:
                    # Create new session with provided session_id
                    new_session = ResearchSession(
                        session_id=session_id,
                        user_id=user_id
                    )
                    await cosmos.create_session(new_session)
                    logger.info("Created new session in Cosmos DB", session_id=session_id, user_id=user_id)
                else:
                    # Update last_active
                    await cosmos.update_session(session_id, {"last_active": datetime.now(timezone.utc)})
                    logger.info("Using existing session", session_id=session_id, user_id=user_id)
            else:
                # No session_id provided, create new one
                new_session = ResearchSession(
                    session_id=f"session-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    user_id=user_id
                )
                await cosmos.create_session(new_session)
                session_id = new_session.session_id
                logger.info("Created new session (no ID provided)", session_id=session_id, user_id=user_id)
            
            # Create research run in the session
            run = ResearchRun(
                run_id=execution_id,  # Use execution_id as run_id
                session_id=session_id,
                user_id=user_id,
                topic=request.topic,
                depth=request.depth,
                max_sources=request.max_sources,
                include_citations=request.include_citations,
                execution_mode=request.execution_mode,
                status="pending"
            )
            
            logger.info(f"Creating ResearchRun in Cosmos DB: run_id={run.run_id}, session_id={session_id}, topic={request.topic}")
            
            await cosmos.create_run(run)
            run_id = run.run_id
            
            logger.info(
                "✅ CREATED ResearchRun in Cosmos DB",
                session_id=session_id,
                run_id=run_id,
                user_id=user_id,
                topic=request.topic
            )
        except Exception as e:
            logger.error(f"❌ FAILED to persist to Cosmos DB: {e}. Continuing without persistence.", exc_info=True)
        
        # Prepare document context if documents are selected
        document_context_data = None
        if request.document_ids and len(request.document_ids) > 0:
            logger.info(
                f"🔍 Preparing document context from {len(request.document_ids)} selected documents",
                document_ids=request.document_ids
            )
            document_context_data = await prepare_document_context(request.document_ids)
            if document_context_data:
                logger.info(
                    f"📄 Document context prepared for research",
                    document_count=len(request.document_ids),
                    total_words=document_context_data["document_stats"].get("total_words", 0),
                    total_pages=document_context_data["document_stats"].get("total_pages", 0),
                    context_length=len(document_context_data["document_context"])
                )
            else:
                logger.warning(f"⚠️ Failed to prepare document context despite having document IDs")
        else:
            logger.info(f"ℹ️ No documents selected - using web search only")
        
        # Determine workflow engine and pattern based on execution mode
        if request.execution_mode == "maf-workflow":
            workflow_engine_type = "MAF Graph-based Workflows"
            orchestration_pattern = "Graph-based (Executors with Fan-out/Fan-in)"
            pattern_details = {
                "planner": "Create research plan",
                "researchers": "Parallel research (fan-out to 3 executors)",
                "synthesizer": "Combine findings (fan-in from researchers)",
                "reviewer": "Validate quality",
                "summarizer": "Create executive summary"
            }
        elif request.execution_mode == "code":
            workflow_engine_type = "Programmatic Code-based"
            orchestration_pattern = "Hybrid (Sequential → Concurrent → Sequential)"
            pattern_details = {
                "phase_1": "Sequential Planning",
                "phase_2": "Concurrent Investigation (5 parallel research tasks)",
                "phase_3": "Sequential Synthesis",
                "phase_4": "Sequential Validation",
                "phase_5": "Sequential Finalization",
                "phase_6": "Sequential Summarization"
            }
        else:  # workflow
            workflow_engine_type = "Declarative YAML-based"
            orchestration_pattern = "Hybrid (Sequential → Concurrent → Sequential)"
            pattern_details = {
                "phase_1": "Sequential Planning",
                "phase_2": "Concurrent Investigation (5 parallel research tasks)",
                "phase_3": "Sequential Synthesis",
                "phase_4": "Sequential Validation",
                "phase_5": "Sequential Finalization",
                "phase_6": "Sequential Summarization"
            }
        
        # Store execution info with metadata
        active_executions[execution_id] = {
            "id": execution_id,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "request": request.model_dump(),
            "progress": 0.0,
            "current_task": "Initializing..." if request.execution_mode in ["code", "maf-workflow"] else None,
            "completed_tasks": [],
            "failed_tasks": [],
            "session_id": session_id,  # For Cosmos DB persistence
            "run_id": run_id,  # For Cosmos DB persistence
            "metadata": {
                "topic": request.topic,  # Research topic/objective
                "execution_mode": request.execution_mode,
                "orchestration_pattern": orchestration_pattern,
                "framework": "Foundation Framework",
                "workflow_engine": workflow_engine_type,
                "agent_count": 5,
                "agents_used": ["planner", "researcher", "writer", "reviewer", "summarizer"],
                "parallel_tasks": 3 if request.execution_mode == "maf-workflow" else 5,
                "total_phases": 5 if request.execution_mode == "maf-workflow" else 6,
                "pattern_details": pattern_details
            }
        }
        
        # Execute based on mode
        if request.execution_mode == "maf-workflow":
            # MAF Workflow execution: Use graph-based workflow with executors
            logger.info(f"Starting MAF workflow-based research execution", execution_id=execution_id, topic=request.topic)
            
            # Get depth configuration
            depth_config = DEPTH_CONFIGS.get(request.depth, DEPTH_CONFIGS["comprehensive"])
            max_sources_for_depth = depth_config["max_sources"]
            
            background_tasks.add_task(
                execute_maf_workflow_research_task,
                execution_id,
                request.topic,
                max_sources_for_depth,  # Use depth-specific max_sources
                document_context_data  # Pass document context
            )
        elif request.execution_mode == "code":
            # Code-based execution: Use programmatic approach with orchestrator
            logger.info(f"Starting code-based research execution", execution_id=execution_id, topic=request.topic)
            background_tasks.add_task(
                execute_code_based_research,
                execution_id,
                agent_registry,
                orchestrator,
                request.topic,
                request.depth,
                request.max_sources,
                request.include_citations,
                document_context_data  # Pass document context
            )
        else:
            # Workflow-based execution: Use declarative YAML
            logger.info(f"Starting workflow-based research execution", execution_id=execution_id, topic=request.topic)
            
            # Get depth configuration
            depth_config = DEPTH_CONFIGS.get(request.depth, DEPTH_CONFIGS["comprehensive"])
            logger.info(f"🎯 YAML Workflow depth: {request.depth}", config=depth_config)
            
            # Override max_sources with depth-specific value
            max_sources_for_depth = depth_config["max_sources"]
            
            # Prepare workflow variables
            variables = {
                "research_topic": request.topic,
                "research_depth": request.depth,
                "max_sources": max_sources_for_depth,  # Use depth-specific max_sources
                "include_citations": request.include_citations,
                "depth_config": depth_config,  # Pass full config for agents to use
                "document_context": document_context_data["document_context"] if document_context_data else "",  # Pass document context
                "has_documents": bool(document_context_data)  # Flag to indicate documents are available
            }
            
            # Start workflow execution with our execution_id
            workflow_execution_id = await workflow_engine.execute_workflow(
                workflow_name="deep_research_workflow",
                variables=variables
            )
            
            # Map workflow execution ID to our execution ID
            active_executions[execution_id]["workflow_execution_id"] = workflow_execution_id
            
            # Start background task to monitor workflow execution
            background_tasks.add_task(monitor_execution, execution_id)
        
        logger.info(f"Started research execution", execution_id=execution_id, topic=request.topic, mode=request.execution_mode)
        
        return ResearchResponse(
            execution_id=execution_id,
            status="running",
            message=f"Research execution started for topic: {request.topic} (mode: {request.execution_mode})",
            execution_mode=request.execution_mode,
            orchestration_pattern="Hybrid (Sequential → Concurrent → Sequential)"
        )
        
    except Exception as e:
        logger.error(f"Failed to start research execution", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@app.get("/api/research/status/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str):
    """Get the status of a research execution (workflow or code-based)."""
    
    # Check if execution is active (in-memory)
    if execution_id in active_executions:
        # Active execution - get from memory
        exec_info = active_executions[execution_id]
        execution_mode = exec_info.get("request", {}).get("execution_mode", "workflow")
        
        if execution_mode in ["code", "maf-workflow"]:
            # Code-based or MAF workflow execution: Get status from active_executions
            status = exec_info.get("status", "running")
            start_time = exec_info.get("start_time")
            end_time = exec_info.get("end_time")
            # Check both "results" (code-based) and "result" (maf-workflow) for compatibility
            results = exec_info.get("results") or exec_info.get("result")
            error = exec_info.get("error")
            
            # Get progress information updated during execution
            progress = exec_info.get("progress", 0.0)
            current_task = exec_info.get("current_task")
            completed_tasks = exec_info.get("completed_tasks", [])
            failed_tasks = exec_info.get("failed_tasks", [])
            
            # Calculate duration
            duration = exec_info.get("duration")
            
            return ExecutionStatusResponse(
                execution_id=execution_id,
                status=status,
                progress=progress,
                current_task=current_task,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                result=results,
                error=error,
                metadata=exec_info.get("metadata", {})
            )
        else:
            # Workflow-based execution: Get status from workflow engine
            if not workflow_engine:
                raise HTTPException(status_code=503, detail="Workflow engine not initialized")
            
            # Get the workflow execution ID (may be different from our execution_id)
            workflow_execution_id = exec_info.get("workflow_execution_id", execution_id)
            
            status_info = await workflow_engine.get_execution_status(workflow_execution_id)
            execution = await workflow_engine.get_execution(workflow_execution_id)
            
            if not status_info or not execution:
                raise HTTPException(status_code=404, detail=f"Workflow execution {workflow_execution_id} not found in workflow engine")
            
            # Extract information from status
            progress = status_info.get("progress", 0)
            completed_count = status_info.get("completed_tasks", 0)
            total_count = status_info.get("total_tasks", 0)
            workflow_status = status_info.get("status", "running")
            
            # Find current task
            current_task = None
            completed_tasks = []
            failed_tasks = []
            
            if hasattr(execution, 'task_executions'):
                task_list = execution.task_executions if isinstance(execution.task_executions, list) else list(execution.task_executions.values())
                for t in task_list:
                    task_name = t.task_name if hasattr(t, 'task_name') else str(t)
                    task_status = str(t.status).lower() if hasattr(t, 'status') else "unknown"
                    
                    if "running" in task_status:
                        current_task = task_name
                    elif "success" in task_status or "completed" in task_status:
                        completed_tasks.append(task_name)
                    elif "failed" in task_status or "error" in task_status:
                        failed_tasks.append(task_name)
            
            # Calculate duration
            duration = None
            start_time = None
            end_time = None
            
            if hasattr(execution, 'start_time') and execution.start_time:
                start_time = execution.start_time.isoformat() if hasattr(execution.start_time, 'isoformat') else str(execution.start_time)
                end = execution.end_time if hasattr(execution, 'end_time') and execution.end_time else datetime.now()
                if hasattr(execution.start_time, 'timestamp'):
                    duration = (end - execution.start_time).total_seconds()
            
            if hasattr(execution, 'end_time') and execution.end_time:
                end_time = execution.end_time.isoformat() if hasattr(execution.end_time, 'isoformat') else str(execution.end_time)
            
            # Get result and error
            result = None
            error = status_info.get("error")
            
            if "success" in workflow_status.lower():
                # Try to get results from execution.variables (where workflow stores outputs)
                if hasattr(execution, 'variables') and execution.variables:
                    result = execution.variables
                # Fallback to other result attributes
                elif hasattr(execution, 'result') and execution.result:
                    result = execution.result
                elif hasattr(execution, 'outputs') and execution.outputs:
                    result = execution.outputs
                
                # Log what we found
                if result:
                    logger.info(f"Retrieved execution results", execution_id=execution_id, result_keys=list(result.keys()) if isinstance(result, dict) else type(result).__name__)
                else:
                    logger.warning(f"No results found for completed execution", execution_id=execution_id)
            
            # Get metadata from stored execution info
            metadata = exec_info.get("metadata", {})
            
            return ExecutionStatusResponse(
                execution_id=execution_id,
                status=workflow_status,
                progress=progress,
                current_task=current_task,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                result=result,
                error=error,
                metadata=metadata
            )
    else:
        # Historical execution - load from Cosmos DB
        try:
            logger.info("Loading historical execution from Cosmos DB", execution_id=execution_id)
            
            # Get cosmos store instance
            from app.persistence.cosmos_memory import get_cosmos_store
            cosmos = get_cosmos_store()
            await cosmos.initialize()
            
            # Get the run from Cosmos DB using execution_id as run_id
            run = await cosmos.get_run(execution_id)
            
            if not run:
                raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found in history")
            
            # Build execution status from stored run data
            status = run.status
            progress = run.progress
            current_task = run.current_task
            completed_tasks = run.completed_tasks if run.completed_tasks else []
            failed_tasks = run.failed_tasks if run.failed_tasks else []
            
            # Time information
            start_time = run.started_at.isoformat() if run.started_at else None
            end_time = run.completed_at.isoformat() if run.completed_at else None
            duration = run.execution_time
            
            # Build result from stored data
            result = None
            if status == "completed":
                task_results = run.result_sections or run.task_results or {}
                metadata_source = run.metadata or {}

                logger.info(
                    "Rehydrating historical execution",
                    execution_id=execution_id,
                    task_result_keys=list(task_results.keys()) if isinstance(task_results, dict) else type(task_results).__name__,
                    metadata_keys=list(metadata_source.keys()) if isinstance(metadata_source, dict) else type(metadata_source).__name__
                )

                def pick_value(key: str) -> Any:
                    if isinstance(task_results, dict) and task_results.get(key):
                        return task_results.get(key)
                    if isinstance(metadata_source, dict):
                        return metadata_source.get(key)
                    return None

                result = {
                    "research_plan": pick_value("research_plan") or "",
                    "core_concepts": pick_value("core_concepts") or "",
                    "current_state": pick_value("current_state") or "",
                    "applications": pick_value("applications") or "",
                    "challenges": pick_value("challenges") or "",
                    "future_trends": pick_value("future_trends") or "",
                    "final_report": run.research_report
                        or pick_value("final_report")
                        or pick_value("report")
                        or "",
                    "executive_summary": run.summary
                        or pick_value("executive_summary")
                        or pick_value("summary")
                        or "",
                    "validation_results": pick_value("validation_results") or "",
                }

                # Remove empty entries to avoid frontend fallback rendering
                result = {k: v for k, v in result.items() if v}
                if not result:
                    result = None
            
            # Get error if failed
            error = run.error_message
            
            # Metadata - include orchestration pattern and framework info
            metadata = run.metadata if run.metadata else {}
            
            # Add top-level technical details to metadata if available
            if run.orchestration_pattern:
                metadata["orchestration_pattern"] = run.orchestration_pattern
            if run.framework:
                metadata["framework"] = run.framework
            if run.workflow_engine:
                metadata["workflow_engine"] = run.workflow_engine
            
            logger.info("Loaded historical execution", execution_id=execution_id, status=status, progress=progress)
            
            return ExecutionStatusResponse(
                execution_id=execution_id,
                status=status,
                progress=progress,
                current_task=current_task,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                result=result,
                error=error,
                metadata=metadata
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error loading historical execution", execution_id=execution_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"Error loading execution from history: {str(e)}")



@app.get("/api/research/list")
async def list_executions(request: Request):
    """List all research executions (active and recent from Cosmos DB) for the authenticated user."""
    # Extract authenticated user
    from app.auth.auth_utils import get_authenticated_user_details
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    executions = []
    
    # Get active executions (in-memory) for this user
    for exec_id, exec_info in active_executions.items():
        try:
            # Check if this execution belongs to the user
            exec_user_id = exec_info.get("user_id")
            if exec_user_id != user_id:
                continue  # Skip executions from other users
            
            request_info = exec_info.get("request", {})
            execution_mode = request_info.get("execution_mode", "workflow")
            
            if execution_mode in ["code", "maf-workflow"]:
                # Code-based or MAF workflow execution
                executions.append({
                    "execution_id": exec_id,
                    "status": exec_info.get("status", "running"),
                    "topic": request_info.get("topic", "Unknown"),
                    "start_time": exec_info.get("start_time"),
                    "end_time": exec_info.get("end_time"),
                })
            else:
                # Workflow-based execution
                if workflow_engine:
                    status_info = await workflow_engine.get_execution_status(exec_id)
                    execution = await workflow_engine.get_execution(exec_id)
                    
                    if status_info and execution:
                        start_time = None
                        end_time = None
                        
                        if hasattr(execution, 'start_time') and execution.start_time:
                            start_time = execution.start_time.isoformat() if hasattr(execution.start_time, 'isoformat') else str(execution.start_time)
                        
                        if hasattr(execution, 'end_time') and execution.end_time:
                            end_time = execution.end_time.isoformat() if hasattr(execution.end_time, 'isoformat') else str(execution.end_time)
                        
                        executions.append({
                            "execution_id": exec_id,
                            "status": status_info.get("status", "unknown"),
                            "topic": request_info.get("topic", "Unknown"),
                            "start_time": start_time,
                            "end_time": end_time,
                        })
        except Exception as e:
            logger.error(f"Error getting active execution info", execution_id=exec_id, error=str(e))
    
    # Get recent completed executions from Cosmos DB (last 24 hours) for this user
    try:
        from app.persistence.cosmos_memory import get_cosmos_store
        from datetime import datetime, timedelta
        
        cosmos = get_cosmos_store()
        await cosmos.ensure_initialized()
        
        # Get recent runs (last 50) for this specific user
        query = """
        SELECT c.run_id, c.status, c.topic, c.started_at, c.completed_at
        FROM c 
        WHERE c.data_type='research_run' 
        AND c.user_id=@user_id
        AND c.started_at >= @cutoff_time
        ORDER BY c.started_at DESC
        OFFSET 0 LIMIT 50
        """
        
        # Get runs from last 24 hours
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@cutoff_time", "value": cutoff}
        ]
        
        query_iter = cosmos._container.query_items(
            query=query,
            parameters=parameters
        )
        
        async for item in query_iter:
            # Only add if not already in active executions
            if item['run_id'] not in active_executions:
                executions.append({
                    "execution_id": item['run_id'],
                    "status": item.get('status', 'unknown'),
                    "topic": item.get('topic', 'Unknown'),
                    "start_time": item.get('started_at'),
                    "end_time": item.get('completed_at'),
                })
    except Exception as e:
        logger.warning(f"Failed to load recent executions from Cosmos DB", error=str(e))
    
    return {"executions": executions}


@app.get("/api/models/deployments")
async def get_deployments():
    """
    Get all Azure OpenAI deployments available in the AI Foundry resource.
    Returns chat and embedding model deployments with metadata.
    """
    try:
        from .services.azure_openai_deployment_service import get_deployment_service
        
        # Get configuration from environment
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_AI_FOUNDRY_RESOURCE_GROUP")
        
        # Extract account name from endpoint
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        account_name = endpoint.split("//")[1].split(".")[0] if "//" in endpoint else ""
        
        if not all([subscription_id, resource_group, account_name]):
            logger.error("Missing Azure configuration for deployment service")
            raise HTTPException(
                status_code=500,
                detail="Azure OpenAI configuration incomplete. Check AZURE_SUBSCRIPTION_ID, AZURE_AI_FOUNDRY_RESOURCE_GROUP, and AZURE_OPENAI_ENDPOINT"
            )
        
        async with get_deployment_service(subscription_id, resource_group, account_name) as service:
            summary = await service.get_deployments_summary()
            return summary
            
    except Exception as e:
        logger.error(f"Error fetching deployments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch deployments: {str(e)}")


@app.get("/api/models/config")
async def get_model_configs():
    """
    Get model configurations for all research depth levels.
    Shows recommended models, temperature, max_tokens for each depth.
    """
    try:
        from .services.azure_openai_deployment_service import get_deployment_service
        from .services.model_config_service import ModelConfigService
        
        # Get configuration from environment
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_AI_FOUNDRY_RESOURCE_GROUP")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        account_name = endpoint.split("//")[1].split(".")[0] if "//" in endpoint else ""
        
        if not all([subscription_id, resource_group, account_name]):
            logger.error("Missing Azure configuration")
            raise HTTPException(status_code=500, detail="Azure configuration incomplete")
        
        # Fetch available deployments
        async with get_deployment_service(subscription_id, resource_group, account_name) as service:
            summary = await service.get_deployments_summary()
            chat_models = summary.get("chat_models", [])
        
        # Create model config service with available deployments
        config_service = ModelConfigService(available_deployments=chat_models)
        
        # Get configurations for all depth levels
        all_configs = config_service.get_all_depth_configs()
        
        return {
            "depth_configs": all_configs,
            "available_chat_models": chat_models
        }
        
    except Exception as e:
        logger.error(f"Error fetching model configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch model configs: {str(e)}")


@app.get("/api/models/for-depth/{depth}")
async def get_models_for_depth(depth: str):
    """
    Get recommended models for a specific research depth.
    
    Args:
        depth: Research depth (quick, standard, comprehensive, exhaustive)
    """
    if depth not in ["quick", "standard", "comprehensive", "exhaustive"]:
        raise HTTPException(status_code=400, detail=f"Invalid depth: {depth}")
    
    try:
        from .services.azure_openai_deployment_service import get_deployment_service
        from .services.model_config_service import ModelConfigService
        
        # Get configuration from environment
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_AI_FOUNDRY_RESOURCE_GROUP")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        account_name = endpoint.split("//")[1].split(".")[0] if "//" in endpoint else ""
        
        # Fetch available deployments
        async with get_deployment_service(subscription_id, resource_group, account_name) as service:
            summary = await service.get_deployments_summary()
            chat_models = summary.get("chat_models", [])
        
        # Create model config service
        config_service = ModelConfigService(available_deployments=chat_models)
        
        # Get recommended models for this depth
        recommended_models = config_service.get_available_models_for_depth(depth)
        
        # Get optimal config
        model_config = config_service.get_model_config_for_depth(depth)
        
        # Get the depth config to extract preferred models
        from .services.model_config_service import MODEL_CONFIGS_BY_DEPTH
        depth_config = MODEL_CONFIGS_BY_DEPTH.get(depth, {})
        
        # Return config in the format expected by frontend
        return {
            "deployment_name": model_config.deployment_name,
            "model_name": model_config.model_name,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens,
            "use_reasoning_model": model_config.use_reasoning_model,
            "preferred_models": depth_config.get("preferred_models", []),
            "depth": depth,
            "recommended_models": recommended_models
        }
        
    except Exception as e:
        logger.error(f"Error fetching models for depth {depth}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch models for depth: {str(e)}")


# ============================================================
# EXPORT ENDPOINTS
# ============================================================

class ExportRequest(BaseModel):
    """Request model for export endpoint"""
    execution_id: str
    include_metadata: bool = True

@app.post("/api/export/{format}")
async def export_report(
    format: str,
    request: ExportRequest
):
    """Export research report in specified format.
    
    Args:
        format: Export format (markdown, pdf, html)
        request: Export request with execution_id and include_metadata
        
    Returns:
        FileResponse with the exported file
    """
    try:
        # Validate format
        valid_formats = ["markdown", "pdf", "html"]
        if format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Get execution data - check active executions first, then Cosmos DB
        execution_data = None
        final_report = None
        title = "Research Report"
        
        if request.execution_id in active_executions:
            # Active execution - get from memory
            execution_data = active_executions[request.execution_id]
            final_report = execution_data.get("results", {}).get("final_report")
            title = execution_data.get("topic", "Research Report")
        else:
            # Historical execution - load from Cosmos DB
            try:
                logger.info("Loading historical execution from Cosmos DB for export", execution_id=request.execution_id)
                
                from app.persistence.cosmos_memory import get_cosmos_store
                cosmos = get_cosmos_store()
                await cosmos.initialize()
                
                run = await cosmos.get_run(request.execution_id)
                
                if not run:
                    raise HTTPException(status_code=404, detail=f"Execution {request.execution_id} not found")
                
                # Get final report from stored data
                final_report = run.research_report
                title = run.metadata.get("topic", "Research Report") if run.metadata else "Research Report"
                
                logger.info("Loaded historical execution for export", execution_id=request.execution_id)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Error loading historical execution for export", execution_id=request.execution_id, error=str(e))
                raise HTTPException(status_code=500, detail=f"Error loading execution: {str(e)}")
        
        if not final_report:
            raise HTTPException(status_code=404, detail="No report content found for this execution")
        
        # Generate export ID
        export_id = f"{request.execution_id}_{int(datetime.now().timestamp())}"
        
        # Get export service
        export_service = get_export_service()
        
        # Export based on format
        if format == "markdown":
            file_path = await export_service.export_markdown(
                report_content=final_report,
                title=title,
                export_id=export_id,
                include_metadata=request.include_metadata
            )
            media_type = "text/markdown"
            filename = f"{title.replace(' ', '_')}.md"
            
        elif format == "pdf":
            file_path = await export_service.export_pdf(
                report_content=final_report,
                title=title,
                export_id=export_id,
                include_metadata=request.include_metadata
            )
            media_type = "application/pdf"
            filename = f"{title.replace(' ', '_')}.pdf"
            
        elif format == "html":
            file_path = await export_service.export_html(
                report_content=final_report,
                title=title,
                export_id=export_id,
                include_metadata=request.include_metadata
            )
            media_type = "text/html"
            filename = f"{title.replace(' ', '_')}.html"
        
        logger.info(f"Export successful", format=format, export_id=export_id, file_path=file_path)
        
        # Return file as download - FileResponse automatically sets Content-Disposition when filename is provided
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed", format=format, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.websocket("/ws/research/{execution_id}")
async def websocket_research_updates(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint for real-time research updates."""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        logger.info(f"WebSocket connected for execution {execution_id}")
        
        # Check if this is an active execution
        if execution_id not in active_executions:
            # Historical execution - load from Cosmos DB and send complete state
            logger.info(f"Loading historical execution from Cosmos DB for WebSocket", execution_id=execution_id)
            
            try:
                from app.persistence.cosmos_memory import get_cosmos_store
                cosmos = get_cosmos_store()
                await cosmos.initialize()
                
                run = await cosmos.get_run(execution_id)
                
                if run:
                    # Send initial status with historical data
                    await websocket.send_json({
                        "type": "status",
                        "execution_id": execution_id,
                        "status": run.status,
                        "message": "Loaded historical execution"
                    })
                    
                    # Send task details from execution_details if available
                    if run.execution_details and "tasks" in run.execution_details:
                        for task in run.execution_details["tasks"]:
                            await websocket.send_json({
                                "type": "task_update",
                                "execution_id": execution_id,
                                "task_id": task.get("task_number", 0),
                                "task_name": task.get("name", "Unknown"),
                                "status": task.get("status", "unknown"),
                                "agent": task.get("agent", ""),
                                "output": task.get("output", ""),
                                "duration": task.get("duration")
                            })
                    
                    # Send final completion status
                    result_data = None
                    if run.metadata:
                        result_data = {
                            "research_plan": run.metadata.get("research_plan", ""),
                            "core_concepts": run.metadata.get("core_concepts", ""),
                            "current_state": run.metadata.get("current_state", ""),
                            "applications": run.metadata.get("applications", ""),
                            "challenges": run.metadata.get("challenges", ""),
                            "future_trends": run.metadata.get("future_trends", ""),
                            "final_report": run.research_report or "",
                            "executive_summary": run.summary or ""
                        }
                    
                    await websocket.send_json({
                        "type": "completed",
                        "execution_id": execution_id,
                        "status": run.status,
                        "result": result_data,
                        "error": run.error_message
                    })
                    
                    # Keep connection open but don't send further updates
                    while True:
                        await asyncio.sleep(10)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "execution_id": execution_id,
                        "error": "Execution not found in active executions or history"
                    })
                    return
                    
            except Exception as e:
                logger.error(f"Error loading historical execution", execution_id=execution_id, error=str(e))
                await websocket.send_json({
                    "type": "error",
                    "execution_id": execution_id,
                    "error": f"Failed to load execution: {str(e)}"
                })
                return
        
        # Active execution - original logic
        exec_info = active_executions[execution_id]
        
        # Determine execution mode and send initial status
        if "execution" in exec_info and hasattr(exec_info.get("execution"), 'status'):
            # YAML workflow mode
            execution = exec_info["execution"]
            await websocket.send_json({
                "type": "status",
                "execution_id": execution_id,
                "status": execution.status.value,
                "message": "Connected to execution updates"
            })
        else:
            # Code-based or MAF workflow mode
            await websocket.send_json({
                "type": "status",
                "execution_id": execution_id,
                "status": exec_info.get("status", "running"),
                "message": "Connected to execution updates"
            })
        
        # Keep connection alive and send updates
        while True:
            if execution_id in active_executions:
                exec_info = active_executions[execution_id]
                
                # Handle different execution modes
                if "execution" in exec_info and hasattr(exec_info["execution"], 'tasks'):
                    # YAML workflow mode - has execution object with tasks
                    execution = exec_info["execution"]
                    
                    # Send task updates
                    for task_id, task in execution.tasks.items():
                        await websocket.send_json({
                            "type": "task_update",
                            "execution_id": execution_id,
                            "task_id": task_id,
                            "task_name": task.name,
                            "status": task.status.value,
                            "result": task.result if task.status == TaskStatus.SUCCESS else None
                        })
                    
                    # Check if execution is complete
                    if execution.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                        await websocket.send_json({
                            "type": "completed",
                            "execution_id": execution_id,
                            "status": execution.status.value,
                            "result": execution.result,
                            "error": execution.error
                        })
                        break
                else:
                    # Code-based or MAF workflow mode - dict-based structure
                    status = exec_info.get("status", "running")
                    
                    # Send progress update
                    await websocket.send_json({
                        "type": "progress",
                        "execution_id": execution_id,
                        "status": status,
                        "progress": exec_info.get("progress", 0.0),
                        "current_task": exec_info.get("current_task"),
                        "message": f"Progress: {exec_info.get('progress', 0):.1f}%"
                    })
                    
                    # Check if execution is complete
                    if status in ["success", "failed", "cancelled"]:
                        await websocket.send_json({
                            "type": "completed",
                            "execution_id": execution_id,
                            "status": status,
                            "result": exec_info.get("result"),
                            "error": exec_info.get("error")
                        })
                        break
            
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for execution {execution_id}")
    except Exception as e:
        logger.error(f"WebSocket error", error=str(e))
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


async def save_execution_to_cosmos(execution_id: str, status: str, results: Dict[str, Any], execution_details: Optional[Dict[str, Any]] = None):
    """
    Helper function to save execution results to Cosmos DB.
    Works for all execution modes: workflow, code, maf-workflow.
    """
    try:
        exec_info = active_executions.get(execution_id, {})
        run_id = exec_info.get("run_id")
        session_id = exec_info.get("session_id")
        
        logger.info(f"💾 Saving execution to Cosmos DB: execution_id={execution_id}, run_id={run_id}, status={status}")
        
        if not run_id or not session_id:
            logger.warning(f"⚠️ Cannot save - missing run_id or session_id: run_id={run_id}, session_id={session_id}")
            return
        
        from app.persistence.cosmos_memory import get_cosmos_store
        cosmos = get_cosmos_store()
        
        # Prepare update data
        update_data = {
            "status": "completed" if status in ["success", "completed"] else "failed",
            "progress": 100.0 if status in ["success", "completed"] else exec_info.get("progress", 0),
            "completed_at": datetime.now(timezone.utc),
        }
        
        # Add execution details if provided (from workflow mode)
        if execution_details:
            update_data["execution_details"] = sanitize_for_json(execution_details)
        
        # Extract and save results
        metadata_fields = [
            "research_plan",
            "core_concepts",
            "current_state",
            "applications",
            "challenges",
            "future_trends",
            "draft_report",
            "validation_results",
        ]

        if results:
            safe_results = sanitize_for_json(results)

            if isinstance(safe_results, dict):
                logger.info(
                    "Persisting research results",
                    execution_id=execution_id,
                    result_keys=list(safe_results.keys()),
                    has_nested_result="result" in safe_results,
                    has_metadata="metadata" in safe_results
                )
                logger.debug(
                    "Sanitized research results",
                    result_keys=list(safe_results.keys()),
                    execution_id=execution_id
                )

                def collect_candidate_dicts(root: Any) -> List[Dict[str, Any]]:
                    candidates: List[Dict[str, Any]] = []
                    seen: Set[int] = set()
                    stack: List[Any] = [root]
                    while stack:
                        current = stack.pop()
                        identity = id(current)
                        if identity in seen:
                            continue
                        seen.add(identity)
                        if isinstance(current, dict):
                            candidates.append(current)
                            for nested_value in current.values():
                                if isinstance(nested_value, (dict, list, tuple)):
                                    stack.append(nested_value)
                        elif isinstance(current, (list, tuple)):
                            for item in current:
                                if isinstance(item, (dict, list, tuple)):
                                    stack.append(item)
                    return candidates

                candidate_dicts = collect_candidate_dicts(safe_results)

                def extract_value(*aliases: str):
                    for candidate in candidate_dicts:
                        for alias in aliases:
                            if alias in candidate:
                                value = candidate[alias]
                                if value not in (None, "", [], {}):
                                    return value
                    return None

                section_aliases = {
                    "research_plan": ("research_plan", "plan"),
                    "core_concepts": ("core_concepts",),
                    "current_state": ("current_state",),
                    "applications": ("applications",),
                    "challenges": ("challenges",),
                    "future_trends": ("future_trends",),
                    "draft_report": ("draft_report", "draftReport"),
                    "final_report": ("final_report", "report", "finalReport"),
                    "executive_summary": ("executive_summary", "summary", "executiveSummary"),
                    "validation_results": ("validation_results", "validation", "validationResults"),
                    "citations": ("citations", "references"),
                    "sources": ("sources", "source_list"),
                    "sources_count": ("sources_count", "sources_analyzed", "sourcesAnalyzed", "total_sources"),
                    "source_quality": ("source_quality", "sourceQuality"),
                }

                extracted_sections: Dict[str, Any] = {}
                for canonical, aliases in section_aliases.items():
                    value = extract_value(*aliases)
                    if value not in (None, "", [], {}):
                        extracted_sections[canonical] = value

                logger.info(
                    "Extracted canonical sections from research results",
                    execution_id=execution_id,
                    section_keys=list(extracted_sections.keys())
                )

                final_report = extracted_sections.get("final_report") or safe_results.get("final_report") or safe_results.get("report")
                summary_text = extracted_sections.get("executive_summary") or safe_results.get("executive_summary") or safe_results.get("summary")
                research_plan_value = extracted_sections.get("research_plan") or safe_results.get("research_plan")
                citations_value = extracted_sections.get("citations") or safe_results.get("citations")
                sources_value = extracted_sections.get("sources") or safe_results.get("sources")
                validation_value = extracted_sections.get("validation_results") or safe_results.get("validation_results")
                sources_count_value = extracted_sections.get("sources_count") or extract_value("sources_analyzed", "sourcesAnalyzed", "total_sources")

                if final_report:
                    update_data["research_report"] = final_report

                if summary_text:
                    update_data["summary"] = summary_text

                if research_plan_value:
                    update_data["research_plan"] = research_plan_value

                if citations_value:
                    update_data["citations"] = citations_value

                if sources_count_value is not None:
                    try:
                        update_data["sources_analyzed"] = int(float(sources_count_value))
                    except (TypeError, ValueError):
                        pass
                elif safe_results.get("sources_analyzed") is not None:
                    update_data["sources_analyzed"] = safe_results.get("sources_analyzed")

                task_results_payload = dict(safe_results)
                for key, value in extracted_sections.items():
                    task_results_payload.setdefault(key, value)
                update_data["task_results"] = task_results_payload

                if extracted_sections:
                    update_data["result_sections"] = extracted_sections

                # Merge selected result fields into metadata while preserving original metadata
                existing_metadata = sanitize_for_json(exec_info.get("metadata", {}))
                metadata_update = dict(existing_metadata) if isinstance(existing_metadata, dict) else {}

                for key in metadata_fields:
                    value = extracted_sections.get(key) or safe_results.get(key)
                    if value:
                        metadata_update[key] = value

                if summary_text:
                    metadata_update["executive_summary"] = summary_text
                if final_report:
                    metadata_update["final_report"] = final_report
                if citations_value:
                    metadata_update["citations"] = citations_value
                if sources_value and isinstance(sources_value, (list, dict, str)):
                    metadata_update["sources"] = sources_value
                if validation_value:
                    metadata_update["validation_results"] = validation_value
                if extracted_sections.get("source_quality"):
                    metadata_update["source_quality"] = extracted_sections["source_quality"]
                if extracted_sections:
                    metadata_update["result_sections"] = extracted_sections
                if task_results_payload:
                    metadata_update["raw_results"] = task_results_payload

                update_data["metadata"] = metadata_update

                # Also save orchestration pattern and framework info at top level (if present)
                if metadata_update:
                    pattern = metadata_update.get("orchestration_pattern")
                    framework = metadata_update.get("framework")
                    engine = metadata_update.get("workflow_engine")

                    if pattern:
                        update_data["orchestration_pattern"] = pattern
                    if framework:
                        update_data["framework"] = framework
                    if engine:
                        update_data["workflow_engine"] = engine
            else:
                update_data["task_results"] = safe_results
        
        # Add completed tasks from exec_info
        if "completed_tasks" in exec_info:
            update_data["completed_tasks"] = sanitize_for_json(exec_info["completed_tasks"])
        
        await cosmos.update_run(run_id, update_data)
        logger.info(f"✅ Saved execution to Cosmos DB successfully", run_id=run_id, status=update_data["status"])
        
    except Exception as e:
        logger.error(f"❌ Failed to save execution to Cosmos DB: {e}", exc_info=True)


async def monitor_execution(execution_id: str):
    """Background task to monitor workflow execution and broadcast updates."""
    try:
        logger.info(f"🔍 Starting monitor_execution for execution_id={execution_id}")
        
        if not workflow_engine:
            logger.error("Workflow engine not available for monitoring")
            return
        
        execution_complete = False
        
        # Get the workflow execution ID (stored when workflow was started)
        exec_info = active_executions.get(execution_id, {})
        workflow_execution_id = exec_info.get("workflow_execution_id", execution_id)
        
        logger.info(f"🔍 Monitoring workflow_execution_id={workflow_execution_id} for execution_id={execution_id}")
        
        while not execution_complete:
            try:
                # Get status from workflow engine using workflow_execution_id
                status = await workflow_engine.get_execution_status(workflow_execution_id)
                execution = await workflow_engine.get_execution(workflow_execution_id)
                
                if not status:
                    logger.warning(f"No status found for workflow_execution_id {workflow_execution_id}")
                    await asyncio.sleep(2)
                    continue
                
                workflow_status = status.get("status", "").lower()
                
                # Update ResearchRun progress in Cosmos DB periodically
                try:
                    exec_info = active_executions.get(execution_id, {})
                    run_id = exec_info.get("run_id")
                    
                    if run_id:
                        from app.persistence.cosmos_memory import get_cosmos_store
                        cosmos = get_cosmos_store()
                        
                        progress_update = {
                            "status": "running",
                            "progress": status.get("progress", 0),
                        }
                        
                        # Add task execution details if available
                        if execution and hasattr(execution, 'task_executions'):
                            task_list = execution.task_executions if isinstance(execution.task_executions, list) else list(execution.task_executions.values())
                            completed_tasks = [
                                t.task_name if hasattr(t, 'task_name') else str(t)
                                for t in task_list
                                if hasattr(t, 'status') and str(t.status).lower() in ["completed", "success"]
                            ]
                            if completed_tasks:
                                progress_update["completed_tasks"] = completed_tasks
                        
                        await cosmos.update_run(run_id, progress_update)
                except Exception as e:
                    logger.debug(f"Failed to update progress in Cosmos DB: {e}")
                
                # Broadcast updates to all connected WebSocket clients
                for ws in websocket_connections[:]:
                    try:
                        update_data = {
                            "type": "progress",
                            "execution_id": execution_id,
                            "status": workflow_status,
                            "progress": status.get("progress", 0),
                            "completed_tasks": status.get("completed_tasks", 0),
                            "total_tasks": status.get("total_tasks", 0)
                        }
                        
                        # Add task details if available
                        if execution and hasattr(execution, 'task_executions'):
                            task_list = execution.task_executions if isinstance(execution.task_executions, list) else list(execution.task_executions.values())
                            update_data["tasks"] = []
                            for t in task_list:
                                update_data["tasks"].append({
                                    "name": t.task_name if hasattr(t, 'task_name') else str(t),
                                    "status": str(t.status).lower() if hasattr(t, 'status') else "unknown"
                                })
                        
                        await ws.send_json(update_data)
                    except Exception as e:
                        logger.warning(f"Failed to send WebSocket update", error=str(e))
                        if ws in websocket_connections:
                            websocket_connections.remove(ws)
                
                # Check if complete
                if workflow_status in ["success", "failed", "cancelled", "workflowstatus.success"]:
                    execution_complete = True
                    logger.info(f"✅ Execution {execution_id} completed with status {workflow_status}")
                    
                    # Extract execution details for Cosmos DB
                    try:
                        # Extract ALL execution details
                        execution_details = {
                            "workflow_name": execution.workflow_name if hasattr(execution, 'workflow_name') else None,
                            "workflow_status": workflow_status,
                            "start_time": execution.start_time.isoformat() if hasattr(execution, 'start_time') and execution.start_time else None,
                            "end_time": execution.end_time.isoformat() if hasattr(execution, 'end_time') and execution.end_time else None,
                            "duration": execution.duration if hasattr(execution, 'duration') else None,
                            "total_tasks": status.get("total_tasks", 0),
                            "completed_tasks_count": status.get("completed_tasks", 0),
                        }
                        
                        # Extract task execution details
                        task_details = []
                        if hasattr(execution, 'task_executions'):
                            task_list = execution.task_executions if isinstance(execution.task_executions, list) else list(execution.task_executions.values())
                            for t in task_list:
                                task_info = {
                                    "task_name": t.task_name if hasattr(t, 'task_name') else str(t),
                                    "status": str(t.status) if hasattr(t, 'status') else "unknown",
                                    "start_time": t.start_time.isoformat() if hasattr(t, 'start_time') and t.start_time else None,
                                    "end_time": t.end_time.isoformat() if hasattr(t, 'end_time') and t.end_time else None,
                                    "duration": t.duration if hasattr(t, 'duration') else None,
                                    "agent": t.agent if hasattr(t, 'agent') else None,
                                    "error": t.error if hasattr(t, 'error') else None,
                                }
                                if hasattr(t, 'output'):
                                    task_info["output"] = t.output
                                elif hasattr(t, 'result'):
                                    task_info["result"] = t.result
                                task_details.append(task_info)
                        
                        execution_details["tasks"] = task_details
                        
                        # Get final results
                        final_results = {}
                        if hasattr(execution, 'variables') and execution.variables:
                            final_results = execution.variables
                        elif hasattr(execution, 'output_variables'):
                            final_results = execution.output_variables
                        
                        # Save to Cosmos DB
                        await save_execution_to_cosmos(
                            execution_id=execution_id,
                            status=workflow_status,
                            results=final_results,
                            execution_details=execution_details
                        )
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to save workflow execution to Cosmos DB: {e}", exc_info=True)
                    
                    break
                
            except Exception as e:
                logger.error(f"Error in monitoring loop", execution_id=execution_id, error=str(e))
                break
            
            await asyncio.sleep(2)
        
    except Exception as e:
        logger.error(f"Error monitoring execution {execution_id}", error=str(e))


async def execute_maf_workflow_research_task(
    execution_id: str,
    topic: str,
    max_sources: int,
    document_context_data: Optional[Dict[str, Any]] = None
):
    """Background task to execute MAF graph-based workflow research."""
    try:
        logger.info(f"Starting MAF workflow research execution", execution_id=execution_id, topic=topic)
        
        # Extract document context if available
        document_context = ""
        document_sources = []
        has_documents = False
        
        if document_context_data:
            document_context = document_context_data.get("document_context", "")
            document_sources = document_context_data.get("document_sources", [])
            has_documents = len(document_context) > 0
            logger.info(
                f"📄 MAF workflow will include document context",
                doc_words=document_context_data.get("document_stats", {}).get("total_words", 0),
                doc_pages=document_context_data.get("document_stats", {}).get("total_pages", 0)
            )
        
        # Update initial progress
        if execution_id in active_executions:
            active_executions[execution_id]["progress"] = 0.0
            active_executions[execution_id]["current_task"] = "Initializing MAF workflow..."
        
        # Get Azure OpenAI and Tavily clients
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "chat4o")
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if not all([azure_endpoint, azure_api_key, tavily_api_key]):
            raise ValueError("Missing required API credentials for MAF workflow")
        
        # Create clients
        azure_client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version="2024-08-01-preview"
        )
        
        tavily_client = TavilyClient(api_key=tavily_api_key)
        
        # Update progress
        if execution_id in active_executions:
            active_executions[execution_id]["progress"] = 10.0
            active_executions[execution_id]["current_task"] = "Creating workflow graph..."
        
        # Execute MAF workflow with progress callback
        completed_executors = set()
        total_executors = 7  # planner + 3 researchers + synthesizer + reviewer + summarizer
        
        async def progress_callback(event_type: str, executor_id: str = None):
            """Update progress based on workflow events."""
            if execution_id not in active_executions:
                return
            
            if event_type == "executor_completed" and executor_id:
                completed_executors.add(executor_id)
                progress = 10 + (len(completed_executors) / total_executors) * 80  # 10-90%
                active_executions[execution_id]["progress"] = progress
                active_executions[execution_id]["current_task"] = f"Completed: {executor_id}"
                active_executions[execution_id]["completed_tasks"].append(executor_id)
        
        # Execute MAF workflow with multi-query configuration
        results = await maf_workflow.execute_maf_workflow_research(
            topic=topic,
            execution_id=execution_id,
            azure_client=azure_client,
            tavily_api_key=tavily_api_key,  # Pass API key instead of client
            model=azure_deployment,
            max_sources=max_sources,
            queries_per_area=2,  # Multi-query deep research
            results_per_query=5,
            progress_callback=progress_callback,
            document_context=document_context,
            document_sources=document_sources
        )
        
        # Update execution status with results
        if execution_id in active_executions:
            active_executions[execution_id]["status"] = results.get("status", "success")
            active_executions[execution_id]["progress"] = 100.0
            active_executions[execution_id]["current_task"] = "Completed"
            active_executions[execution_id]["end_time"] = datetime.now().isoformat()
            active_executions[execution_id]["result"] = results
            
            start_time = datetime.fromisoformat(active_executions[execution_id]["start_time"])
            duration = (datetime.now() - start_time).total_seconds()
            active_executions[execution_id]["duration"] = duration
            
            # Build execution_details from completed_tasks
            exec_info = active_executions[execution_id]
            completed_tasks = exec_info.get("completed_tasks", [])
            
            execution_details = {
                "tasks": [],
                "total_duration": duration,
                "execution_mode": "maf-workflow"
            }
            
            # Map completed executors to task details
            for i, executor_id in enumerate(completed_tasks, 1):
                execution_details["tasks"].append({
                    "task_number": i,
                    "name": executor_id,
                    "status": "completed",
                    "agent": executor_id,
                    "output": "",  # MAF workflow doesn't provide per-executor output
                    "duration": None
                })
            
            # Save to Cosmos DB with execution details
            await save_execution_to_cosmos(
                execution_id=execution_id,
                status=results.get("status", "success"),
                results=results,
                execution_details=execution_details
            )
            
            # Broadcast completion to WebSocket clients
            for ws in websocket_connections[:]:
                try:
                    await ws.send_json({
                        "type": "complete",
                        "execution_id": execution_id,
                        "status": results.get("status", "success"),
                        "results": results
                    })
                except Exception as e:
                    logger.warning(f"Failed to send completion WebSocket update", error=str(e))
                    if ws in websocket_connections:
                        websocket_connections.remove(ws)
        
        logger.info(f"MAF workflow research completed", execution_id=execution_id, status=results.get("status"))
        
    except Exception as e:
        logger.error(f"Error in MAF workflow research execution", execution_id=execution_id, error=str(e))
        
        # Update execution status with error
        if execution_id in active_executions:
            active_executions[execution_id]["status"] = "failed"
            active_executions[execution_id]["end_time"] = datetime.now().isoformat()
            active_executions[execution_id]["error"] = str(e)
            
            # Build execution_details for failed execution
            exec_info = active_executions[execution_id]
            completed_tasks = exec_info.get("completed_tasks", [])
            current_task = exec_info.get("current_task")
            
            execution_details = {
                "tasks": [],
                "execution_mode": "maf-workflow",
                "error": str(e)
            }
            
            # Add completed executors
            for i, executor_id in enumerate(completed_tasks, 1):
                execution_details["tasks"].append({
                    "task_number": i,
                    "name": executor_id,
                    "status": "completed",
                    "agent": executor_id,
                    "output": ""
                })
            
            # Add current task as failed
            if current_task and current_task != "Initializing MAF workflow...":
                execution_details["tasks"].append({
                    "task_number": len(completed_tasks) + 1,
                    "name": current_task,
                    "status": "failed",
                    "agent": "maf-workflow",
                    "output": f"Error: {str(e)}"
                })
            
            # Save error to Cosmos DB with execution details
            await save_execution_to_cosmos(
                execution_id=execution_id,
                status="failed",
                results={"error": str(e)},
                execution_details=execution_details
            )
            
            # Broadcast error to WebSocket clients
            for ws in websocket_connections[:]:
                try:
                    await ws.send_json({
                        "type": "error",
                        "execution_id": execution_id,
                        "status": "failed",
                        "error": str(e)
                    })
                except Exception as e2:
                    logger.warning(f"Failed to send error WebSocket update", error=str(e2))
                    if ws in websocket_connections:
                        websocket_connections.remove(ws)


async def execute_code_based_research(
    execution_id: str,
    registry: AgentRegistry,
    orchestrator_instance: MagenticOrchestrator,
    topic: str,
    depth: str,
    max_sources: int,
    include_citations: bool,
    document_context_data: Optional[Dict[str, Any]] = None,
    model_deployment: Optional[str] = None
):
    """Background task to execute code-based (programmatic) research with orchestrator."""
    try:
        logger.info(f"Starting code-based research execution with orchestrator", execution_id=execution_id, topic=topic)
        
        # Call the programmatic execution function with orchestrator
        results = await execute_research_programmatically(
            agent_registry=registry,
            orchestrator_instance=orchestrator_instance,
            execution_id=execution_id,
            topic=topic,
            depth=depth,
            max_sources=max_sources,
            include_citations=include_citations,
            document_context_data=document_context_data,
            model_deployment=model_deployment
        )
        
        # Update execution status with results
        if execution_id in active_executions:
            active_executions[execution_id]["status"] = "success"  # Use 'success' to match workflow engine
            active_executions[execution_id]["end_time"] = datetime.now().isoformat()
            active_executions[execution_id]["results"] = results
            
            start_time = datetime.fromisoformat(active_executions[execution_id]["start_time"])
            duration = (datetime.now() - start_time).total_seconds()
            active_executions[execution_id]["duration"] = duration
            
            # Build execution_details from completed_tasks and results
            exec_info = active_executions[execution_id]
            completed_tasks = exec_info.get("completed_tasks", [])
            
            # Create execution details with task breakdown
            execution_details = {
                "tasks": [],
                "total_duration": duration,
                "execution_mode": "code"
            }
            
            # Map completed tasks to execution details with actual research outputs
            # Build comprehensive output for Phase 2 (5 concurrent research tasks)
            phase2_outputs = []
            if results.get("core_concepts"):
                phase2_outputs.append(f"**Core Concepts:**\n{results['core_concepts']}")
            if results.get("current_state"):
                phase2_outputs.append(f"**Current State:**\n{results['current_state']}")
            if results.get("applications"):
                phase2_outputs.append(f"**Applications:**\n{results['applications']}")
            if results.get("challenges"):
                phase2_outputs.append(f"**Challenges:**\n{results['challenges']}")
            if results.get("future_trends"):
                phase2_outputs.append(f"**Future Trends:**\n{results['future_trends']}")
            
            phase2_combined_output = "\n\n".join(phase2_outputs) if phase2_outputs else "Completed 5 concurrent research tasks"
            
            # Build comprehensive output for Phase 3-6 (synthesis results)
            phase3_outputs = []
            if results.get("draft_report"):
                phase3_outputs.append(f"**Draft Report (Writer):**\n{results['draft_report']}")
            if results.get("validation_results"):
                phase3_outputs.append(f"**Validation Results (Reviewer):**\n{results['validation_results']}")
            if results.get("executive_summary"):
                phase3_outputs.append(f"**Executive Summary (Summarizer):**\n{results['executive_summary']}")
            
            phase3_combined_output = "\n\n".join(phase3_outputs) if phase3_outputs else results.get("final_report", "")
            
            task_mapping = {
                "Phase 1: Research Planning (sequential)": {
                    "agent": "planner",
                    "output": results.get("research_plan", "")
                },
                "Phase 2: Concurrent Investigation (ConcurrentPattern)": {
                    "agent": "researcher (concurrent)",
                    "output": phase2_combined_output
                },
                "Phase 3-6: Synthesis, Validation, Finalization, Summarization (sequential)": {
                    "agent": "writer → reviewer → summarizer",
                    "output": phase3_combined_output
                }
            }
            
            for i, task_name in enumerate(completed_tasks, 1):
                task_info = task_mapping.get(task_name, {})
                execution_details["tasks"].append({
                    "task_number": i,
                    "name": task_name,
                    "status": "completed",
                    "agent": task_info.get("agent", "unknown"),
                    "output": task_info.get("output", ""),
                    "duration": None  # Code mode doesn't track per-task duration
                })
            
            # Save to Cosmos DB with execution details
            await save_execution_to_cosmos(
                execution_id=execution_id,
                status="success",
                results=results,
                execution_details=execution_details
            )
            
            # Broadcast completion to WebSocket clients
            for ws in websocket_connections[:]:
                try:
                    await ws.send_json({
                        "type": "complete",
                        "execution_id": execution_id,
                        "status": "success",
                        "results": results
                    })
                except Exception as e:
                    logger.warning(f"Failed to send completion WebSocket update", error=str(e))
                    if ws in websocket_connections:
                        websocket_connections.remove(ws)
        
        logger.info(f"Code-based research completed successfully", execution_id=execution_id)
        
    except Exception as e:
        logger.error(f"Error in code-based research execution", execution_id=execution_id, error=str(e))
        
        # Update execution status with error
        if execution_id in active_executions:
            active_executions[execution_id]["status"] = "failed"
            active_executions[execution_id]["end_time"] = datetime.now().isoformat()
            active_executions[execution_id]["error"] = str(e)
            
            # Build execution_details even for failed executions
            exec_info = active_executions[execution_id]
            completed_tasks = exec_info.get("completed_tasks", [])
            current_task = exec_info.get("current_task")
            
            execution_details = {
                "tasks": [],
                "execution_mode": "code",
                "error": str(e)
            }
            
            # Add completed tasks
            for i, task_name in enumerate(completed_tasks, 1):
                execution_details["tasks"].append({
                    "task_number": i,
                    "name": task_name,
                    "status": "completed",
                    "agent": "code-based",
                    "output": ""
                })
            
            # Add current task as failed
            if current_task:
                execution_details["tasks"].append({
                    "task_number": len(completed_tasks) + 1,
                    "name": current_task,
                    "status": "failed",
                    "agent": "code-based",
                    "output": f"Error: {str(e)}"
                })
            
            # Save error to Cosmos DB with execution details
            await save_execution_to_cosmos(
                execution_id=execution_id,
                status="failed",
                results={"error": str(e)},
                execution_details=execution_details
            )
            
            # Broadcast error to WebSocket clients
            for ws in websocket_connections[:]:
                try:
                    await ws.send_json({
                        "type": "error",
                        "execution_id": execution_id,
                        "status": "failed",
                        "error": str(e)
                    })
                except Exception as e2:
                    logger.warning(f"Failed to send error WebSocket update", error=str(e2))
                    if ws in websocket_connections:
                        websocket_connections.remove(ws)


# Mount static files (frontend build) if they exist
# This allows serving the frontend from the same container
# __file__ is /app/app/main.py, so parent.parent gives us /app
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists() and static_dir.is_dir():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    # Serve static files
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    
    # Serve index.html for all other routes (SPA support)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes."""
        # Don't interfere with API routes and specific endpoints
        if (full_path.startswith("api/") or 
            full_path.startswith("ws/") or 
            full_path == "health" or
            full_path == "docs" or
            full_path == "redoc" or
            full_path == "openapi.json"):
            raise HTTPException(status_code=404)
        
        # If it's the root path or any other path, serve index.html
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        else:
            raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

"""
Deep Research Backend API

FastAPI backend for the Deep Research application using Foundation Framework.
Provides REST and WebSocket endpoints for workflow execution, monitoring, and real-time updates.
"""

import asyncio
import os
import sys
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncIterable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# Now import from framework package
from framework.workflows.engine import WorkflowEngine, WorkflowStatus, TaskStatus
from framework.core.orchestrator import MagenticOrchestrator
from framework.core.registry import AgentRegistry
from framework.core.observability import ObservabilityService
from framework.mcp_integration.client import MCPClient
from framework.config.settings import Settings
from framework.patterns.sequential import SequentialPattern
from framework.patterns.concurrent import ConcurrentPattern

# Microsoft Agent Framework imports
from agent_framework import (
    BaseAgent, AgentRunResponse, AgentRunResponseUpdate,
    AgentThread, ChatMessage, Role, TextContent
)

# Azure OpenAI and Tavily imports
from openai import AzureOpenAI
from tavily import TavilyClient

# Import MAF workflow module
from . import maf_workflow

# Import routers
from app.routers import sessions

logger = structlog.get_logger(__name__)

# Global state
workflow_engine: Optional[WorkflowEngine] = None
agent_registry: Optional[AgentRegistry] = None
orchestrator: Optional[MagenticOrchestrator] = None
active_executions: Dict[str, Dict[str, Any]] = {}
websocket_connections: List[WebSocket] = []


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
        system_prompt: str
    ):
        # Initialize Microsoft Agent Framework's BaseAgent
        super().__init__(name=name, description=description)
        
        # Store our custom attributes
        self.agent_id = agent_id
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = system_prompt
    
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
                    temperature=0.7,
                    max_tokens=2000
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
        model: str
    ):
        # Initialize Microsoft Agent Framework's BaseAgent
        super().__init__(name=name, description=description)
        
        # Store our custom attributes
        self.agent_id = agent_id
        self.tavily = tavily_client
        self.azure_client = azure_client
        self.model = model
    
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
                
                # Build search query - ensure it's not empty
                search_query = task.strip()
                if not search_query:
                    raise ValueError("Empty search query")
                
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
                    temperature=0.7,
                    max_tokens=2000
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
            name="Quality Reviewer",
            description="AI agent that reviews research quality",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="You are an expert research reviewer. Provide thorough quality feedback."
        )
        await agent_registry.register_agent("reviewer", reviewer)
        logger.info("Registered agent", agent_id="reviewer")
    except ValueError:
        logger.info("Agent already registered", agent_id="reviewer")
    
    try:
        summarizer = AIResearchAgent(
            agent_id="summarizer",
            name="Executive Summarizer",
            description="AI agent that creates executive summaries",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="You are an expert at creating concise executive summaries."
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
    include_citations: bool
) -> Dict[str, Any]:
    """
    Execute research using programmatic code-based approach with framework patterns.
    
    This demonstrates proper usage of the Foundation Framework patterns:
    - SequentialPattern for ordered agent execution
    - ConcurrentPattern for parallel agent execution
    - Pattern composition for hybrid workflows
    """
    results = {}
    
    try:
        # Import patterns from framework
        from framework.patterns import SequentialPattern, ConcurrentPattern
        
        # Phase 1: Sequential Planning using SequentialPattern
        logger.info("Code-based execution: Phase 1 - Sequential Planning with SequentialPattern")
        logger.info("sequential_task_start", phase=1, task="planning", agent="planner")
        
        # Update progress: Phase 1 starting
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = "Phase 1: Research Planning"
            active_executions[execution_id]["progress"] = 10.0
            active_executions[execution_id]["completed_tasks"] = []
        
        # Use SequentialPattern for planning phase
        planning_pattern = SequentialPattern(
            agents=["planner"],
            name="research_planning",
            description="Create comprehensive research plan",
            config={"preserve_context": True}
        )
        
        planning_context = await orchestrator_instance.execute(
            task=f"Create a comprehensive research plan for the topic: {topic}. Break down into key subtopics, identify research questions, and suggest investigation approaches. Context: depth={depth}, max_sources={max_sources}",
            pattern=planning_pattern
        )
        
        # Extract research plan with better error handling
        research_plan = ""
        if planning_context and planning_context.result:
            logger.info(f"Planning context result structure: {planning_context.result.keys() if isinstance(planning_context.result, dict) else type(planning_context.result)}")
            
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
                logger.warning(f"⚠️ No research plan content found. Full result keys: {planning_context.result.keys()}")
        else:
            logger.warning(f"⚠️ Planning context or result is None")
        
        results["research_plan"] = research_plan
        logger.info("sequential_task_completed", phase=1, task="planning", result_length=len(str(research_plan)))
        
        # Update progress: Phase 1 complete
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = "Phase 2: Concurrent Investigation"
            active_executions[execution_id]["progress"] = 20.0
            active_executions[execution_id]["completed_tasks"] = ["Phase 1: Research Planning"]
        
        # Phase 2: Concurrent Investigation using ConcurrentPattern
        logger.info("Code-based execution: Phase 2 - Concurrent Investigation with ConcurrentPattern")
        logger.info("concurrent_phase_start", phase=2, task="investigation", agents=5)
        
        # To truly showcase ConcurrentPattern, we'll execute all 5 research tasks in parallel
        # We'll use asyncio.gather to run multiple concurrent executions simultaneously
        # Each execution uses ConcurrentBuilder with 2 researcher agents for redundancy/quality
        
        research_aspects = [
            ("core_concepts", f"Research the core concepts and fundamental definitions related to: {topic}. Focus on authoritative sources and foundational understanding."),
            ("current_state", f"Investigate the current state, recent developments, and latest trends regarding: {topic}. Focus on recent publications from the last 2-3 years."),
            ("applications", f"Research practical applications, use cases, and real-world implementations of: {topic}. Include examples and case studies."),
            ("challenges", f"Investigate the challenges, limitations, criticisms, and potential risks associated with: {topic}. Include counterarguments."),
            ("future_trends", f"Research future trends, predictions, and emerging directions for: {topic}. Focus on expert opinions and forecasts.")
        ]
        
        # Execute all research tasks concurrently using asyncio.gather
        # This demonstrates true parallel execution with the framework
        async def execute_research_task(key: str, task_prompt: str):
            """Execute a single research task with a single agent."""
            logger.info("research_task_start", task=key, execution="sequential")
            
            # Since Microsoft Agent Framework doesn't allow duplicate agent instances,
            # we'll use sequential execution with a single researcher agent per task
            # The concurrency comes from running multiple sequential executions in parallel
            sequential_result = await orchestrator_instance.execute_sequential(
                task=task_prompt,
                agent_ids=["researcher"],
                tools=[]
            )
            
            if sequential_result and "results" in sequential_result:
                response_content = sequential_result["results"][0].get("content", "") if sequential_result["results"] else ""
                logger.info("research_task_completed", task=key, result_length=len(str(response_content)))
                return (key, response_content)
            else:
                logger.error("research_task_failed", task=key, error="No response")
                return (key, f"Error: No response received")
        
        # Execute all 5 research tasks in parallel
        logger.info("Executing 5 research tasks concurrently with ConcurrentPattern")
        research_results = await asyncio.gather(
            *[execute_research_task(key, task_prompt) for key, task_prompt in research_aspects],
            return_exceptions=True
        )
        
        # Process results
        for result in research_results:
            if isinstance(result, Exception):
                logger.error("Research task failed with exception", error=str(result))
            else:
                key, content = result
                results[key] = content
        
        # Update progress: Phase 2 complete
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = "Phase 3: Synthesizing Findings"
            active_executions[execution_id]["progress"] = 50.0
            active_executions[execution_id]["completed_tasks"] = [
                "Phase 1: Research Planning",
                "Phase 2: Concurrent Investigation (5 parallel tasks)"
            ]
        
        # Phase 3-6: Sequential Processing using SequentialPattern
        logger.info("Code-based execution: Phase 3-6 - Sequential Processing with SequentialPattern")
        logger.info("sequential_task_start", phase=3, task="synthesis_validation_finalization", agents=["writer", "reviewer", "summarizer"])
        
        # Build comprehensive context for remaining phases
        comprehensive_context = f"""Research Topic: {topic}

Research Plan:
{research_plan}

Core Concepts:
{results.get('core_concepts', '')}

Current State:
{results.get('current_state', '')}

Applications:
{results.get('applications', '')}

Challenges:
{results.get('challenges', '')}

Future Trends:
{results.get('future_trends', '')}

Instructions: Process this research through synthesis, validation, finalization, and summarization phases."""
        
        # Use SequentialPattern for the remaining workflow
        # Note: Microsoft Agent Framework doesn't allow duplicate agent instances
        # So we use: writer → reviewer → summarizer (removed duplicate writer)
        final_phases_pattern = SequentialPattern(
            agents=["writer", "reviewer", "summarizer"],
            name="synthesis_validation_finalization",
            description="Sequential synthesis, validation, and summarization",
            config={"preserve_context": True, "fail_fast": False}
        )
        
        final_context = await orchestrator_instance.execute(
            task=comprehensive_context,
            pattern=final_phases_pattern
        )
        
        # Extract results from sequential execution with better error handling
        if final_context and final_context.result:
            logger.info(f"Final context result structure: {final_context.result.keys() if isinstance(final_context.result, dict) else type(final_context.result)}")
            
            # Check if we have a summary field (contains the final synthesized output)
            if "summary" in final_context.result:
                # The summary contains the final output from all agents
                final_summary = final_context.result.get("summary", "")
                results["draft_report"] = final_summary
                results["final_report"] = final_summary
                results["executive_summary"] = final_summary
                logger.info("Using summary field for final phases", summary_length=len(final_summary))
            
            # Also check for individual results
            if "results" in final_context.result:
                responses = final_context.result["results"]
                logger.info(f"Got {len(responses)} responses from final phases")
                
                # Extract individual agent responses if available
                if len(responses) >= 1:
                    writer_output = responses[0].get("content", "")
                    if writer_output:
                        results["draft_report"] = writer_output
                        results["final_report"] = writer_output
                if len(responses) >= 2:
                    reviewer_output = responses[1].get("content", "")
                    if reviewer_output:
                        results["validation_results"] = reviewer_output
                if len(responses) >= 3:
                    summarizer_output = responses[2].get("content", "")
                    if summarizer_output:
                        results["executive_summary"] = summarizer_output
                
                logger.info("sequential_phases_completed", phases=[3, 4, 5], 
                           draft_length=len(results.get("draft_report", "")),
                           validation_length=len(results.get("validation_results", "")),
                           summary_length=len(results.get("executive_summary", "")))
            else:
                logger.warning(f"⚠️ No 'results' key in final_context.result. Keys: {final_context.result.keys()}")
        else:
            logger.warning(f"⚠️ Final context or result is None")
        
        # Update progress: All phases complete
        if execution_id in active_executions:
            active_executions[execution_id]["current_task"] = None
            active_executions[execution_id]["progress"] = 100.0
            active_executions[execution_id]["completed_tasks"] = [
                "Phase 1: Research Planning (SequentialPattern)",
                "Phase 2: Concurrent Investigation (ConcurrentPattern)",
                "Phase 3-6: Synthesis, Validation, Finalization, Summarization (SequentialPattern)"
            ]
        
        logger.info("Code-based execution completed successfully using framework patterns")
        return results
        
    except Exception as e:
        logger.error(f"Code-based execution failed", error=str(e))
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application."""
    global workflow_engine, agent_registry, orchestrator
    
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
            background_tasks.add_task(
                execute_maf_workflow_research_task,
                execution_id,
                request.topic,
                request.max_sources
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
                request.include_citations
            )
        else:
            # Workflow-based execution: Use declarative YAML
            logger.info(f"Starting workflow-based research execution", execution_id=execution_id, topic=request.topic)
            
            # Prepare workflow variables
            variables = {
                "research_topic": request.topic,
                "research_depth": request.depth,
                "max_sources": request.max_sources,
                "include_citations": request.include_citations
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
            if status == "completed" and run.metadata:
                # Reconstruct result from metadata
                result = {
                    "research_plan": run.metadata.get("research_plan", ""),
                    "core_concepts": run.metadata.get("core_concepts", ""),
                    "current_state": run.metadata.get("current_state", ""),
                    "applications": run.metadata.get("applications", ""),
                    "challenges": run.metadata.get("challenges", ""),
                    "future_trends": run.metadata.get("future_trends", ""),
                    "final_report": run.research_report or "",
                    "executive_summary": run.summary or ""
                }
            
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
            update_data["execution_details"] = execution_details
        
        # Extract and save results
        if results:
            # Save final report
            if "final_report" in results:
                update_data["research_report"] = results.get("final_report")
            elif "report" in results:
                update_data["research_report"] = results.get("report")
            
            # Save executive summary
            if "executive_summary" in results:
                update_data["executive_summary"] = results.get("executive_summary")
            elif "summary" in results:
                update_data["executive_summary"] = results.get("summary")
            
            # Save research plan
            if "research_plan" in results:
                update_data["research_plan"] = results.get("research_plan")
            
            # Merge results with existing metadata from exec_info
            existing_metadata = exec_info.get("metadata", {})
            update_data["metadata"] = {**existing_metadata, **results}
            
            # Also save orchestration pattern and framework info at top level
            if existing_metadata:
                update_data["orchestration_pattern"] = existing_metadata.get("orchestration_pattern")
                update_data["framework"] = existing_metadata.get("framework")
                update_data["workflow_engine"] = existing_metadata.get("workflow_engine")
        
        # Add completed tasks from exec_info
        if "completed_tasks" in exec_info:
            update_data["completed_tasks"] = exec_info["completed_tasks"]
        
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
    max_sources: int
):
    """Background task to execute MAF graph-based workflow research."""
    try:
        logger.info(f"Starting MAF workflow research execution", execution_id=execution_id, topic=topic)
        
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
        
        # Execute MAF workflow
        results = await maf_workflow.execute_maf_workflow_research(
            topic=topic,
            execution_id=execution_id,
            azure_client=azure_client,
            tavily_client=tavily_client,
            model=azure_deployment,
            max_sources=max_sources,
            progress_callback=progress_callback
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
    include_citations: bool
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
            include_citations=include_citations
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
                "Phase 1: Research Planning (SequentialPattern)": {
                    "agent": "planner",
                    "output": results.get("research_plan", "")
                },
                "Phase 2: Concurrent Investigation (ConcurrentPattern)": {
                    "agent": "researcher (concurrent)",
                    "output": phase2_combined_output
                },
                "Phase 3-6: Synthesis, Validation, Finalization, Summarization (SequentialPattern)": {
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

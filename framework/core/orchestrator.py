"""
Magentic Orchestrator - Main Orchestration Engine

This is the core orchestration engine that coordinates multi-agent workflows,
manages execution patterns, and integrates with MCP tools for dynamic capabilities.
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import asynccontextmanager

import structlog
from pydantic import BaseModel, Field

# Microsoft Agent Framework imports
from agent_framework import (
    SequentialBuilder, ConcurrentBuilder, MagenticBuilder, 
    WorkflowBuilder, ChatMessage, Role, WorkflowOutputEvent, TextContent
)
from azure.identity import AzureCliCredential

from ..agents.factory import AgentFactory
from ..mcp_integration.client import MCPClient
from ..config.settings import Settings
from .registry import AgentRegistry
from .planning import DynamicPlanner
from .observability import ObservabilityService


logger = structlog.get_logger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionContext(BaseModel):
    """Execution context for orchestration sessions."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    pattern_name: str
    agents: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class OrchestrationPattern(BaseModel):
    """Base class for orchestration patterns."""
    name: str
    description: str
    agents: List[str]
    tools: Optional[List[str]] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class MagenticOrchestrator:
    """
    Main orchestration engine for the Magentic Foundation Framework.
    
    Coordinates multi-agent workflows, manages execution patterns, and provides
    enterprise-grade capabilities including monitoring, security, and MCP integration.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        agent_registry: Optional[AgentRegistry] = None,
        mcp_client: Optional[MCPClient] = None,
        observability: Optional[ObservabilityService] = None
    ):
        """Initialize the orchestrator with configuration and dependencies."""
        self.settings = settings or Settings()
        self.agent_registry = agent_registry or AgentRegistry(self.settings)
        self.mcp_client = mcp_client or MCPClient(self.settings)
        self.observability = observability or ObservabilityService(self.settings)
        
        self.agent_factory = AgentFactory(self.settings)
        self.planner = DynamicPlanner(self.settings)
        
        # Active execution tracking
        self._active_executions: Dict[str, ExecutionContext] = {}
        self._execution_lock = asyncio.Lock()
        
        logger.info(
            "MagenticOrchestrator initialized",
            settings=self.settings.model_dump(exclude_secrets=True)
        )

    async def initialize(self) -> None:
        """Initialize the orchestrator and its dependencies."""
        logger.info("Initializing MagenticOrchestrator")
        
        # Initialize components
        await self.agent_registry.initialize()
        await self.mcp_client.initialize()
        await self.observability.initialize()
        
        # Register built-in agents
        await self._register_builtin_agents()
        
        logger.info("MagenticOrchestrator initialization complete")

    async def shutdown(self) -> None:
        """Shutdown the orchestrator and cleanup resources."""
        logger.info("Shutting down MagenticOrchestrator")
        
        # Cancel active executions
        for execution_id in list(self._active_executions.keys()):
            await self.cancel_execution(execution_id)
        
        # Shutdown components
        await self.mcp_client.shutdown()
        await self.observability.shutdown()
        
        logger.info("MagenticOrchestrator shutdown complete")

    async def execute(
        self,
        task: str,
        pattern: Union[str, OrchestrationPattern],
        agents: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionContext:
        """
        Execute a task using the specified orchestration pattern.
        
        Args:
            task: The task description to execute
            pattern: Orchestration pattern name or configuration
            agents: Optional list of specific agents to use
            tools: Optional list of MCP tools to make available
            metadata: Optional metadata for the execution
            
        Returns:
            ExecutionContext with execution details and results
        """
        # Create execution context
        context = ExecutionContext(
            task=task,
            pattern_name=pattern if isinstance(pattern, str) else pattern.name,
            agents=agents or [],
            tools=tools or [],
            metadata=metadata or {}
        )
        
        async with self._execution_lock:
            self._active_executions[context.id] = context
        
        logger.info(
            "Starting task execution",
            execution_id=context.id,
            task=task[:100],  # Truncate for logging
            pattern=context.pattern_name
        )

        try:
            context.start_time = datetime.utcnow()
            context.status = ExecutionStatus.RUNNING
            
            # Execute based on pattern type
            if isinstance(pattern, str):
                result = await self._execute_named_pattern(context, pattern)
            else:
                result = await self._execute_pattern_config(context, pattern)
            
            context.result = result
            context.status = ExecutionStatus.COMPLETED
            context.end_time = datetime.utcnow()
            
            logger.info(
                "Task execution completed",
                execution_id=context.id,
                duration=(context.end_time - context.start_time).total_seconds()
            )
            
        except Exception as e:
            context.error = str(e)
            context.status = ExecutionStatus.FAILED
            context.end_time = datetime.utcnow()
            
            logger.error(
                "Task execution failed",
                execution_id=context.id,
                error=str(e),
                exc_info=True
            )
            
        finally:
            async with self._execution_lock:
                if context.id in self._active_executions:
                    del self._active_executions[context.id]
        
        return context

    async def execute_sequential(
        self,
        task: str,
        agent_ids: Optional[List[str]] = None,
        tools: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute a sequential orchestration pattern."""
        agents = agent_ids or []
        logger.info("Executing sequential pattern", agents=agents)
        
        # Get agent instances
        agent_instances = []
        for agent_name in agents:
            agent = await self.agent_registry.get_agent(agent_name)
            if not agent:
                raise ValueError(f"Agent not found: {agent_name}")
            agent_instances.append(agent)
        
        # Set up MCP tools if provided
        if tools:
            await self._setup_mcp_tools(tools)
        
        # Create sequential workflow using Microsoft Agent Framework
        # SequentialBuilder() takes no arguments - agents are added via participants()
        builder = SequentialBuilder()
        if agent_instances:
            builder = builder.participants(agent_instances)
        workflow = builder.build()
        
        # Execute workflow
        # ChatMessage requires 'contents' (list of TextContent), not 'content'
        messages = [ChatMessage(role=Role.USER, contents=[TextContent(text=task)])]
        
        results = []
        # workflow.run() returns WorkflowRunResult (list of events)
        workflow_run = await workflow.run(messages)
        for event in workflow_run:
            if isinstance(event, WorkflowOutputEvent):
                # WorkflowOutputEvent has data (list of ChatMessages) and source_executor_id
                # ChatMessage has 'text' property, not 'content'
                last_message = event.data[-1] if event.data else None
                results.append({
                    "agent": event.source_executor_id,
                    "content": last_message.text if last_message else "",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return {
            "pattern": "sequential",
            "task": task,
            "agents": agents,
            "results": results,
            "summary": results[-1]["content"] if results else None
        }

    async def execute_concurrent(
        self,
        task: str,
        agent_ids: Optional[List[str]] = None,
        tools: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute a concurrent orchestration pattern."""
        agents = agent_ids or []
        logger.info("Executing concurrent pattern", agents=agents)
        
        # Get agent instances
        agent_instances = []
        for agent_name in agents:
            agent = await self.agent_registry.get_agent(agent_name)
            if not agent:
                raise ValueError(f"Agent not found: {agent_name}")
            agent_instances.append(agent)
        
        # Set up MCP tools if provided
        if tools:
            await self._setup_mcp_tools(tools)
        
        # Create concurrent workflow using Microsoft Agent Framework
        # ConcurrentBuilder() takes no arguments - agents are added via participants()
        builder = ConcurrentBuilder()
        if agent_instances:
            builder = builder.participants(agent_instances)
        workflow = builder.build()
        
        # Execute workflow
        # ChatMessage requires 'contents' (list of TextContent), not 'content'
        messages = [ChatMessage(role=Role.USER, contents=[TextContent(text=task)])]
        
        results = []
        workflow_run = await workflow.run(messages)
        for event in workflow_run:
            if isinstance(event, WorkflowOutputEvent):
                last_message = event.data[-1] if event.data else None
                results.append({
                    "agent": event.source_executor_id,
                    "content": last_message.text if last_message else "",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Aggregate results
        agent_outputs = {}
        for result in results:
            agent_outputs[result["agent"]] = result["content"]
        
        return {
            "pattern": "concurrent",
            "task": task,
            "agents": agents,
            "results": results,
            "agent_outputs": agent_outputs,
            "summary": self._aggregate_concurrent_results(results)
        }

    async def execute_react(
        self,
        task: str,
        agent: str,
        tools: Optional[List[str]] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """Execute a ReAct (Reasoning + Acting) pattern."""
        logger.info("Executing ReAct pattern", agent=agent, max_iterations=max_iterations)
        
        # Get the reasoning agent
        agent_instance = await self.agent_registry.get_agent(agent)
        if not agent_instance:
            raise ValueError(f"Agent not found: {agent}")
        
        # Set up MCP tools
        if tools:
            await self._setup_mcp_tools(tools)
        
        # Use dynamic planner for ReAct execution
        result = await self.planner.execute_react_loop(
            task=task,
            agent=agent_instance,
            tools=tools or [],
            max_iterations=max_iterations
        )
        
        return {
            "pattern": "react",
            "task": task,
            "agent": agent,
            "tools": tools or [],
            "iterations": result.iterations if hasattr(result, 'iterations') else 0,
            "final_result": result.result if hasattr(result, 'result') else None,
            "reasoning_trace": result.reasoning_trace if hasattr(result, 'reasoning_trace') else []
        }

    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get the status of a specific execution."""
        async with self._execution_lock:
            return self._active_executions.get(execution_id)

    async def list_active_executions(self) -> List[ExecutionContext]:
        """List all currently active executions."""
        async with self._execution_lock:
            return list(self._active_executions.values())

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an active execution."""
        async with self._execution_lock:
            if execution_id in self._active_executions:
                context = self._active_executions[execution_id]
                context.status = ExecutionStatus.CANCELLED
                context.end_time = datetime.utcnow()
                del self._active_executions[execution_id]
                
                logger.info("Execution cancelled", execution_id=execution_id)
                return True
            return False

    # Private methods

    async def _execute_named_pattern(
        self, 
        context: ExecutionContext, 
        pattern_name: str
    ) -> Dict[str, Any]:
        """Execute a named orchestration pattern."""
        pattern_handlers = {
            "sequential": self._handle_sequential_pattern,
            "concurrent": self._handle_concurrent_pattern,
            "react": self._handle_react_pattern,
            "group_chat": self._handle_group_chat_pattern,
            "handoff": self._handle_handoff_pattern
        }
        
        handler = pattern_handlers.get(pattern_name)
        if not handler:
            raise ValueError(f"Unknown pattern: {pattern_name}")
        
        return await handler(context)

    async def _execute_pattern_config(
        self, 
        context: ExecutionContext, 
        pattern: OrchestrationPattern
    ) -> Dict[str, Any]:
        """Execute using a pattern configuration."""
        # Update context with pattern details
        context.agents = pattern.agents
        context.tools = pattern.tools or []
        
        # Determine pattern type from class name
        # SequentialPattern -> "sequential", ConcurrentPattern -> "concurrent", etc.
        pattern_type = type(pattern).__name__.replace("Pattern", "").lower()
        
        # Map pattern class to handler name
        pattern_type_map = {
            "sequential": "sequential",
            "concurrent": "concurrent",
            "react": "react",
            "groupchat": "group_chat",  # GroupChatPattern -> group_chat handler
            "handoff": "handoff"  # HandoffPattern -> handoff handler
        }
        
        handler_name = pattern_type_map.get(pattern_type, pattern_type)
        
        return await self._execute_named_pattern(context, handler_name)

    async def _handle_sequential_pattern(self, context: ExecutionContext) -> Dict[str, Any]:
        """Handle sequential pattern execution."""
        agents = context.agents or ["planner", "researcher", "writer", "reviewer"]
        return await self.execute_sequential(context.task, agents, context.tools)

    async def _handle_concurrent_pattern(self, context: ExecutionContext) -> Dict[str, Any]:
        """Handle concurrent pattern execution."""
        agents = context.agents or ["summarizer", "pros_cons", "risk_assessor"]
        return await self.execute_concurrent(context.task, agents, context.tools)

    async def _handle_react_pattern(self, context: ExecutionContext) -> Dict[str, Any]:
        """Handle ReAct pattern execution."""
        agent = context.agents[0] if context.agents else "strategic_planner"
        max_iterations = context.metadata.get("max_iterations", 10)
        return await self.execute_react(context.task, agent, context.tools, max_iterations)

    async def _handle_group_chat_pattern(self, context: ExecutionContext) -> Dict[str, Any]:
        """Handle group chat pattern execution."""
        agents = context.agents or []
        task = context.task
        
        if not agents:
            raise ValueError("No agents specified for group chat pattern")
        
        logger.info(f"Executing group chat pattern with {len(agents)} agents")
        
        # Get agent instances
        agent_instances = []
        for agent_name in agents:
            agent = await self.agent_registry.get_agent(agent_name)
            if not agent:
                raise ValueError(f"Agent not found: {agent_name}")
            agent_instances.append(agent)
        
        # Set up MCP tools if provided
        if context.tools:
            await self._setup_mcp_tools(context.tools)
        
        # Create group chat workflow using Microsoft Agent Framework
        # MagenticBuilder is used for group chat / multi-agent collaboration
        builder = MagenticBuilder()
        if agent_instances:
            builder = builder.participants(agent_instances)
        workflow = builder.build()
        
        # Execute workflow
        messages = [ChatMessage(role=Role.USER, contents=[TextContent(text=task)])]
        
        results = []
        conversation_history = []
        
        try:
            workflow_run = await workflow.run(messages)
            for event in workflow_run:
                if isinstance(event, WorkflowOutputEvent):
                    last_message = event.data[-1] if event.data else None
                    message_content = last_message.text if last_message else ""
                    
                    result_entry = {
                        "agent": event.source_executor_id,
                        "content": message_content,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    results.append(result_entry)
                    conversation_history.append(f"{event.source_executor_id}: {message_content[:100]}")
            
            # Extract final consensus or summary from the last message
            final_result = results[-1]["content"] if results else "No result generated"
            
            return {
                "pattern": "group_chat",
                "task": task,
                "agents": agents,
                "results": results,
                "conversation_history": conversation_history,
                "final_result": final_result,
                "message_count": len(results),
                "participating_agents": list(set(r["agent"] for r in results))
            }
            
        except Exception as e:
            logger.error(f"Group chat pattern execution failed: {str(e)}")
            raise

    async def _handle_handoff_pattern(self, context: ExecutionContext) -> Dict[str, Any]:
        """Handle handoff pattern execution."""
        # Get pattern from context metadata or reconstruct from context
        # For now, implement basic handoff by starting with the initial agent
        agents = context.agents or []
        task = context.task
        
        if not agents:
            raise ValueError("No agents specified for handoff pattern")
        
        # Use the first agent as the initial agent (should be set by pattern)
        initial_agent_name = agents[0] if agents else None
        if not initial_agent_name:
            raise ValueError("No initial agent specified for handoff pattern")
        
        logger.info(f"Executing handoff pattern starting with agent: {initial_agent_name}")
        
        # Get the initial agent instance
        agent = await self.agent_registry.get_agent(initial_agent_name)
        if not agent:
            raise ValueError(f"Agent not found: {initial_agent_name}")
        
        # Set up MCP tools if provided
        if context.tools:
            await self._setup_mcp_tools(context.tools)
        
        # Execute with the initial agent
        # For now, use a simple execution without actual handoff mechanism
        # TODO: Implement proper handoff mechanism with Microsoft Agent Framework
        try:
            result = await agent.process(task)
            
            return {
                "pattern": "handoff",
                "task": task,
                "initial_agent": initial_agent_name,
                "available_agents": agents,
                "result": result,
                "handoffs_performed": 0  # TODO: Track actual handoffs
            }
        except Exception as e:
            logger.error(f"Handoff pattern execution failed: {str(e)}")
            raise

    async def _setup_mcp_tools(self, tools: List[str]) -> None:
        """Set up MCP tools for the execution."""
        for tool_name in tools:
            if not await self.mcp_client.is_tool_available(tool_name):
                logger.warning("MCP tool not available", tool=tool_name)

    async def _register_builtin_agents(self) -> None:
        """Register built-in agents with the registry."""
        builtin_agents = [
            "planner", "researcher", "writer", "reviewer",
            "summarizer", "pros_cons", "risk_assessor",
            "strategic_planner", "coordinator"
        ]
        
        for agent_name in builtin_agents:
            try:
                agent = self.agent_factory.create_agent(agent_name)
                await self.agent_registry.register_agent(agent_name, agent)
                logger.debug("Registered builtin agent", agent=agent_name)
            except Exception as e:
                logger.warning("Failed to register builtin agent", agent=agent_name, error=str(e))

    def _aggregate_concurrent_results(self, results: List[Dict[str, Any]]) -> str:
        """Aggregate results from concurrent execution."""
        if not results:
            return "No results generated"
        
        summary_parts = []
        for result in results:
            agent_name = result["agent"]
            content = result["content"][:200]  # Truncate for summary
            summary_parts.append(f"{agent_name}: {content}")
        
        return " | ".join(summary_parts)

    @asynccontextmanager
    async def execution_context(self, task: str, pattern: str):
        """Context manager for orchestration execution."""
        context = ExecutionContext(task=task, pattern_name=pattern)
        
        async with self._execution_lock:
            self._active_executions[context.id] = context
        
        try:
            context.start_time = datetime.utcnow()
            context.status = ExecutionStatus.RUNNING
            yield context
            context.status = ExecutionStatus.COMPLETED
        except Exception as e:
            context.error = str(e)
            context.status = ExecutionStatus.FAILED
            raise
        finally:
            context.end_time = datetime.utcnow()
            async with self._execution_lock:
                if context.id in self._active_executions:
                    del self._active_executions[context.id]
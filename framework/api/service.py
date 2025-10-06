"""
API Layer - FastAPI REST Interface

Provides REST API endpoints for managing agents, workflows, MCP tools,
and monitoring the Foundation Framework.
"""

import asyncio
import json
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from ..config.settings import Settings
from ..core.orchestrator import MagenticOrchestrator
from ..core.registry import AgentRegistry, AgentMetadata
from ..core.planning import DynamicPlanner, ExecutionPlan
from ..core.security import SecurityManager, SecurityContext
from ..core.observability import ObservabilityService
from ..mcp_integration.client import MCPClient
from ..mcp_integration.server import MCPServer
from ..workflows.engine import (
    WorkflowEngine, 
    WorkflowDefinition, 
    WorkflowExecution,
    WorkflowStatus,
    TaskStatus
)

logger = structlog.get_logger(__name__)

# Security
security = HTTPBearer()

# Request/Response Models
class AgentExecuteRequest(BaseModel):
    """Request for agent execution."""
    agent_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None


class AgentExecuteResponse(BaseModel):
    """Response for agent execution."""
    execution_id: str
    result: Any
    success: bool
    duration: float
    error: Optional[str] = None


class OrchestrationRequest(BaseModel):
    """Request for orchestration execution."""
    pattern: str  # sequential, concurrent, react
    agents: List[str]
    task: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None


class OrchestrationResponse(BaseModel):
    """Response for orchestration execution."""
    execution_id: str
    pattern: str
    agents: List[str]
    results: List[Any]
    success: bool
    duration: float
    error: Optional[str] = None


class MCPToolCallRequest(BaseModel):
    """Request for MCP tool execution."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None


class MCPToolCallResponse(BaseModel):
    """Response for MCP tool execution."""
    tool_name: str
    result: Any
    success: bool
    duration: float
    error: Optional[str] = None


class WorkflowExecuteRequest(BaseModel):
    """Request for workflow execution."""
    workflow_name: str
    variables: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecuteResponse(BaseModel):
    """Response for workflow execution."""
    execution_id: str
    workflow_name: str
    status: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    components: Dict[str, Any]
    version: str


class MetricsResponse(BaseModel):
    """Metrics response."""
    metrics: Dict[str, List[Dict[str, Any]]]
    timestamp: str


class APIService:
    """
    FastAPI-based REST API service for the Foundation Framework.
    
    Provides comprehensive REST endpoints for agent management, orchestration,
    workflow execution, MCP tool integration, and system monitoring.
    """

    def __init__(
        self,
        settings: Settings,
        orchestrator: MagenticOrchestrator,
        agent_registry: AgentRegistry,
        planner: DynamicPlanner,
        security_manager: SecurityManager,
        observability: ObservabilityService,
        mcp_client: MCPClient,
        mcp_server: MCPServer,
        workflow_engine: WorkflowEngine
    ):
        """Initialize API service."""
        self.settings = settings
        self.orchestrator = orchestrator
        self.agent_registry = agent_registry
        self.planner = planner
        self.security_manager = security_manager
        self.observability = observability
        self.mcp_client = mcp_client
        self.mcp_server = mcp_server
        self.workflow_engine = workflow_engine
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Foundation API",
            description="Multi-Agent Orchestration and Workflow Management API",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Configure middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.api.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Setup routes
        self._setup_routes()
        
        logger.info("APIService initialized")

    def _setup_routes(self):
        """Setup API routes."""
        
        # Health and Status
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Get system health status."""
            # Basic health check - observability provides detailed metrics
            return HealthResponse(
                status="healthy",
                timestamp=datetime.utcnow().isoformat(),
                components={
                    "agents": "healthy",
                    "mcp": "healthy",
                    "workflows": "healthy",
                    "observability": "healthy" if self.observability else "disabled"
                },
                version="1.0.0"
            )

        @self.app.get("/status")
        async def system_status():
            """Get detailed system status."""
            agent_stats = await self.agent_registry.get_statistics()
            
            return {
                "agents": agent_stats,
                "observability_enabled": self.observability is not None,
                "timestamp": datetime.utcnow().isoformat()
            }

        # Authentication
        async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Get current authenticated user."""
            if not self.settings.api.auth_enabled:
                return {"user_id": "anonymous", "roles": ["admin"]}
            
            try:
                # Validate token and get user context
                context = await self.security_manager.validate_session(credentials.credentials)
                return context
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )

        # Agent Management
        @self.app.get("/agents", response_model=List[Dict[str, Any]])
        async def list_agents(current_user: dict = Depends(get_current_user)):
            """List all registered agents."""
            agents = await self.agent_registry.list_agents()
            return [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "type": agent.type,
                    "status": agent.status,
                    "capabilities": agent.capabilities,
                    "description": agent.description,
                    "metadata": agent.metadata
                }
                for agent in agents
            ]

        @self.app.get("/agents/{agent_id}", response_model=Dict[str, Any])
        async def get_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
            """Get specific agent information."""
            agent = await self.agent_registry.get_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            agent_info = await self.agent_registry.get_agent_info(agent_id)
            
            return {
                "id": agent_info.id if agent_info else agent_id,
                "name": agent_info.name if agent_info else "Unknown",
                "type": agent_info.type if agent_info else "Unknown", 
                "status": agent_info.status if agent_info else "unknown",
                "capabilities": agent_info.capabilities if agent_info else [],
                "description": agent_info.description if agent_info else "",
                "metadata": agent_info.metadata if agent_info else {}
            }

        @self.app.post("/agents/{agent_id}/execute", response_model=AgentExecuteResponse)
        async def execute_agent(
            agent_id: str,
            request: AgentExecuteRequest,
            background_tasks: BackgroundTasks,
            current_user: dict = Depends(get_current_user)
        ):
            """Execute an agent."""
            import uuid
            
            execution_id = str(uuid.uuid4())
            
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Get agent
                agent = await self.agent_registry.get_agent(agent_id)
                if not agent:
                    raise HTTPException(status_code=404, detail="Agent not found")
                
                # Execute agent
                result = await agent.execute(request.parameters)
                
                duration = asyncio.get_event_loop().time() - start_time
                
                # MAF observability automatically tracks agent executions
                
                return AgentExecuteResponse(
                    execution_id=execution_id,
                    result=result,
                    success=True,
                    duration=duration
                )
            
            except Exception as e:
                duration = asyncio.get_event_loop().time() - start_time
                
                # MAF observability automatically tracks errors
                
                return AgentExecuteResponse(
                    execution_id=execution_id,
                    result=None,
                    success=False,
                    duration=duration,
                    error=str(e)
                )

        # Orchestration
        @self.app.post("/orchestration/execute", response_model=OrchestrationResponse)
        async def execute_orchestration(
            request: OrchestrationRequest,
            background_tasks: BackgroundTasks,
            current_user: dict = Depends(get_current_user)
        ):
            """Execute orchestrated agent workflow."""
            import uuid
            
            execution_id = str(uuid.uuid4())
            
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Execute orchestration
                results = await self.orchestrator.execute(
                    agents=request.agents,
                    task=request.task,
                    pattern=request.pattern,
                    parameters=request.parameters
                )
                
                duration = asyncio.get_event_loop().time() - start_time
                
                # MAF observability automatically tracks orchestration
                
                return OrchestrationResponse(
                    execution_id=execution_id,
                    pattern=request.pattern,
                    agents=request.agents,
                    results=results,
                    success=True,
                    duration=duration
                )
            
            except Exception as e:
                duration = asyncio.get_event_loop().time() - start_time
                
                # MAF observability automatically tracks errors
                
                return OrchestrationResponse(
                    execution_id=execution_id,
                    pattern=request.pattern,
                    agents=request.agents,
                    results=[],
                    success=False,
                    duration=duration,
                    error=str(e)
                )

        # MCP Tools
        @self.app.get("/mcp/tools")
        async def list_mcp_tools(current_user: dict = Depends(get_current_user)):
            """List available MCP tools."""
            tools = await self.mcp_server.list_tools()
            
            return {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "type": tool.tool_type,
                        "parameters": [
                            {
                                "name": param.name,
                                "type": param.type,
                                "description": param.description,
                                "required": param.required,
                                "default": param.default
                            }
                            for param in tool.parameters
                        ],
                        "metadata": tool.metadata
                    }
                    for tool in tools
                ]
            }

        @self.app.post("/mcp/tools/{tool_name}/call", response_model=MCPToolCallResponse)
        async def call_mcp_tool(
            tool_name: str,
            request: MCPToolCallRequest,
            background_tasks: BackgroundTasks,
            current_user: dict = Depends(get_current_user)
        ):
            """Execute an MCP tool."""
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Execute MCP tool
                result = await self.mcp_client.call_tool(tool_name, request.arguments)
                
                duration = asyncio.get_event_loop().time() - start_time
                
                # MAF observability automatically tracks tool executions
                
                return MCPToolCallResponse(
                    tool_name=tool_name,
                    result=result,
                    success=True,
                    duration=duration
                )
            
            except Exception as e:
                duration = asyncio.get_event_loop().time() - start_time
                
                # MAF observability automatically tracks errors
                
                return MCPToolCallResponse(
                    tool_name=tool_name,
                    result=None,
                    success=False,
                    duration=duration,
                    error=str(e)
                )

        # Workflows
        @self.app.get("/workflows")
        async def list_workflows(current_user: dict = Depends(get_current_user)):
            """List all registered workflows."""
            workflows = await self.workflow_engine.list_workflows()
            
            return {
                "workflows": [
                    {
                        "name": wf.name,
                        "version": wf.version,
                        "description": wf.description,
                        "task_count": len(wf.tasks),
                        "variables": [
                            {
                                "name": var.name,
                                "type": var.type,
                                "required": var.required,
                                "description": var.description
                            }
                            for var in wf.variables
                        ],
                        "metadata": wf.metadata,
                        "created_at": wf.created_at.isoformat()
                    }
                    for wf in workflows
                ]
            }

        @self.app.post("/workflows/{workflow_name}/execute", response_model=WorkflowExecuteResponse)
        async def execute_workflow(
            workflow_name: str,
            request: WorkflowExecuteRequest,
            current_user: dict = Depends(get_current_user)
        ):
            """Execute a workflow."""
            try:
                execution_id = await self.workflow_engine.execute_workflow(
                    workflow_name,
                    request.variables
                )
                
                return WorkflowExecuteResponse(
                    execution_id=execution_id,
                    workflow_name=workflow_name,
                    status="started"
                )
            
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.get("/workflows/executions/{execution_id}")
        async def get_workflow_execution(
            execution_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Get workflow execution status."""
            execution = await self.workflow_engine.get_execution(execution_id)
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")
            
            return {
                "execution_id": execution.execution_id,
                "workflow_name": execution.workflow_name,
                "status": execution.status,
                "start_time": execution.start_time.isoformat() if execution.start_time else None,
                "end_time": execution.end_time.isoformat() if execution.end_time else None,
                "duration": execution.duration,
                "variables": execution.variables,
                "tasks": {
                    task_id: {
                        "status": task_exec.status,
                        "start_time": task_exec.start_time.isoformat() if task_exec.start_time else None,
                        "end_time": task_exec.end_time.isoformat() if task_exec.end_time else None,
                        "duration": task_exec.duration,
                        "result": task_exec.result,
                        "error": task_exec.error,
                        "attempt": task_exec.attempt
                    }
                    for task_id, task_exec in execution.task_executions.items()
                }
            }

        @self.app.post("/workflows/{workflow_name}/upload")
        async def upload_workflow(
            workflow_name: str,
            file: UploadFile = File(...),
            current_user: dict = Depends(get_current_user)
        ):
            """Upload and register a workflow definition."""
            try:
                content = await file.read()
                workflow_data = yaml.safe_load(content.decode('utf-8'))
                
                # Ensure workflow name matches
                workflow_data["name"] = workflow_name
                
                # Register workflow
                await self.workflow_engine.register_workflow(workflow_data)
                
                return {"message": f"Workflow '{workflow_name}' uploaded successfully"}
            
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        # Monitoring and Metrics
        @self.app.get("/metrics", response_model=MetricsResponse)
        async def get_metrics(
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            name_pattern: Optional[str] = None,
            current_user: dict = Depends(get_current_user)
        ):
            """
            Get system metrics information.
            
            Note: With MAF observability, metrics are exported to configured backends:
            - OTLP endpoint (Jaeger, Zipkin, etc.)
            - Azure Application Insights
            - VS Code AI Toolkit
            
            Query those systems for detailed metrics and traces.
            """
            return MetricsResponse(
                metrics={
                    "info": [{
                        "message": "MAF observability is enabled. Metrics are exported to configured backends.",
                        "observability_enabled": self.observability is not None,
                        "note": "Check your OTLP endpoint or Azure Application Insights for detailed metrics"
                    }]
                },
                timestamp=datetime.utcnow().isoformat()
            )

        @self.app.get("/metrics/stream")
        async def stream_metrics(current_user: dict = Depends(get_current_user)):
            """
            Stream real-time metrics information.
            
            Note: With MAF observability, use your observability backend's streaming capabilities.
            """
            async def metric_generator():
                yield f"data: {json.dumps({'message': 'MAF observability exports to configured backends', 'observability_enabled': self.observability is not None})}\n\n"
                return
            
            return StreamingResponse(
                metric_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream"
                }
            )

        @self.app.get("/traces")
        async def get_traces(
            limit: int = 100,
            operation_name: Optional[str] = None,
            current_user: dict = Depends(get_current_user)
        ):
            """Get distributed tracing data."""
            # TODO: Implement trace retrieval from monitoring service
            return {"traces": [], "message": "Tracing endpoint not fully implemented"}

    async def initialize(self) -> None:
        """Initialize API service."""
        logger.info("Initializing APIService")
        # Additional initialization if needed
        logger.info("APIService initialization complete")

    async def shutdown(self) -> None:
        """Shutdown API service."""
        logger.info("APIService shutdown complete")

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app
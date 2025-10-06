"""
MCP Server - Model Context Protocol Server Implementation

Provides a standardized server for hosting and managing MCP tools with
SSE-based communication, protocol standardization, and containerized execution.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from ..config.settings import Settings
from ..core.observability import ObservabilityService

logger = structlog.get_logger(__name__)


class MCPMessageType(str, Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPToolType(str, Enum):
    """Types of MCP tools."""
    FUNCTION = "function"
    RESOURCE = "resource"
    PROMPT = "prompt"
    COMPLETION = "completion"


class MCPCapability(str, Enum):
    """MCP server capabilities."""
    TOOLS = "tools"
    RESOURCES = "resources"
    PROMPTS = "prompts"
    COMPLETIONS = "completions"
    LOGGING = "logging"
    PROGRESS = "progress"


@dataclass
class MCPToolParameter:
    """MCP tool parameter definition."""
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    enum_values: Optional[List[str]] = None


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    tool_type: MCPToolType
    parameters: List[MCPToolParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    container_image: Optional[str] = None
    timeout: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPMessage(BaseModel):
    """MCP protocol message."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPRequest(BaseModel):
    """MCP request message."""
    jsonrpc: str = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP response message."""
    jsonrpc: str = "2.0"
    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPNotification(BaseModel):
    """MCP notification message."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPServerCapabilities(BaseModel):
    """MCP server capabilities."""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    completions: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    progress: Optional[bool] = None


class MCPServerInfo(BaseModel):
    """MCP server information."""
    name: str
    version: str
    capabilities: MCPServerCapabilities
    instructions: Optional[str] = None


@dataclass
class MCPSession:
    """MCP client session."""
    session_id: str
    client_info: Dict[str, Any]
    capabilities: MCPServerCapabilities
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    active: bool = True


class MCPServer:
    """
    Model Context Protocol Server implementation.
    
    Provides standardized tool hosting, protocol communication,
    and containerized execution for MCP tools.
    """

    def __init__(self, settings: Settings, observability: Optional[ObservabilityService] = None):
        """Initialize MCP server."""
        self.settings = settings
        self.observability = observability
        
        # Server info
        self.server_info = MCPServerInfo(
            name="Foundation MCP Server",
            version="1.0.0",
            capabilities=MCPServerCapabilities(
                tools={"listChanged": True},
                resources={"listChanged": True, "subscribe": True},
                prompts={"listChanged": True},
                logging={}
            )
        )
        
        # Tool registry
        self._tools: Dict[str, MCPTool] = {}
        self._tools_lock = asyncio.Lock()
        
        # Session management
        self._sessions: Dict[str, MCPSession] = {}
        self._sessions_lock = asyncio.Lock()
        
        # Message handlers
        self._handlers: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "ping": self._handle_ping,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool,
            "resources/list": self._handle_list_resources,
            "resources/read": self._handle_read_resource,
            "prompts/list": self._handle_list_prompts,
            "prompts/get": self._handle_get_prompt,
            "logging/setLevel": self._handle_set_log_level,
            "notifications/tools/list_changed": self._handle_tools_changed,
            "notifications/resources/list_changed": self._handle_resources_changed,
            "notifications/prompts/list_changed": self._handle_prompts_changed
        }
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        
        logger.info("MCPServer initialized")

    async def initialize(self) -> None:
        """Initialize MCP server."""
        logger.info("Initializing MCPServer")
        
        # Register default tools
        await self._register_default_tools()
        
        # Start session cleanup task
        self._background_tasks.append(
            asyncio.create_task(self._session_cleanup_loop())
        )
        
        logger.info("MCPServer initialization complete")

    async def shutdown(self) -> None:
        """Shutdown MCP server."""
        logger.info("Shutting down MCPServer")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        async with self._sessions_lock:
            for session in self._sessions.values():
                session.active = False
        
        logger.info("MCPServer shutdown complete")

    # Tool Management

    async def register_tool(
        self,
        name: str,
        description: str,
        tool_type: MCPToolType,
        handler: Callable,
        parameters: Optional[List[MCPToolParameter]] = None,
        container_image: Optional[str] = None,
        timeout: int = 30,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a new MCP tool."""
        tool = MCPTool(
            name=name,
            description=description,
            tool_type=tool_type,
            parameters=parameters or [],
            handler=handler,
            container_image=container_image,
            timeout=timeout,
            metadata=metadata or {}
        )
        
        async with self._tools_lock:
            self._tools[name] = tool
        
        # Notify clients of tool changes
        await self._notify_tools_changed()
        
        logger.info("MCP tool registered", tool_name=name, tool_type=tool_type)

    async def unregister_tool(self, name: str) -> bool:
        """Unregister an MCP tool."""
        async with self._tools_lock:
            if name in self._tools:
                del self._tools[name]
                await self._notify_tools_changed()
                logger.info("MCP tool unregistered", tool_name=name)
                return True
        
        return False

    async def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a specific tool."""
        async with self._tools_lock:
            return self._tools.get(name)

    async def list_tools(self) -> List[MCPTool]:
        """List all registered tools."""
        async with self._tools_lock:
            return list(self._tools.values())

    # Message Processing

    async def handle_message(
        self,
        message: Union[str, Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> Optional[MCPMessage]:
        """Handle incoming MCP message."""
        try:
            # Parse message
            if isinstance(message, str):
                message_data = json.loads(message)
            else:
                message_data = message
            
            # Validate JSON-RPC format
            if message_data.get("jsonrpc") != "2.0":
                return MCPResponse(
                    id=message_data.get("id", "unknown"),
                    error={
                        "code": -32600,
                        "message": "Invalid Request - JSON-RPC 2.0 required"
                    }
                )
            
            # Update session activity
            if session_id:
                await self._update_session_activity(session_id)
            
            # Handle different message types
            method = message_data.get("method")
            if method:
                # Request or notification
                if "id" in message_data:
                    # Request - needs response
                    request = MCPRequest(**message_data)
                    return await self._handle_request(request, session_id)
                else:
                    # Notification - no response needed
                    notification = MCPNotification(**message_data)
                    await self._handle_notification(notification, session_id)
                    return None
            else:
                # Response message (not expected in server)
                logger.warning("Received response message on server", message=message_data)
                return None
        
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in MCP message", error=str(e))
            return MCPResponse(
                id="unknown",
                error={
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(e)
                }
            )
        
        except Exception as e:
            logger.error("Error handling MCP message", error=str(e), message=message)
            return MCPResponse(
                id=message_data.get("id", "unknown"),
                error={
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            )

    async def _handle_request(
        self,
        request: MCPRequest,
        session_id: Optional[str] = None
    ) -> MCPResponse:
        """Handle MCP request."""
        try:
            # Find handler
            handler = self._handlers.get(request.method)
            if not handler:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32601,
                        "message": "Method not found",
                        "data": request.method
                    }
                )
            
            # Record metrics
            if self.observability:
                await self.observability.increment_counter(
                    "mcp_requests_total",
                    labels={"method": request.method}
                )
            
            # Execute handler
            start_time = asyncio.get_event_loop().time()
            
            try:
                result = await handler(request.params or {}, session_id)
                
                if self.observability:
                    duration = asyncio.get_event_loop().time() - start_time
                    await self.observability.record_timer(
                        "mcp_request_duration",
                        duration,
                        labels={
                            "method": request.method,
                            "status": "success"
                        }
                    )
                
                return MCPResponse(id=request.id, result=result)
            
            except Exception as e:
                if self.observability:
                    duration = asyncio.get_event_loop().time() - start_time
                    await self.observability.record_timer(
                        "mcp_request_duration",
                        duration,
                        labels={
                            "method": request.method,
                            "status": "error"
                        }
                    )
                
                raise e
        
        except Exception as e:
            logger.error("Error handling MCP request", method=request.method, error=str(e))
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            )

    async def _handle_notification(
        self,
        notification: MCPNotification,
        session_id: Optional[str] = None
    ) -> None:
        """Handle MCP notification."""
        try:
            # Find handler
            handler = self._handlers.get(notification.method)
            if handler:
                await handler(notification.params or {}, session_id)
            else:
                logger.warning("Unknown notification method", method=notification.method)
        
        except Exception as e:
            logger.error("Error handling MCP notification", method=notification.method, error=str(e))

    # Protocol Handlers

    async def _handle_initialize(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle initialize request."""
        client_info = params.get("clientInfo", {})
        capabilities = params.get("capabilities", {})
        
        # Create session
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session = MCPSession(
            session_id=session_id,
            client_info=client_info,
            capabilities=MCPServerCapabilities(**capabilities)
        )
        
        async with self._sessions_lock:
            self._sessions[session_id] = session
        
        logger.info(
            "MCP client initialized",
            session_id=session_id,
            client_name=client_info.get("name", "unknown")
        )
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": self.server_info.capabilities.model_dump(exclude_none=True),
            "serverInfo": {
                "name": self.server_info.name,
                "version": self.server_info.version
            },
            "instructions": self.server_info.instructions
        }

    async def _handle_initialized(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> None:
        """Handle initialized notification."""
        logger.info("MCP client initialization complete", session_id=session_id)

    async def _handle_ping(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle ping request."""
        return {}

    async def _handle_list_tools(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = await self.list_tools()
        
        tool_list = []
        for tool in tools:
            tool_dict = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # Add parameters to schema
            for param in tool.parameters:
                prop = {
                    "type": param.type,
                    "description": param.description
                }
                
                if param.default is not None:
                    prop["default"] = param.default
                
                if param.enum_values:
                    prop["enum"] = param.enum_values
                
                tool_dict["inputSchema"]["properties"][param.name] = prop
                
                if param.required:
                    tool_dict["inputSchema"]["required"].append(param.name)
            
            tool_list.append(tool_dict)
        
        return {"tools": tool_list}

    async def _handle_call_tool(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise ValueError("Tool name is required")
        
        tool = await self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Execute tool
        start_time = asyncio.get_event_loop().time()
        
        try:
            if tool.container_image:
                # Execute in container
                result = await self._execute_tool_in_container(tool, arguments)
            else:
                # Execute directly
                result = await self._execute_tool_direct(tool, arguments)
            
            if self.observability:
                duration = asyncio.get_event_loop().time() - start_time
                await self.observability.record_mcp_tool_call(tool_name, duration, True)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    }
                ]
            }
        
        except Exception as e:
            if self.observability:
                duration = asyncio.get_event_loop().time() - start_time
                await self.observability.record_mcp_tool_call(tool_name, duration, False)
            
            raise e

    async def _handle_list_resources(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle resources/list request."""
        # TODO: Implement resource management
        return {"resources": []}

    async def _handle_read_resource(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle resources/read request."""
        # TODO: Implement resource reading
        uri = params.get("uri")
        raise ValueError(f"Resource '{uri}' not found")

    async def _handle_list_prompts(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle prompts/list request."""
        # TODO: Implement prompt management
        return {"prompts": []}

    async def _handle_get_prompt(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle prompts/get request."""
        # TODO: Implement prompt retrieval
        name = params.get("name")
        raise ValueError(f"Prompt '{name}' not found")

    async def _handle_set_log_level(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> None:
        """Handle logging/setLevel notification."""
        level = params.get("level", "info")
        logger.info("Log level set", level=level, session_id=session_id)

    async def _handle_tools_changed(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> None:
        """Handle tools list changed notification."""
        pass

    async def _handle_resources_changed(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> None:
        """Handle resources list changed notification."""
        pass

    async def _handle_prompts_changed(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> None:
        """Handle prompts list changed notification."""
        pass

    # Tool Execution

    async def _execute_tool_direct(self, tool: MCPTool, arguments: Dict[str, Any]) -> Any:
        """Execute tool directly."""
        if not tool.handler:
            raise ValueError(f"No handler defined for tool '{tool.name}'")
        
        try:
            # Validate arguments
            # TODO: Add parameter validation against tool schema
            
            # Execute with timeout
            result = await asyncio.wait_for(
                tool.handler(arguments),
                timeout=tool.timeout
            )
            
            return result
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool '{tool.name}' execution timed out after {tool.timeout}s")

    async def _execute_tool_in_container(self, tool: MCPTool, arguments: Dict[str, Any]) -> Any:
        """Execute tool in container."""
        # TODO: Implement containerized execution
        logger.warning("Container execution not yet implemented", tool_name=tool.name)
        
        # Fallback to direct execution for now
        return await self._execute_tool_direct(tool, arguments)

    # Notification System

    async def _notify_tools_changed(self) -> None:
        """Notify all clients that tools list has changed."""
        notification = MCPNotification(
            method="notifications/tools/list_changed"
        )
        
        await self._broadcast_notification(notification)

    async def _notify_resources_changed(self) -> None:
        """Notify all clients that resources list has changed."""
        notification = MCPNotification(
            method="notifications/resources/list_changed"
        )
        
        await self._broadcast_notification(notification)

    async def _notify_prompts_changed(self) -> None:
        """Notify all clients that prompts list has changed."""
        notification = MCPNotification(
            method="notifications/prompts/list_changed"
        )
        
        await self._broadcast_notification(notification)

    async def _broadcast_notification(self, notification: MCPNotification) -> None:
        """Broadcast notification to all active sessions."""
        # TODO: Implement notification broadcasting
        # This would typically involve WebSocket connections or SSE streams
        logger.info("Broadcasting notification", method=notification.method)

    # Session Management

    async def _update_session_activity(self, session_id: str) -> None:
        """Update session last activity time."""
        async with self._sessions_lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_activity = datetime.utcnow()

    async def _session_cleanup_loop(self) -> None:
        """Clean up inactive sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                current_time = datetime.utcnow()
                expired_sessions = []
                
                async with self._sessions_lock:
                    for session_id, session in self._sessions.items():
                        # Remove sessions inactive for more than 1 hour
                        if (current_time - session.last_activity).seconds > 3600:
                            expired_sessions.append(session_id)
                    
                    for session_id in expired_sessions:
                        del self._sessions[session_id]
                        logger.info("Session expired", session_id=session_id)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in session cleanup loop", error=str(e))

    # Default Tools

    async def _register_default_tools(self) -> None:
        """Register default MCP tools."""
        
        # System info tool
        async def get_system_info(args: Dict[str, Any]) -> Dict[str, Any]:
            import platform
            import sys
            
            return {
                "platform": platform.platform(),
                "python_version": sys.version,
                "architecture": platform.architecture(),
                "processor": platform.processor(),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        await self.register_tool(
            name="get_system_info",
            description="Get system information",
            tool_type=MCPToolType.FUNCTION,
            handler=get_system_info,
            timeout=10
        )
        
        # Echo tool for testing
        async def echo(args: Dict[str, Any]) -> Dict[str, Any]:
            message = args.get("message", "Hello, World!")
            return {"echo": message, "timestamp": datetime.utcnow().isoformat()}
        
        await self.register_tool(
            name="echo",
            description="Echo a message back",
            tool_type=MCPToolType.FUNCTION,
            handler=echo,
            parameters=[
                MCPToolParameter(
                    name="message",
                    type="string",
                    description="Message to echo",
                    required=False,
                    default="Hello, World!"
                )
            ]
        )
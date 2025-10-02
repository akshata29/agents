"""
MCP Tool Registry and Management

Provides centralized registry for MCP tools with discovery, validation, and execution capabilities.
"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import logging

from .client import MCPClient, MCPTool
from ..core.security import SecurityContext
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class MCPToolType(str, Enum):
    """Types of MCP tools."""
    FUNCTION = "function"
    RESOURCE = "resource"
    PROMPT = "prompt"


class MCPToolStatus(str, Enum):
    """Status of MCP tool registration."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    DISABLED = "disabled"


class MCPToolRegistration(BaseModel):
    """MCP tool registration information."""
    name: str = Field(..., description="Tool name")
    description: str = Field("", description="Tool description")
    tool_type: MCPToolType = Field(MCPToolType.FUNCTION, description="Type of tool")
    status: MCPToolStatus = Field(MCPToolStatus.AVAILABLE, description="Tool status")
    server_name: str = Field(..., description="MCP server providing this tool")
    server_config: Dict[str, Any] = Field(default_factory=dict, description="Server configuration")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters schema")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    last_used: Optional[str] = Field(None, description="Last usage timestamp")
    usage_count: int = Field(0, description="Number of times used")


class MCPToolRegistry:
    """
    Registry for managing MCP tools across multiple servers.
    
    Provides tool discovery, registration, validation, and execution
    with security and monitoring capabilities.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize MCP tool registry."""
        self.settings = settings or Settings()
        self.tools: Dict[str, MCPToolRegistration] = {}
        self.clients: Dict[str, MCPClient] = {}
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the registry and discover tools."""
        try:
            logger.info("Initializing MCP tool registry...")
            
            # Initialize MCP clients for configured servers
            if hasattr(self.settings, 'mcp') and self.settings.mcp:
                for server_name, server_config in self.settings.mcp.servers.items():
                    await self._register_server(server_name, server_config)
            
            # Discover available tools
            await self._discover_tools()
            
            logger.info(f"MCP tool registry initialized with {len(self.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP tool registry: {e}")
            raise
    
    async def _register_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """Register an MCP server."""
        try:
            client = MCPClient(server_config.get("command", ""), server_config.get("args", []))
            await client.connect()
            
            self.clients[server_name] = client
            logger.info(f"Registered MCP server: {server_name}")
            
        except Exception as e:
            logger.error(f"Failed to register MCP server {server_name}: {e}")
    
    async def _discover_tools(self) -> None:
        """Discover tools from all registered servers."""
        async with self._lock:
            for server_name, client in self.clients.items():
                try:
                    # Get tools from server
                    tools = await client.list_tools()
                    
                    for tool in tools:
                        tool_reg = MCPToolRegistration(
                            name=tool.name,
                            description=tool.description,
                            tool_type=MCPToolType.FUNCTION,
                            status=MCPToolStatus.AVAILABLE,
                            server_name=server_name,
                            parameters=tool.inputSchema or {},
                            metadata={
                                "server_config": client.command,
                                "discovered_at": "now"
                            }
                        )
                        
                        # Use qualified name to avoid conflicts
                        qualified_name = f"{server_name}.{tool.name}"
                        self.tools[qualified_name] = tool_reg
                        
                        logger.debug(f"Discovered tool: {qualified_name}")
                
                except Exception as e:
                    logger.error(f"Failed to discover tools from {server_name}: {e}")
    
    async def register_tool(
        self, 
        name: str, 
        server_name: str, 
        description: str = "",
        tool_type: MCPToolType = MCPToolType.FUNCTION,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a tool manually."""
        try:
            async with self._lock:
                qualified_name = f"{server_name}.{name}"
                
                tool_reg = MCPToolRegistration(
                    name=name,
                    description=description,
                    tool_type=tool_type,
                    status=MCPToolStatus.AVAILABLE,
                    server_name=server_name,
                    parameters=parameters or {},
                    metadata=metadata or {}
                )
                
                self.tools[qualified_name] = tool_reg
                logger.info(f"Manually registered tool: {qualified_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register tool {name}: {e}")
            return False
    
    async def unregister_tool(self, qualified_name: str) -> bool:
        """Unregister a tool."""
        try:
            async with self._lock:
                if qualified_name in self.tools:
                    del self.tools[qualified_name]
                    logger.info(f"Unregistered tool: {qualified_name}")
                    return True
                else:
                    logger.warning(f"Tool not found for unregistration: {qualified_name}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to unregister tool {qualified_name}: {e}")
            return False
    
    def list_tools(self, server_name: Optional[str] = None, status_filter: Optional[MCPToolStatus] = None) -> List[MCPToolRegistration]:
        """List registered tools with optional filtering."""
        tools = list(self.tools.values())
        
        if server_name:
            tools = [t for t in tools if t.server_name == server_name]
        
        if status_filter:
            tools = [t for t in tools if t.status == status_filter]
        
        return tools
    
    def get_tool(self, qualified_name: str) -> Optional[MCPToolRegistration]:
        """Get tool by qualified name."""
        return self.tools.get(qualified_name)
    
    async def call_tool(
        self, 
        qualified_name: str, 
        arguments: Dict[str, Any],
        security_context: Optional[SecurityContext] = None
    ) -> Dict[str, Any]:
        """Execute a tool call through appropriate MCP server."""
        try:
            tool = self.get_tool(qualified_name)
            if not tool:
                raise ValueError(f"Tool not found: {qualified_name}")
            
            if tool.status != MCPToolStatus.AVAILABLE:
                raise ValueError(f"Tool not available: {qualified_name} (status: {tool.status})")
            
            # Security validation
            if security_context:
                if not await self._validate_tool_access(tool, security_context):
                    raise PermissionError(f"Access denied for tool: {qualified_name}")
            
            # Get MCP client for server
            client = self.clients.get(tool.server_name)
            if not client:
                raise ValueError(f"MCP server not available: {tool.server_name}")
            
            # Execute tool call
            result = await client.call_tool(tool.name, arguments)
            
            # Update usage statistics
            async with self._lock:
                tool.usage_count += 1
                tool.last_used = "now"  # Should use actual timestamp
            
            logger.info(f"Tool executed successfully: {qualified_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute tool {qualified_name}: {e}")
            raise
    
    async def _validate_tool_access(self, tool: MCPToolRegistration, security_context: SecurityContext) -> bool:
        """Validate if user has access to tool."""
        # Basic security validation - extend as needed
        if not security_context.user_id:
            return False
        
        # Check if tool is allowed for user role
        if hasattr(security_context, 'role'):
            restricted_tools = ["system", "admin", "delete"]
            if any(keyword in tool.name.lower() for keyword in restricted_tools):
                return security_context.role in ["admin", "system"]
        
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all MCP servers and tools."""
        health_status = {
            "registry_status": "healthy",
            "total_tools": len(self.tools),
            "servers": {},
            "tools_by_status": {}
        }
        
        # Check server health
        for server_name, client in self.clients.items():
            try:
                # Try to ping server
                await client.list_tools()
                health_status["servers"][server_name] = "healthy"
            except Exception as e:
                health_status["servers"][server_name] = f"unhealthy: {str(e)}"
        
        # Count tools by status
        for status in MCPToolStatus:
            count = len([t for t in self.tools.values() if t.status == status])
            health_status["tools_by_status"][status.value] = count
        
        return health_status
    
    async def refresh_tools(self) -> None:
        """Refresh tool discovery from all servers."""
        logger.info("Refreshing MCP tools...")
        await self._discover_tools()
        logger.info(f"Tool refresh completed - {len(self.tools)} tools available")
    
    async def shutdown(self) -> None:
        """Shutdown registry and disconnect from servers."""
        logger.info("Shutting down MCP tool registry...")
        
        for server_name, client in self.clients.items():
            try:
                await client.disconnect()
                logger.debug(f"Disconnected from MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {server_name}: {e}")
        
        self.clients.clear()
        self.tools.clear()
        
        logger.info("MCP tool registry shutdown complete")
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        stats = {
            "total_tools": len(self.tools),
            "total_usage": sum(t.usage_count for t in self.tools.values()),
            "most_used_tools": [],
            "least_used_tools": [],
            "servers": {}
        }
        
        # Sort tools by usage
        sorted_tools = sorted(self.tools.values(), key=lambda t: t.usage_count, reverse=True)
        
        stats["most_used_tools"] = [
            {"name": t.name, "usage_count": t.usage_count} 
            for t in sorted_tools[:10]
        ]
        
        stats["least_used_tools"] = [
            {"name": t.name, "usage_count": t.usage_count} 
            for t in sorted_tools[-10:]
        ]
        
        # Server statistics
        for server_name in set(t.server_name for t in self.tools.values()):
            server_tools = [t for t in self.tools.values() if t.server_name == server_name]
            stats["servers"][server_name] = {
                "tool_count": len(server_tools),
                "total_usage": sum(t.usage_count for t in server_tools)
            }
        
        return stats
"""
MCP Client - Model Context Protocol Client Implementation

Provides client functionality for connecting to MCP servers and executing tools.
Supports tool discovery, execution, and result handling with proper error management.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from urllib.parse import urlparse

import aiohttp
import structlog
import websockets
from pydantic import BaseModel, Field

from ..config.settings import Settings


logger = structlog.get_logger(__name__)


class MCPTool(BaseModel):
    """MCP tool definition."""
    
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    server_url: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    

class MCPResource(BaseModel):
    """MCP resource definition."""
    
    uri: str
    name: str
    description: str
    mime_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPServerConnection(BaseModel):
    """MCP server connection information."""
    
    url: str
    name: str
    description: str = ""
    connected: bool = False
    last_ping: Optional[datetime] = None
    tools: List[MCPTool] = Field(default_factory=list)
    resources: List[MCPResource] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPExecutionResult(BaseModel):
    """Result of MCP tool execution."""
    
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    tool_name: str = ""
    server_url: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPClient:
    """
    MCP client for connecting to Model Context Protocol servers.
    
    Provides functionality for server discovery, tool execution,
    and resource management with SSE-based communication.
    """

    def __init__(self, settings: Settings):
        """Initialize MCP client."""
        self.settings = settings
        
        # Connection management
        self._connections: Dict[str, MCPServerConnection] = {}
        self._websockets: Dict[str, websockets.WebSocketServerProtocol] = {}
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        # Tool and resource caches
        self._tools_cache: Dict[str, MCPTool] = {}
        self._resources_cache: Dict[str, MCPResource] = {}
        
        # Configuration
        self.timeout = settings.mcp.tool_timeout
        self.max_concurrent = settings.mcp.max_concurrent_tools
        
        # Execution tracking
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._execution_semaphore = asyncio.Semaphore(self.max_concurrent)
        
        logger.info("MCPClient initialized")

    async def initialize(self) -> None:
        """Initialize the MCP client."""
        logger.info("Initializing MCP client")
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._http_session = aiohttp.ClientSession(timeout=timeout)
        
        logger.info("MCP client initialization complete")

    async def shutdown(self) -> None:
        """Shutdown the MCP client."""
        logger.info("Shutting down MCP client")
        
        # Cancel active executions
        for execution_id, task in list(self._active_executions.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket connections
        for ws in self._websockets.values():
            if not ws.closed:
                await ws.close()
        
        # Close HTTP session properly
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
            # Give it time to close properly
            await asyncio.sleep(0.25)
        
        logger.info("MCP client shutdown complete")

    async def connect_server(
        self,
        server_url: str,
        name: str = "",
        description: str = ""
    ) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            server_url: MCP server URL
            name: Server name (optional)
            description: Server description (optional)
            
        Returns:
            True if connection successful
        """
        try:
            logger.info("Connecting to MCP server", server_url=server_url)
            
            # Parse URL to determine connection method
            parsed_url = urlparse(server_url)
            
            if parsed_url.scheme in ['ws', 'wss']:
                # WebSocket connection
                success = await self._connect_websocket(server_url, name, description)
            else:
                # HTTP/HTTPS connection
                success = await self._connect_http(server_url, name, description)
            
            if success:
                # Discover tools and resources
                await self._discover_capabilities(server_url)
                
                logger.info(
                    "Connected to MCP server",
                    server_url=server_url,
                    tools_count=len(self._connections[server_url].tools),
                    resources_count=len(self._connections[server_url].resources)
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to connect to MCP server",
                server_url=server_url,
                error=str(e)
            )
            return False

    async def disconnect_server(self, server_url: str) -> bool:
        """Disconnect from an MCP server."""
        if server_url not in self._connections:
            return False
        
        try:
            # Close WebSocket if exists
            if server_url in self._websockets:
                ws = self._websockets[server_url]
                if not ws.closed:
                    await ws.close()
                del self._websockets[server_url]
            
            # Remove from connections
            connection = self._connections[server_url]
            connection.connected = False
            
            # Clean up caches
            tools_to_remove = [name for name, tool in self._tools_cache.items() 
                             if tool.server_url == server_url]
            for tool_name in tools_to_remove:
                del self._tools_cache[tool_name]
            
            resources_to_remove = [uri for uri, resource in self._resources_cache.items() 
                                 if resource.metadata.get("server_url") == server_url]
            for resource_uri in resources_to_remove:
                del self._resources_cache[resource_uri]
            
            logger.info("Disconnected from MCP server", server_url=server_url)
            return True
            
        except Exception as e:
            logger.error(
                "Error disconnecting from MCP server",
                server_url=server_url,
                error=str(e)
            )
            return False

    async def list_servers(self) -> List[MCPServerConnection]:
        """List all connected MCP servers."""
        return list(self._connections.values())

    async def list_tools(self, server_url: Optional[str] = None) -> List[MCPTool]:
        """
        List available MCP tools.
        
        Args:
            server_url: Optional server URL filter
            
        Returns:
            List of available tools
        """
        if server_url:
            connection = self._connections.get(server_url)
            return connection.tools if connection else []
        
        return list(self._tools_cache.values())

    async def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a specific MCP tool by name."""
        return self._tools_cache.get(tool_name)

    async def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available."""
        return tool_name in self._tools_cache
    
    async def discover_tools(self, server_url: Optional[str] = None) -> List[MCPTool]:
        """
        Discover available tools from connected servers.
        
        Args:
            server_url: Optional specific server to discover from
            
        Returns:
            List of discovered tools
        """
        discovered_tools = []
        
        if server_url:
            # Discover from specific server
            if server_url in self._connections:
                await self._discover_capabilities(server_url)
                connection = self._connections[server_url]
                discovered_tools.extend(connection.tools)
        else:
            # Discover from all connected servers
            for url in list(self._connections.keys()):
                try:
                    await self._discover_capabilities(url)
                    connection = self._connections[url]
                    discovered_tools.extend(connection.tools)
                except Exception as e:
                    logger.error(
                        "Failed to discover tools from server",
                        server_url=url,
                        error=str(e)
                    )
        
        logger.info(
            "Tool discovery complete",
            tools_count=len(discovered_tools),
            server_url=server_url or "all"
        )
        
        return discovered_tools
        return tool_name in self._tools_cache

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> MCPExecutionResult:
        """
        Execute an MCP tool.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            timeout: Optional timeout override
            
        Returns:
            Execution result
        """
        tool = self._tools_cache.get(tool_name)
        if not tool:
            return MCPExecutionResult(
                success=False,
                error=f"Tool not found: {tool_name}",
                tool_name=tool_name
            )
        
        execution_id = f"{tool_name}_{datetime.utcnow().timestamp()}"
        
        async with self._execution_semaphore:
            try:
                logger.debug(
                    "Executing MCP tool",
                    tool_name=tool_name,
                    server_url=tool.server_url,
                    parameters=parameters
                )
                
                start_time = datetime.utcnow()
                
                # Execute the tool
                if tool.server_url in self._websockets:
                    result = await self._execute_tool_websocket(tool, parameters, timeout)
                else:
                    result = await self._execute_tool_http(tool, parameters, timeout)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                logger.debug(
                    "MCP tool execution completed",
                    tool_name=tool_name,
                    execution_time=execution_time,
                    success=result.success
                )
                
                result.execution_time = execution_time
                return result
                
            except asyncio.TimeoutError:
                return MCPExecutionResult(
                    success=False,
                    error=f"Tool execution timed out: {tool_name}",
                    tool_name=tool_name,
                    server_url=tool.server_url
                )
            
            except Exception as e:
                logger.error(
                    "MCP tool execution failed",
                    tool_name=tool_name,
                    error=str(e),
                    exc_info=True
                )
                
                return MCPExecutionResult(
                    success=False,
                    error=str(e),
                    tool_name=tool_name,
                    server_url=tool.server_url
                )

    async def list_resources(self, server_url: Optional[str] = None) -> List[MCPResource]:
        """List available MCP resources."""
        if server_url:
            connection = self._connections.get(server_url)
            return connection.resources if connection else []
        
        return list(self._resources_cache.values())

    async def get_resource(self, resource_uri: str) -> Optional[Any]:
        """Get content of an MCP resource."""
        resource = self._resources_cache.get(resource_uri)
        if not resource:
            return None
        
        server_url = resource.metadata.get("server_url")
        if not server_url:
            return None
        
        try:
            if server_url in self._websockets:
                return await self._get_resource_websocket(resource)
            else:
                return await self._get_resource_http(resource)
        except Exception as e:
            logger.error(
                "Failed to get MCP resource",
                resource_uri=resource_uri,
                error=str(e)
            )
            return None

    # Private methods

    async def _connect_websocket(
        self,
        server_url: str,
        name: str,
        description: str
    ) -> bool:
        """Connect to MCP server via WebSocket."""
        try:
            ws = await websockets.connect(server_url)
            self._websockets[server_url] = ws
            
            connection = MCPServerConnection(
                url=server_url,
                name=name or server_url,
                description=description,
                connected=True
            )
            self._connections[server_url] = connection
            
            return True
            
        except Exception as e:
            logger.error(
                "WebSocket connection failed",
                server_url=server_url,
                error=str(e)
            )
            return False

    async def _connect_http(
        self,
        server_url: str,
        name: str,
        description: str
    ) -> bool:
        """Connect to MCP server via HTTP."""
        try:
            # Test connection with a ping
            if not self._http_session:
                return False
            
            async with self._http_session.get(f"{server_url}/health") as response:
                if response.status == 200:
                    connection = MCPServerConnection(
                        url=server_url,
                        name=name or server_url,
                        description=description,
                        connected=True,
                        last_ping=datetime.utcnow()
                    )
                    self._connections[server_url] = connection
                    return True
            
            return False
            
        except Exception as e:
            logger.error(
                "HTTP connection failed",
                server_url=server_url,
                error=str(e)
            )
            return False

    async def _discover_capabilities(self, server_url: str) -> None:
        """Discover tools and resources from MCP server."""
        try:
            # Discover tools
            await self._discover_tools(server_url)
            
            # Discover resources
            await self._discover_resources(server_url)
            
        except Exception as e:
            logger.error(
                "Capability discovery failed",
                server_url=server_url,
                error=str(e)
            )

    async def _discover_tools(self, server_url: str) -> None:
        """Discover tools from MCP server."""
        if not self._http_session:
            return
        
        try:
            async with self._http_session.get(f"{server_url}/tools") as response:
                if response.status == 200:
                    tools_data = await response.json()
                    
                    connection = self._connections[server_url]
                    for tool_data in tools_data.get("tools", []):
                        tool = MCPTool(
                            name=tool_data["name"],
                            description=tool_data["description"],
                            input_schema=tool_data.get("inputSchema", {}),
                            output_schema=tool_data.get("outputSchema"),
                            server_url=server_url
                        )
                        
                        connection.tools.append(tool)
                        self._tools_cache[tool.name] = tool
                        
        except Exception as e:
            logger.error(
                "Tool discovery failed",
                server_url=server_url,
                error=str(e)
            )

    async def _discover_resources(self, server_url: str) -> None:
        """Discover resources from MCP server."""
        if not self._http_session:
            return
        
        try:
            async with self._http_session.get(f"{server_url}/resources") as response:
                if response.status == 200:
                    resources_data = await response.json()
                    
                    connection = self._connections[server_url]
                    for resource_data in resources_data.get("resources", []):
                        resource = MCPResource(
                            uri=resource_data["uri"],
                            name=resource_data["name"],
                            description=resource_data["description"],
                            mime_type=resource_data.get("mimeType"),
                            metadata={"server_url": server_url}
                        )
                        
                        connection.resources.append(resource)
                        self._resources_cache[resource.uri] = resource
                        
        except Exception as e:
            logger.error(
                "Resource discovery failed",
                server_url=server_url,
                error=str(e)
            )

    async def _execute_tool_websocket(
        self,
        tool: MCPTool,
        parameters: Dict[str, Any],
        timeout: Optional[int]
    ) -> MCPExecutionResult:
        """Execute tool via WebSocket."""
        ws = self._websockets[tool.server_url]
        
        # Prepare MCP message
        message = {
            "jsonrpc": "2.0",
            "id": f"tool_{datetime.utcnow().timestamp()}",
            "method": "tools/call",
            "params": {
                "name": tool.name,
                "arguments": parameters
            }
        }
        
        # Send message
        await ws.send(json.dumps(message))
        
        # Wait for response
        response_timeout = timeout or self.timeout
        try:
            response_data = await asyncio.wait_for(
                ws.recv(), 
                timeout=response_timeout
            )
            
            response = json.loads(response_data)
            
            if "error" in response:
                return MCPExecutionResult(
                    success=False,
                    error=response["error"].get("message", "Unknown error"),
                    tool_name=tool.name,
                    server_url=tool.server_url
                )
            
            return MCPExecutionResult(
                success=True,
                result=response.get("result"),
                tool_name=tool.name,
                server_url=tool.server_url
            )
            
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return MCPExecutionResult(
                success=False,
                error=str(e),
                tool_name=tool.name,
                server_url=tool.server_url
            )

    async def _execute_tool_http(
        self,
        tool: MCPTool,
        parameters: Dict[str, Any],
        timeout: Optional[int]
    ) -> MCPExecutionResult:
        """Execute tool via HTTP."""
        if not self._http_session:
            return MCPExecutionResult(
                success=False,
                error="HTTP session not available",
                tool_name=tool.name,
                server_url=tool.server_url
            )
        
        payload = {
            "name": tool.name,
            "arguments": parameters
        }
        
        try:
            request_timeout = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with self._http_session.post(
                f"{tool.server_url}/tools/call",
                json=payload,
                timeout=request_timeout
            ) as response:
                
                if response.status == 200:
                    result_data = await response.json()
                    return MCPExecutionResult(
                        success=True,
                        result=result_data,
                        tool_name=tool.name,
                        server_url=tool.server_url
                    )
                else:
                    error_text = await response.text()
                    return MCPExecutionResult(
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        tool_name=tool.name,
                        server_url=tool.server_url
                    )
                    
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return MCPExecutionResult(
                success=False,
                error=str(e),
                tool_name=tool.name,
                server_url=tool.server_url
            )

    async def _get_resource_websocket(self, resource: MCPResource) -> Optional[Any]:
        """Get resource content via WebSocket."""
        server_url = resource.metadata.get("server_url")
        ws = self._websockets[server_url]
        
        message = {
            "jsonrpc": "2.0",
            "id": f"resource_{datetime.utcnow().timestamp()}",
            "method": "resources/read",
            "params": {
                "uri": resource.uri
            }
        }
        
        await ws.send(json.dumps(message))
        response_data = await ws.recv()
        response = json.loads(response_data)
        
        if "error" in response:
            return None
        
        return response.get("result", {}).get("contents")

    async def _get_resource_http(self, resource: MCPResource) -> Optional[Any]:
        """Get resource content via HTTP."""
        if not self._http_session:
            return None
        
        server_url = resource.metadata.get("server_url")
        
        async with self._http_session.get(
            f"{server_url}/resources/read",
            params={"uri": resource.uri}
        ) as response:
            
            if response.status == 200:
                return await response.json()
            return None
"""
MAF MCP Adapter

Integration layer between Microsoft Agent Framework's MCP tools and our custom MCP implementation.
Provides a unified interface to use both MAF's simple MCP client and our advanced MCP features.

Key Capabilities:
- Register external MCP servers using MAF's McpTool
- Convert MAF tool definitions to our framework format
- Provide unified tool execution interface
- Support both MAF and custom MCP simultaneously
"""

from typing import Dict, List, Any, Optional
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

# Try to import MAF MCP tools (optional dependency)
try:
    from azure.ai.agents.models import McpTool as AzureMcpTool
    MAF_MCP_AVAILABLE = True
    AzureMcpToolType = AzureMcpTool
except ImportError:
    MAF_MCP_AVAILABLE = False
    logger.warning("Azure AI Agents SDK not available. MAF MCP adapter will be disabled.")
    AzureMcpTool = None
    AzureMcpToolType = Any  # Fallback type


@dataclass
class ExternalMCPServer:
    """Configuration for an external MCP server using MAF."""
    server_label: str
    server_url: str
    description: str = ""
    allowed_tools: List[str] = None
    require_approval: str = "auto"  # auto, always, never
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.allowed_tools is None:
            self.allowed_tools = []
        if self.headers is None:
            self.headers = {}


class MAFMCPAdapter:
    """
    Adapter for integrating Microsoft Agent Framework's MCP tools.
    
    This adapter allows the framework to use MAF's simple MCP client
    for connecting to external MCP servers while maintaining compatibility
    with our custom MCP implementation for internal servers.
    
    Usage:
        # Create adapter
        adapter = MAFMCPAdapter()
        
        # Register external server
        github_server = adapter.register_external_server(
            server_label="github",
            server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
            description="GitHub MCP server for Azure REST API specs"
        )
        
        # Get tool definitions for agent
        tools = adapter.get_tool_definitions("github")
        
        # Use with agent
        agent = agents_client.create_agent(
            model="gpt-4o",
            tools=tools
        )
    """
    
    def __init__(self):
        """Initialize MAF MCP adapter."""
        if not MAF_MCP_AVAILABLE:
            raise ImportError(
                "Azure AI Agents SDK is required for MAF MCP adapter. "
                "Install with: pip install azure-ai-agents"
            )
        
        self.external_servers: Dict[str, ExternalMCPServer] = {}
        self.mcp_tools: Dict[str, Any] = {}  # type: ignore - AzureMcpTool instances
        
        logger.info("MAF MCP adapter initialized")
    
    def register_external_server(
        self,
        server_label: str,
        server_url: str,
        description: str = "",
        allowed_tools: List[str] = None,
        require_approval: str = "auto",
        headers: Dict[str, str] = None
    ) -> ExternalMCPServer:
        """
        Register an external MCP server using MAF's MCP client.
        
        Args:
            server_label: Unique label for the server
            server_url: MCP server endpoint URL
            description: Human-readable description
            allowed_tools: List of tool names to allow (empty = all)
            require_approval: Tool approval mode (auto, always, never)
            headers: Custom HTTP headers for authentication
            
        Returns:
            ExternalMCPServer configuration
            
        Example:
            >>> adapter.register_external_server(
            ...     server_label="github",
            ...     server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
            ...     allowed_tools=["search_azure_rest_api_code"]
            ... )
        """
        if server_label in self.external_servers:
            logger.warning(f"Server {server_label} already registered, updating...")
        
        # Create server config
        server_config = ExternalMCPServer(
            server_label=server_label,
            server_url=server_url,
            description=description,
            allowed_tools=allowed_tools or [],
            require_approval=require_approval,
            headers=headers or {}
        )
        
        # Create MAF MCP tool
        mcp_tool = AzureMcpTool(
            server_label=server_label,
            server_url=server_url,
            allowed_tools=allowed_tools or []
        )
        
        # Update headers if provided
        if headers:
            for key, value in headers.items():
                mcp_tool.update_headers(key, value)
        
        # Set approval mode
        if require_approval != "auto":
            mcp_tool.set_approval_mode(require_approval)
        
        # Store
        self.external_servers[server_label] = server_config
        self.mcp_tools[server_label] = mcp_tool
        
        logger.info(
            f"Registered external MCP server",
            server=server_label,
            url=server_url,
            allowed_tools=len(allowed_tools) if allowed_tools else "all"
        )
        
        return server_config
    
    def unregister_server(self, server_label: str) -> None:
        """
        Unregister an external MCP server.
        
        Args:
            server_label: Label of server to unregister
        """
        if server_label not in self.external_servers:
            raise ValueError(f"Server {server_label} not registered")
        
        del self.external_servers[server_label]
        del self.mcp_tools[server_label]
        
        logger.info(f"Unregistered external MCP server", server=server_label)
    
    def get_mcp_tool(self, server_label: str) -> Any:  # type: ignore - Returns AzureMcpTool
        """
        Get MAF MCP tool instance for a registered server.
        
        Args:
            server_label: Label of registered server
            
        Returns:
            Azure McpTool instance
        """
        if server_label not in self.mcp_tools:
            raise ValueError(f"Server {server_label} not registered")
        
        return self.mcp_tools[server_label]
    
    def get_tool_definitions(self, server_label: str) -> List[Dict[str, Any]]:
        """
        Get tool definitions for a registered server.
        
        These definitions can be passed to Azure AI Agents.
        
        Args:
            server_label: Label of registered server
            
        Returns:
            List of tool definitions
        """
        mcp_tool = self.get_mcp_tool(server_label)
        return mcp_tool.definitions
    
    def get_all_tool_definitions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get tool definitions for all registered servers.
        
        Returns:
            Dictionary mapping server labels to tool definitions
        """
        return {
            server_label: self.get_tool_definitions(server_label)
            for server_label in self.external_servers.keys()
        }
    
    def get_tool_resources(self, server_label: str):
        """
        Get tool resources for a registered server.
        
        Tool resources are required when creating agent runs.
        
        Args:
            server_label: Label of registered server
            
        Returns:
            Tool resources for the MCP server
        """
        mcp_tool = self.get_mcp_tool(server_label)
        return mcp_tool.resources
    
    def update_headers(
        self,
        server_label: str,
        header_name: str,
        header_value: str
    ) -> None:
        """
        Update authentication headers for a server.
        
        Args:
            server_label: Label of registered server
            header_name: Header name (e.g., "Authorization")
            header_value: Header value (e.g., "Bearer token123")
        """
        mcp_tool = self.get_mcp_tool(server_label)
        mcp_tool.update_headers(header_name, header_value)
        
        # Update our config
        server_config = self.external_servers[server_label]
        server_config.headers[header_name] = header_value
        
        logger.info(
            f"Updated headers for server",
            server=server_label,
            header=header_name
        )
    
    def allow_tool(self, server_label: str, tool_name: str) -> None:
        """
        Add a tool to the allowed list for a server.
        
        Args:
            server_label: Label of registered server
            tool_name: Name of tool to allow
        """
        mcp_tool = self.get_mcp_tool(server_label)
        mcp_tool.allow_tool(tool_name)
        
        # Update our config
        server_config = self.external_servers[server_label]
        if tool_name not in server_config.allowed_tools:
            server_config.allowed_tools.append(tool_name)
        
        logger.info(
            f"Allowed tool for server",
            server=server_label,
            tool=tool_name
        )
    
    def disallow_tool(self, server_label: str, tool_name: str) -> None:
        """
        Remove a tool from the allowed list for a server.
        
        Args:
            server_label: Label of registered server
            tool_name: Name of tool to disallow
        """
        mcp_tool = self.get_mcp_tool(server_label)
        mcp_tool.disallow_tool(tool_name)
        
        # Update our config
        server_config = self.external_servers[server_label]
        if tool_name in server_config.allowed_tools:
            server_config.allowed_tools.remove(tool_name)
        
        logger.info(
            f"Disallowed tool for server",
            server=server_label,
            tool=tool_name
        )
    
    def list_servers(self) -> List[str]:
        """
        List all registered external MCP servers.
        
        Returns:
            List of server labels
        """
        return list(self.external_servers.keys())
    
    def get_server_info(self, server_label: str) -> Dict[str, Any]:
        """
        Get information about a registered server.
        
        Args:
            server_label: Label of registered server
            
        Returns:
            Dictionary with server information
        """
        if server_label not in self.external_servers:
            raise ValueError(f"Server {server_label} not registered")
        
        server_config = self.external_servers[server_label]
        mcp_tool = self.mcp_tools[server_label]
        
        return {
            "server_label": server_config.server_label,
            "server_url": server_config.server_url,
            "description": server_config.description,
            "allowed_tools": mcp_tool.allowed_tools,
            "require_approval": server_config.require_approval,
            "has_headers": len(server_config.headers) > 0,
            "tool_count": len(self.get_tool_definitions(server_label))
        }
    
    def get_all_servers_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered servers.
        
        Returns:
            Dictionary mapping server labels to server info
        """
        return {
            server_label: self.get_server_info(server_label)
            for server_label in self.external_servers.keys()
        }


def create_maf_mcp_adapter_from_config(config: Dict[str, Any]) -> MAFMCPAdapter:
    """
    Create MAF MCP adapter from configuration dictionary.
    
    Args:
        config: Configuration dict with external_servers section
        
    Returns:
        Configured MAF MCP adapter
        
    Example:
        >>> config = {
        ...     "external_servers": {
        ...         "github": {
        ...             "server_url": "https://gitmcp.io/Azure/azure-rest-api-specs",
        ...             "description": "GitHub MCP server",
        ...             "allowed_tools": ["search_azure_rest_api_code"]
        ...         }
        ...     }
        ... }
        >>> adapter = create_maf_mcp_adapter_from_config(config)
    """
    adapter = MAFMCPAdapter()
    
    external_servers = config.get("external_servers", {})
    for server_label, server_config in external_servers.items():
        adapter.register_external_server(
            server_label=server_label,
            server_url=server_config["server_url"],
            description=server_config.get("description", ""),
            allowed_tools=server_config.get("allowed_tools", []),
            require_approval=server_config.get("require_approval", "auto"),
            headers=server_config.get("headers", {})
        )
    
    logger.info(f"Created MAF MCP adapter with {len(external_servers)} servers")
    
    return adapter


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example():
        """Example of using MAF MCP adapter."""
        
        # Create adapter
        adapter = MAFMCPAdapter()
        
        # Register GitHub MCP server
        adapter.register_external_server(
            server_label="github",
            server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
            description="GitHub MCP server for Azure REST API specifications",
            allowed_tools=["search_azure_rest_api_code"]
        )
        
        # Register Microsoft Learn MCP server
        adapter.register_external_server(
            server_label="ms-learn",
            server_url="https://learn.microsoft.com/api/mcp",
            description="Microsoft Learn documentation MCP server",
            allowed_tools=["microsoft_docs_search", "microsoft_docs_fetch"]
        )
        
        # List all servers
        print("\nRegistered MCP Servers:")
        for server_label in adapter.list_servers():
            info = adapter.get_server_info(server_label)
            print(f"  {server_label}:")
            print(f"    URL: {info['server_url']}")
            print(f"    Tools: {info['allowed_tools']}")
            print(f"    Description: {info['description']}")
        
        # Get tool definitions for use with agents
        github_tools = adapter.get_tool_definitions("github")
        print(f"\nGitHub tools: {len(github_tools)} tools available")
        
        # Get tool resources for agent runs
        github_resources = adapter.get_tool_resources("github")
        print(f"GitHub resources ready for agent runs")
        
        # Dynamic tool management
        adapter.allow_tool("github", "list_commits")
        print("\nAdded 'list_commits' tool to GitHub server")
        
        updated_info = adapter.get_server_info("github")
        print(f"Updated allowed tools: {updated_info['allowed_tools']}")
    
    # Run example
    asyncio.run(example())

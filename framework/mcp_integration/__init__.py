"""
Model Context Protocol (MCP) Integration

Provides MCP server, client, and tool implementations for standardized
tool communication and dynamic capability extension.

Includes MAF MCP adapter for integration with Microsoft Agent Framework's
native MCP tools for external server connectivity.
"""

from .client import MCPClient
from .server import MCPServer
from .tools import MCPToolRegistry

# MAF MCP adapter (optional - requires azure-ai-agents)
try:
    from .maf_adapter import MAFMCPAdapter, ExternalMCPServer, create_maf_mcp_adapter_from_config
    MAF_ADAPTER_AVAILABLE = True
except ImportError:
    MAFMCPAdapter = None
    ExternalMCPServer = None
    create_maf_mcp_adapter_from_config = None
    MAF_ADAPTER_AVAILABLE = False

__all__ = [
    "MCPClient",
    "MCPServer", 
    "MCPToolRegistry",
    # MAF integration (optional)
    "MAFMCPAdapter",
    "ExternalMCPServer",
    "create_maf_mcp_adapter_from_config",
    "MAF_ADAPTER_AVAILABLE"
]
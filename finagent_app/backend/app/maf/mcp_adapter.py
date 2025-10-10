"""Microsoft Agent Framework MCP adapter utilities scoped to the finagent app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# Optional dependency: Azure AI Agents SDK provides McpTool implementation
try:  # pragma: no cover - optional dependency branch
    from azure.ai.agents.models import McpTool as AzureMcpTool

    MAF_MCP_AVAILABLE = True
except ImportError:  # pragma: no cover - executed when SDK missing
    MAF_MCP_AVAILABLE = False
    logger.warning(
        "Azure AI Agents SDK not available. MAF MCP adapter will be disabled."
    )
    AzureMcpTool = None  # type: ignore[assignment]


@dataclass
class ExternalMCPServer:
    """Configuration for an external MCP server using MAF."""

    server_label: str
    server_url: str
    description: str = ""
    allowed_tools: List[str] | None = None
    require_approval: str = "auto"  # auto, always, never
    headers: Dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.allowed_tools is None:
            self.allowed_tools = []
        if self.headers is None:
            self.headers = {}


class MAFMCPAdapter:
    """Adapter for integrating Microsoft Agent Framework's MCP tools."""

    def __init__(self) -> None:
        if not MAF_MCP_AVAILABLE:
            raise ImportError(
                "Azure AI Agents SDK is required for MAF MCP adapter. Install with: "
                "pip install azure-ai-agents"
            )
        self.external_servers: Dict[str, ExternalMCPServer] = {}
        self.mcp_tools: Dict[str, Any] = {}

        logger.info("MAF MCP adapter initialized")

    def register_external_server(
        self,
        server_label: str,
        server_url: str,
        description: str = "",
        allowed_tools: Optional[List[str]] = None,
        require_approval: str = "auto",
        headers: Optional[Dict[str, str]] = None,
    ) -> ExternalMCPServer:
        if server_label in self.external_servers:
            logger.warning("Server %s already registered, updating...", server_label)

        server_config = ExternalMCPServer(
            server_label=server_label,
            server_url=server_url,
            description=description,
            allowed_tools=allowed_tools or [],
            require_approval=require_approval,
            headers=headers or {},
        )

        mcp_tool = AzureMcpTool(
            server_label=server_label,
            server_url=server_url,
            allowed_tools=allowed_tools or [],
        )

        if headers:
            for key, value in headers.items():
                mcp_tool.update_headers(key, value)

        if require_approval != "auto":
            mcp_tool.set_approval_mode(require_approval)

        self.external_servers[server_label] = server_config
        self.mcp_tools[server_label] = mcp_tool

        logger.info(
            "Registered external MCP server",
            server=server_label,
            url=server_url,
            allowed_tools=len(allowed_tools) if allowed_tools else "all",
        )

        return server_config

    def unregister_server(self, server_label: str) -> None:
        if server_label not in self.external_servers:
            raise ValueError(f"Server {server_label} not registered")

        del self.external_servers[server_label]
        del self.mcp_tools[server_label]

        logger.info("Unregistered external MCP server", server=server_label)

    def get_mcp_tool(self, server_label: str) -> Any:
        if server_label not in self.mcp_tools:
            raise ValueError(f"Server {server_label} not registered")

        return self.mcp_tools[server_label]

    def get_tool_definitions(self, server_label: str) -> List[Dict[str, Any]]:
        mcp_tool = self.get_mcp_tool(server_label)
        return mcp_tool.definitions

    def get_all_tool_definitions(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            label: self.get_tool_definitions(label)
            for label in self.external_servers.keys()
        }

    def get_tool_resources(self, server_label: str) -> Any:
        mcp_tool = self.get_mcp_tool(server_label)
        return mcp_tool.resources

    def update_headers(
        self,
        server_label: str,
        header_name: str,
        header_value: str,
    ) -> None:
        mcp_tool = self.get_mcp_tool(server_label)
        mcp_tool.update_headers(header_name, header_value)

        server_config = self.external_servers[server_label]
        server_config.headers[header_name] = header_value

        logger.info(
            "Updated headers for server",
            server=server_label,
            header=header_name,
        )

    def allow_tool(self, server_label: str, tool_name: str) -> None:
        mcp_tool = self.get_mcp_tool(server_label)
        mcp_tool.allow_tool(tool_name)

        server_config = self.external_servers[server_label]
        if tool_name not in server_config.allowed_tools:
            server_config.allowed_tools.append(tool_name)

        logger.info("Allowed tool for server", server=server_label, tool=tool_name)

    def disallow_tool(self, server_label: str, tool_name: str) -> None:
        mcp_tool = self.get_mcp_tool(server_label)
        mcp_tool.disallow_tool(tool_name)

        server_config = self.external_servers[server_label]
        if tool_name in server_config.allowed_tools:
            server_config.allowed_tools.remove(tool_name)

        logger.info("Disallowed tool for server", server=server_label, tool=tool_name)

    def list_servers(self) -> List[str]:
        return list(self.external_servers.keys())

    def get_server_info(self, server_label: str) -> Dict[str, Any]:
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
            "has_headers": bool(server_config.headers),
            "tool_count": len(self.get_tool_definitions(server_label)),
        }

    def get_all_servers_info(self) -> Dict[str, Dict[str, Any]]:
        return {label: self.get_server_info(label) for label in self.external_servers.keys()}


def create_maf_mcp_adapter_from_config(config: Dict[str, Any]) -> MAFMCPAdapter:
    adapter = MAFMCPAdapter()

    external_servers = config.get("external_servers", {})
    for server_label, server_config in external_servers.items():
        adapter.register_external_server(
            server_label=server_label,
            server_url=server_config["server_url"],
            description=server_config.get("description", ""),
            allowed_tools=server_config.get("allowed_tools", []),
            require_approval=server_config.get("require_approval", "auto"),
            headers=server_config.get("headers", {}),
        )

    logger.info("Created MAF MCP adapter with %d servers", len(external_servers))

    return adapter


__all__ = [
    "ExternalMCPServer",
    "MAFMCPAdapter",
    "create_maf_mcp_adapter_from_config",
    "MAF_MCP_AVAILABLE",
]

"""
Magentic Foundation Framework - Enterprise Multi-Agent Orchestration

A comprehensive framework for building and orchestrating multi-agent systems
with dynamic planning, MCP tool integration, workflow management, and enterprise security.
"""

__version__ = "1.0.0"
__author__ = "Foundation Team"
__description__ = "Enterprise Multi-Agent Orchestration Framework"

# Core imports for easy access
from .main import MagenticFoundation, create_app
from .core.orchestrator import MagenticOrchestrator
from .core.registry import AgentRegistry
from .core.planning import DynamicPlanner
from .core.security import SecurityManager
from .core.observability import ObservabilityService
from .agents.factory import AgentFactory
from .mcp_integration.client import MCPClient
from .mcp_integration.server import MCPServer
from .workflows.engine import WorkflowEngine
from .api.service import APIService
from .patterns.sequential import SequentialPattern
from .patterns.concurrent import ConcurrentPattern
from .patterns.react import ReActPattern

__all__ = [
    "MagenticFoundation",
    "create_app",
    "MagenticOrchestrator",
    "AgentRegistry", 
    "DynamicPlanner",
    "SecurityManager",
    "ObservabilityService",
    "AgentFactory",
    "MCPClient",
    "MCPServer", 
    "WorkflowEngine",
    "APIService",
    "SequentialPattern",
    "ConcurrentPattern", 
    "ReActPattern"
]
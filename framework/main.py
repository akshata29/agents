"""
Main Application - Magentic Foundation Framework

Complete enterprise multi-agent framework with orchestration, workflows,
MCP integration, security, monitoring, and REST API.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import structlog
import uvicorn
from fastapi import FastAPI

from .config.settings import Settings
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

logger = structlog.get_logger(__name__)


class MagenticFoundation:
    """
    Main Magentic Foundation Framework Application.
    
    Coordinates all framework components including orchestration, workflows,
    MCP integration, security, monitoring, and API services.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Magentic Foundation Framework."""
        # Load settings
        self.settings = Settings(_env_file=config_path)
        
        # Configure logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            context_class=dict,
            cache_logger_on_first_use=True
        )
        
        # Initialize components
        self.observability: Optional[ObservabilityService] = None
        self.security_manager: Optional[SecurityManager] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self.agent_factory: Optional[AgentFactory] = None
        self.planner: Optional[DynamicPlanner] = None
        self.mcp_client: Optional[MCPClient] = None
        self.mcp_server: Optional[MCPServer] = None
        self.workflow_engine: Optional[WorkflowEngine] = None
        self.orchestrator: Optional[MagenticOrchestrator] = None
        self.api_service: Optional[APIService] = None
        
        # Application state
        self._initialized = False
        self._shutdown_event = asyncio.Event()
        
        logger.info("MagenticFoundation initialized", config_path=str(config_path))

    async def initialize(self) -> None:
        """Initialize all framework components."""
        if self._initialized:
            return
        
        logger.info("Initializing Magentic Foundation Framework")
        
        try:
            # Initialize core services first
            self.observability = ObservabilityService(self.settings)
            await self.observability.initialize()
            
            self.security_manager = SecurityManager(self.settings)
            await self.security_manager.initialize()
            
            # Initialize agent components
            self.agent_registry = AgentRegistry(self.settings)
            await self.agent_registry.initialize()
            
            self.agent_factory = AgentFactory(self.settings)
            
            # Initialize MCP components
            self.mcp_client = MCPClient(self.settings)
            await self.mcp_client.initialize()
            
            self.mcp_server = MCPServer(self.settings)
            await self.mcp_server.initialize()
            
            # Initialize planning and orchestration
            self.planner = DynamicPlanner(self.settings, self.mcp_client)
            
            self.orchestrator = MagenticOrchestrator(
                self.settings,
                self.agent_registry,
                self.mcp_client,
                self.observability
            )
            await self.orchestrator.initialize()
            
            # Initialize workflow engine
            self.workflow_engine = WorkflowEngine(
                self.settings,
                self.agent_registry,
                self.mcp_client,
                self.observability
            )
            await self.workflow_engine.initialize()
            
            # Initialize API service
            self.api_service = APIService(
                self.settings,
                self.orchestrator,
                self.agent_registry,
                self.planner,
                self.security_manager,
                self.observability,
                self.mcp_client,
                self.mcp_server,
                self.workflow_engine
            )
            await self.api_service.initialize()
            
            self._initialized = True
            logger.info("Magentic Foundation Framework initialization complete")
            
        except Exception as e:
            logger.error("Failed to initialize Magentic Foundation Framework", error=str(e))
            await self.shutdown()
            raise

    async def shutdown(self) -> None:
        """Shutdown all framework components."""
        logger.info("Shutting down Magentic Foundation Framework")
        
        # Shutdown in reverse order
        components = [
            ("API Service", self.api_service),
            ("Workflow Engine", self.workflow_engine),
            ("Orchestrator", self.orchestrator),
            ("Dynamic Planner", self.planner),
            ("MCP Server", self.mcp_server),
            ("MCP Client", self.mcp_client),
            ("Agent Factory", self.agent_factory),
            ("Agent Registry", self.agent_registry),
            ("Security Manager", self.security_manager),
            ("Monitoring Service", self.monitoring)
        ]
        
        for name, component in components:
            if component:
                try:
                    await component.shutdown()
                    logger.info("Component shutdown complete", component=name)
                except Exception as e:
                    logger.error("Error shutting down component", component=name, error=str(e))
        
        self._shutdown_event.set()
        logger.info("Magentic Foundation Framework shutdown complete")

    async def run_api_server(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False
    ) -> None:
        """Run the FastAPI server."""
        if not self._initialized:
            await self.initialize()
        
        if not self.api_service:
            raise RuntimeError("API service not initialized")
        
        # Setup lifespan context
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info("Starting API server", host=host, port=port)
            yield
            logger.info("Stopping API server")
        
        # Get FastAPI app with lifespan
        app = self.api_service.get_app()
        app.router.lifespan_context = lifespan
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            reload=reload,
            log_config=None,  # Use structlog instead
            access_log=False
        )
        
        server = uvicorn.Server(config)
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal", signal=signum)
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            await server.serve()
        except Exception as e:
            logger.error("API server error", error=str(e))
            raise
        finally:
            await self.shutdown()

    async def run_cli(self) -> None:
        """Run in CLI mode."""
        if not self._initialized:
            await self.initialize()
        
        logger.info("Magentic Foundation Framework running in CLI mode")
        logger.info("Press Ctrl+C to shutdown")
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal", signal=signum)
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.shutdown()

    # Convenience methods for direct usage

    async def execute_agent(self, agent_id: str, parameters: dict) -> any:
        """Execute an agent directly."""
        if not self._initialized:
            await self.initialize()
        
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        agent = await self.agent_registry.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        return await agent.execute(parameters)

    async def execute_orchestration(
        self,
        agents: list[str],
        task: str,
        pattern: str = "sequential",
        parameters: dict = None
    ) -> list:
        """Execute orchestrated workflow."""
        if not self._initialized:
            await self.initialize()
        
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        return await self.orchestrator.execute(
            agents=agents,
            task=task,
            pattern=pattern,
            parameters=parameters or {}
        )

    async def execute_workflow(self, workflow_name: str, variables: dict = None) -> str:
        """Execute a workflow."""
        if not self._initialized:
            await self.initialize()
        
        if not self.workflow_engine:
            raise RuntimeError("Workflow engine not initialized")
        
        return await self.workflow_engine.execute_workflow(
            workflow_name,
            variables or {}
        )

    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> any:
        """Call an MCP tool."""
        if not self._initialized:
            await self.initialize()
        
        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized")
        
        return await self.mcp_client.call_tool(tool_name, arguments)


# Application factory function
def create_app(config_path: Optional[Path] = None) -> MagenticFoundation:
    """Create Magentic Foundation application instance."""
    return MagenticFoundation(config_path)


# CLI entry point
async def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Magentic Foundation Framework")
    parser.add_argument("--config", type=Path, help="Configuration file path")
    parser.add_argument("--mode", choices=["api", "cli"], default="api", help="Run mode")
    parser.add_argument("--host", default="127.0.0.1", help="API server host")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    # Create application
    app = create_app(args.config)
    
    try:
        if args.mode == "api":
            await app.run_api_server(
                host=args.host,
                port=args.port,
                reload=args.reload
            )
        else:
            await app.run_cli()
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error("Application error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
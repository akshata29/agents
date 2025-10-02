"""
Agent Factory - Dynamic Agent Creation and Management

Factory class for creating specialized agents with Microsoft Agent Framework integration.
Supports both built-in and custom agent types with configuration management.
"""

from typing import Any, Dict, Optional, Type, List

import structlog
from azure.identity import AzureCliCredential

# Microsoft Agent Framework imports
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient

from .base import BaseAgent, AgentResponse, AgentMessage, AgentCapability
from ..config.settings import Settings


logger = structlog.get_logger(__name__)


class MicrosoftAgentWrapper(BaseAgent):
    """
    Wrapper for Microsoft Agent Framework ChatAgent.
    
    Adapts Microsoft Agent Framework agents to work with our BaseAgent interface.
    """

    def __init__(
        self,
        name: str,
        chat_agent: ChatAgent,
        description: str = "",
        settings: Optional[Settings] = None,
        **kwargs
    ):
        """Initialize the wrapper with a Microsoft Agent Framework ChatAgent."""
        super().__init__(name, description, settings, **kwargs)
        self.chat_agent = chat_agent
        self._allow_concurrent = True  # Microsoft agents can handle concurrency

    async def _process_message(
        self,
        message: AgentMessage,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process message using Microsoft Agent Framework."""
        try:
            # Convert to Microsoft Agent Framework message format
            from agent_framework import ChatMessage, Role
            
            chat_messages = [
                ChatMessage(
                    role=Role.USER,
                    text=message.content
                )
            ]
            
            # Process with Microsoft Agent Framework
            # ChatAgent uses .run() method which returns response with messages
            response = await self.chat_agent.run(chat_messages)
            
            # Extract content from response messages
            content = ""
            if response.messages:
                # Get the last message content
                content = response.messages[-1].text if hasattr(response.messages[-1], 'text') else str(response.messages[-1])
            
            return AgentResponse(
                success=True,
                content=content,
                metadata={
                    "agent_type": "microsoft_agent_framework",
                    "model": getattr(self.chat_agent, 'model_name', 'unknown')
                }
            )
            
        except Exception as e:
            logger.error(
                "Microsoft agent processing failed",
                agent_name=self.name,
                error=str(e)
            )
            
            return AgentResponse(
                success=False,
                content="",
                error=str(e),
                metadata={"agent_type": "microsoft_agent_framework"}
            )

    async def _register_capabilities(self) -> None:
        """Register Microsoft Agent Framework specific capabilities."""
        capabilities = [
            AgentCapability(
                name="chat_completion",
                description="Generate chat completions using LLM",
                parameters={"model": "llm", "context_window": "large"}
            ),
            AgentCapability(
                name="azure_openai_integration",
                description="Native Azure OpenAI integration",
                parameters={"service": "azure_openai"}
            )
        ]
        
        for capability in capabilities:
            self._add_capability(capability)


class AgentFactory:
    """
    Factory for creating and configuring agents.
    
    Supports both Microsoft Agent Framework agents and custom agent implementations.
    Provides centralized agent creation with configuration management.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the agent factory."""
        self.settings = settings or Settings()
        
        # Initialize Azure OpenAI client for Microsoft Agent Framework
        try:
            self._chat_client = AzureOpenAIChatClient(
                endpoint=self.settings.azure_openai.endpoint,
                api_key=self.settings.azure_openai.api_key,
                deployment_name=self.settings.azure_openai.chat_deployment_name,
                api_version=self.settings.azure_openai.api_version
            )
            logger.info("Azure OpenAI client initialized")
        except Exception as e:
            logger.warning("Failed to initialize Azure OpenAI client", error=str(e))
            self._chat_client = None
        
        # Registry of available agent types
        self._agent_types: Dict[str, Dict[str, Any]] = {}
        self._register_builtin_agents()
        
        logger.info("AgentFactory initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the agent factory and cleanup resources."""
        logger.info("Shutting down AgentFactory")
        # Close Azure OpenAI client if needed
        if self._chat_client:
            # Note: AzureOpenAIChatClient doesn't have a close method
            # but we can clear the reference
            self._chat_client = None
        logger.info("AgentFactory shutdown complete")

    def create_agent(
        self,
        agent_type: str,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseAgent:
        """
        Create an agent of the specified type.
        
        Args:
            agent_type: Type of agent to create
            name: Optional agent name (defaults to agent_type)
            config: Optional configuration override
            
        Returns:
            Configured agent instance
        """
        if agent_type not in self._agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_name = name or agent_type
        agent_config = self._agent_types[agent_type].copy()
        
        # Apply configuration overrides
        if config:
            agent_config.update(config)
        
        logger.info(
            "Creating agent",
            agent_type=agent_type,
            agent_name=agent_name,
            config=agent_config.get("description", "")
        )
        
        try:
            # Create the agent using the registered factory function
            factory_func = agent_config["factory"]
            agent = factory_func(agent_name, agent_config)
            
            logger.info(
                "Agent created successfully",
                agent_type=agent_type,
                agent_name=agent_name,
                agent_id=agent.id
            )
            
            return agent
            
        except Exception as e:
            logger.error(
                "Failed to create agent",
                agent_type=agent_type,
                agent_name=agent_name,
                error=str(e)
            )
            raise

    def register_agent_type(
        self,
        agent_type: str,
        factory_func: callable,
        description: str = "",
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a new agent type.
        
        Args:
            agent_type: Unique agent type identifier
            factory_func: Function to create agent instances
            description: Agent type description
            config: Default configuration for this agent type
        """
        self._agent_types[agent_type] = {
            "factory": factory_func,
            "description": description,
            "config": config or {}
        }
        
        logger.info(
            "Agent type registered",
            agent_type=agent_type,
            description=description
        )

    def list_agent_types(self) -> List[Dict[str, Any]]:
        """List all available agent types."""
        return [
            {
                "type": agent_type,
                "description": config["description"],
                "config_keys": list(config["config"].keys())
            }
            for agent_type, config in self._agent_types.items()
        ]

    def get_agent_type_info(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific agent type."""
        return self._agent_types.get(agent_type)

    # Built-in agent creation methods

    def _create_planner_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a planning agent."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt", 
            "You are an expert planning agent. Break down complex tasks into "
            "clear, actionable steps with dependencies and resource requirements."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Task planning and decomposition agent"),
            settings=self.settings
        )

    def _create_researcher_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a research agent."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt",
            "You are an expert research agent. Gather, analyze, and synthesize "
            "information from multiple sources to provide comprehensive insights."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Information gathering and research agent"),
            settings=self.settings
        )

    def _create_writer_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a content writing agent."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt",
            "You are an expert content writer. Create clear, engaging, and "
            "well-structured content based on provided information and requirements."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Content creation and writing agent"),
            settings=self.settings
        )

    def _create_reviewer_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a review and validation agent."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt",
            "You are an expert reviewer and quality assurance agent. Review content "
            "for accuracy, completeness, clarity, and adherence to requirements."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Content review and validation agent"),
            settings=self.settings
        )

    def _create_summarizer_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a summarization agent."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt",
            "You are an expert summarization agent. Extract key insights and "
            "create concise, informative summaries of complex information."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Content summarization agent"),
            settings=self.settings
        )

    def _create_pros_cons_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a pros/cons analysis agent."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt",
            "You are an expert analytical agent specializing in pros and cons analysis. "
            "Provide balanced, objective evaluations of advantages and disadvantages."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Pros and cons analysis agent"),
            settings=self.settings
        )

    def _create_risk_assessor_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a risk assessment agent."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt",
            "You are an expert risk assessment agent. Identify, analyze, and "
            "evaluate potential risks, their likelihood, and impact."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Risk assessment and analysis agent"),
            settings=self.settings
        )

    def _create_strategic_planner_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a strategic planning agent with ReAct capabilities."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt",
            "You are an expert strategic planning agent with reasoning and acting capabilities. "
            "Break down complex problems, reason through solutions step by step, and "
            "adapt your approach based on new information and feedback."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Strategic planning agent with ReAct capabilities"),
            settings=self.settings
        )

    def _create_coordinator_agent(self, name: str, config: Dict[str, Any]) -> BaseAgent:
        """Create a coordination agent for multi-agent orchestration."""
        if not self._chat_client:
            raise RuntimeError("Azure OpenAI client not available")
        
        system_prompt = config.get("system_prompt",
            "You are an expert coordination agent. Orchestrate multiple agents, "
            "manage task delegation, and ensure effective collaboration between team members."
        )
        
        chat_agent = ChatAgent(
            name=name,
            system_message=system_prompt,
            chat_client=self._chat_client
        )
        
        return MicrosoftAgentWrapper(
            name=name,
            chat_agent=chat_agent,
            description=config.get("description", "Multi-agent coordination agent"),
            settings=self.settings
        )

    def _register_builtin_agents(self) -> None:
        """Register built-in agent types."""
        builtin_agents = [
            ("planner", self._create_planner_agent, "Task planning and decomposition"),
            ("researcher", self._create_researcher_agent, "Information gathering and research"),
            ("writer", self._create_writer_agent, "Content creation and writing"),
            ("reviewer", self._create_reviewer_agent, "Content review and validation"),
            ("summarizer", self._create_summarizer_agent, "Content summarization"),
            ("pros_cons", self._create_pros_cons_agent, "Pros and cons analysis"),
            ("risk_assessor", self._create_risk_assessor_agent, "Risk assessment and analysis"),
            ("strategic_planner", self._create_strategic_planner_agent, "Strategic planning with ReAct"),
            ("coordinator", self._create_coordinator_agent, "Multi-agent coordination")
        ]
        
        for agent_type, factory_func, description in builtin_agents:
            self.register_agent_type(agent_type, factory_func, description)
        
        logger.info(f"Registered {len(builtin_agents)} built-in agent types")
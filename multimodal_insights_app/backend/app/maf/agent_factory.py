"""Lightweight Microsoft Agent Framework agent factory for app agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type

import structlog

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient

from ..infra.settings import Settings


logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class AgentDefinition:
    """Metadata describing a Microsoft Agent Framework chat agent type."""

    type_name: str
    system_prompt: str
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    defaults: Dict[str, Any] = field(default_factory=dict)


class MAFAgentFactory:
    """Factory that produces `agent_framework.ChatAgent` instances."""

    def __init__(
        self,
        settings: Settings,
        *,
        chat_client: Optional[AzureOpenAIChatClient] = None,
        chat_agent_cls: Type[ChatAgent] = ChatAgent,
    ) -> None:
        self._settings = settings
        self._chat_agent_cls = chat_agent_cls
        self._chat_client = chat_client or self._create_chat_client(settings)
        self._registry: Dict[str, AgentDefinition] = {}
        self._register_defaults()
        logger.info(
            "MAF agent factory initialised",
            available_types=list(self._registry),
        )

    def _create_chat_client(self, settings: Settings) -> AzureOpenAIChatClient:
        """Create an Azure OpenAI chat client for Microsoft Agent Framework."""
        try:
            client = AzureOpenAIChatClient(
                endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                deployment_name=settings.AZURE_OPENAI_DEPLOYMENT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
            logger.debug("Azure OpenAI chat client created for MAF usage")
            return client
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to build Azure OpenAI chat client", error=str(exc))
            raise

    def _register_defaults(self) -> None:
        """Register baseline agent archetypes used by the multimodal app."""
        self.register_agent_type(
            AgentDefinition(
                type_name="planner",
                description="Generates multimodal execution plans",
                system_prompt=(
                    "You are a senior programme manager who specialises in breaking down"
                    " complex multimodal processing goals into concrete steps."
                ),
                tags=("planning",),
                defaults={"temperature": 0.2},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="summarizer",
                description="Produces adaptive summaries aligned with personas",
                system_prompt=(
                    "You craft concise and persona-aware summaries using combined audio,"
                    " video and document context."
                ),
                tags=("summarisation", "analysis"),
                defaults={"temperature": 0.1},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="analytics",
                description="Finds insights, patterns and recommendations",
                system_prompt=(
                    "You perform analytical reasoning over multimodal content to surface"
                    " risks, opportunities and next-best-actions."
                ),
                tags=("analytics", "insights"),
                defaults={"temperature": 0.3},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="sentiment",
                description="Evaluates tone, emotion and speaker sentiment",
                system_prompt=(
                    "You assess the emotional tone and sentiment present in transcripts"
                    " and textual artefacts."
                ),
                tags=("sentiment", "analysis"),
                defaults={"temperature": 0.25},
            )
        )

    def register_agent_type(self, definition: AgentDefinition) -> None:
        """Expose additional agent archetypes for downstream services."""
        self._registry[definition.type_name] = definition
        logger.debug("Registered MAF agent type", type=definition.type_name)

    def list_agent_types(self) -> list[AgentDefinition]:
        """Return the currently registered agent definitions."""
        return list(self._registry.values())

    def get_definition(self, agent_type: str) -> AgentDefinition:
        """Fetch a registered definition or raise if missing."""
        if agent_type not in self._registry:
            raise KeyError(f"Unknown agent type: {agent_type}")
        return self._registry[agent_type]

    def create_chat_agent(
        self,
        agent_type: str,
        *,
        name: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> ChatAgent:
        """Instantiate a MAF `ChatAgent` configured for the requested type."""
        definition = self.get_definition(agent_type)
        config = {"system_message": definition.system_prompt, **definition.defaults}
        if overrides:
            config.update(overrides)

        agent_name = name or agent_type
        logger.info(
            "Creating native MAF chat agent",
            agent_type=agent_type,
            agent_name=agent_name,
        )
        return self._chat_agent_cls(name=agent_name, chat_client=self._chat_client, **config)

    @property
    def chat_client(self) -> AzureOpenAIChatClient:
        """Expose the underlying chat client for advanced scenarios."""
        return self._chat_client
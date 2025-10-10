"""Native Microsoft Agent Framework agent factory for financial research agents."""

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
    """Metadata describing a native MAF chat agent archetype."""

    type_name: str
    system_prompt: str
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    defaults: Dict[str, Any] = field(default_factory=dict)


class MAFAgentFactory:
    """Factory that provides configured `ChatAgent` instances for the app."""

    def __init__(
        self,
        settings: Settings,
        *,
        chat_client: Optional[AzureOpenAIChatClient] = None,
        chat_agent_cls: Type[ChatAgent] = ChatAgent,
    ) -> None:
        self._settings = settings
        self._chat_agent_cls = chat_agent_cls
        self._chat_client = chat_client or self._build_chat_client(settings)
        self._registry: Dict[str, AgentDefinition] = {}
        self._register_default_agents()
        logger.info("Financial MAF agent factory initialised", available=list(self._registry))

    def _build_chat_client(self, settings: Settings) -> AzureOpenAIChatClient:
        """Create an Azure OpenAI chat client for Microsoft Agent Framework usage."""
        try:
            client = AzureOpenAIChatClient(
                endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                deployment_name=settings.AZURE_OPENAI_DEPLOYMENT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
            logger.debug("Azure OpenAI chat client created for financial MAF agents")
            return client
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to build Azure OpenAI chat client", error=str(exc))
            raise

    def _register_default_agents(self) -> None:
        """Register the core agent archetypes used across the financial workflows."""
        self.register_agent_type(
            AgentDefinition(
                type_name="planner",
                description="Leads research planning and orchestrates agent collaboration",
                system_prompt=(
                    "You are the lead financial research planner. Analyse objectives, determine"
                    " the required research tracks (company profile, SEC filings, earnings,"
                    " fundamentals, technicals, forecasts, summaries, reports) and produce"
                    " an execution plan tailored to the user's goals."
                ),
                tags=("planning", "financial", "strategy"),
                defaults={"temperature": 0.2},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="company",
                description="Provides company intelligence using finance data providers",
                system_prompt=(
                    "You are a company intelligence specialist using market data, profile"
                    " information, and news to describe the business, key metrics, and"
                    " current catalysts."
                ),
                tags=("company", "profile"),
                defaults={"temperature": 0.3},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="sec",
                description="Analyses SEC filings and regulatory documents",
                system_prompt=(
                    "You are an SEC filings expert. Extract material information, risk factors,"
                    " forward-looking statements, and compliance issues from regulatory filings."
                ),
                tags=("sec", "regulation"),
                defaults={"temperature": 0.15},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="earnings",
                description="Reviews earnings transcripts and quarterly performance",
                system_prompt=(
                    "You specialise in earnings events. Analyse transcripts, guidance,"
                    " revenue drivers, and management commentary to surface key takeaways."
                ),
                tags=("earnings", "transcripts"),
                defaults={"temperature": 0.25},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="fundamentals",
                description="Performs fundamental financial analysis",
                system_prompt=(
                    "You are a fundamental analyst who evaluates financial statements,"
                    " ratio trends, liquidity, profitability, and valuation context."
                ),
                tags=("fundamentals", "valuation"),
                defaults={"temperature": 0.2},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="technicals",
                description="Conducts technical price analysis",
                system_prompt=(
                    "You focus on technical analysis using price action, indicators,"
                    " chart patterns, and momentum signals to describe trends and setups."
                ),
                tags=("technicals", "charts"),
                defaults={"temperature": 0.25},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="forecaster",
                description="Produces forecasts and scenario analysis",
                system_prompt=(
                    "You create forward-looking forecasts by combining fundamental, technical,"
                    " and sentiment signals. Provide base, bull, and bear scenarios when helpful."
                ),
                tags=("forecasting", "scenarios"),
                defaults={"temperature": 0.35},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="summarizer",
                description="Synthesises research into concise narratives",
                system_prompt=(
                    "You summarise financial research for specific audiences, balancing context,"
                    " opportunities, risks, and recommendations. Tailor tone to the requested persona."
                ),
                tags=("summary", "persona"),
                defaults={"temperature": 0.2},
            )
        )

        self.register_agent_type(
            AgentDefinition(
                type_name="report",
                description="Creates structured research reports",
                system_prompt=(
                    "You compile multi-agent findings into structured reports with sections such"
                    " as investment thesis, financial highlights, risk considerations, and next steps."
                ),
                tags=("report", "synthesis"),
                defaults={"temperature": 0.2},
            )
        )

    def register_agent_type(self, definition: AgentDefinition) -> None:
        """Register or update an agent archetype."""
        self._registry[definition.type_name] = definition
        logger.debug("Registered financial agent type", type=definition.type_name)

    def list_agent_types(self) -> list[AgentDefinition]:
        """Return the registered agent definitions."""
        return list(self._registry.values())

    def get_definition(self, agent_type: str) -> AgentDefinition:
        """Retrieve an agent definition by type."""
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
        """Instantiate a chat agent configured for the specified archetype."""
        definition = self.get_definition(agent_type)
        config = {"system_message": definition.system_prompt, **definition.defaults}
        if overrides:
            config.update(overrides)

        agent_name = name or agent_type
        logger.info(
            "Creating financial MAF chat agent",
            agent_type=agent_type,
            agent_name=agent_name,
        )
        return self._chat_agent_cls(
            name=agent_name,
            chat_client=self._chat_client,
            **config,
        )

    @property
    def chat_client(self) -> AzureOpenAIChatClient:
        """Expose the underlying chat client for advanced consumers."""
        return self._chat_client

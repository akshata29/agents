"""Dynamic planning helpers built on Microsoft Agent Framework."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import structlog

from agent_framework import AgentRunResponse, ChatAgent, ChatMessage, Role, TextContent

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class PlanStep:
    """Structured representation of a single plan step."""

    order: int
    action: str
    agent: str
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable dictionary representation."""
        return {
            "order": self.order,
            "action": self.action,
            "agent": self.agent,
            "tool": self.tool,
            "parameters": self.parameters,
        }


class PlanParsingError(RuntimeError):
    """Raised when the planner response cannot be parsed into steps."""


class MAFDynamicPlanner:
    """LLM-powered planner that uses a Microsoft Agent Framework chat agent."""

    def __init__(
        self,
        planner_agent: ChatAgent,
        *,
        planning_rules: Optional[str] = None,
    ) -> None:
        self._planner_agent = planner_agent
        self._planning_rules = planning_rules or self._default_rules()
        logger.info("Financial MAF planner initialised", agent=planner_agent.name)

    async def generate_plan(
        self,
        objective: str,
        files_info: Iterable[Dict[str, Any]] | None = None,
        *,
        summary_type: str = "executive",
        persona: str = "investment",
        ticker: Optional[str] = None,
    ) -> List[PlanStep]:
        """Create a structured plan using the underlying chat agent."""
        prompt = self._build_prompt(objective, files_info, summary_type, persona, ticker)
        logger.debug("Generating plan with financial MAF planner", objective_preview=objective[:80])

        response = await self._planner_agent.run(
            messages=[
                ChatMessage(role=Role.USER, contents=[TextContent(text=prompt)]),
            ]
        )

        plan_text = self._extract_text(response)
        steps = self.parse_plan_text(
            plan_text,
            objective=objective,
            files_info=list(files_info or []),
            summary_type=summary_type,
            persona=persona,
            ticker=ticker,
        )
        logger.info("Plan generated via financial MAF planner", steps=len(steps))
        return steps

    def _build_prompt(
        self,
        objective: str,
        files_info: Iterable[Dict[str, Any]] | None,
        summary_type: str,
        persona: str,
        ticker: Optional[str],
    ) -> str:
        """Compose the planning instruction sent to the LLM."""
        files_block = ""
        files = list(files_info or [])
        if files:
            lines = [f"- {f['filename']} ({f.get('file_type', 'n/a')})" for f in files]
            files_block = "\nResearch Artifacts:\n" + "\n".join(lines)

        ticker_line = f"Ticker: {ticker}\n" if ticker else ""

        prompt = (
            f"Objective: {objective}\n"
            f"{ticker_line}"
            f"Preferred Summary Style: {summary_type}\n"
            f"Primary Persona: {persona}\n"
            f"{files_block}\n\n"
            f"{self._planning_rules}\n"
            "Return ONLY numbered steps with the required format."
        )
        return prompt

    @staticmethod
    def _default_rules() -> str:
        return (
            "Follow these planning rules for financial research:\n"
            "1. Start with Company_Agent to gather core company context when ticker/company is provided.\n"
            "2. Include SEC_Agent for compliance and filing review when filings or regulatory risk is relevant.\n"
            "3. Leverage Earnings, Fundamentals, Technicals, Forecaster agents based on the analysis depth requested.\n"
            "4. Use Summarizer_Agent for persona-aligned synthesis; use Report_Agent for final deliverables.\n"
            "5. Reference tools explicitly and include objective_context in Summarizer/Report parameters.\n"
            "6. Format each step as: Step N: <action>. Agent: <AgentName>. Tool: <tool>."
        )

    @staticmethod
    def _extract_text(response: AgentRunResponse) -> str:
        if not response or not response.messages:
            raise PlanParsingError("Planner returned empty response")
        last_message = response.messages[-1]
        if isinstance(last_message, ChatMessage):
            return last_message.text or ""
        return str(last_message)

    @classmethod
    def parse_plan_text(
        cls,
        plan_text: str,
        *,
        objective: str,
        files_info: List[Dict[str, Any]],
        summary_type: str,
        persona: str,
        ticker: Optional[str],
    ) -> List[PlanStep]:
        """Convert the LLM response into structured `PlanStep` objects."""
        if not plan_text.strip():
            raise PlanParsingError("Planner returned empty plan text")

        plan_section = cls._extract_plan_section(plan_text)
        step_lines = [line for line in plan_section.splitlines() if line.strip().startswith("Step")]
        if not step_lines:
            raise PlanParsingError("No plan steps found in planner response")

        steps: List[PlanStep] = []
        for raw_line in step_lines:
            parsed = cls._parse_step_line(raw_line)
            if parsed is None:
                logger.warning("Skipping unparsable plan line", line=raw_line)
                continue

            order, action, agent, tool, parameters = parsed
            parameters = cls._enrich_parameters(
                parameters,
                agent,
                objective=objective,
                summary_type=summary_type,
                persona=persona,
                ticker=ticker,
            )
            steps.append(
                PlanStep(order=order, action=action, agent=agent, tool=tool, parameters=parameters)
            )

        if not steps:
            raise PlanParsingError("No valid steps could be parsed from planner response")

        return steps

    @staticmethod
    def _extract_plan_section(plan_text: str) -> str:
        upper = plan_text.upper()
        if "FINAL ANSWER:" in upper:
            return plan_text.split("FINAL ANSWER:")[-1].strip()
        return plan_text.strip()

    @staticmethod
    def _parse_step_line(line: str) -> Optional[tuple[int, str, str, str, Dict[str, Any]]]:
        pattern = (
            r"Step\s+(?P<order>\d+):\s*(?P<action>.+?)\.\s*"
            r"Agent:\s*(?P<agent>[\w_]+)\.\s*"
            r"Tool:\s*(?P<tool>[\w_]+)"
            r"(?:\.\s*Parameters:\s*\{(?P<params>[^}]*)\})?"
        )
        match = re.search(pattern, line)
        if not match:
            return None

        order = int(match.group("order"))
        action = match.group("action").strip()
        agent = match.group("agent").strip()
        tool = match.group("tool").strip()
        params = match.group("params") or ""
        parameters = MAFDynamicPlanner._parse_parameters(params)
        return order, action, agent, tool, parameters

    @staticmethod
    def _parse_parameters(raw_params: str) -> Dict[str, Any]:
        if not raw_params:
            return {}

        parsed: Dict[str, Any] = {}
        pair_pattern = re.compile(r"(?P<key>[\w_]+)\s*:\s*(?P<value>\[[^\]]*\]|[^,]+)")

        for match in pair_pattern.finditer(raw_params):
            key = match.group("key").strip()
            value = match.group("value").strip()

            if value.startswith("[") and value.endswith("]"):
                items = [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
                parsed[key] = items
            else:
                parsed[key] = value.strip("'\"")

        return parsed

    @staticmethod
    def _enrich_parameters(
        parameters: Dict[str, Any],
        agent: str,
        *,
        objective: str,
        summary_type: str,
        persona: str,
        ticker: Optional[str],
    ) -> Dict[str, Any]:
        enriched = dict(parameters)
        if agent in {"Summarizer_Agent", "Report_Agent"}:
            enriched.setdefault("summary_type", summary_type)
            enriched.setdefault("persona", persona)
            enriched.setdefault("objective_context", objective)
            if ticker:
                enriched.setdefault("ticker", ticker)
        if agent == "Forecaster_Agent" and ticker:
            enriched.setdefault("ticker", ticker)
        if agent == "Company_Agent" and ticker:
            enriched.setdefault("ticker", ticker)
        return enriched

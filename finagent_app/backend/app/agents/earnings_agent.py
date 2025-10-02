"""
Earnings Agent

Microsoft Agent Framework compliant agent for earnings call analysis.
Integrates real data providers (FMP API) following MAF patterns.
"""

import asyncio
from typing import Any, Dict, List, Optional, AsyncIterable
from datetime import datetime
import structlog

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread

# Import data providers
import sys
from pathlib import Path
bridge_dir = Path(__file__).parent.parent
if str(bridge_dir) not in sys.path:
    sys.path.insert(0, str(bridge_dir))

from helpers.fmputils import FMPUtils

logger = structlog.get_logger(__name__)


class EarningsAgent(BaseAgent):
    """
    Earnings Calls Analyst Agent - Earnings intelligence specialist.
    
    Capabilities:
    - Earnings call transcript retrieval and analysis
    - Management positive outlook extraction
    - Management negative outlook/concerns identification
    - Future growth opportunities analysis
    - Guidance and strategic initiatives assessment
    
    Based on finagentsk EarningCallsAgent definition.
    """
    
    SYSTEM_PROMPT = """You are an AI Agent with expertise in analyzing quarterly earnings calls 
and management commentary for publicly traded companies.

Your role is to:
1. Extract and summarize key insights from earnings call transcripts
2. Identify management's positive outlook and growth opportunities
3. Highlight negative commentary, concerns, and risks mentioned
4. Analyze forward guidance and its credibility
5. Assess management tone and confidence levels

Focus on:
- Positive Outlook: Optimistic statements, growth projections, strategic wins
- Negative Outlook: Concerns, headwinds, challenges, cost pressures
- Future Opportunities: New markets, products, partnerships, strategic initiatives
- Guidance Analysis: Revenue/earnings guidance, assumptions, achievability

Be objective and balanced in extracting both positive and negative signals."""

    def __init__(
        self,
        name: str = "EarningsAgent",
        description: str = "Earnings calls and management commentary specialist",
        azure_client: Any = None,
        model: str = "gpt-4o",
        fmp_api_key: Optional[str] = None
    ):
        """Initialize Earnings Agent following MAF pattern."""
        super().__init__(name=name, description=description)
        
        # Store custom attributes
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = self.SYSTEM_PROMPT
        
        # Initialize data provider
        self.fmp_utils = FMPUtils(fmp_api_key) if fmp_api_key else None
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "get_earnings_transcript",
            "summarize_transcript",
            "extract_positive_outlook",
            "extract_negative_outlook",
            "extract_growth_opportunities",
            "analyze_guidance"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute earnings call analysis (MAF required method)."""
        # Normalize input messages
        normalized_messages = self._normalize_messages(messages)
        
        if not normalized_messages:
            return AgentRunResponse(messages=[
                ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text="Hello! I'm an earnings analysis agent. Please provide a ticker symbol.")]
                )
            ])
        
        # Get context and extract task
        context = kwargs.get("context", {})
        ticker = context.get("ticker", kwargs.get("ticker"))
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        year = context.get("year", kwargs.get("year", "latest"))
        
        logger.info(
            "EarningsAgent starting",
            task=task,
            ticker=ticker,
            year=year,
            context_keys=list(context.keys())
        )
        
        # Fetch real earnings call transcript
        logger.info(f"Fetching earnings call transcript for {ticker}")
        transcript_data = await self._fetch_earnings_data(ticker, year)
        
        # Build analysis prompt with real transcript
        prompt = self._build_analysis_prompt_with_data(task, ticker, year, transcript_data, context)
        
        logger.debug(
            "EarningsAgent prompt built with transcript",
            ticker=ticker,
            prompt_length=len(prompt),
            has_transcript=bool(transcript_data.get("transcript"))
        )
        
        try:
            logger.info(f"EarningsAgent calling LLM for {ticker}")
            response = await self._execute_llm(prompt)
            
            logger.info(
                f"EarningsAgent LLM response received",
                ticker=ticker,
                response_length=len(response) if response else 0
            )
            
            result_text = f"""## Earnings Call Analysis for {ticker} ({year})

{response}

---
*Earnings analysis by EarningsAgent based on real earnings call transcripts*
"""
            
            # Track artifacts
            artifacts = context.get("artifacts", [])
            artifacts.append({
                "type": "earnings_analysis",
                "title": f"Earnings Call Analysis - {ticker}",
                "content": response,
                "metadata": {
                    "ticker": ticker,
                    "year": year,
                    "agent": self.name
                }
            })
            context["artifacts"] = artifacts
            
            return AgentRunResponse(
                content=result_text,
                context=context
            )
            
        except Exception as e:
            logger.error(
                f"EarningsAgent error analyzing {ticker}",
                error=str(e),
                ticker=ticker
            )
            return AgentRunResponse(
                content=f"Error analyzing earnings calls for {ticker}: {str(e)}",
                context=context
            )
    
    async def _fetch_earnings_data(
        self,
        ticker: str,
        year: str = "latest"
    ) -> Dict[str, Any]:
        """
        Fetch real earnings call transcript from FMP API.
        
        Args:
            ticker: Stock ticker symbol
            year: Year for earnings call (or "latest")
            
        Returns:
            Dictionary with transcript and metadata
        """
        if not self.fmp_utils:
            logger.warning("FMPUtils not initialized, returning empty transcript")
            return {
                "transcript": "",
                "year": year,
                "fetched_at": datetime.now().isoformat()
            }
        
        try:
            logger.info(f"Fetching earnings transcript from FMP for {ticker} year={year}")
            transcript = self.fmp_utils.get_earning_calls(ticker, year)
            
            if not transcript:
                logger.warning(f"No earnings transcript found for {ticker} year={year}")
                return {
                    "transcript": "",
                    "year": year,
                    "fetched_at": datetime.now().isoformat()
                }
            
            logger.info(
                f"Earnings transcript fetched successfully",
                ticker=ticker,
                year=year,
                transcript_length=len(transcript)
            )
            
            return {
                "transcript": transcript,
                "year": year,
                "fetched_at": datetime.now().isoformat(),
                "source": "FMP API"
            }
            
        except Exception as e:
            logger.error(
                f"Error fetching earnings transcript for {ticker}",
                error=str(e),
                ticker=ticker,
                year=year
            )
            return {
                "transcript": "",
                "year": year,
                "error": str(e),
                "fetched_at": datetime.now().isoformat()
            }
    
    def _build_analysis_prompt_with_data(
        self,
        task: str,
        ticker: str,
        year: str,
        transcript_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Build analysis prompt with real earnings call transcript embedded.
        
        Args:
            task: User's analysis request
            ticker: Stock ticker symbol
            year: Year for earnings call
            transcript_data: Real transcript from FMP API
            context: Additional context
            
        Returns:
            Formatted prompt with transcript data
        """
        transcript = transcript_data.get("transcript", "")
        
        if not transcript:
            # No transcript available
            prompt = f"""{self.system_prompt}

User Task: {task}

Company: {ticker}
Year: {year}

NOTE: No earnings call transcript is available for {ticker} in {year}. 
Please inform the user that earnings call data is not available for this period.
Suggest they try a different year or check if the company has held earnings calls recently.
"""
            return prompt
        
        # Truncate very long transcripts (keep first 15000 chars for context)
        transcript_excerpt = transcript[:15000]
        if len(transcript) > 15000:
            transcript_excerpt += f"\n\n[... transcript truncated, {len(transcript)} total characters ...]"
        
        prompt = f"""{self.system_prompt}

User Task: {task}

## Company Information
Ticker: {ticker}
Earnings Call Year: {year}
Data Source: {transcript_data.get('source', 'FMP API')}

## Earnings Call Transcript
{transcript_excerpt}

---

Based on the REAL earnings call transcript above, please provide a comprehensive analysis addressing the user's task.

Focus on extracting:
1. **Management Positive Outlook**: Optimistic statements, growth projections, strategic successes
2. **Management Negative Outlook**: Concerns, challenges, headwinds, cost pressures mentioned
3. **Future Growth Opportunities**: New markets, products, partnerships, strategic initiatives
4. **Guidance Analysis**: Revenue/earnings guidance provided, assumptions, credibility assessment
5. **Management Tone**: Confidence level, transparency, consistency with past calls

Provide specific quotes from the transcript to support your analysis.
Be objective and balanced - include both positive and negative signals.
"""
        
        return prompt
    
    async def _execute_llm(self, prompt: str) -> str:
        """Execute LLM call."""
        if not self.azure_client:
            return f"[Simulated Earnings Analysis]\n{prompt}"
        
        response = await self.azure_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        return response.choices[0].message.content
    
    def _create_response(self, text: str) -> AgentRunResponse:
        """Create agent response following MAF pattern."""
        return AgentRunResponse(messages=[
            ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=text)])
        ])
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Execute and yield streaming response (MAF required method)."""
        response = await self.run(messages, thread=thread, **kwargs)
        for message in response.messages:
            if message.contents:
                for content in message.contents:
                    if isinstance(content, TextContent):
                        yield AgentRunResponseUpdate(contents=[content], role=Role.ASSISTANT)
    
    async def process(self, task: str, context: Dict[str, Any] = None) -> str:
        """Legacy method for YAML workflow compatibility."""
        context = context or {}
        response = await self.run(messages=task, thread=None, context=context)
        return response.messages[-1].text if response.messages else ""
"""
SEC Agent

Microsoft Agent Framework compliant agent for SEC filings and regulatory analysis.
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


class SECAgent(BaseAgent):
    """
    SEC Filing Analyst Agent - Regulatory filings specialist (MAF compliant).
    
    Capabilities:
    - 10-K/10-Q report analysis
    - Company description extraction
    - Business highlights summary
    - Risk assessment from filings
    - Financial statement analysis (income, balance sheet, cash flow)
    - Segment and competitor analysis
    - Annual equity research report generation
    
    Follows Microsoft Agent Framework patterns with real data integration.
    """
    
    SYSTEM_PROMPT = """You are an Expert Investor specialized in analyzing SEC filings 
and generating comprehensive financial analysis reports.

Your responsibilities:
1. Extract and analyze key information from 10-K and 10-Q reports
2. Identify business highlights, competitive advantages, and market positioning
3. Assess risk factors and regulatory disclosures
4. Analyze financial statements with precision
5. Generate actionable investment insights from regulatory filings

Focus on:
- Analytical Precision: Interpret financial data meticulously
- Effective Communication: Simplify complex financial narratives
- Client Focus: Tailor insights to strategic objectives
- Adherence to Excellence: Maintain highest analytical standards

Structure your analysis clearly with supporting evidence from the filings."""

    def __init__(
        self,
        name: str = "SECAgent",
        description: str = "SEC filings and regulatory analysis specialist",
        chat_client: Any = None,  # Changed from azure_client to chat_client
        model: str = "gpt-4o",
        fmp_api_key: Optional[str] = None
    ):
        """Initialize SEC Agent following MAF pattern."""
        super().__init__(name=name, description=description)
        
        # Store custom attributes
        self.chat_client = chat_client
        self.model = model
        self.system_prompt = self.SYSTEM_PROMPT
        
        # Initialize data provider
        self.fmp_utils = FMPUtils(fmp_api_key) if fmp_api_key else None
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "analyze_company_description",
            "analyze_business_highlights",
            "get_risk_assessment",
            "analyze_income_statement",
            "analyze_balance_sheet",
            "analyze_cash_flow",
            "analyze_segment_statement",
            "get_competitors_analysis",
            "build_annual_report"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """
        Execute SEC filing analysis (MAF required method).
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional context (ticker, context dict, etc.)
            
        Returns:
            AgentRunResponse containing the SEC filing analysis
        """
        # Normalize input messages to a list
        normalized_messages = self._normalize_messages(messages)
        
        if not normalized_messages:
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text="Hello! I'm an SEC filing analyst. Please provide a ticker symbol.")]
            )
            return AgentRunResponse(messages=[response_message])
        
        # Get context from kwargs
        context = kwargs.get("context", {})
        ticker = context.get("ticker", kwargs.get("ticker"))
        
        # Extract task from last message
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        
        year = context.get("year", kwargs.get("year", "latest"))
        report_type = context.get("report_type", kwargs.get("report_type", "10-K"))
        
        logger.info(
            "SECAgent starting",
            task=task[:100],  # Log first 100 chars
            ticker=ticker,
            year=year,
            report_type=report_type
        )
        
        # Fetch real SEC filing data
        logger.info(f"Fetching SEC {report_type} filing for {ticker}")
        sec_data = await self._fetch_sec_data(ticker, year, report_type)
        
        # Build analysis prompt with real data
        prompt = self._build_analysis_prompt_with_data(task, ticker, year, report_type, sec_data, context)
        
        logger.debug(
            "SECAgent prompt built with filing data",
            ticker=ticker,
            prompt_length=len(prompt),
            has_filing=bool(sec_data.get("filing_date")),
            filing_type=sec_data.get("type", "N/A")
        )
        
        try:
            logger.info(f"SECAgent calling LLM for {ticker}")
            response = await self._execute_llm(prompt)
            
            logger.info(
                f"SECAgent LLM response received",
                ticker=ticker,
                response_length=len(response) if response else 0
            )
            
            result_text = f"""## SEC Filing Analysis for {ticker} ({year})

{response}

---
*SEC analysis by SECAgent based on real regulatory filings*
"""
            
            # Track artifacts
            artifacts = context.get("artifacts", [])
            artifacts.append({
                "type": "sec_analysis",
                "title": f"SEC {report_type} Analysis - {ticker}",
                "content": response,
                "metadata": {
                    "ticker": ticker,
                    "year": year,
                    "report_type": report_type,
                    "filing_date": sec_data.get("filing_date", "N/A"),
                    "agent": self.name
                }
            })
            context["artifacts"] = artifacts
            
            logger.info(
                f"SECAgent completed successfully",
                ticker=ticker,
                artifacts_count=len(artifacts)
            )
            
            return self._create_response(result_text)
            
        except Exception as e:
            logger.error("SEC agent execution failed", error=str(e), ticker=ticker)
            return self._create_response(
                f"SEC analysis failed for {ticker}: {str(e)}"
            )
    
    async def _fetch_sec_data(
        self,
        ticker: str,
        year: str = "latest",
        report_type: str = "10-K"
    ) -> Dict[str, Any]:
        """
        Fetch real SEC filing data from FMP API.
        
        Args:
            ticker: Stock ticker symbol
            year: Year for the filing (or "latest")
            report_type: Type of SEC report ("10-K" or "10-Q")
            
        Returns:
            Dictionary with SEC filing information
        """
        if not self.fmp_utils:
            logger.warning("FMPUtils not initialized, returning empty SEC data")
            return {
                "ticker": ticker,
                "year": year,
                "type": report_type,
                "error": "FMP API not configured"
            }
        
        try:
            logger.info(f"Fetching SEC {report_type} filing from FMP for {ticker} year={year}")
            
            sec_filing = self.fmp_utils.get_sec_report(ticker, year, report_type)
            
            if "error" in sec_filing:
                logger.warning(f"SEC filing error for {ticker}: {sec_filing['error']}")
            else:
                logger.info(
                    f"SEC filing fetched successfully",
                    ticker=ticker,
                    type=sec_filing.get("type", report_type),
                    filing_date=sec_filing.get("filing_date", "N/A")
                )
            
            return sec_filing
            
        except Exception as e:
            logger.error(
                f"Error fetching SEC data for {ticker}",
                error=str(e),
                ticker=ticker,
                year=year
            )
            return {
                "ticker": ticker,
                "year": year,
                "type": report_type,
                "error": str(e)
            }
    
    def _build_analysis_prompt_with_data(
        self,
        task: str,
        ticker: str,
        year: str,
        report_type: str,
        sec_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Build analysis prompt with real SEC filing data embedded.
        
        Args:
            task: User's analysis request
            ticker: Stock ticker symbol
            year: Year for the filing
            report_type: Type of SEC report
            sec_data: Real SEC filing data from FMP API
            context: Additional context
            
        Returns:
            Formatted prompt with SEC filing data
        """
        if "error" in sec_data:
            prompt = f"""{self.system_prompt}

User Task: {task}

Company: {ticker}
Report Type: {report_type}
Year: {year}

ERROR: {sec_data['error']}

Please inform the user that SEC filing data is not available for {ticker} for year {year}.
Suggest they try a different year or check if the company has filed recent {report_type} reports.
"""
            return prompt
        
        prompt = f"""{self.system_prompt}

User Task: {task}

## SEC Filing Information
Ticker: {ticker}
Report Type: {sec_data.get('type', report_type)}
Filing Date: {sec_data.get('filing_date', 'N/A')}
Accepted Date: {sec_data.get('accepted_date', 'N/A')}
CIK: {sec_data.get('cik', 'N/A')}
SEC Filing URL: {sec_data.get('url', 'N/A')}

"""
        
        # Add filing link if available
        if sec_data.get('link') or sec_data.get('url'):
            filing_url = sec_data.get('link') or sec_data.get('url')
            prompt += f"""## SEC Filing Access
You can access the full {report_type} filing at: {filing_url}

"""
        
        prompt += f"""## Analysis Instructions

Based on the SEC {report_type} filing information above, please provide a comprehensive analysis addressing the user's task.

Your analysis should cover:

1. **Company Business Overview**
   - Core business description and operations
   - Products and services offered
   - Market positioning and competitive advantages
   - Geographic presence and segment breakdown

2. **Business Highlights & Strategy**
   - Key strategic initiatives and developments
   - Recent acquisitions or divestitures
   - Research and development focus areas
   - Management's strategic vision

3. **Risk Assessment**
   - Item 1A Risk Factors analysis
   - Market and competitive risks
   - Regulatory and compliance risks
   - Operational and financial risks
   - Economic and geopolitical risks
   - Technology and cybersecurity risks

4. **Financial Statement Analysis**
   - Income Statement trends and key metrics
   - Balance Sheet strength and liquidity
   - Cash Flow generation and usage
   - Working capital management
   - Debt levels and capital structure

5. **Segment Performance** (if applicable)
   - Revenue and profitability by segment
   - Segment growth trends
   - Geographic performance
   - Product/service line analysis

6. **Competitive Landscape**
   - Main competitors identified
   - Competitive advantages and disadvantages
   - Market share and positioning
   - Industry trends and dynamics

7. **Management Discussion & Analysis (MD&A)**
   - Management's perspective on results
   - Forward-looking statements
   - Critical accounting policies
   - Off-balance sheet arrangements

8. **Investment Implications**
   - Key strengths from the filing
   - Areas of concern or weakness
   - Regulatory compliance status
   - Overall financial health assessment

IMPORTANT: Since we have access to the filing metadata and URL, you should:
- Reference specific sections of the {report_type} filing
- Provide context about when this filing was made ({sec_data.get('filing_date', 'N/A')})
- Note that detailed analysis would require reviewing the full document
- Highlight that investors should review the complete filing for comprehensive information
- Focus on high-level insights based on typical {report_type} structure

Be professional, analytical, and provide actionable insights for investment decision-making.
"""
        
        return prompt
    
    async def _execute_llm(self, prompt: str) -> str:
        """Execute LLM call using agent_framework's AzureOpenAIChatClient."""
        if not self.chat_client:
            return f"[Simulated SEC Analysis]\n{prompt}"
        
        from agent_framework import ChatMessage, Role
        
        messages = [
            ChatMessage(role=Role.SYSTEM, text=self.system_prompt),
            ChatMessage(role=Role.USER, text=prompt)
        ]
        
        response = await self.chat_client.get_response(
            messages=messages,
            temperature=0.7,
            max_tokens=3000
        )
        
        return response.text
    
    def _create_response(self, text: str) -> AgentRunResponse:
        """Create agent response following MAF pattern."""
        message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text=text)]
        )
        return AgentRunResponse(messages=[message])
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """
        Execute the agent and yield streaming response updates (MAF required method).
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional keyword arguments
            
        Yields:
            AgentRunResponseUpdate objects containing chunks of the response
        """
        # For now, implement non-streaming version by yielding complete response
        # Future: Implement true streaming with Azure OpenAI streaming API
        response = await self.run(messages, thread=thread, **kwargs)
        
        # Yield the complete response as a single update
        for message in response.messages:
            if message.contents:
                for content in message.contents:
                    if isinstance(content, TextContent):
                        yield AgentRunResponseUpdate(
                            contents=[content],
                            role=Role.ASSISTANT
                        )
    
    async def process(self, task: str, context: Dict[str, Any] = None) -> str:
        """Legacy method for YAML-based workflow compatibility."""
        context = context or {}
        response = await self.run(messages=task, thread=None, ticker=context.get('ticker'), context=context)
        return response.messages[-1].text if response.messages else ""
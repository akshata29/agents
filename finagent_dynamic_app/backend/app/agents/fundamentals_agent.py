"""
Fundamentals Agent

Microsoft Agent Framework compliant agent for fundamental analysis.
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


class FundamentalsAgent(BaseAgent):
    """
    Fundamental Analysis Agent - Financial metrics and ratios specialist.
    
    Capabilities:
    - Fetch fundamental data (income, balance sheet, cash flow statements)
    - Compute financial ratios (ROE, ROA, profit margins, etc.)
    - Calculate Altman Z-Score (bankruptcy risk)
    - Calculate Piotroski F-Score (financial strength)
    - Analyze financial health and trends
    - Valuation metrics analysis
    
    Based on finagentsk FundamentalAnalysisAgent definition.
    """
    
    SYSTEM_PROMPT = """You are a Fundamental Analysis Agent specialized in analyzing 
financial statements and computing key financial ratios.

IMPORTANT: Always use the current date provided in prompts when discussing recent data or trends.

Your responsibilities:
1. Retrieve and analyze 3-5 years of fundamental data (cash flow, income, balance sheet)
2. Compute key financial ratios:
   - Profitability: ROE, ROA, Net Margin, Gross Margin
   - Efficiency: Asset Turnover, Inventory Turnover
   - Leverage: Debt-to-Equity, Interest Coverage
   - Liquidity: Current Ratio, Quick Ratio
3. Calculate financial health scores:
   - Altman Z-Score (bankruptcy prediction)
   - Piotroski F-Score (financial strength 0-9)
4. Identify trends in financial performance
5. Provide investment-grade fundamental assessment

Be quantitative, use specific numbers, and highlight trends and anomalies."""

    def __init__(
        self,
        name: str = "FundamentalsAgent",
        description: str = "Fundamental analysis and financial ratios specialist",
        chat_client: Any = None,  # Changed from azure_client to chat_client
        model: str = "gpt-4o",
        tools: Optional[List[Dict[str, Any]]] = None,
        fmp_api_key: Optional[str] = None
    ):
        """Initialize Fundamentals Agent."""
        super().__init__(name=name, description=description)
        self.chat_client = chat_client
        self.model = model
        self.tools = tools or []
        self.system_prompt = self.SYSTEM_PROMPT
        
        # Initialize data provider
        self.fmp_utils = FMPUtils(fmp_api_key) if fmp_api_key else None
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "fetch_financial_statements",
            "compute_profitability_ratios",
            "compute_leverage_ratios",
            "compute_liquidity_ratios",
            "compute_efficiency_ratios",
            "calculate_altman_z_score",
            "calculate_piotroski_score",
            "analyze_financial_trends"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute fundamental analysis (MAF required method)."""
        normalized_messages = self._normalize_messages(messages)
        if not normalized_messages:
            return AgentRunResponse(messages=[ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text="Hello! I'm a fundamentals agent.")])])
        
        context = kwargs.get("context", {})
        ticker = context.get("ticker", kwargs.get("ticker"))
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        years = context.get("years", kwargs.get("years", 5))
        
        logger.info(
            "FundamentalsAgent starting",
            task=task,
            ticker=ticker,
            years=years,
            context_keys=list(context.keys())
        )
        
        # Fetch real fundamental data from FMP
        logger.info(f"Fetching fundamental data from FMP for {ticker}")
        fundamental_data = await self._fetch_fundamental_data(ticker, years)
        
        # Build analysis prompt with real data
        prompt = self._build_analysis_prompt_with_data(task, ticker, years, fundamental_data, context)
        
        # Check if data exists - handle DataFrames properly
        metrics = fundamental_data.get("financial_metrics")
        has_metrics = metrics is not None and (not metrics.empty if hasattr(metrics, 'empty') else bool(metrics))
        
        logger.debug(
            "FundamentalsAgent prompt built with data",
            ticker=ticker,
            prompt_length=len(prompt),
            has_metrics=has_metrics,
            has_ratings=bool(fundamental_data.get("ratings")),
            has_scores=bool(fundamental_data.get("financial_scores"))
        )
        
        try:
            logger.info(f"FundamentalsAgent calling LLM for {ticker}")
            response = await self._execute_llm(prompt)
            
            logger.info(
                f"FundamentalsAgent LLM response received",
                ticker=ticker,
                response_length=len(response) if response else 0
            )
            
            result_text = f"""## Fundamental Analysis for {ticker}

{response}

---
*Fundamental analysis by FundamentalsAgent based on real financial statements and ratios*
"""
            
            # Track artifacts
            artifacts = context.get("artifacts", [])
            artifacts.append({
                "type": "fundamental_analysis",
                "title": f"Fundamental Analysis - {ticker}",
                "content": response,
                "metadata": {
                    "ticker": ticker,
                    "years": years,
                    "agent": self.name
                }
            })
            context["artifacts"] = artifacts
            
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            
        except Exception as e:
            logger.error(
                f"FundamentalsAgent error analyzing {ticker}",
                error=str(e),
                ticker=ticker
            )
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=f"Error analyzing fundamentals for {ticker}: {str(e)}")]
                )]
            )
    
    async def _fetch_fundamental_data(
        self,
        ticker: str,
        years: int = 5
    ) -> Dict[str, Any]:
        """
        Fetch real fundamental data from FMP API.
        
        The planner already specifies what analysis to perform,
        so we fetch all available data and let the LLM extract what's relevant.
        
        Args:
            ticker: Stock ticker symbol
            years: Number of years of historical data
            
        Returns:
            Dictionary with financial metrics, ratings, and scores
        """
        if not self.fmp_utils:
            logger.warning("FMPUtils not initialized, returning empty data")
            return {
                "financial_metrics": None,
                "ratings": {},
                "financial_scores": [],
                "fetched_at": datetime.now().isoformat()
            }
        
        try:
            logger.info(f"Fetching fundamental data from FMP for {ticker} ({years} years)")
            
            # Fetch all fundamental data
            financial_metrics = self.fmp_utils.get_financial_metrics(ticker, years)
            ratings = self.fmp_utils.get_ratings(ticker)
            financial_scores = self.fmp_utils.get_financial_scores(ticker)
            
            logger.info(
                f"Fundamental data fetched successfully",
                ticker=ticker,
                has_metrics=not financial_metrics.empty if hasattr(financial_metrics, 'empty') else False,
                has_ratings=bool(isinstance(ratings, dict) and 'error' not in ratings),
                num_scores=len(financial_scores) if financial_scores is not None else 0
            )
            
            return {
                "financial_metrics": financial_metrics,
                "ratings": ratings,
                "financial_scores": financial_scores,
                "fetched_at": datetime.now().isoformat(),
                "source": "FMP API"
            }
            
        except Exception as e:
            logger.error(
                f"Error fetching fundamental data for {ticker}",
                error=str(e),
                ticker=ticker
            )
            return {
                "financial_metrics": None,
                "ratings": {},
                "financial_scores": [],
                "error": str(e),
                "fetched_at": datetime.now().isoformat()
            }
    
    def _build_analysis_prompt_with_data(
        self,
        task: str,
        ticker: str,
        years: int,
        fundamental_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Build analysis prompt with real fundamental data embedded.
        
        Args:
            task: User's analysis request
            ticker: Stock ticker symbol
            years: Number of years analyzed
            fundamental_data: Real data from FMP API
            context: Additional context
            
        Returns:
            Formatted prompt with fundamental data
        """
        financial_metrics = fundamental_data.get("financial_metrics")
        ratings = fundamental_data.get("ratings", {})
        financial_scores = fundamental_data.get("financial_scores", [])
        
        # Get current date for temporal context
        current_date = datetime.utcnow().strftime("%B %d, %Y")
        
        # Build prompt with real data
        prompt = f"""{self.system_prompt}

IMPORTANT: Today's date is {current_date}. Use this date when discussing recent trends or current data.

User Task: {task}

## Company Information
Ticker: {ticker}
Analysis Period: {years} years
Data Source: {fundamental_data.get('source', 'FMP API')}

"""
        
        # Add financial metrics if available
        if financial_metrics is not None and not financial_metrics.empty:
            # Convert DataFrame to markdown table
            import tabulate
            metrics_table = tabulate.tabulate(
                financial_metrics,
                headers='keys',
                tablefmt='pipe',
                showindex=True
            )
            prompt += f"""## Financial Metrics ({years}-Year History)
{metrics_table}

Note: Revenue, EBITDA, Net Income in millions USD

"""
        else:
            prompt += f"""## Financial Metrics
No financial metrics data available for {ticker}.

"""
        
        # Add ratings if available
        if ratings is not None and isinstance(ratings, dict) and 'error' not in ratings:
            prompt += f"""## Analyst Ratings & Recommendations
- Overall Rating: {ratings.get('rating', 'N/A')} (Score: {ratings.get('ratingScore', 0)}/5)
- Recommendation: {ratings.get('ratingRecommendation', 'N/A')}
- DCF Analysis: {ratings.get('ratingDetailsDCFRecommendation', 'N/A')} (Score: {ratings.get('ratingDetailsDCFScore', 0)})
- ROE Analysis: {ratings.get('ratingDetailsROERecommendation', 'N/A')} (Score: {ratings.get('ratingDetailsROEScore', 0)})
- ROA Analysis: {ratings.get('ratingDetailsROARecommendation', 'N/A')} (Score: {ratings.get('ratingDetailsROAScore', 0)})
- Debt/Equity: {ratings.get('ratingDetailsDERecommendation', 'N/A')} (Score: {ratings.get('ratingDetailsDEScore', 0)})
- P/E Ratio: {ratings.get('ratingDetailsPERecommendation', 'N/A')} (Score: {ratings.get('ratingDetailsPEScore', 0)})
- P/B Ratio: {ratings.get('ratingDetailsPBRecommendation', 'N/A')} (Score: {ratings.get('ratingDetailsPBScore', 0)})
- Last Updated: {ratings.get('date', 'N/A')}

"""
        
        # Add financial scores if available
        if financial_scores is not None and len(financial_scores) > 0:
            prompt += f"""## Financial Health Scores

"""
            for score in financial_scores[:3]:  # Show most recent 3 years
                prompt += f"""### {score.get('date', 'N/A')}
- **Altman Z-Score**: {score.get('altmanZScore', 'N/A')} (>2.99=Safe, 1.81-2.99=Grey, <1.81=Distress)
- **Piotroski F-Score**: {score.get('piotroskiScore', 'N/A')}/9 (0-3=Poor, 4-6=Average, 7-9=Strong)
- Working Capital: ${score.get('workingCapital', 0):,.0f}
- Total Assets: ${score.get('totalAssets', 0):,.0f}
- Market Cap: ${score.get('marketCap', 0):,.0f}
- EBIT: ${score.get('ebit', 0):,.0f}

"""
        
        prompt += f"""---

Based on the REAL financial data above, please provide a comprehensive fundamental analysis addressing the user's task.

Your analysis should include:

1. **Financial Performance Trends**
   - Revenue growth trajectory
   - Profitability trends (margins, EPS growth)
   - Key metric evolution over {years} years

2. **Financial Health Assessment**
   - Altman Z-Score interpretation (bankruptcy risk)
   - Piotroski F-Score analysis (financial strength)
   - Overall financial stability

3. **Valuation Analysis**
   - P/E ratio trends and comparison
   - P/B ratio assessment
   - DCF-based valuation perspective from ratings

4. **Profitability Ratios**
   - ROE, ROA trends
   - Gross margin and net margin analysis
   - Efficiency in capital deployment

5. **Investment Recommendation**
   - Fundamental strengths
   - Fundamental weaknesses or concerns
   - Overall assessment based on real data

Be specific with numbers from the data above. Identify trends, anomalies, and provide actionable insights.
"""
        
        return prompt
    
    async def _execute_llm(self, prompt: str) -> str:
        """Execute LLM call using agent_framework's AzureOpenAIChatClient."""
        if not self.chat_client:
            return f"[Simulated Fundamental Analysis]\n{prompt}"
        
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
        return AgentRunResponse(messages=[ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=text)])])
    
    async def run_stream(self, messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None, *, thread: AgentThread | None = None, **kwargs: Any) -> AsyncIterable[AgentRunResponseUpdate]:
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
        response = await self.run(messages=task, thread=None, ticker=context.get('ticker'), context=context)
        return response.messages[-1].text if response.messages else ""

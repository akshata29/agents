"""
Company Agent

Microsoft Agent Framework compliant agent for company intelligence and market data analysis.
Integrates real data providers (FMP, Yahoo Finance) following MAF patterns.
"""

import asyncio
from typing import Any, Dict, List, Optional, AsyncIterable
from datetime import date, timedelta
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
from helpers.yfutils import YFUtils

logger = structlog.get_logger(__name__)


class CompanyAgent(BaseAgent):
    """
    Company Analyst Agent - Financial intelligence specialist (MAF compliant).
    
    Capabilities:
    - Company profile and metrics
    - Stock quotes and time-series data
    - Latest financial metrics
    - Analyst recommendations
    - Company news aggregation
    
    Follows Microsoft Agent Framework patterns with real data integration.
    """
    
    SYSTEM_PROMPT = """You are an AI Agent with deep knowledge about stock markets, 
company information, company news, analyst recommendations, and company financial data and metrics. 

Your role is to:
1. Provide comprehensive company profiles including industry, sector, market cap, and key metrics
2. Retrieve and analyze real-time stock data and historical price trends
3. Aggregate and summarize analyst recommendations and target prices
4. Extract key financial metrics (P/E ratios, revenue, margins, etc.)
5. Summarize relevant company news and market sentiment

Be data-driven, factual, and provide actionable insights. Always cite your data sources."""

    def __init__(
        self,
        name: str = "CompanyAgent",
        description: str = "Company intelligence and market data specialist",
        azure_client: Any = None,
        model: str = "gpt-4o",
        fmp_api_key: Optional[str] = None
    ):
        """Initialize Company Agent following MAF pattern."""
        super().__init__(name=name, description=description)
        
        # Store custom attributes
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = self.SYSTEM_PROMPT
        
        # Initialize data providers
        self.fmp_utils = FMPUtils(fmp_api_key) if fmp_api_key else None
        self.yf_utils = YFUtils()
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "get_company_profile",
            "get_stock_quotes",
            "get_financial_metrics",
            "get_analyst_recommendations",
            "get_company_news",
            "get_market_sentiment"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """
        Execute company analysis task (MAF required method).
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional context (ticker, context dict, etc.)
            
        Returns:
            AgentRunResponse containing the agent's analysis
        """
        # Normalize input messages to a list
        normalized_messages = self._normalize_messages(messages)
        
        if not normalized_messages:
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text="Hello! I'm a company intelligence agent. Please provide a ticker symbol.")]
            )
            return AgentRunResponse(messages=[response_message])
        
        # Get context from kwargs
        context = kwargs.get("context", {})
        ticker = context.get("ticker", kwargs.get("ticker"))
        
        # Extract task from last message
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        
        logger.info(
            "CompanyAgent starting",
            task=task[:100],  # Log first 100 chars
            ticker=ticker,
            context_keys=list(context.keys())
        )
        
        # Fetch real data from providers
        logger.info(f"Fetching real market data for {ticker}")
        market_data = await self._fetch_market_data(ticker, context)
        
        # Build analysis prompt with real data
        prompt = self._build_analysis_prompt_with_data(task, ticker, market_data, context)
        
        logger.debug(
            "CompanyAgent prompt built with data",
            ticker=ticker,
            prompt_length=len(prompt),
            data_sources=list(market_data.keys())
        )
        
        # Execute with Azure OpenAI
        try:
            logger.info(f"CompanyAgent calling LLM for {ticker}")
            response = await self._execute_llm(prompt)
            
            logger.info(
                f"CompanyAgent LLM response received",
                ticker=ticker,
                response_length=len(response) if response else 0
            )
            
            result_text = f"""## Company Analysis for {ticker}

{response}

---
*Analysis provided by CompanyAgent using market data APIs and financial databases*
"""
            
            # Track artifacts
            artifacts = context.get("artifacts", [])
            artifacts.append({
                "type": "company_profile",
                "ticker": ticker,
                "content": response,
                "agent": self.name
            })
            context["artifacts"] = artifacts
            
            logger.info(
                f"CompanyAgent completed successfully",
                ticker=ticker,
                artifacts_count=len(artifacts)
            )
            
            return self._create_response(result_text)
            
        except Exception as e:
            logger.error("Company agent execution failed", error=str(e), ticker=ticker)
            return self._create_response(
                f"Company analysis failed for {ticker}: {str(e)}"
            )
    
    async def _fetch_market_data(self, ticker: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch real market data from FMP and Yahoo Finance."""
        data = {}
        
        try:
            # Get company profile from FMP
            if self.fmp_utils:
                logger.info(f"Fetching company profile from FMP for {ticker}")
                data["company_profile"] = self.fmp_utils.get_company_profile(ticker)
                
                # Get financial metrics
                logger.info(f"Fetching financial metrics from FMP for {ticker}")
                metrics_df = self.fmp_utils.get_financial_metrics(ticker, years=4)
                if not metrics_df.empty:
                    data["financial_metrics"] = metrics_df.to_markdown()
                
                # Get company news
                end_date = date.today().strftime("%Y-%m-%d")
                start_date = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
                news_df = self.fmp_utils.get_company_news(ticker, start_date, end_date, max_news=5)
                if not news_df.empty:
                    data["company_news"] = news_df.to_markdown()
            
            # Get data from Yahoo Finance
            logger.info(f"Fetching stock info from Yahoo Finance for {ticker}")
            stock_info = self.yf_utils.get_stock_info(ticker)
            if stock_info:
                data["stock_info"] = {
                    "current_price": stock_info.get("currentPrice", "N/A"),
                    "market_cap": stock_info.get("marketCap", "N/A"),
                    "52_week_high": stock_info.get("fiftyTwoWeekHigh", "N/A"),
                    "52_week_low": stock_info.get("fiftyTwoWeekLow", "N/A"),
                    "pe_ratio": stock_info.get("trailingPE", "N/A"),
                    "forward_pe": stock_info.get("forwardPE", "N/A"),
                    "dividend_yield": stock_info.get("dividendYield", "N/A"),
                }
            
            # Get analyst recommendations
            analyst_recs = self.yf_utils.get_analyst_recommendations(ticker)
            if analyst_recs:
                data["analyst_recommendations"] = analyst_recs
            
            # Get stock price data (last year)
            end_date_dt = date.today().strftime("%Y-%m-%d")
            start_date_dt = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
            stock_data = self.yf_utils.get_stock_data(ticker, start_date_dt, end_date_dt)
            if not stock_data.empty:
                # Calculate performance metrics
                initial_price = stock_data['Close'].iloc[0]
                current_price = stock_data['Close'].iloc[-1]
                year_performance = ((current_price - initial_price) / initial_price) * 100
                data["stock_performance"] = {
                    "1_year_return": f"{year_performance:.2f}%",
                    "52_week_high": stock_data['High'].max(),
                    "52_week_low": stock_data['Low'].min(),
                }
            
            logger.info(f"Market data fetched successfully for {ticker}", data_keys=list(data.keys()))
            return data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {ticker}", error=str(e))
            return data
    
    def _build_analysis_prompt_with_data(
        self,
        task: str,
        ticker: str,
        market_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Build analysis prompt with real market data."""
        prompt = f"""Perform comprehensive company analysis for {ticker}.

Task: {task}

## Real-Time Market Data:

### Company Profile:
{market_data.get('company_profile', 'N/A')}

### Stock Information:
{market_data.get('stock_info', 'N/A')}

### Financial Metrics (Last 4 Years):
{market_data.get('financial_metrics', 'No financial metrics available')}

### Stock Performance:
{market_data.get('stock_performance', 'N/A')}

### Analyst Recommendations:
{market_data.get('analyst_recommendations', 'No analyst recommendations available')}

### Recent News (Last 7 Days):
{market_data.get('company_news', 'No recent news available')}

---

Based on the above real market data, please provide a comprehensive analysis covering:
1. Business Overview & Competitive Position
2. Financial Health & Key Metrics Analysis
3. Stock Performance & Valuation Analysis
4. Recent Developments & News Impact
5. Analyst Sentiment & Investment Outlook

Structure your response with clear headings and data-driven insights."""
        
        return prompt
    
    def _build_analysis_prompt(
        self,
        task: str,
        ticker: Optional[str],
        context: Dict[str, Any]
    ) -> str:
        """Build analysis prompt (legacy method - kept for compatibility)."""
        scope = context.get("scope", ["profile", "metrics", "news"])
        
        prompt = f"""Perform comprehensive company analysis for {ticker or 'the specified company'}.

Task: {task}

Analysis Scope: {', '.join(scope)}

Please provide:
1. Company Profile: Industry, sector, market cap, business description
2. Latest Financial Metrics: Revenue, margins, P/E ratio, growth rates
3. Stock Performance: Current price, 52-week range, trends
4. Analyst Consensus: Recommendations, target price, ratings distribution
5. Recent News: Key developments and market sentiment

Structure your response with clear headings and data-driven insights.
Include specific numbers and dates where available."""
        
        return prompt
    
    async def _execute_llm(self, prompt: str) -> str:
        """Execute LLM call."""
        if not self.azure_client:
            logger.warning("No Azure client configured, returning simulated response")
            return f"[Simulated Company Analysis]\n{prompt}"
        
        import time
        start_time = time.time()
        
        logger.info("Calling Azure OpenAI", model=self.model, prompt_length=len(prompt))
        
        response = await self.azure_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        duration = time.time() - start_time
        logger.info(
            "Azure OpenAI response received",
            model=self.model,
            duration_seconds=round(duration, 2),
            response_tokens=len(response.choices[0].message.content) if response.choices else 0
        )
        
        return response.choices[0].message.content
    
    def _extract_task(self, messages) -> str:
        """Extract task from messages."""
        if isinstance(messages, str):
            return messages
        if isinstance(messages, list) and messages:
            last_msg = messages[-1]
            if isinstance(last_msg, str):
                return last_msg
            if hasattr(last_msg, 'text'):
                return last_msg.text
        return "Perform comprehensive company analysis"
    
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
        response = await self.run(messages=task, thread=None, context=context)
        return response.messages[-1].text if response.messages else ""

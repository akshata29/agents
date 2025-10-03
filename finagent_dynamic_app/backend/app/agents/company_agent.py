"""
Company Agent

Microsoft Agent Framework compliant agent for company intelligence and market data analysis.
Integrates real data providers (FMP, Yahoo Finance MCP Server) following MAF patterns.

Uses native MAF function calling - tools are defined as Python functions with type hints,
and the framework automatically handles function calling via Azure OpenAI.
"""

import asyncio
from typing import Any, Dict, List, Optional, AsyncIterable, Annotated
from datetime import date, timedelta
import structlog
import json

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread
from pydantic import Field

# Import data providers
import sys
from pathlib import Path
bridge_dir = Path(__file__).parent.parent
if str(bridge_dir) not in sys.path:
    sys.path.insert(0, str(bridge_dir))

from helpers.fmputils import FMPUtils

# Import MCP client for calling Yahoo Finance MCP server
from mcp import ClientSession
from mcp.client.sse import sse_client

logger = structlog.get_logger(__name__)


class CompanyAgent(BaseAgent):
    """
    Company Analyst Agent - Financial intelligence specialist (MAF compliant).
    
    Exposes Yahoo Finance MCP Server tools and FMP tools to the planner.
    The planner specifies which specific MCP tool to call in the task.
    
    Available MCP Tools (exposed to planner):
    - get_stock_info: Current stock data and metrics from Yahoo Finance
    - get_historical_stock_prices: Historical OHLCV data from Yahoo Finance
    - get_yahoo_finance_news: Latest news from Yahoo Finance
    - get_recommendations: Analyst recommendations from Yahoo Finance
    - get_company_profile: Company profile from FMP
    - get_financial_metrics: Financial metrics from FMP
    
    The agent calls the specific MCP tool based on what the planner requested.
    """
    
    SYSTEM_PROMPT = """You are an AI Agent with deep knowledge about stock markets, 
company information, company news, analyst recommendations, and company financial data and metrics. 

The task you receive will specify which specific MCP tool or function to use.
Your role is to analyze the data returned and provide insights.

Be data-driven, factual, and provide actionable insights."""

    def __init__(
        self,
        name: str = "CompanyAgent",
        description: str = "Company intelligence and market data specialist",
        chat_client: Any = None,
        model: str = "gpt-4o",
        fmp_api_key: Optional[str] = None,
        mcp_server_url: Optional[str] = None
    ):
        """Initialize Company Agent with MCP Server integration."""
        logger.info(
            "CompanyAgent.__init__ called",
            name=name,
            has_chat_client=chat_client is not None,
            model=model,
            has_fmp_key=fmp_api_key is not None,
            mcp_url=mcp_server_url
        )
        
        super().__init__(name=name, description=description)
        
        # Store custom attributes
        self.chat_client = chat_client
        self.model = model
        self.system_prompt = self.SYSTEM_PROMPT
        
        # Initialize data providers
        self.fmp_utils = FMPUtils(fmp_api_key) if fmp_api_key else None
        self.mcp_server_url = mcp_server_url or "http://localhost:8001/sse"
        self.mcp_session: Optional[ClientSession] = None
        
        logger.info(
            "CompanyAgent initialized with MCP Server tools",
            mcp_server_url=self.mcp_server_url,
            has_fmp_utils=self.fmp_utils is not None,
            agent_name=self.name
        )
    
    @staticmethod
    def get_tools_info() -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available MCP and FMP tools.
        This is exposed to the planner so it knows exactly what tools are available.
        
        Returns dict with tool names as keys and metadata as values.
        """
        return {
            "get_stock_info": {
                "description": "Get comprehensive stock data from Yahoo Finance including current price, market cap, P/E ratios, dividends, and financial metrics",
                "parameters": "ticker (string)",
                "mcp_tool": "get_stock_info",
                "source": "Yahoo Finance MCP Server"
            },
            "get_historical_stock_prices": {
                "description": "Get historical OHLCV (Open, High, Low, Close, Volume) data for price analysis and trends",
                "parameters": "ticker (string), period (string: 1mo/1y/etc), interval (string: 1d/1wk/etc)",
                "mcp_tool": "get_historical_stock_prices",
                "source": "Yahoo Finance MCP Server"
            },
            "get_yahoo_finance_news": {
                "description": "Retrieve latest news articles and press releases from Yahoo Finance",
                "parameters": "ticker (string)",
                "mcp_tool": "get_yahoo_finance_news",
                "source": "Yahoo Finance MCP Server"
            },
            "get_recommendations": {
                "description": "Get analyst recommendations, upgrades/downgrades, target prices, and rating distribution",
                "parameters": "ticker (string), recommendation_type (string: recommendations/upgrades_downgrades)",
                "mcp_tool": "get_recommendations",
                "source": "Yahoo Finance MCP Server"
            },
            "get_company_profile": {
                "description": "Get company profile from FMP including industry, sector, business description, CEO, employees",
                "parameters": "ticker (string)",
                "mcp_tool": None,
                "source": "FMP API"
            },
            "get_financial_metrics": {
                "description": "Get financial metrics from FMP including revenue, margins, profitability ratios (last 4 years)",
                "parameters": "ticker (string), years (int: default 4)",
                "mcp_tool": None,
                "source": "FMP API"
            }
        }
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities (list of available tools)."""
        return list(self.get_tools_info().keys())
    
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
        
        # Log what we received
        logger.info(
            "CompanyAgent.run() - checking ticker sources",
            ticker_from_context=context.get("ticker"),
            ticker_from_kwargs=kwargs.get("ticker"),
            final_ticker=ticker,
            all_kwargs_keys=list(kwargs.keys())
        )
        
        # Extract task from last message
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        
        logger.info(
            "CompanyAgent starting",
            task=task[:200],  # Log first 200 chars
            ticker=ticker,
            context_keys=list(context.keys())
        )
        
        # Parse task to determine which specific MCP tool(s) to call
        # The planner should specify tool names like "Function: get_recommendations"
        logger.info(f"Determining which MCP tools to call for task")
        market_data = await self._fetch_data_for_task(ticker, task, context)
        
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
    
    async def _fetch_data_for_task(self, ticker: str, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligently call specific MCP tools based on what the task requests.
        
        The planner's task should mention which function/tool to use.
        Examples:
          - "Function: get_recommendations" → Call get_recommendations MCP tool
          - "Function: get_yahoo_finance_news" → Call get_yahoo_finance_news MCP tool
          - "Gather analyst recommendations and latest news" → Call both tools
        
        Args:
            ticker: Stock ticker symbol
            task: The specific task from the planner
            context: Additional context
            
        Returns:
            Dictionary containing data from the called MCP tools
        """
        data = {}
        task_lower = task.lower()
        
        try:
            # Detect which tools to call based on task content
            # Look for explicit "Function:" mentions from planner
            tools_to_call = set()
            
            if "function: get_stock_info" in task_lower or "stock info" in task_lower or "stock quote" in task_lower or "current price" in task_lower:
                tools_to_call.add("get_stock_info")
            
            if "function: get_historical_stock_prices" in task_lower or "historical" in task_lower or "price history" in task_lower:
                tools_to_call.add("get_historical_stock_prices")
            
            if "function: get_yahoo_finance_news" in task_lower or "news" in task_lower:
                tools_to_call.add("get_yahoo_finance_news")
            
            if "function: get_recommendations" in task_lower or "analyst" in task_lower or "recommendation" in task_lower:
                tools_to_call.add("get_recommendations")
            
            if "function: get_company_profile" in task_lower or "company profile" in task_lower or "company info" in task_lower:
                tools_to_call.add("get_company_profile")
            
            if "function: get_financial_metrics" in task_lower or "financial metrics" in task_lower or "financials" in task_lower:
                tools_to_call.add("get_financial_metrics")
            
            # If no specific tools detected, make a smart guess based on keywords
            if not tools_to_call:
                logger.info("No specific tools detected in task, using default tools based on keywords")
                if any(word in task_lower for word in ["news", "article", "recent", "latest"]):
                    tools_to_call.add("get_yahoo_finance_news")
                if any(word in task_lower for word in ["analyst", "recommendation", "rating", "upgrade", "downgrade"]):
                    tools_to_call.add("get_recommendations")
                if any(word in task_lower for word in ["price", "stock", "quote", "market"]):
                    tools_to_call.add("get_stock_info")
            
            logger.info(f"Tools to call based on task analysis: {tools_to_call}")
            
            # Call MCP server for Yahoo Finance tools
            if any(tool in tools_to_call for tool in ["get_stock_info", "get_historical_stock_prices", "get_yahoo_finance_news", "get_recommendations"]):
                async with sse_client(self.mcp_server_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        
                        # Call get_stock_info if needed
                        if "get_stock_info" in tools_to_call:
                            logger.info(f"Calling MCP tool: get_stock_info for {ticker}")
                            result = await session.call_tool("get_stock_info", arguments={"ticker": ticker})
                            stock_info_data = json.loads(result.content[0].text)
                            data["stock_info"] = {
                                "current_price": stock_info_data.get("currentPrice", "N/A"),
                                "market_cap": stock_info_data.get("marketCap", "N/A"),
                                "52_week_high": stock_info_data.get("fiftyTwoWeekHigh", "N/A"),
                                "52_week_low": stock_info_data.get("fiftyTwoWeekLow", "N/A"),
                                "pe_ratio": stock_info_data.get("trailingPE", "N/A"),
                                "forward_pe": stock_info_data.get("forwardPE", "N/A"),
                                "dividend_yield": stock_info_data.get("dividendYield", "N/A"),
                            }
                        
                        # Call get_historical_stock_prices if needed
                        if "get_historical_stock_prices" in tools_to_call:
                            logger.info(f"Calling MCP tool: get_historical_stock_prices for {ticker}")
                            result = await session.call_tool(
                                "get_historical_stock_prices",
                                arguments={"ticker": ticker, "period": "1y", "interval": "1d"}
                            )
                            hist_data = json.loads(result.content[0].text)
                            
                            # Calculate performance
                            if hist_data and len(hist_data) > 0:
                                first_close = hist_data[0].get("Close", 0)
                                last_close = hist_data[-1].get("Close", 0)
                                if first_close > 0:
                                    year_performance = ((last_close - first_close) / first_close) * 100
                                    high_prices = [d.get("High", 0) for d in hist_data]
                                    low_prices = [d.get("Low", 0) for d in hist_data]
                                    
                                    data["stock_performance"] = {
                                        "1_year_return": f"{year_performance:.2f}%",
                                        "52_week_high": max(high_prices) if high_prices else "N/A",
                                        "52_week_low": min(low_prices) if low_prices else "N/A",
                                    }
                        
                        # Call get_yahoo_finance_news if needed
                        if "get_yahoo_finance_news" in tools_to_call:
                            logger.info(f"Calling MCP tool: get_yahoo_finance_news for {ticker}")
                            result = await session.call_tool("get_yahoo_finance_news", arguments={"ticker": ticker})
                            data["company_news"] = result.content[0].text
                        
                        # Call get_recommendations if needed
                        if "get_recommendations" in tools_to_call:
                            logger.info(f"Calling MCP tool: get_recommendations for {ticker}")
                            result = await session.call_tool(
                                "get_recommendations",
                                arguments={"ticker": ticker, "recommendation_type": "recommendations"}
                            )
                            data["analyst_recommendations"] = result.content[0].text
            
            # Call FMP tools if needed
            if self.fmp_utils:
                if "get_company_profile" in tools_to_call:
                    logger.info(f"Calling FMP: get_company_profile for {ticker}")
                    data["company_profile"] = self.fmp_utils.get_company_profile(ticker)
                
                if "get_financial_metrics" in tools_to_call:
                    logger.info(f"Calling FMP: get_financial_metrics for {ticker}")
                    metrics_df = self.fmp_utils.get_financial_metrics(ticker, years=4)
                    if not metrics_df.empty:
                        data["financial_metrics"] = metrics_df.to_markdown()
            
            logger.info(f"Data fetched successfully for {ticker}", tools_called=list(tools_to_call), data_keys=list(data.keys()))
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}", error=str(e), exc_info=True)
            return data
    
    def _build_analysis_prompt_with_data(
        self,
        task: str,
        ticker: str,
        market_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Build analysis prompt with ONLY the data that was fetched.
        
        The task from the planner specifies exactly what to analyze,
        so we only include the relevant data sections and ask the LLM
        to focus on that specific aspect.
        """
        # Build data sections dynamically based on what was actually fetched
        data_sections = []
        
        if 'company_profile' in market_data:
            data_sections.append(f"### Company Profile:\n{market_data['company_profile']}")
        
        if 'stock_info' in market_data:
            data_sections.append(f"### Stock Information:\n{market_data['stock_info']}")
        
        if 'financial_metrics' in market_data:
            data_sections.append(f"### Financial Metrics (Last 4 Years):\n{market_data['financial_metrics']}")
        
        if 'stock_performance' in market_data:
            data_sections.append(f"### Stock Performance:\n{market_data['stock_performance']}")
        
        if 'analyst_recommendations' in market_data:
            data_sections.append(f"### Analyst Recommendations:\n{market_data['analyst_recommendations']}")
        
        if 'company_news' in market_data:
            data_sections.append(f"### Recent News:\n{market_data['company_news']}")
        
        # Join all data sections
        data_content = "\n\n".join(data_sections) if data_sections else "No data available"
        
        # Build focused prompt based on the specific task
        prompt = f"""Task: {task}

Stock Ticker: {ticker}

## Available Data:

{data_content}

---

Based on the data provided above, please analyze and provide insights specifically for the task requested.
Focus ONLY on what the task is asking for - do not provide unnecessary information.
Be data-driven, factual, and concise. Structure your response with clear headings."""
        
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
        """Execute LLM call using agent_framework's AzureOpenAIChatClient."""
        if not self.chat_client:
            logger.warning("No chat client configured, returning simulated response")
            return f"[Simulated Company Analysis]\n{prompt}"
        
        import time
        start_time = time.time()
        
        logger.info("Calling Azure OpenAI via agent_framework", model=self.model, prompt_length=len(prompt))
        
        # Use Microsoft Agent Framework's chat client
        from agent_framework import ChatMessage, Role
        
        messages = [
            ChatMessage(role=Role.SYSTEM, text=self.system_prompt),
            ChatMessage(role=Role.USER, text=prompt)
        ]
        
        response = await self.chat_client.get_response(
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        duration = time.time() - start_time
        logger.info(
            "Azure OpenAI response received",
            model=self.model,
            duration_seconds=round(duration, 2),
            response_length=len(response.text) if response.text else 0
        )
        
        return response.text
    
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
    
    def _normalize_messages(self, messages):
        """Normalize messages to a list of ChatMessage objects."""
        if messages is None:
            return []
        
        if isinstance(messages, str):
            return [ChatMessage(role=Role.USER, contents=[TextContent(text=messages)])]
        
        if isinstance(messages, ChatMessage):
            return [messages]
        
        if isinstance(messages, list):
            normalized = []
            for msg in messages:
                if isinstance(msg, str):
                    normalized.append(ChatMessage(role=Role.USER, contents=[TextContent(text=msg)]))
                elif isinstance(msg, ChatMessage):
                    normalized.append(msg)
            return normalized
        
        return []
    
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
        logger.info(
            "CompanyAgent.process() called",
            task=task[:100] if task else "None",
            context_keys=list(context.keys()),
            ticker=context.get('ticker'),
            agent_name=self.name
        )
        
        # Pass context via kwargs so run() can access it
        response = await self.run(messages=task, thread=None, ticker=context.get('ticker'), context=context)
        result = response.messages[-1].text if response.messages else ""
        logger.info(
            "CompanyAgent.process() completed",
            result_length=len(result),
            agent_name=self.name
        )
        return result

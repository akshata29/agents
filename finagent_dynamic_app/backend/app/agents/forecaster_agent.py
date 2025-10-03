"""
Forecaster Agent

Microsoft Agent Framework compliant agent for stock price prediction and forecasting.
Uses technical analysis, sentiment analysis, and market data to make predictions.
"""

import asyncio
from typing import Any, Dict, List, Optional, AsyncIterable
from datetime import date, timedelta
import structlog
import json

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread

logger = structlog.get_logger(__name__)


class ForecasterAgent(BaseAgent):
    """
    Forecaster Agent - Stock price prediction specialist (MAF compliant).
    
    Exposes forecasting tools to the planner.
    The planner specifies which specific forecasting tool to call in the task.
    
    Available Tools (exposed to planner):
    - predict_stock_movement: Predict stock price movement based on multiple data sources
    - analyze_sentiment: Analyze sentiment from news and social media
    - technical_forecast: Technical analysis-based price prediction
    
    The agent uses data from other agents (company news, analyst recommendations,
    technical indicators) to make informed predictions.
    """
    
    SYSTEM_PROMPT = """You are an AI Agent specialized in stock price forecasting and prediction.

Your role is to:
1. Analyze multiple data sources (news, analyst recommendations, technical indicators, fundamentals)
2. Identify positive developments and potential concerns
3. Make data-driven predictions about stock price movements
4. Provide clear rationale for your predictions

You should:
- Be conservative and realistic in predictions
- Clearly state assumptions and confidence levels
- Identify key factors driving the prediction
- Provide percentage ranges (e.g., up 2-5%, down 1-3%)
- Focus on short-term (1 week) and medium-term (1 month) predictions

Be data-driven, factual, and transparent about uncertainty."""

    def __init__(
        self,
        name: str = "ForecasterAgent",
        description: str = "Stock price forecasting and prediction specialist",
        chat_client: Any = None,
        model: str = "gpt-4o"
    ):
        """Initialize Forecaster Agent."""
        logger.info(
            "ForecasterAgent.__init__ called",
            name=name,
            has_chat_client=chat_client is not None,
            model=model
        )
        
        super().__init__(name=name, description=description)
        
        # Store custom attributes
        self.chat_client = chat_client
        self.model = model
        self.system_prompt = self.SYSTEM_PROMPT
        
        logger.info(
            "ForecasterAgent initialized",
            agent_name=self.name
        )
    
    @staticmethod
    def get_tools_info() -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available forecasting tools.
        This is exposed to the planner so it knows exactly what tools are available.
        
        Returns dict with tool names as keys and metadata as values.
        """
        return {
            "predict_stock_movement": {
                "description": "Predict stock price movement for next week based on news sentiment, analyst recommendations, and market trends. Provides percentage prediction with supporting rationale.",
                "parameters": "ticker (string), analysis_data (dict with news, recommendations, etc.)",
                "source": "LLM Analysis"
            },
            "analyze_positive_developments": {
                "description": "Identify and analyze 2-4 most important positive developments from company news and data. Focus on factors that could drive stock price up.",
                "parameters": "ticker (string), news_data (string), recommendations (string)",
                "source": "LLM Analysis"
            },
            "analyze_potential_concerns": {
                "description": "Identify and analyze 2-4 most important potential concerns from company news and data. Focus on risk factors that could drive stock price down.",
                "parameters": "ticker (string), news_data (string), recommendations (string)",
                "source": "LLM Analysis"
            },
            "technical_forecast": {
                "description": "Technical analysis-based price prediction using chart patterns, indicators, and price trends",
                "parameters": "ticker (string), technical_data (dict)",
                "source": "Technical Analysis"
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
        Execute forecasting task (MAF required method).
        
        Args:
            messages: The message(s) to process
            thread: The conversation thread (optional)
            **kwargs: Additional context (ticker, context dict, analysis_data, etc.)
            
        Returns:
            AgentRunResponse containing the forecast analysis
        """
        # Normalize input messages to a list
        normalized_messages = self._normalize_messages(messages)
        
        if not normalized_messages:
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text="Hello! I'm a forecasting agent. Please provide analysis data for prediction.")]
            )
            return AgentRunResponse(messages=[response_message])
        
        # Get context from kwargs
        context = kwargs.get("context", {})
        ticker = context.get("ticker", kwargs.get("ticker"))
        
        # Log what we received
        logger.info(
            "ForecasterAgent.run() - checking sources",
            ticker=ticker,
            context_keys=list(context.keys()),
            all_kwargs_keys=list(kwargs.keys())
        )
        
        # Extract task from last message
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        
        logger.info(
            "ForecasterAgent starting",
            task=task[:200],
            ticker=ticker,
            context_keys=list(context.keys())
        )
        
        # Determine which forecasting tool to use based on the task
        tool_name = self._determine_tool_from_task(task)
        
        logger.info(f"Using forecasting tool: {tool_name}")
        
        # Build analysis prompt based on tool and available data
        prompt = self._build_forecast_prompt(task, ticker, tool_name, context)
        
        logger.debug(
            "ForecasterAgent prompt built",
            ticker=ticker,
            tool=tool_name,
            prompt_length=len(prompt)
        )
        
        # Execute with Azure OpenAI
        try:
            logger.info(f"ForecasterAgent calling LLM for {ticker}")
            response = await self._execute_llm(prompt)
            
            logger.info(
                f"ForecasterAgent LLM response received",
                ticker=ticker,
                response_length=len(response) if response else 0
            )
            
            result_text = f"""## Forecast Analysis for {ticker}

{response}

---
*Forecast provided by ForecasterAgent using {tool_name}*
"""
            
            # Track artifacts
            artifacts = context.get("artifacts", [])
            artifacts.append({
                "type": "forecast",
                "ticker": ticker,
                "tool": tool_name,
                "content": response,
                "agent": self.name
            })
            context["artifacts"] = artifacts
            
            logger.info(
                f"ForecasterAgent completed successfully",
                ticker=ticker,
                tool=tool_name,
                artifacts_count=len(artifacts)
            )
            
            return self._create_response(result_text)
            
        except Exception as e:
            logger.error("Forecaster agent execution failed", error=str(e), ticker=ticker)
            return self._create_response(
                f"Forecast analysis failed for {ticker}: {str(e)}"
            )
    
    def _determine_tool_from_task(self, task: str) -> str:
        """Determine which forecasting tool to use based on the task."""
        task_lower = task.lower()
        
        if "positive development" in task_lower or "positive factor" in task_lower:
            return "analyze_positive_developments"
        elif "concern" in task_lower or "risk" in task_lower or "negative" in task_lower:
            return "analyze_potential_concerns"
        elif "predict" in task_lower or "forecast" in task_lower or "movement" in task_lower or "price" in task_lower:
            return "predict_stock_movement"
        elif "technical" in task_lower:
            return "technical_forecast"
        else:
            # Default to prediction
            return "predict_stock_movement"
    
    def _build_forecast_prompt(
        self,
        task: str,
        ticker: str,
        tool_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Build forecasting prompt based on the specific tool and available data.
        
        For synthesis agents like Forecaster, uses session_context (ALL previous steps).
        Falls back to dependency_artifacts for backward compatibility.
        """
        # First priority: session_context (comprehensive context for synthesis agents)
        session_context = context.get("session_context", [])
        
        # Fallback: dependency_artifacts (explicit dependencies only)
        if not session_context:
            session_context = context.get("dependency_artifacts", [])
        
        # Further fallback: legacy artifacts list
        if not session_context:
            session_context = context.get("artifacts", [])
        
        logger.info(
            "Building forecast prompt with context",
            num_artifacts=len(session_context),
            tool_name=tool_name,
            context_keys=list(context.keys()),
            source="session_context" if context.get("session_context") else "dependency_artifacts" if context.get("dependency_artifacts") else "legacy_artifacts"
        )
        
        # Log each artifact for debugging
        for idx, artifact in enumerate(session_context):
            logger.info(
                f"Artifact {idx + 1}",
                step_order=artifact.get("step_order"),
                type=artifact.get("type"),
                agent=artifact.get("agent"),
                tools=artifact.get("tools"),
                action_preview=artifact.get("action", "")[:100] if artifact.get("action") else "",
                content_preview=artifact.get("content", "")[:200] if artifact.get("content") else "No content"
            )
        
        # Extract data from ALL previous steps
        news_data = None
        recommendations_data = None
        stock_data = None
        company_data = None
        fundamentals_data = None
        
        for artifact in session_context:
            content = artifact.get("content", "")
            artifact_type = artifact.get("type", "")
            tools_used = artifact.get("tools", [])
            agent = artifact.get("agent", "")
            step_order = artifact.get("step_order", 0)
            
            logger.info(
                f"Processing artifact from step {step_order}",
                type=artifact_type,
                agent=agent,
                tools=tools_used,
                has_content=bool(content)
            )
            
            # Check for news data
            if "get_yahoo_finance_news" in tools_used or "news" in agent.lower():
                news_data = content
                logger.info(f"✓ Found news data from step {step_order} ({agent})")
            
            # Check for recommendations
            if "get_recommendations" in tools_used:
                recommendations_data = content
                logger.info(f"✓ Found recommendations data from step {step_order} ({agent})")
            
            # Check for stock/company data
            if "get_stock_info" in tools_used or "company" in agent.lower():
                if not company_data:  # Take first occurrence
                    company_data = content
                    logger.info(f"✓ Found company data from step {step_order} ({agent})")
            
            # Check for fundamentals
            if "fundamental" in agent.lower() or "earnings" in agent.lower():
                fundamentals_data = content
                logger.info(f"✓ Found fundamentals data from step {step_order} ({agent})")
        
        logger.info(
            "Data extraction summary from session context",
            has_news=bool(news_data),
            has_recommendations=bool(recommendations_data),
            has_company_data=bool(company_data),
            has_stock_data=bool(stock_data),
            has_fundamentals=bool(fundamentals_data),
            total_artifacts=len(session_context)
        )
        
        # Build prompt based on the tool
        if tool_name == "analyze_positive_developments":
            prompt = f"""Task: {task}

Stock Ticker: {ticker}

## Available Data from Previous Analysis:

### Company Information:
{company_data or 'No company data available'}

### Company News:
{news_data or 'No news data available - waiting for news gathering step'}

### Analyst Recommendations:
{recommendations_data or 'No analyst recommendations available'}

### Fundamentals:
{fundamentals_data or 'No fundamentals data available'}

---

Based on the data above, identify and analyze the 2-4 MOST IMPORTANT positive developments or factors that could positively impact {ticker}'s stock price.

For each positive factor:
1. State the factor clearly and concisely
2. Explain why it's significant
3. Assess its potential impact on stock price

Keep each factor to 2-3 sentences. Focus on the most material positive developments."""
        
        elif tool_name == "analyze_potential_concerns":
            prompt = f"""Task: {task}

Stock Ticker: {ticker}

## Available Data from Previous Analysis:

### Company Information:
{company_data or 'No company data available'}

### Company News:
{news_data or 'No news data available - waiting for news gathering step'}

### Analyst Recommendations:
{recommendations_data or 'No analyst recommendations available'}

---

Based on the data above, identify and analyze the 2-4 MOST IMPORTANT potential concerns or risk factors that could negatively impact {ticker}'s stock price.

For each concern:
1. State the concern clearly and concisely
2. Explain why it's a risk
3. Assess its potential impact on stock price

Keep each concern to 2-3 sentences. Focus on the most material risks."""
        
        elif tool_name == "predict_stock_movement":
            prompt = f"""Task: {task}

Stock Ticker: {ticker}

## Available Analysis Data from Previous Steps:

### Company Information:
{company_data or 'No company data available'}

### Company News:
{news_data or 'No news data available'}

### Analyst Recommendations:
{recommendations_data or 'No analyst recommendations available'}

### Fundamentals:
{fundamentals_data or 'No fundamentals data available'}

### Stock Data:
{stock_data or 'No stock data available'}

---

Based on all the data above, make a rough prediction for {ticker}'s stock price movement for the NEXT WEEK.

Your prediction should include:
1. Direction: up or down
2. Magnitude: percentage range (e.g., up 2-5%, down 1-3%)
3. Key factors: 2-3 main reasons supporting your prediction
4. Confidence level: high/medium/low
5. Summary: 2-3 sentence rationale

Be realistic and conservative. Focus on short-term (1 week) movement based on the available data."""
        
        else:
            # Default prompt
            prompt = f"""Task: {task}

Stock Ticker: {ticker}

Available data from previous analysis steps:
{json.dumps(session_context, indent=2) if session_context else 'No prior analysis data'}

---

Provide your forecast analysis based on the task requirements and available data."""
        
        return prompt
    
    async def _execute_llm(self, prompt: str) -> str:
        """Execute LLM call using agent_framework's AzureOpenAIChatClient."""
        if not self.chat_client:
            logger.warning("No chat client configured, returning simulated response")
            return f"[Simulated Forecast Analysis]\n{prompt}"
        
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
            temperature=0.5,  # Slightly higher for creative forecasting
            max_tokens=1500
        )
        
        duration = time.time() - start_time
        logger.info(
            "Azure OpenAI response received",
            model=self.model,
            duration_seconds=round(duration, 2),
            response_length=len(response.text) if response.text else 0
        )
        
        return response.text
    
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
        """
        response = await self.run(messages, thread=thread, **kwargs)
        
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
            "ForecasterAgent.process() called",
            task=task[:100] if task else "None",
            context_keys=list(context.keys()),
            ticker=context.get('ticker'),
            agent_name=self.name
        )
        
        response = await self.run(messages=task, thread=None, ticker=context.get('ticker'), context=context)
        result = response.messages[-1].text if response.messages else ""
        logger.info(
            "ForecasterAgent.process() completed",
            result_length=len(result),
            agent_name=self.name
        )
        return result

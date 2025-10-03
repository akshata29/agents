"""
Technicals Agent Adapter

Wraps finagentsk Technical Analysis Agent capabilities with real data provider integration.
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

from helpers.yfutils import YFUtils

logger = structlog.get_logger(__name__)


class TechnicalsAgent(BaseAgent):
    """
    Technical Analysis Agent - Chart patterns and indicators specialist.
    
    Capabilities:
    - Technical indicator calculations (EMA, RSI, MACD, Bollinger Bands, etc.)
    - Candlestick pattern detection
    - Support/resistance level identification
    - Trend analysis
    - Overall technical rating (buy/sell/hold)
    
    Based on finagentsk TechnicalAnalysisAgent definition.
    """
    
    SYSTEM_PROMPT = """You are a specialized Technical Analysis Agent with expertise in 
historical stock price data, technical indicators, and chart pattern recognition.

Your capabilities include:
1. Calculate and interpret multiple technical indicators:
   - EMA Crossover (short-term vs long-term trends)
   - RSI (overbought/oversold conditions)
   - MACD (momentum and trend changes)
   - Bollinger Bands (volatility and price extremes)
   - Stochastics, ATR, ADX
2. Detect candlestick patterns (hammer, engulfing, doji, etc.)
3. Identify support and resistance levels
4. Assess trend strength and direction
5. Provide overall technical rating with confidence score

Provide JSON-structured output with clear signals and an aggregated rating.
Be data-driven and explain the reasoning behind signals."""

    def __init__(
        self,
        name: str = "TechnicalsAgent",
        description: str = "Technical analysis and charting specialist",
        azure_client: Any = None,
        model: str = "gpt-4o",
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """Initialize Technicals Agent."""
        super().__init__(name=name, description=description)
        self.azure_client = azure_client
        self.model = model
        self.tools = tools or []
        self.system_prompt = self.SYSTEM_PROMPT
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "calculate_technical_indicators",
            "detect_candlestick_patterns",
            "identify_support_resistance",
            "analyze_trend",
            "generate_technical_rating",
            "analyze_volume",
            "assess_momentum"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute technical analysis (MAF required method)."""
        normalized_messages = self._normalize_messages(messages)
        if not normalized_messages:
            return AgentRunResponse(messages=[ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text="Hello! I'm a technical analysis agent.")])])
        
        context = kwargs.get("context", {})
        ticker = context.get("ticker", kwargs.get("ticker"))
        last_message = normalized_messages[-1]
        task = last_message.text if hasattr(last_message, 'text') else str(last_message)
        context = kwargs.get("context", {})
        ticker = context.get("ticker", kwargs.get("ticker"))
        days = context.get("days", kwargs.get("days", 365))
        
        logger.info(
            "TechnicalsAgent starting",
            task=task,
            ticker=ticker,
            days=days,
            context_keys=list(context.keys())
        )
        
        # Fetch real technical analysis data
        logger.info(f"Calculating technical indicators for {ticker}")
        technical_data = await self._fetch_technical_data(ticker, days)
        
        # Build analysis prompt with real data
        prompt = self._build_analysis_prompt_with_data(task, ticker, days, technical_data, context)
        
        logger.debug(
            "TechnicalsAgent prompt built with indicators",
            ticker=ticker,
            prompt_length=len(prompt),
            has_indicators=bool(technical_data.get("indicators")),
            overall_rating=technical_data.get("signals", {}).get("overall_rating", "N/A")
        )
        
        try:
            logger.info(f"TechnicalsAgent calling LLM for {ticker}")
            response = await self._execute_llm(prompt)
            
            logger.info(
                f"TechnicalsAgent LLM response received",
                ticker=ticker,
                response_length=len(response) if response else 0
            )
            
            result_text = f"""## Technical Analysis for {ticker}

{response}

---
*Technical analysis by TechnicalsAgent based on real price data and calculated indicators*
"""
            
            # Track artifacts
            artifacts = context.get("artifacts", [])
            artifacts.append({
                "type": "technical_analysis",
                "title": f"Technical Analysis - {ticker}",
                "content": response,
                "metadata": {
                    "ticker": ticker,
                    "days": days,
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
                f"TechnicalsAgent error analyzing {ticker}",
                error=str(e),
                ticker=ticker
            )
            return AgentRunResponse(
                content=f"Error performing technical analysis for {ticker}: {str(e)}",
                context=context
            )
    
    async def _fetch_technical_data(
        self,
        ticker: str,
        days: int = 365
    ) -> Dict[str, Any]:
        """
        Fetch real technical analysis data using YFUtils.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days of historical data
            
        Returns:
            Dictionary with technical indicators and signals
        """
        try:
            logger.info(f"Running technical analysis for {ticker} ({days} days)")
            
            # Run comprehensive technical analysis
            technical_data = YFUtils.run_technical_analysis(ticker, days)
            
            if "error" in technical_data:
                logger.warning(f"Technical analysis error for {ticker}: {technical_data['error']}")
            else:
                logger.info(
                    f"Technical analysis completed successfully",
                    ticker=ticker,
                    overall_rating=technical_data.get("signals", {}).get("overall_rating", "N/A"),
                    num_patterns=len(technical_data.get("candlestick_patterns", []))
                )
            
            return technical_data
            
        except Exception as e:
            logger.error(
                f"Error fetching technical data for {ticker}",
                error=str(e),
                ticker=ticker
            )
            return {
                "ticker_symbol": ticker,
                "error": str(e),
                "analysis": {}
            }
    
    def _build_analysis_prompt_with_data(
        self,
        task: str,
        ticker: str,
        days: int,
        technical_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Build analysis prompt with real technical indicators embedded.
        
        Args:
            task: User's analysis request
            ticker: Stock ticker symbol
            days: Number of days analyzed
            technical_data: Real technical data from YFUtils
            context: Additional context
            
        Returns:
            Formatted prompt with technical data
        """
        if "error" in technical_data:
            prompt = f"""{self.system_prompt}

User Task: {task}

Company: {ticker}
Period: {days} days

ERROR: {technical_data['error']}

Please inform the user that technical analysis data is not available for {ticker}.
"""
            return prompt
        
        indicators = technical_data.get("indicators", {})
        patterns = technical_data.get("candlestick_patterns", [])
        signals = technical_data.get("signals", {})
        
        prompt = f"""{self.system_prompt}

User Task: {task}

## Company Information
Ticker: {ticker}
Analysis Period: {days} days
Analysis Date: {technical_data.get('analysis_date', 'N/A')}
Current Price: ${indicators.get('close_price', 'N/A')}

"""
        
        # Add technical indicators
        if indicators:
            ema = indicators.get("ema", {})
            rsi = indicators.get("rsi", {})
            macd = indicators.get("macd", {})
            bb = indicators.get("bollinger_bands", {})
            stoch = indicators.get("stochastics", {})
            atr = indicators.get("atr", {})
            adx = indicators.get("adx", {})
            
            prompt += f"""## Technical Indicators

### Moving Averages (EMA)
- Short EMA (12): ${ema.get('short_ema', 'N/A'):.2f}
- Long EMA (26): ${ema.get('long_ema', 'N/A'):.2f}
- Signal: **{ema.get('signal', 'N/A').upper()}**

### RSI (Relative Strength Index)
- Value: {rsi.get('value', 'N/A'):.2f}
- Signal: **{rsi.get('signal', 'N/A').upper()}**
- Interpretation: <70 = Normal, >70 = Overbought, <30 = Oversold

### MACD (Moving Average Convergence Divergence)
- MACD Line: {macd.get('value', 'N/A'):.4f}
- Signal Line: {macd.get('signal_line', 'N/A'):.4f}
- Histogram: {macd.get('histogram', 'N/A'):.4f}
- Trend: **{macd.get('trend', 'N/A').upper()}**

### Bollinger Bands
- Upper Band: ${bb.get('upper', 'N/A'):.2f}
- Middle Band: ${bb.get('middle', 'N/A'):.2f}
- Lower Band: ${bb.get('lower', 'N/A'):.2f}
- Signal: **{bb.get('signal', 'N/A').upper()}**
- Interpretation: Price near upper = overbought, near lower = oversold

### Stochastics
- %K: {stoch.get('k', 'N/A'):.2f}
- %D: {stoch.get('d', 'N/A'):.2f}
- Signal: **{stoch.get('signal', 'N/A').upper()}**
- Interpretation: >80 = Overbought, <20 = Oversold

### ATR (Average True Range)
- Value: ${atr.get('value', 'N/A'):.2f}
- Description: Volatility measure - higher = more volatile

### ADX (Average Directional Index)
- ADX Value: {adx.get('value', 'N/A'):.2f}
- +DI: {adx.get('plus_di', 'N/A'):.2f}
- -DI: {adx.get('minus_di', 'N/A'):.2f}
- Trend Strength: **{adx.get('strength', 'N/A').upper()}**
- Direction: **{adx.get('direction', 'N/A').upper()}**
- Interpretation: ADX >25 = strong trend, <20 = weak/sideways

"""
        
        # Add candlestick patterns
        if patterns:
            prompt += f"""## Candlestick Patterns Detected

"""
            for pattern in patterns:
                prompt += f"""- **{pattern.get('pattern', 'Unknown').replace('_', ' ').title()}**
  - Type: {pattern.get('type', 'N/A').replace('_', ' ').title()}
  - {pattern.get('description', 'N/A')}

"""
        else:
            prompt += f"""## Candlestick Patterns Detected
No significant candlestick patterns detected in recent trading.

"""
        
        # Add overall signals summary
        if signals:
            prompt += f"""## Overall Technical Signals

- **Bullish Signals**: {signals.get('bullish_count', 0)}
- **Bearish Signals**: {signals.get('bearish_count', 0)}
- **Neutral Signals**: {signals.get('neutral_count', 0)}
- **Overall Rating**: **{signals.get('overall_rating', 'N/A').replace('_', ' ').upper()}**
- **Confidence Score**: {signals.get('confidence', 0):.2%}

"""
        
        prompt += f"""---

Based on the REAL technical indicators and price data above, please provide a comprehensive technical analysis addressing the user's task.

Your analysis should include:

1. **Trend Analysis**
   - Current trend direction (bullish/bearish/sideways)
   - Trend strength using ADX
   - EMA crossover signals and momentum

2. **Momentum Assessment**
   - RSI overbought/oversold levels
   - MACD momentum and divergence
   - Stochastics confirmation

3. **Volatility & Risk**
   - Bollinger Bands positioning
   - ATR volatility levels
   - Price extremes and reversals

4. **Pattern Recognition**
   - Candlestick patterns significance
   - Reversal or continuation signals
   - Pattern confirmation with indicators

5. **Trading Signals**
   - Entry/exit points based on indicators
   - Support and resistance levels
   - Risk/reward assessment

6. **Overall Recommendation**
   - Technical rating (buy/sell/hold)
   - Confidence level
   - Key risks and considerations

Be specific with the actual numbers from the data above. Explain why certain indicators support or contradict each other.
"""
        
        return prompt
    
    async def _execute_llm(self, prompt: str) -> str:
        """Execute LLM call."""
        if not self.azure_client:
            return f"[Simulated Technical Analysis]\n{prompt}"
        
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
        response = await self.run(messages=task, thread=None, context=context)
        return response.messages[-1].text if response.messages else ""

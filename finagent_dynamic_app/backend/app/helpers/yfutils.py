"""
Yahoo Finance Utilities

Helper functions to fetch financial data from Yahoo Finance using yfinance.
"""

import yfinance as yf
import pandas as pd
from typing import Annotated, Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class YFUtils:
    """Yahoo Finance utilities."""
    
    @staticmethod
    def get_stock_info(ticker_symbol: str) -> dict:
        """Get stock information."""
        try:
            ticker = yf.Ticker(ticker_symbol)
            return ticker.info
        except Exception as e:
            logger.error(f"Error fetching stock info", ticker=ticker_symbol, error=str(e))
            return {}
    
    @staticmethod
    def get_stock_data(ticker_symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get historical stock price data."""
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(start=start_date, end=end_date)
            return hist
        except Exception as e:
            logger.error(f"Error fetching stock data", ticker=ticker_symbol, error=str(e))
            return pd.DataFrame()
    
    @staticmethod
    def get_analyst_recommendations(ticker_symbol: str) -> str:
        """Get analyst recommendations."""
        try:
            ticker = yf.Ticker(ticker_symbol)
            recommendations = ticker.recommendations
            
            if recommendations is None or recommendations.empty:
                return "No analyst recommendations available"
            
            # Get the latest recommendations (last 30 days)
            recent = recommendations.tail(10)
            
            # Count recommendation types
            if 'To Grade' in recent.columns:
                counts = recent['To Grade'].value_counts()
                summary = ", ".join([f"{grade}: {count}" for grade, count in counts.items()])
                return f"Recent analyst recommendations: {summary}"
            
            return "Analyst recommendations data available but format not standard"
            
        except Exception as e:
            logger.error(f"Error fetching analyst recommendations", ticker=ticker_symbol, error=str(e))
            return f"Error: {str(e)}"
    
    @staticmethod
    def get_company_news(ticker_symbol: str, start_date: str, end_date: str, max_news: int = 10) -> pd.DataFrame:
        """Get company news from Yahoo Finance."""
        try:
            ticker = yf.Ticker(ticker_symbol)
            news = ticker.news
            
            if not news:
                return pd.DataFrame()
            
            news_list = [
                {
                    "date": datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime("%Y-%m-%d"),
                    "headline": n.get('title', ''),
                    "summary": n.get('summary', '')[:200]  # Truncate
                }
                for n in news[:max_news]
            ]
            
            return pd.DataFrame(news_list)
            
        except Exception as e:
            logger.error(f"Error fetching company news", ticker=ticker_symbol, error=str(e))
            return pd.DataFrame()
    
    @staticmethod
    def run_technical_analysis(ticker_symbol: str, days: int = 365) -> Dict[str, Any]:
        """
        Perform comprehensive technical analysis using the ta library.
        
        Calculates:
        - EMA crossover (short/long)
        - RSI (Relative Strength Index)
        - MACD (Moving Average Convergence Divergence)
        - Bollinger Bands
        - Stochastics
        - ATR (Average True Range)
        - ADX (Average Directional Index)
        - Simple candlestick patterns
        
        Args:
            ticker_symbol: Stock ticker symbol
            days: Number of days of historical data (default 365)
            
        Returns:
            Dictionary with comprehensive technical analysis
        """
        try:
            # Import ta library for technical indicators
            import ta
            
            # Fetch historical price data
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            df = YFUtils.get_stock_data(ticker_symbol, start_date, end_date)
            
            if df.empty:
                return {
                    "ticker_symbol": ticker_symbol,
                    "error": "No data found",
                    "analysis": {}
                }
            
            # Ensure data is sorted by date
            df.sort_index(ascending=True, inplace=True)
            
            # Initialize result structure
            result = {
                "ticker_symbol": ticker_symbol,
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "data_period": f"{days} days",
                "indicators": {},
                "candlestick_patterns": [],
                "signals": {}
            }
            
            # Calculate technical indicators
            short_window = 12
            long_window = 26
            
            # A) EMA (Exponential Moving Average)
            df["EMA_Short"] = ta.trend.EMAIndicator(close=df["Close"], window=short_window).ema_indicator()
            df["EMA_Long"] = ta.trend.EMAIndicator(close=df["Close"], window=long_window).ema_indicator()
            
            # B) RSI (Relative Strength Index)
            df["RSI"] = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
            
            # C) MACD
            macd_indicator = ta.trend.MACD(close=df["Close"], window_slow=26, window_fast=12, window_sign=9)
            df["MACD"] = macd_indicator.macd()
            df["MACD_Signal"] = macd_indicator.macd_signal()
            df["MACD_Hist"] = macd_indicator.macd_diff()
            
            # D) Bollinger Bands
            bollinger = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
            df["BB_High"] = bollinger.bollinger_hband()
            df["BB_Low"] = bollinger.bollinger_lband()
            df["BB_Mid"] = bollinger.bollinger_mavg()
            
            # E) Stochastics
            stoch = ta.momentum.StochasticOscillator(
                high=df["High"], low=df["Low"], close=df["Close"], 
                window=14, smooth_window=3
            )
            df["Stoch_%K"] = stoch.stoch()
            df["Stoch_%D"] = stoch.stoch_signal()
            
            # F) ATR (Average True Range)
            atr_indicator = ta.volatility.AverageTrueRange(
                high=df["High"], low=df["Low"], close=df["Close"], window=14
            )
            df["ATR"] = atr_indicator.average_true_range()
            
            # G) ADX (Average Directional Index)
            adx_indicator = ta.trend.ADXIndicator(
                high=df["High"], low=df["Low"], close=df["Close"], window=14
            )
            df["ADX"] = adx_indicator.adx()
            df["+DI"] = adx_indicator.adx_pos()
            df["-DI"] = adx_indicator.adx_neg()
            
            # Get latest and previous data points
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else None
            
            # Analyze indicators and generate signals
            
            # EMA Signal
            ema_signal = "neutral"
            if previous is not None:
                was_short_below = previous["EMA_Short"] < previous["EMA_Long"]
                is_short_above = latest["EMA_Short"] > latest["EMA_Long"]
                was_short_above = previous["EMA_Short"] >= previous["EMA_Long"]
                is_short_below = latest["EMA_Short"] < latest["EMA_Long"]
                
                if was_short_below and is_short_above:
                    ema_signal = "bullish_crossover"
                elif was_short_above and is_short_below:
                    ema_signal = "bearish_crossover"
                elif is_short_above:
                    ema_signal = "bullish"
                else:
                    ema_signal = "bearish"
            
            # RSI Signal
            rsi_value = latest["RSI"]
            if rsi_value >= 70:
                rsi_signal = "overbought"
            elif rsi_value <= 30:
                rsi_signal = "oversold"
            else:
                rsi_signal = "neutral"
            
            # MACD Signal
            macd_value = latest["MACD"]
            macd_signal_line = latest["MACD_Signal"]
            if macd_value > macd_signal_line:
                macd_trend = "bullish"
            elif macd_value < macd_signal_line:
                macd_trend = "bearish"
            else:
                macd_trend = "neutral"
            
            # Bollinger Bands Signal
            close_price = latest["Close"]
            if close_price > latest["BB_High"]:
                bb_signal = "overbought"
            elif close_price < latest["BB_Low"]:
                bb_signal = "oversold"
            else:
                bb_signal = "neutral"
            
            # Stochastics Signal
            stoch_k = latest["Stoch_%K"]
            if stoch_k >= 80:
                stoch_signal = "overbought"
            elif stoch_k <= 20:
                stoch_signal = "oversold"
            else:
                stoch_signal = "neutral"
            
            # ADX Trend Strength
            adx_value = latest["ADX"]
            plus_di = latest["+DI"]
            minus_di = latest["-DI"]
            
            if adx_value > 25:
                adx_strength = "strong_trend"
            elif adx_value > 20:
                adx_strength = "moderate_trend"
            else:
                adx_strength = "weak_or_sideways"
            
            if plus_di > minus_di:
                adx_direction = "bullish"
            elif plus_di < minus_di:
                adx_direction = "bearish"
            else:
                adx_direction = "neutral"
            
            # Populate indicators
            result["indicators"] = {
                "close_price": float(close_price),
                "ema": {
                    "short_ema": float(latest["EMA_Short"]),
                    "long_ema": float(latest["EMA_Long"]),
                    "signal": ema_signal
                },
                "rsi": {
                    "value": float(rsi_value),
                    "signal": rsi_signal
                },
                "macd": {
                    "value": float(macd_value),
                    "signal_line": float(macd_signal_line),
                    "histogram": float(latest["MACD_Hist"]),
                    "trend": macd_trend
                },
                "bollinger_bands": {
                    "upper": float(latest["BB_High"]),
                    "middle": float(latest["BB_Mid"]),
                    "lower": float(latest["BB_Low"]),
                    "signal": bb_signal
                },
                "stochastics": {
                    "k": float(stoch_k),
                    "d": float(latest["Stoch_%D"]),
                    "signal": stoch_signal
                },
                "atr": {
                    "value": float(latest["ATR"]),
                    "description": "Average True Range - volatility measure"
                },
                "adx": {
                    "value": float(adx_value),
                    "plus_di": float(plus_di),
                    "minus_di": float(minus_di),
                    "strength": adx_strength,
                    "direction": adx_direction
                }
            }
            
            # Simple candlestick pattern detection
            patterns_detected = []
            
            # Hammer pattern
            candle_body = abs(latest["Close"] - latest["Open"])
            lower_wick = min(latest["Close"], latest["Open"]) - latest["Low"]
            upper_wick = latest["High"] - max(latest["Close"], latest["Open"])
            
            if lower_wick > 2 * candle_body and upper_wick < 0.3 * candle_body:
                patterns_detected.append({
                    "pattern": "hammer",
                    "type": "bullish_reversal",
                    "description": "Potential bullish reversal signal"
                })
            
            # Bullish Engulfing
            if previous is not None:
                prev_body = abs(previous["Close"] - previous["Open"])
                curr_body = abs(latest["Close"] - latest["Open"])
                prev_bearish = previous["Close"] < previous["Open"]
                curr_bullish = latest["Close"] > latest["Open"]
                
                if (prev_bearish and curr_bullish and 
                    curr_body > prev_body and 
                    latest["Close"] > previous["Open"]):
                    patterns_detected.append({
                        "pattern": "bullish_engulfing",
                        "type": "bullish_reversal",
                        "description": "Strong bullish reversal signal"
                    })
            
            result["candlestick_patterns"] = patterns_detected
            
            # Overall signal aggregation
            bullish_signals = 0
            bearish_signals = 0
            total_signals = 0
            
            signals = [
                ema_signal,
                rsi_signal,
                macd_trend,
                bb_signal,
                stoch_signal,
                adx_direction
            ]
            
            for signal in signals:
                total_signals += 1
                if "bullish" in signal or signal == "oversold":
                    bullish_signals += 1
                elif "bearish" in signal or signal == "overbought":
                    bearish_signals += 1
            
            # Calculate overall rating
            if bullish_signals > bearish_signals * 1.5:
                overall_rating = "strong_buy"
            elif bullish_signals > bearish_signals:
                overall_rating = "buy"
            elif bearish_signals > bullish_signals * 1.5:
                overall_rating = "strong_sell"
            elif bearish_signals > bullish_signals:
                overall_rating = "sell"
            else:
                overall_rating = "hold"
            
            result["signals"] = {
                "bullish_count": bullish_signals,
                "bearish_count": bearish_signals,
                "neutral_count": total_signals - bullish_signals - bearish_signals,
                "overall_rating": overall_rating,
                "confidence": abs(bullish_signals - bearish_signals) / total_signals if total_signals > 0 else 0
            }
            
            logger.info(
                f"Technical analysis completed for {ticker_symbol}",
                overall_rating=overall_rating,
                bullish_signals=bullish_signals,
                bearish_signals=bearish_signals
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing technical analysis", ticker=ticker_symbol, error=str(e))
            return {
                "ticker_symbol": ticker_symbol,
                "error": str(e),
                "analysis": {}
            }

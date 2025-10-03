"""
Financial Modeling Prep (FMP) API Utilities

Helper functions to fetch financial data from FMP API.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Annotated, Optional
import structlog

logger = structlog.get_logger(__name__)


class FMPUtils:
    """Financial Modeling Prep API utilities."""
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
    
    def get_company_profile(self, ticker_symbol: str) -> str:
        """Get company profile information."""
        url = f"{self.base_url}/profile/{ticker_symbol}?apikey={self.api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or len(data) == 0:
                return f"No profile found for {ticker_symbol}"
            
            company = data[0]
            formatted_str = (
                f"[Company Introduction]:\n\n"
                f"{company.get('companyName', ticker_symbol)} is a leading entity in the {company.get('sector', 'N/A')} sector. "
                f"Incorporated and publicly traded since {company.get('ipoDate', 'N/A')}, the company has established its reputation as "
                f"one of the key players in the market. As of today, {company.get('companyName', ticker_symbol)} has a market capitalization "
                f"of {company.get('mktCap', 0) / 1e9:.2f}B in {company.get('currency', 'USD')}.\n\n"
                f"{company.get('companyName', ticker_symbol)} operates primarily in {company.get('country', 'N/A')}, "
                f"trading under the ticker {company.get('symbol', ticker_symbol)} on the {company.get('exchange', 'N/A')}. "
                f"As a dominant force in the {company.get('industry', 'N/A')} space, the company continues to innovate and drive "
                f"progress within the industry. The detailed description of the company's business and products: {company.get('description', 'N/A')}"
            )
            
            return formatted_str
            
        except Exception as e:
            logger.error(f"Error fetching company profile", ticker=ticker_symbol, error=str(e))
            return f"Error fetching company profile: {str(e)}"
    
    def get_financial_metrics(self, ticker_symbol: str, years: int = 4) -> pd.DataFrame:
        """Get financial metrics for the last N years."""
        df = pd.DataFrame()
        
        try:
            income_url = f"{self.base_url}/income-statement/{ticker_symbol}?limit={years}&apikey={self.api_key}"
            ratios_url = f"{self.base_url}/ratios/{ticker_symbol}?limit={years}&apikey={self.api_key}"
            metrics_url = f"{self.base_url}/key-metrics/{ticker_symbol}?limit={years}&apikey={self.api_key}"
            
            income_data = requests.get(income_url, timeout=10).json()
            ratios_data = requests.get(ratios_url, timeout=10).json()
            metrics_data = requests.get(metrics_url, timeout=10).json()
            
            for year_offset in range(min(years, len(income_data))):
                year = income_data[year_offset]["date"][:4]
                metrics_dict = {
                    "Revenue": round(income_data[year_offset]["revenue"] / 1e6),
                    "Gross Margin": round(income_data[year_offset]["grossProfit"] / income_data[year_offset]["revenue"], 2),
                    "EBITDA": round(income_data[year_offset]["ebitda"] / 1e6),
                    "Net Income": round(income_data[year_offset]["netIncome"] / 1e6),
                    "EPS": round(income_data[year_offset]["eps"], 2),
                    "PE Ratio": round(ratios_data[year_offset]["priceEarningsRatio"], 2),
                    "PB Ratio": round(metrics_data[year_offset]["pbRatio"], 2),
                }
                df[year] = pd.Series(metrics_dict)
            
            df = df.sort_index(axis=1)
            return df
            
        except Exception as e:
            logger.error(f"Error fetching financial metrics", ticker=ticker_symbol, error=str(e))
            return pd.DataFrame()
    
    def get_company_news(self, ticker_symbol: str, start_date: str, end_date: str, max_news: int = 10) -> pd.DataFrame:
        """Get company news."""
        url = f"{self.base_url}/stock_news?tickers={ticker_symbol}&apikey={self.api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return pd.DataFrame()
            
            news = [
                {
                    "date": n.get("publishedDate", ""),
                    "headline": n.get("title", ""),
                    "summary": n.get("text", "")[:200]  # Truncate summary
                }
                for n in data[:max_news]
            ]
            
            return pd.DataFrame(news)
            
        except Exception as e:
            logger.error(f"Error fetching company news", ticker=ticker_symbol, error=str(e))
            return pd.DataFrame()
    
    def get_earning_calls(self, ticker_symbol: str, year: str = "latest") -> str:
        """Get earning call transcripts."""
        try:
            if year is None or year == "latest":
                year = datetime.now().year
                if datetime.now().month < 3:
                    year = int(year) - 1
            
            url = f"https://financialmodelingprep.com/api/v4/batch_earning_call_transcript/{ticker_symbol}?year={year}&apikey={self.api_key}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or len(data) == 0:
                return f"No earning call transcripts found for {ticker_symbol} in {year}"
            
            # Return the most recent transcript
            transcript = data[0].get('content', '')
            return transcript
            
        except Exception as e:
            logger.error(f"Error fetching earning calls", ticker=ticker_symbol, year=year, error=str(e))
            return f"Error fetching earning calls: {str(e)}"
    
    def get_ratings(self, ticker_symbol: str) -> dict:
        """Get analyst ratings and recommendations."""
        url = f"{self.base_url}/rating/{ticker_symbol}?apikey={self.api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or len(data) == 0:
                return {"error": f"No ratings found for {ticker_symbol}"}
            
            # Get most recent rating
            rating = data[0]
            return {
                "symbol": rating.get("symbol", ticker_symbol),
                "date": rating.get("date", ""),
                "rating": rating.get("rating", "N/A"),
                "ratingScore": rating.get("ratingScore", 0),
                "ratingRecommendation": rating.get("ratingRecommendation", "N/A"),
                "ratingDetailsDCFScore": rating.get("ratingDetailsDCFScore", 0),
                "ratingDetailsDCFRecommendation": rating.get("ratingDetailsDCFRecommendation", "N/A"),
                "ratingDetailsROEScore": rating.get("ratingDetailsROEScore", 0),
                "ratingDetailsROERecommendation": rating.get("ratingDetailsROERecommendation", "N/A"),
                "ratingDetailsROAScore": rating.get("ratingDetailsROAScore", 0),
                "ratingDetailsROARecommendation": rating.get("ratingDetailsROARecommendation", "N/A"),
                "ratingDetailsDEScore": rating.get("ratingDetailsDEScore", 0),
                "ratingDetailsDERecommendation": rating.get("ratingDetailsDERecommendation", "N/A"),
                "ratingDetailsPEScore": rating.get("ratingDetailsPEScore", 0),
                "ratingDetailsPERecommendation": rating.get("ratingDetailsPERecommendation", "N/A"),
                "ratingDetailsPBScore": rating.get("ratingDetailsPBScore", 0),
                "ratingDetailsPBRecommendation": rating.get("ratingDetailsPBRecommendation", "N/A")
            }
            
        except Exception as e:
            logger.error(f"Error fetching ratings", ticker=ticker_symbol, error=str(e))
            return {"error": f"Error fetching ratings: {str(e)}"}
    
    def get_financial_scores(self, ticker_symbol: str) -> list:
        """Get financial scores including Altman Z-Score and Piotroski F-Score."""
        url = f"{self.base_url}/score?symbol={ticker_symbol}&apikey={self.api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or len(data) == 0:
                return []
            
            scores = []
            for score_data in data[:5]:  # Get up to 5 years
                scores.append({
                    "symbol": score_data.get("symbol", ticker_symbol),
                    "date": score_data.get("date", ""),
                    "altmanZScore": score_data.get("altmanZScore", 0),
                    "piotroskiScore": score_data.get("piotroskiScore", 0),
                    "workingCapital": score_data.get("workingCapital", 0),
                    "totalAssets": score_data.get("totalAssets", 0),
                    "retainedEarnings": score_data.get("retainedEarnings", 0),
                    "ebit": score_data.get("ebit", 0),
                    "marketCap": score_data.get("marketCap", 0),
                    "totalLiabilities": score_data.get("totalLiabilities", 0),
                    "revenue": score_data.get("revenue", 0)
                })
            
            return scores
            
        except Exception as e:
            logger.error(f"Error fetching financial scores", ticker=ticker_symbol, error=str(e))
            return []
    
    def get_sec_report(self, ticker_symbol: str, year: str = "latest", report_type: str = "10-K") -> dict:
        """
        Get SEC filing report (10-K or 10-Q) for a company.
        
        Args:
            ticker_symbol: Stock ticker symbol
            year: Year for the report (or "latest")
            report_type: Type of SEC report ("10-K" for annual, "10-Q" for quarterly)
            
        Returns:
            Dictionary with SEC filing data including sections
        """
        try:
            if year is None or year == "latest":
                year = datetime.now().year
            
            # FMP API endpoint for SEC filings
            url = f"{self.base_url}/sec_filings/{ticker_symbol}?type={report_type}&page=0&apikey={self.api_key}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or len(data) == 0:
                logger.warning(f"No SEC {report_type} filings found for {ticker_symbol}")
                return {
                    "ticker": ticker_symbol,
                    "year": year,
                    "type": report_type,
                    "error": f"No {report_type} filings found"
                }
            
            # Find the most recent filing for the requested year
            target_filing = None
            for filing in data:
                filing_date = filing.get("fillingDate", "")
                if str(year) in filing_date or year == datetime.now().year:
                    target_filing = filing
                    break
            
            if not target_filing:
                target_filing = data[0]  # Use most recent if year not found
            
            # Get the filing URL and extract content
            filing_url = target_filing.get("finalLink", "")
            filing_date = target_filing.get("fillingDate", "")
            accepted_date = target_filing.get("acceptedDate", "")
            
            logger.info(
                f"SEC filing found for {ticker_symbol}",
                type=report_type,
                filing_date=filing_date,
                url=filing_url
            )
            
            # Return structured filing data
            result = {
                "ticker": ticker_symbol,
                "type": report_type,
                "filing_date": filing_date,
                "accepted_date": accepted_date,
                "url": filing_url,
                "cik": target_filing.get("cik", ""),
                "form_type": target_filing.get("type", report_type),
                "raw_data": target_filing
            }
            
            # Try to fetch additional details if available
            if filing_url:
                result["link"] = filing_url
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching SEC report", ticker=ticker_symbol, year=year, error=str(e))
            return {
                "ticker": ticker_symbol,
                "year": year,
                "type": report_type,
                "error": str(e)
            }

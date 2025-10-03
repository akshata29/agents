# Yahoo Finance MCP Server

A Model Context Protocol (MCP) server providing comprehensive financial data from Yahoo Finance via HTTP/SSE transport. This server exposes 9 tools for stock information, financial statements, options data, and analyst recommendations.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Overview](#overview)
3. [Features & Tools](#features--tools)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Architecture](#architecture)
7. [Agent Integration](#agent-integration)
8. [Migration Guide](#migration-guide)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)
11. [Parameter Reference](#parameter-reference)

---

## Quick Start

Get started in 5 minutes:

### 1. Install Dependencies (1 minute)

```bash
cd finagent_app/backend/mcp_servers
pip install -r requirements.txt
```

This installs: `mcp`, `fastmcp`, `yfinance`, `pandas`, `pydantic`

### 2. Start the Server (1 minute)

```bash
# Using the start script (recommended)
python start_server.py

# Or directly with Python
python yahoo_finance_server.py
```

The server will start on `http://localhost:8001` with SSE transport.

### 3. Test the Server (1 minute)

```bash
python -c "
import asyncio
from yahoo_finance_server import get_stock_info

async def test():
    info = await get_stock_info('AAPL')
    print('✅ MCP server working!')
    print(f'   Data length: {len(info)} characters')

asyncio.run(test())
"
```

### 4. Use in Your Code (2 minutes)

**Option A: Direct Tool Usage**
```python
import asyncio
from mcp_servers.yahoo_finance_server import (
    get_stock_info,
    get_historical_stock_prices,
    get_yahoo_finance_news
)

async def analyze_stock(ticker: str):
    info = await get_stock_info(ticker)
    prices = await get_historical_stock_prices(ticker, period="6mo", interval="1d")
    news = await get_yahoo_finance_news(ticker)
    return {"info": info, "prices": prices, "news": news}

asyncio.run(analyze_stock("AAPL"))
```

**Option B: With MCP Client (for agents)**
```python
from mcp.client.sse import sse_client

async def use_mcp_client():
    async with sse_client("http://localhost:8001/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Call MCP tool
            result = await session.call_tool(
                "get_stock_info",
                arguments={"ticker": "AAPL"}
            )
            print(result.content[0].text)
```

---

## Overview

This MCP server is based on the [yahoo-finance-mcp](https://github.com/Alex2Yang97/yahoo-finance-mcp) reference implementation and provides:

- **9 MCP Tools** for comprehensive Yahoo Finance data
- **HTTP/SSE Transport** on port 8001 for easy integration
- **Pure MCP Protocol** - no fallback to direct API calls
- **Real-time Data** via Yahoo Finance API through yfinance library
- **Framework Integration** with Microsoft Agent Framework (MAF)

### Why MCP?

The Model Context Protocol (MCP) provides:
- ✅ **Standardized Interface**: Consistent tool interfaces across data providers
- ✅ **Built-in Error Handling**: Automatic retries and error management
- ✅ **Easy Testing**: Mock and test tools independently
- ✅ **Separation of Concerns**: Agents don't need to know about data provider details
- ✅ **Extensibility**: Add new tools without changing agent code

---

## Features & Tools

### Stock Information (4 tools)

1. **get_historical_stock_prices** - Historical OHLCV data
   ```python
   await get_historical_stock_prices(
       ticker="AAPL",
       period="6mo",      # 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
       interval="1d"      # 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
   )
   ```

2. **get_stock_info** - Comprehensive stock data and metrics
   ```python
   await get_stock_info(ticker="MSFT")
   ```

3. **get_yahoo_finance_news** - Latest news articles
   ```python
   await get_yahoo_finance_news(ticker="GOOGL")
   ```

4. **get_stock_actions** - Dividends and splits history
   ```python
   await get_stock_actions(ticker="AAPL")
   ```

### Financial Statements (2 tools)

5. **get_financial_statement** - Income statement, balance sheet, cash flow
   ```python
   await get_financial_statement(
       ticker="TSLA",
       financial_type="quarterly_income_stmt"
       # Options: income_stmt, quarterly_income_stmt, balance_sheet,
       # quarterly_balance_sheet, cashflow, quarterly_cashflow
   )
   ```

6. **get_holder_info** - Holders and insider transactions
   ```python
   await get_holder_info(
       ticker="NVDA",
       holder_type="institutional_holders"
       # Options: major_holders, institutional_holders, mutualfund_holders,
       # insider_transactions, insider_purchases, insider_roster_holders
   )
   ```

### Options Data (2 tools)

7. **get_option_expiration_dates** - Available expiration dates
   ```python
   await get_option_expiration_dates(ticker="SPY")
   ```

8. **get_option_chain** - Options chain data
   ```python
   await get_option_chain(
       ticker="SPY",
       expiration_date="2024-06-21",
       option_type="calls"  # or "puts"
   )
   ```

### Analyst Information (1 tool)

9. **get_recommendations** - Analyst recommendations and upgrades/downgrades
   ```python
   await get_recommendations(
       ticker="AMZN",
       recommendation_type="recommendations",  # or "upgrades_downgrades"
       months_back=6  # for upgrades_downgrades only
   )
   ```

---

## Installation

### Prerequisites
- Python 3.11+
- Existing finagent_app installation

### Step 1: Install MCP Server Dependencies

```bash
cd finagent_app/backend/mcp_servers
pip install -r requirements.txt
```

Required packages:
- `mcp>=1.0.0` - MCP protocol implementation
- `fastmcp>=0.2.0` - Lightweight MCP server framework
- `yfinance>=0.2.50` - Yahoo Finance data provider
- `pandas>=2.0.0` - Data manipulation
- `pydantic>=2.0.0` - Data validation
- `uvicorn>=0.27.0` - ASGI server for HTTP/SSE transport

### Step 2: Verify Installation

```bash
python yahoo_finance_server.py
```

You should see:
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
```

---

## Usage

### Standalone Server

Run the server for testing or development:

```bash
# Using start script (recommended)
python start_server.py

# Or with PowerShell script
.\start_server.ps1

# Or directly
python yahoo_finance_server.py
```

The server runs on **http://localhost:8001** with SSE endpoint at **/sse**.

### Common Use Cases

#### Stock Summary
```python
async def stock_summary(ticker: str):
    """Get complete stock summary."""
    info = await get_stock_info(ticker)
    prices = await get_historical_stock_prices(ticker, period="1mo", interval="1d")
    news = await get_yahoo_finance_news(ticker)
    recs = await get_recommendations(ticker, recommendation_type="recommendations")
    
    return {"info": info, "prices": prices, "news": news, "recommendations": recs}
```

#### Financial Analysis
```python
async def analyze_financials(ticker: str):
    """Analyze company financials."""
    income = await get_financial_statement(ticker, financial_type="quarterly_income_stmt")
    balance = await get_financial_statement(ticker, financial_type="balance_sheet")
    holders = await get_holder_info(ticker, holder_type="institutional_holders")
    
    return {"income_statement": income, "balance_sheet": balance, "holders": holders}
```

#### Options Analysis
```python
async def options_analysis(ticker: str):
    """Analyze options for a stock."""
    dates_json = await get_option_expiration_dates(ticker)
    dates_list = json.loads(dates_json)
    
    if dates_list:
        nearest = dates_list[0]
        calls = await get_option_chain(ticker, expiration_date=nearest, option_type="calls")
        puts = await get_option_chain(ticker, expiration_date=nearest, option_type="puts")
        return {"expiration": nearest, "calls": calls, "puts": puts}
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Financial Agents                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Company    │  │ Technicals   │  │ Fundamentals │      │
│  │    Agent     │  │    Agent     │  │    Agent     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                    HTTP/SSE (port 8001)                      │
│                            │                                 │
└────────────────────────────┼────────────────────────────────┘
                             │
                  ┌──────────▼──────────┐
                  │  Yahoo Finance MCP  │
                  │      Server         │
                  │  (FastMCP + SSE)    │
                  │                     │
                  │  ┌───────────────┐  │
                  │  │  9 MCP Tools  │  │
                  │  └───────────────┘  │
                  └──────┬──────────────┘
                         │
                  ┌──────▼──────────────┐
                  │   yfinance Library  │
                  │  (Yahoo Finance)    │
                  └─────────────────────┘
```

### Technology Stack

- **FastMCP**: Lightweight MCP server framework with SSE support
- **Uvicorn**: ASGI server for HTTP/SSE transport on port 8001
- **yfinance**: Yahoo Finance data provider
- **pandas**: Data manipulation and formatting
- **pydantic**: Data validation
- **MCP Protocol**: Model Context Protocol for tool communication

### Transport Layer

The server uses **HTTP with Server-Sent Events (SSE)** instead of stdio:
- **Endpoint**: `http://localhost:8001/sse`
- **Transport**: SSE (Server-Sent Events)
- **Protocol**: MCP over HTTP
- **Port**: 8001 (to avoid conflicts with backend on 8000)

---

## Agent Integration

### Using MCP Client in Agents

Agents connect to the MCP server via HTTP/SSE:

```python
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

class CompanyAgent(BaseAgent):
    def __init__(self, ...):
        super().__init__(name="Company Agent", description="...")
        self.mcp_server_url = "http://localhost:8001/sse"
    
    async def _fetch_data_via_mcp(self, ticker: str):
        """Fetch data using MCP server (NO fallback)."""
        async with sse_client(self.mcp_server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Get stock info
                stock_info_result = await session.call_tool(
                    "get_stock_info",
                    arguments={"ticker": ticker}
                )
                
                # Get historical data
                historical_result = await session.call_tool(
                    "get_historical_stock_prices",
                    arguments={
                        "ticker": ticker,
                        "period": "1y",
                        "interval": "1d"
                    }
                )
                
                # Get news
                news_result = await session.call_tool(
                    "get_yahoo_finance_news",
                    arguments={"ticker": ticker}
                )
                
                return {
                    "stock_info": stock_info_result.content[0].text,
                    "historical": historical_result.content[0].text,
                    "news": news_result.content[0].text
                }
```

### Integration Requirements

1. **MCP Server Must Be Running**: Start server before running agents
2. **Port 8001**: Ensure port 8001 is available (not used by backend)
3. **No Fallbacks**: Agents use ONLY MCP server (no direct API calls)
4. **Error Handling**: Agents should handle MCP connection errors gracefully

---

## Migration Guide

### From Direct API Calls to MCP

#### Before (Direct API with YFUtils)

```python
class CompanyAgent(BaseAgent):
    def __init__(self, ...):
        self.yf_utils = YFUtils()
    
    async def _fetch_market_data(self, ticker, context):
        stock_info = self.yf_utils.get_stock_info(ticker)
        stock_data = self.yf_utils.get_stock_data(ticker, start, end)
        news = self.yf_utils.get_company_news(ticker, start, end)
        return {"stock_info": stock_info, "stock_data": stock_data, "news": news}
```

#### After (Pure MCP)

```python
class CompanyAgent(BaseAgent):
    def __init__(self, ...):
        self.mcp_server_url = "http://localhost:8001/sse"
    
    async def _fetch_data_via_mcp(self, ticker, context):
        async with sse_client(self.mcp_server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                stock_info = await session.call_tool("get_stock_info", arguments={"ticker": ticker})
                historical = await session.call_tool("get_historical_stock_prices", 
                    arguments={"ticker": ticker, "period": "1y", "interval": "1d"})
                news = await session.call_tool("get_yahoo_finance_news", arguments={"ticker": ticker})
                
                return {
                    "stock_info": stock_info.content[0].text,
                    "historical": historical.content[0].text,
                    "news": news.content[0].text
                }
```

### Tool Mapping

| Old YFUtils Method | New MCP Tool | Notes |
|--------------------|--------------|-------|
| `get_stock_info()` | `get_stock_info` | Direct mapping |
| `get_stock_data()` | `get_historical_stock_prices` | More options (period/interval) |
| `get_company_news()` | `get_yahoo_finance_news` | Same data source |
| `get_analyst_recommendations()` | `get_recommendations` | Enhanced with upgrades/downgrades |
| N/A | `get_stock_actions` | NEW: Dividends/splits |
| N/A | `get_financial_statement` | NEW: Full financials |
| N/A | `get_holder_info` | NEW: Institutional holders |
| N/A | `get_option_chain` | NEW: Options data |

### Migration Steps

1. **Start MCP Server**: Ensure server is running on port 8001
2. **Update Agent Imports**: Replace YFUtils with MCP client
3. **Update Data Fetching**: Use MCP tool calls instead of direct methods
4. **Remove Fallback Logic**: No fallback to YFUtils (pure MCP only)
5. **Test Thoroughly**: Verify all data flows work correctly

---

## Testing

### Test 1: Standalone Server

```bash
python -c "
import asyncio
from yahoo_finance_server import get_stock_info

async def test():
    result = await get_stock_info('AAPL')
    print('✅ Server working!')
    print(f'Data length: {len(result)} characters')

asyncio.run(test())
"
```

### Test 2: MCP Client Connection

```python
# test_mcp_client.py
import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def test_mcp_connection():
    """Test MCP server connection and tool call."""
    async with sse_client("http://localhost:8001/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test get_stock_info tool
            result = await session.call_tool(
                "get_stock_info",
                arguments={"ticker": "AAPL"}
            )
            
            print("✅ MCP client connection successful!")
            print(f"Result: {result.content[0].text[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
```

### Test 3: All Tools

```python
# test_all_tools.py
import asyncio
from yahoo_finance_server import *

async def test_all_tools():
    """Test all 9 MCP tools."""
    ticker = "AAPL"
    
    print("Testing Stock Info Tools...")
    info = await get_stock_info(ticker)
    print(f"✅ get_stock_info: {len(info)} chars")
    
    prices = await get_historical_stock_prices(ticker, "1mo", "1d")
    print(f"✅ get_historical_stock_prices: {len(prices)} chars")
    
    news = await get_yahoo_finance_news(ticker)
    print(f"✅ get_yahoo_finance_news: {len(news)} chars")
    
    actions = await get_stock_actions(ticker)
    print(f"✅ get_stock_actions: {len(actions)} chars")
    
    print("\nTesting Financial Tools...")
    income = await get_financial_statement(ticker, "quarterly_income_stmt")
    print(f"✅ get_financial_statement: {len(income)} chars")
    
    holders = await get_holder_info(ticker, "institutional_holders")
    print(f"✅ get_holder_info: {len(holders)} chars")
    
    print("\nTesting Options Tools...")
    dates = await get_option_expiration_dates(ticker)
    print(f"✅ get_option_expiration_dates: {len(dates)} chars")
    
    import json
    dates_list = json.loads(dates)
    if dates_list:
        chain = await get_option_chain(ticker, dates_list[0], "calls")
        print(f"✅ get_option_chain: {len(chain)} chars")
    
    print("\nTesting Analyst Tools...")
    recs = await get_recommendations(ticker, "recommendations")
    print(f"✅ get_recommendations: {len(recs)} chars")
    
    print("\n🎉 All tools working!")

asyncio.run(test_all_tools())
```

---

## Troubleshooting

### Issue: MCP Server Not Starting

**Symptoms**: Server fails to start or crashes immediately

**Solutions**:
1. Check port 8001 is available: `netstat -ano | findstr :8001`
2. Verify dependencies: `pip install -r requirements.txt --upgrade`
3. Check Python version: `python --version` (requires 3.11+)
4. Look for error messages in console output

### Issue: Port 8001 Already in Use

**Symptoms**: `[Errno 10048] Address already in use`

**Solutions**:
1. Find process using port 8001: `netstat -ano | findstr :8001`
2. Kill the process: `taskkill /PID <pid> /F`
3. Or change server port in `yahoo_finance_server.py` (update line with `port=8001`)

### Issue: Agent Can't Connect to MCP Server

**Symptoms**: Connection refused or timeout errors

**Solutions**:
1. Ensure server is running: Check terminal for "Uvicorn running on..."
2. Verify URL: Should be `http://localhost:8001/sse`
3. Check firewall: Allow connections on port 8001
4. Test manually: `curl http://localhost:8001/sse`

### Issue: Invalid Ticker Symbol

**Symptoms**: "Ticker not found" or empty responses

**Solutions**:
1. Use uppercase ticker symbols: `AAPL` not `aapl`
2. Verify ticker exists: Check on Yahoo Finance website first
3. Some tickers may not have all data types (options, financials)

### Issue: No Historical Data Returned

**Symptoms**: Empty data for historical prices

**Solutions**:
1. Check period/interval combination is valid
2. Intraday data (`1m`, `5m`, etc.) limited to last 60 days
3. Some intervals not available for all periods
4. Try with known good ticker like `AAPL`

### Issue: yfinance Rate Limiting

**Symptoms**: Errors after many requests

**Solutions**:
1. Add delays between requests in your code
2. Cache results when possible
3. Use broader time periods to reduce requests
4. Consider using batch requests for multiple tickers

### Debug Mode

Enable detailed logging:

```python
import logging
import structlog

# Configure logging
logging.basicConfig(level=logging.DEBUG)
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
)

logger = structlog.get_logger(__name__)
logger.debug("MCP server status", port=8001, transport="SSE")
```

---

## Parameter Reference

### Financial Statement Types

```python
# Annual statements
"income_stmt"              # Annual income statement
"balance_sheet"           # Annual balance sheet  
"cashflow"                # Annual cash flow statement

# Quarterly statements
"quarterly_income_stmt"    # Quarterly income statement
"quarterly_balance_sheet"  # Quarterly balance sheet
"quarterly_cashflow"       # Quarterly cash flow statement
```

### Holder Types

```python
"major_holders"            # Major institutional and insider holders (summary)
"institutional_holders"    # Institutional investors (detailed)
"mutualfund_holders"      # Mutual fund holders
"insider_transactions"     # Insider buy/sell transactions
"insider_purchases"        # Insider purchases only
"insider_roster_holders"   # Current insider holders
```

### Recommendation Types

```python
"recommendations"          # Current analyst recommendations
"upgrades_downgrades"     # Recent upgrades and downgrades (requires months_back)
```

### Historical Data Periods

```python
"1d"    # 1 day
"5d"    # 5 days
"1mo"   # 1 month
"3mo"   # 3 months
"6mo"   # 6 months
"1y"    # 1 year
"2y"    # 2 years
"5y"    # 5 years
"10y"   # 10 years
"ytd"   # Year to date
"max"   # Maximum available history
```

### Historical Data Intervals

```python
# Intraday (limited to last 60 days)
"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"

# Daily and longer
"1d"    # Daily
"5d"    # 5 days
"1wk"   # Weekly
"1mo"   # Monthly
"3mo"   # 3 months
```

**Note**: Intraday intervals (`1m`, `5m`, etc.) cannot extend beyond 60 days.

---

## Best Practices

### 1. Always Start MCP Server First
```bash
# Start in separate terminal
python start_server.py
```

### 2. Handle MCP Connection Errors Gracefully
```python
try:
    async with sse_client(self.mcp_server_url) as (read, write):
        async with ClientSession(read, write) as session:
            # Your MCP calls here
            pass
except Exception as e:
    logger.error("MCP connection failed", error=str(e))
    # Don't fallback to direct API - raise error
    raise
```

### 3. Use Appropriate Time Periods
```python
# Good: Specific period for analysis
await get_historical_stock_prices(ticker, period="1y", interval="1d")

# Bad: Max period with minute interval (will fail)
await get_historical_stock_prices(ticker, period="max", interval="1m")
```

### 4. Cache Results When Possible
```python
from functools import lru_cache
import asyncio

@lru_cache(maxsize=100)
def _cache_key(ticker, period, interval):
    return f"{ticker}_{period}_{interval}"

# Implement caching layer for frequently requested data
```

### 5. Test with Known Good Tickers
```python
# Reliable tickers for testing
test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
```

---

## License

MIT License (same as the reference implementation)

## Credits

Based on [yahoo-finance-mcp](https://github.com/Alex2Yang97/yahoo-finance-mcp) by AlexYoung.

## Additional Resources

- **MCP Protocol**: https://modelcontextprotocol.io
- **FastMCP Framework**: https://github.com/jlowin/fastmcp
- **yfinance Library**: https://github.com/ranaroussi/yfinance
- **Yahoo Finance**: https://finance.yahoo.com

## Support

For issues or questions:
1. Check this README for common issues
2. Review the troubleshooting section above
3. Check the main finagent_app documentation
4. Consult the MCP protocol specification

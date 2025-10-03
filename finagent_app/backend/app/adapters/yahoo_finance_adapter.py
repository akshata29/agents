"""
Yahoo Finance MCP Adapter

This module provides an adapter to integrate the Yahoo Finance MCP server
with the Financial Agent application, allowing agents to use MCP tools
for fetching Yahoo Finance data.
"""

from typing import Any, Dict, List, Optional
import structlog
import asyncio

from framework.mcp_integration.maf_adapter import MAFMCPAdapter, ExternalMCPServer

logger = structlog.get_logger(__name__)


class YahooFinanceMCPAdapter:
    """
    Adapter for the Yahoo Finance MCP server.
    
    This adapter provides a simple interface for agents to interact with
    the Yahoo Finance MCP server using the MAF adapter pattern.
    
    Usage:
        # Create adapter
        adapter = YahooFinanceMCPAdapter()
        
        # Register the server
        await adapter.initialize()
        
        # Use tools via agents
        tools = adapter.get_tool_definitions()
    """
    
    def __init__(self, server_path: Optional[str] = None):
        """
        Initialize Yahoo Finance MCP Adapter.
        
        Args:
            server_path: Path to the yahoo_finance_server.py file.
                        If None, uses the default location.
        """
        self.server_path = server_path or "mcp_servers/yahoo_finance_server.py"
        self.maf_adapter: Optional[MAFMCPAdapter] = None
        self.server_label = "yahoo_finance"
        
        logger.info("Yahoo Finance MCP Adapter initialized", server_path=self.server_path)
    
    async def initialize(self) -> bool:
        """
        Initialize the MCP adapter and register the Yahoo Finance server.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Create MAF MCP adapter
            self.maf_adapter = MAFMCPAdapter()
            
            # Register Yahoo Finance server
            # Note: For local MCP servers, we might use stdio transport
            # This is a placeholder - actual implementation depends on deployment
            logger.info(f"Registering Yahoo Finance MCP server: {self.server_label}")
            
            # The server configuration will depend on how it's deployed
            # For now, we'll document the expected tools
            self._document_tools()
            
            logger.info("Yahoo Finance MCP Adapter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Yahoo Finance MCP Adapter", error=str(e))
            return False
    
    def _document_tools(self):
        """Document the available Yahoo Finance MCP tools."""
        self.available_tools = {
            # Stock Information Tools
            "get_historical_stock_prices": {
                "description": "Get historical OHLCV data for a stock",
                "parameters": ["ticker", "period", "interval"],
                "category": "stock_info"
            },
            "get_stock_info": {
                "description": "Get comprehensive stock data including price, metrics, and company details",
                "parameters": ["ticker"],
                "category": "stock_info"
            },
            "get_yahoo_finance_news": {
                "description": "Get latest news articles for a stock",
                "parameters": ["ticker"],
                "category": "stock_info"
            },
            "get_stock_actions": {
                "description": "Get stock dividends and splits history",
                "parameters": ["ticker"],
                "category": "stock_info"
            },
            
            # Financial Statement Tools
            "get_financial_statement": {
                "description": "Get income statement, balance sheet, or cash flow statement",
                "parameters": ["ticker", "financial_type"],
                "category": "financials",
                "financial_types": [
                    "income_stmt", "quarterly_income_stmt",
                    "balance_sheet", "quarterly_balance_sheet",
                    "cashflow", "quarterly_cashflow"
                ]
            },
            "get_holder_info": {
                "description": "Get major holders, institutional holders, mutual funds, or insider transactions",
                "parameters": ["ticker", "holder_type"],
                "category": "financials",
                "holder_types": [
                    "major_holders", "institutional_holders", "mutualfund_holders",
                    "insider_transactions", "insider_purchases", "insider_roster_holders"
                ]
            },
            
            # Options Tools
            "get_option_expiration_dates": {
                "description": "Get available options expiration dates",
                "parameters": ["ticker"],
                "category": "options"
            },
            "get_option_chain": {
                "description": "Get options chain for a specific expiration date and type",
                "parameters": ["ticker", "expiration_date", "option_type"],
                "category": "options"
            },
            
            # Analyst Tools
            "get_recommendations": {
                "description": "Get analyst recommendations or upgrades/downgrades history",
                "parameters": ["ticker", "recommendation_type", "months_back"],
                "category": "analyst",
                "recommendation_types": ["recommendations", "upgrades_downgrades"]
            }
        }
        
        logger.info(f"Documented {len(self.available_tools)} Yahoo Finance MCP tools")
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions for use with agents.
        
        Returns:
            List of tool definition dictionaries
        """
        return [
            {
                "name": tool_name,
                **tool_info
            }
            for tool_name, tool_info in self.available_tools.items()
        ]
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """
        Get tool names filtered by category.
        
        Args:
            category: Category to filter by (stock_info, financials, options, analyst)
        
        Returns:
            List of tool names in the category
        """
        return [
            tool_name 
            for tool_name, tool_info in self.available_tools.items()
            if tool_info.get("category") == category
        ]
    
    def get_stock_info_tools(self) -> List[str]:
        """Get stock information tools."""
        return self.get_tools_by_category("stock_info")
    
    def get_financial_tools(self) -> List[str]:
        """Get financial statement tools."""
        return self.get_tools_by_category("financials")
    
    def get_options_tools(self) -> List[str]:
        """Get options data tools."""
        return self.get_tools_by_category("options")
    
    def get_analyst_tools(self) -> List[str]:
        """Get analyst information tools."""
        return self.get_tools_by_category("analyst")


# Convenience function for easy import
def create_yahoo_finance_adapter(server_path: Optional[str] = None) -> YahooFinanceMCPAdapter:
    """
    Create and return a Yahoo Finance MCP Adapter instance.
    
    Args:
        server_path: Optional path to the server file
    
    Returns:
        YahooFinanceMCPAdapter instance
    """
    return YahooFinanceMCPAdapter(server_path=server_path)

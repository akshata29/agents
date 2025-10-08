"""
Entity Extraction & PII Detection Agent

Extracts investment-related entities and detects/redacts PII using Azure Language Service.
MAF-compatible agent implementation.
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, AsyncIterable
from datetime import datetime
from pathlib import Path
import structlog

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread

from openai import AsyncAzureOpenAI

logger = structlog.get_logger(__name__)


class EntityPIIAgent(BaseAgent):
    """
    MAF-compatible agent for entity extraction and PII detection.
    
    Capabilities:
    - Investment entity extraction (tickers, funds, amounts, products)
    - Person and organization identification
    - PII detection and redaction (SSN, account numbers, addresses)
    - Compliance-relevant entity tagging
    - Entity relationship mapping
    """
    
    def __init__(self, settings, name: str = "entity_pii", description: str = "Extracts entities and detects PII"):
        """Initialize the entity/PII agent."""
        super().__init__(name=name, description=description)
        
        self.app_settings = settings
        
        # Initialize Azure OpenAI client for entity extraction
        self.client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT
        
        # PII patterns (regex-based detection)
        self.pii_patterns = {
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "account_number": r'\b(?:Account|Acct)[\s#:]*(\d{4,})\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "zip": r'\b\d{5}(?:-\d{4})?\b'
        }
        
        # Investment entity categories
        self.entity_categories = [
            "ticker_symbols",
            "mutual_funds",
            "etfs",
            "bonds",
            "investment_amounts",
            "percentages",
            "account_types",
            "investment_products",
            "financial_institutions",
            "regulatory_terms"
        ]
        
        logger.info(
            f"Initialized {self.name}",
            entity_categories=len(self.entity_categories),
            pii_patterns=len(self.pii_patterns)
        )
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "entity_extraction",
            "pii_detection",
            "pii_redaction",
            "ticker_extraction",
            "amount_extraction",
            "compliance_tagging",
            "entity_relationship_mapping"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent - REQUIRED by MAF."""
        logger.info(f"🚀 EntityPIIAgent.run() called with messages={type(messages)}, kwargs={list(kwargs.keys())}")
        try:
            # Normalize messages (same as SentimentAgent)
            normalized_messages = self._normalize_messages(messages)
            logger.info(f"📝 Normalized to {len(normalized_messages)} messages")
            
            # Extract text from last message
            last_message = normalized_messages[-1] if normalized_messages else None
            text = last_message.text if last_message and hasattr(last_message, 'text') else ""
            logger.info(f"📄 Extracted text length: {len(text)}")
            
            # Allow override from kwargs (for backward compatibility)
            text = kwargs.get("text", text)
            action = kwargs.get("action", "extract_all")
            redact_pii = kwargs.get("redact_pii", True)
            logger.info(f"📝 Final text length: {len(text)}, action: {action}")
            
            if not text or len(text.strip()) == 0:
                logger.warning("⚠️ No text provided, returning error response")
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: No text provided")]
                    )]
                )
            
            # Route to appropriate method
            if action == "extract_entities":
                result = await self.extract_entities(text)
            elif action == "detect_pii":
                result = await self.detect_pii(text)
            elif action == "redact_pii":
                result = await self.redact_pii(text)
            else:  # extract_all
                result = await self.extract_all(text, redact_pii=redact_pii)
            
            # Return result as ChatMessage
            result_text = json.dumps(result, ensure_ascii=False, default=str)
            logger.info(f"✅ Returning AgentRunResponse with {len(result_text)} chars")
            response = AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            logger.info(f"📦 Response object created: {type(response)}, messages count: {len(response.messages)}")
            return response
            
        except Exception as e:
            logger.error(f"Error in entity/PII processing", error=str(e), exc_info=True)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=f"Error: {str(e)}")]
                )]
            )
    
    def _normalize_messages(
        self, 
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None
    ) -> list[ChatMessage]:
        """Normalize various message formats to list of ChatMessage."""
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
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Stream responses - REQUIRED by MAF."""
        result = await self.run(messages, thread=thread, **kwargs)
        
        for message in result.messages:
            yield AgentRunResponseUpdate(
                messages=[message]
            )
    
    async def extract_all(
        self,
        text: str,
        redact_pii: bool = True
    ) -> Dict[str, Any]:
        """
        Extract all entities and PII in one comprehensive analysis.
        
        Args:
            text: Text to analyze
            redact_pii: Whether to redact detected PII
            
        Returns:
            Comprehensive entity and PII analysis
        """
        logger.info("Extracting entities and PII", text_length=len(text), redact=redact_pii)
        
        # Run extraction and detection in parallel
        entities_task = self.extract_entities(text)
        pii_task = self.detect_pii(text)
        
        entities, pii_data = await asyncio.gather(entities_task, pii_task)
        
        # Redact if requested
        redacted_text = text
        if redact_pii and pii_data.get("pii_found"):
            redaction_result = await self.redact_pii(text)
            redacted_text = redaction_result["redacted_text"]
        
        return {
            "entities": entities,
            "pii": pii_data,
            "original_text": text,
            "redacted_text": redacted_text if redact_pii else None,
            "metadata": {
                "text_length": len(text),
                "entity_count": sum(len(v) for v in entities.values()),
                "pii_count": pii_data.get("pii_count", 0),
                "redacted": redact_pii,
                "analyzed_at": datetime.utcnow().isoformat(),
                "agent": self.name
            }
        }
    
    async def extract_entities(
        self,
        text: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract investment-related entities from text using Azure OpenAI.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            Dictionary of entity categories with extracted entities
        """
        logger.info("Extracting entities", text_length=len(text))
        
        try:
            prompt = f"""Extract investment-related entities from this text.

Text:
{text}

Extract and categorize the following entities:

1. **Ticker Symbols**: Stock ticker symbols (e.g., AAPL, MSFT, GOOGL)
2. **Mutual Funds**: Mutual fund names (e.g., Vanguard 500 Index Fund)
3. **ETFs**: Exchange-traded fund names (e.g., SPDR S&P 500 ETF)
4. **Bonds**: Bond types or specific bonds (e.g., Municipal Bonds, Treasury Notes)
5. **Investment Amounts**: Dollar amounts mentioned (e.g., $50,000, $1.2M)
6. **Percentages**: Percentage allocations or returns (e.g., 60% stocks, 5% return)
7. **Account Types**: Investment account types (e.g., 401(k), IRA, Roth IRA, Brokerage)
8. **Investment Products**: Other products (e.g., Annuities, CDs, Money Market)
9. **Financial Institutions**: Banks, brokerages, fund companies (e.g., Fidelity, Schwab)
10. **Regulatory Terms**: Compliance-related terms (e.g., fiduciary, suitability)
11. **People**: Names of people mentioned
12. **Organizations**: Company names (not financial institutions)
13. **Dates**: Time references (e.g., Q4 2025, next month)

Return in this JSON structure:
{{
    "ticker_symbols": [
        {{"symbol": "AAPL", "company": "Apple Inc.", "mentions": 2}}
    ],
    "mutual_funds": [
        {{"name": "Vanguard 500 Index Fund", "ticker": "VFIAX"}}
    ],
    "etfs": [
        {{"name": "SPDR S&P 500 ETF", "ticker": "SPY"}}
    ],
    "bonds": [
        {{"type": "Municipal Bonds", "details": "Tax-free bonds"}}
    ],
    "investment_amounts": [
        {{"amount": "$50,000", "context": "Initial investment"}}
    ],
    "percentages": [
        {{"value": "60%", "context": "Stock allocation"}}
    ],
    "account_types": [
        {{"type": "401(k)", "context": "Retirement account"}}
    ],
    "investment_products": [
        {{"product": "Annuity", "details": "Fixed annuity"}}
    ],
    "financial_institutions": [
        {{"name": "Fidelity", "type": "Brokerage"}}
    ],
    "regulatory_terms": [
        {{"term": "fiduciary", "context": "Fiduciary duty"}}
    ],
    "people": [
        {{"name": "John Doe", "role": "Client"}}
    ],
    "organizations": [
        {{"name": "Microsoft", "context": "Stock discussion"}}
    ],
    "dates": [
        {{"date": "October 2025", "type": "Month-Year"}}
    ]
}}

Only include categories that have entities found. If no entities in a category, omit it."""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial entity extraction AI. Extract investment-related entities accurately."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Very low temperature for extraction
                response_format={"type": "json_object"}
            )
            
            entities = json.loads(response.choices[0].message.content)
            
            logger.info(
                "Entities extracted",
                category_count=len(entities),
                total_entities=sum(len(v) for v in entities.values())
            )
            
            return entities
            
        except Exception as e:
            logger.error("Failed to extract entities", error=str(e), exc_info=True)
            raise
    
    async def detect_pii(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Detect PII using regex patterns and Azure OpenAI.
        
        Args:
            text: Text to analyze for PII
            
        Returns:
            PII detection results
        """
        logger.info("Detecting PII", text_length=len(text))
        
        pii_found = {}
        
        # Regex-based detection
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                pii_found[pii_type] = matches
        
        # Use AI for additional PII detection
        try:
            prompt = f"""Detect all personally identifiable information (PII) in this text.

Text:
{text}

Identify:
- Names (people's names)
- Social Security Numbers (SSN)
- Account numbers
- Phone numbers
- Email addresses
- Physical addresses (street, city, state)
- Dates of birth
- Driver's license numbers
- Credit card numbers

Return in JSON:
{{
    "names": ["John Doe", "Jane Smith"],
    "ssn": ["123-45-6789"],
    "account_numbers": ["Account 98765432"],
    "phone_numbers": ["555-123-4567"],
    "email_addresses": ["john@example.com"],
    "addresses": ["123 Main St, City, State"],
    "dates_of_birth": ["01/15/1980"],
    "drivers_license": ["D1234567"],
    "credit_cards": ["4111-1111-1111-1111"]
}}

Only include categories with PII found."""
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a PII detection AI. Identify all personally identifiable information accurately."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            ai_pii = json.loads(response.choices[0].message.content)
            
            # Merge regex and AI results
            for key, value in ai_pii.items():
                if value:  # Only add non-empty
                    if key in pii_found:
                        # Combine and deduplicate
                        pii_found[key] = list(set(pii_found[key] + value))
                    else:
                        pii_found[key] = value
            
        except Exception as e:
            logger.warning("AI PII detection failed, using regex only", error=str(e))
        
        pii_count = sum(len(v) for v in pii_found.values())
        
        logger.info(
            "PII detection complete",
            pii_types=len(pii_found),
            total_pii=pii_count
        )
        
        return {
            "pii_found": bool(pii_found),
            "pii_count": pii_count,
            "pii_by_type": pii_found,
            "risk_level": self._assess_pii_risk(pii_found),
            "detected_at": datetime.utcnow().isoformat()
        }
    
    async def redact_pii(
        self,
        text: str,
        replacement_patterns: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            replacement_patterns: Custom replacement patterns (e.g., {"ssn": "***-**-****"})
            
        Returns:
            Redacted text and redaction map
        """
        logger.info("Redacting PII", text_length=len(text))
        
        # Detect PII first
        pii_data = await self.detect_pii(text)
        
        if not pii_data["pii_found"]:
            return {
                "redacted_text": text,
                "original_text": text,
                "redactions_made": 0,
                "redaction_map": {}
            }
        
        redacted_text = text
        redaction_map = {}
        redactions_made = 0
        
        # Default replacement patterns
        defaults = {
            "ssn": "***-**-****",
            "account_numbers": "ACCT-****",
            "phone_numbers": "***-***-****",
            "email_addresses": "[EMAIL REDACTED]",
            "addresses": "[ADDRESS REDACTED]",
            "credit_cards": "****-****-****-****",
            "drivers_license": "[DL REDACTED]",
            "dates_of_birth": "[DOB REDACTED]"
        }
        
        if replacement_patterns:
            defaults.update(replacement_patterns)
        
        # Redact each PII type
        for pii_type, pii_items in pii_data["pii_by_type"].items():
            replacement = defaults.get(pii_type, "[REDACTED]")
            
            for item in pii_items:
                if item in redacted_text:
                    redacted_text = redacted_text.replace(item, replacement)
                    redaction_map[item] = replacement
                    redactions_made += 1
        
        logger.info(
            "PII redaction complete",
            redactions=redactions_made
        )
        
        return {
            "redacted_text": redacted_text,
            "original_text": text,
            "redactions_made": redactions_made,
            "redaction_map": redaction_map,
            "pii_risk_level": pii_data["risk_level"]
        }
    
    def _assess_pii_risk(self, pii_found: Dict[str, List[str]]) -> str:
        """Assess risk level based on PII types found."""
        if not pii_found:
            return "none"
        
        high_risk_types = {"ssn", "credit_cards", "drivers_license", "account_numbers"}
        medium_risk_types = {"dates_of_birth", "addresses", "phone_numbers"}
        
        # Check for high-risk PII
        if any(pii_type in high_risk_types for pii_type in pii_found.keys()):
            return "high"
        
        # Check for medium-risk PII
        if any(pii_type in medium_risk_types for pii_type in pii_found.keys()):
            return "medium"
        
        return "low"
    
    async def extract_ticker_symbols(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """
        Extract and validate stock ticker symbols.
        
        Args:
            text: Text to extract tickers from
            
        Returns:
            List of ticker symbols with context
        """
        logger.info("Extracting ticker symbols")
        
        # Pattern for ticker symbols (1-5 uppercase letters)
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        
        potential_tickers = re.findall(ticker_pattern, text)
        
        # Filter out common words that might match pattern
        common_words = {"I", "A", "US", "UK", "CEO", "CFO", "CTO", "VP", "LLC", "INC", "ETF", "IRA", "SEP"}
        
        tickers = []
        for ticker in potential_tickers:
            if ticker not in common_words:
                # Get context around ticker
                ticker_index = text.find(ticker)
                start = max(0, ticker_index - 50)
                end = min(len(text), ticker_index + 50)
                context = text[start:end].strip()
                
                tickers.append({
                    "symbol": ticker,
                    "context": context,
                    "position": ticker_index
                })
        
        # Deduplicate by symbol
        unique_tickers = {}
        for ticker in tickers:
            symbol = ticker["symbol"]
            if symbol not in unique_tickers:
                unique_tickers[symbol] = ticker
            # Could enhance to count mentions
        
        return list(unique_tickers.values())
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for the planner."""
        return {
            "agent_name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "entity_categories": self.entity_categories,
            "pii_types": list(self.pii_patterns.keys()),
            "output_formats": ["json"],
            "specialized_features": [
                "investment_entity_extraction",
                "pii_detection_and_redaction",
                "ticker_symbol_extraction",
                "compliance_tagging"
            ]
        }

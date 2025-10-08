"""
Investment Recommendation Engine Agent

Generates context-aware investment recommendations based on conversation analysis,
sentiment insights, risk tolerance, and compliance considerations.
MAF-compatible agent implementation.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncIterable
from datetime import datetime
from pathlib import Path
import structlog

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread

from openai import AsyncAzureOpenAI

from ..models.task_models import (
    InvestmentRecommendation,
    RecommendationType
)

logger = structlog.get_logger(__name__)


class InvestmentRecommendationAgent(BaseAgent):
    """
    MAF-compatible agent for generating investment recommendations.
    
    Capabilities:
    - Context-aware investment product recommendations
    - Risk-aligned investment suggestions
    - Sentiment-driven recommendation timing
    - Compliance-filtered suggestions
    - Confidence scoring and rationale
    - Next-best-action recommendations
    - Client education suggestions
    """
    
    def __init__(self, settings, name: str = "investment_recommendation", description: str = "Generates context-aware investment recommendations"):
        """Initialize the investment recommendation agent."""
        super().__init__(name=name, description=description)
        
        self.app_settings = settings
        
        # Initialize Azure OpenAI client
        self.client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT
        
        # Investment product categories
        self.product_categories = {
            "stocks": {
                "risk_level": "high",
                "description": "Individual equities",
                "suitable_for": ["aggressive", "very_aggressive"]
            },
            "bonds": {
                "risk_level": "low",
                "description": "Fixed income securities",
                "suitable_for": ["conservative", "moderate"]
            },
            "index_funds": {
                "risk_level": "moderate",
                "description": "Diversified market index funds",
                "suitable_for": ["moderate", "aggressive"]
            },
            "etfs": {
                "risk_level": "moderate",
                "description": "Exchange-traded funds",
                "suitable_for": ["moderate", "aggressive"]
            },
            "mutual_funds": {
                "risk_level": "moderate",
                "description": "Actively managed funds",
                "suitable_for": ["conservative", "moderate", "aggressive"]
            },
            "target_date_funds": {
                "risk_level": "low_to_moderate",
                "description": "Age-based allocation funds",
                "suitable_for": ["conservative", "moderate"]
            },
            "balanced_funds": {
                "risk_level": "moderate",
                "description": "Mixed stock/bond portfolios",
                "suitable_for": ["moderate"]
            },
            "sector_funds": {
                "risk_level": "high",
                "description": "Sector-specific investments",
                "suitable_for": ["aggressive", "very_aggressive"]
            },
            "real_estate": {
                "risk_level": "moderate_to_high",
                "description": "REITs and real estate funds",
                "suitable_for": ["moderate", "aggressive"]
            },
            "alternatives": {
                "risk_level": "very_high",
                "description": "Alternative investments",
                "suitable_for": ["very_aggressive"]
            }
        }
        
        logger.info(
            f"Initialized {self.name}",
            product_categories=len(self.product_categories)
        )
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "investment_product_recommendations",
            "risk_aligned_suggestions",
            "sentiment_aware_timing",
            "compliance_filtering",
            "education_recommendations",
            "next_best_actions",
            "portfolio_optimization"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent - REQUIRED by MAF."""
        logger.info(f"🚀 InvestmentRecommendationAgent.run() called with messages={type(messages)}, kwargs={list(kwargs.keys())}")
        try:
            # Normalize messages
            normalized_messages = self._normalize_messages(messages)
            logger.info(f"📝 Normalized to {len(normalized_messages)} messages")
            
            # Extract context from kwargs
            session_id = kwargs.get("session_id")
            sentiment_data = kwargs.get("sentiment_data", {})
            conversation_context = kwargs.get("conversation_context", "")
            client_profile = kwargs.get("client_profile", {})
            
            if not conversation_context and normalized_messages:
                last_message = normalized_messages[-1]
                conversation_context = last_message.text if hasattr(last_message, 'text') else ""
            
            logger.info(f"📄 conversation_context length: {len(conversation_context)}")
            
            if not conversation_context:
                logger.warning("⚠️ No conversation context provided, returning error response")
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: No conversation context provided")]
                    )]
                )
            
            # Generate recommendations
            result = await self.generate_recommendations(
                conversation_context=conversation_context,
                sentiment_data=sentiment_data,
                session_id=session_id,
                client_profile=client_profile,
                context=kwargs
            )
            
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
            logger.error(f"Error in recommendation generation", error=str(e), exc_info=True)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=f"Error: {str(e)}")]
                )]
            )
    
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
    
    async def generate_recommendations(
        self,
        conversation_context: str,
        sentiment_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        client_profile: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate investment recommendations based on conversation and sentiment.
        
        Args:
            conversation_context: Recent conversation text
            sentiment_data: Sentiment analysis results from InvestmentSentimentAgent
            session_id: Optional session identifier
            client_profile: Client information (age, goals, timeline, etc.)
            context: Additional context
            
        Returns:
            Dictionary containing recommendations with confidence scores
        """
        logger.info(
            "Generating investment recommendations",
            session_id=session_id,
            has_sentiment=bool(sentiment_data),
            has_profile=bool(client_profile)
        )
        
        try:
            # Extract key sentiment insights
            investment_readiness = 0.5  # Default
            risk_tolerance = "moderate"  # Default
            compliance_flags = []
            
            if sentiment_data:
                if "investment_readiness" in sentiment_data:
                    readiness_data = sentiment_data["investment_readiness"]
                    investment_readiness = readiness_data.get("score", 0.5) if isinstance(readiness_data, dict) else 0.5
                
                if "risk_tolerance" in sentiment_data:
                    risk_data = sentiment_data["risk_tolerance"]
                    risk_tolerance = risk_data.get("level", "moderate") if isinstance(risk_data, dict) else "moderate"
                
                compliance_flags = sentiment_data.get("compliance_flags", [])
            
            # Build recommendation prompt
            prompt = self._build_recommendation_prompt(
                conversation_context=conversation_context,
                investment_readiness=investment_readiness,
                risk_tolerance=risk_tolerance,
                compliance_flags=compliance_flags,
                client_profile=client_profile,
                context=context
            )
            
            # Call Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert investment advisor AI assistant specializing in personalized investment recommendations.
You understand client psychology, risk tolerance, investment products, and compliance requirements.
Generate recommendations that are:
- Aligned with client's risk tolerance and goals
- Timed appropriately based on readiness
- Compliance-aware and suitable
- Evidence-based with clear rationale
- Actionable and specific

Provide structured JSON output."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,  # Moderate creativity for recommendations
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Enhance with metadata
            result["metadata"] = {
                "session_id": session_id,
                "generated_at": datetime.utcnow().isoformat(),
                "investment_readiness": investment_readiness,
                "risk_tolerance": risk_tolerance,
                "compliance_filtered": len(compliance_flags) > 0,
                "agent": self.name
            }
            
            # Filter recommendations based on compliance if needed
            if compliance_flags:
                result = self._apply_compliance_filters(result, compliance_flags)
            
            logger.info(
                "Recommendations generated",
                recommendation_count=len(result.get("recommendations", [])),
                investment_readiness=investment_readiness,
                risk_tolerance=risk_tolerance
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations", error=str(e), exc_info=True)
            raise
    
    def _build_recommendation_prompt(
        self,
        conversation_context: str,
        investment_readiness: float,
        risk_tolerance: str,
        compliance_flags: List[Dict[str, Any]],
        client_profile: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build specialized prompt for investment recommendations."""
        
        # Build client profile section
        profile_section = ""
        if client_profile:
            profile_section = f"""

Client Profile:
{json.dumps(client_profile, indent=2)}
"""
        
        # Build compliance warning section
        compliance_section = ""
        if compliance_flags:
            compliance_section = f"""

⚠️ COMPLIANCE ALERTS DETECTED:
{json.dumps(compliance_flags, indent=2)}

CRITICAL: Apply extra caution. Avoid aggressive products. Focus on education and suitability.
"""
        
        # Determine recommendation strategy based on readiness
        if investment_readiness < 0.3:
            strategy_guidance = """
RECOMMENDATION STRATEGY: EDUCATION FIRST
- Client is NOT ready to invest yet
- Focus on educational recommendations
- Suggest learning resources, articles, tools
- Recommend building understanding before product suggestions
- Propose initial low-risk steps (savings accounts, emergency fund)
"""
        elif investment_readiness < 0.5:
            strategy_guidance = """
RECOMMENDATION STRATEGY: INFORMATION GATHERING
- Client is considering but needs more information
- Provide balanced educational content
- Suggest exploratory products (target-date funds, balanced funds)
- Recommend meeting with advisor for deeper discussion
- Focus on building confidence through knowledge
"""
        elif investment_readiness < 0.7:
            strategy_guidance = """
RECOMMENDATION STRATEGY: GUIDED SELECTION
- Client is leaning toward action
- Provide specific product recommendations
- Match to stated risk tolerance
- Include pros/cons for each suggestion
- Offer clear next steps
"""
        else:
            strategy_guidance = """
RECOMMENDATION STRATEGY: ACTION-ORIENTED
- Client is ready to invest
- Provide concrete, actionable recommendations
- Include specific products/allocations
- Clear implementation steps
- Timeline for action
"""
        
        prompt = f"""Analyze the following investment advisor-client conversation and generate personalized recommendations.

Conversation Context:
{conversation_context}{profile_section}

Sentiment Insights:
- Investment Readiness Score: {investment_readiness} (0.0 = not ready, 1.0 = very ready)
- Risk Tolerance: {risk_tolerance}
{compliance_section}

{strategy_guidance}

Provide recommendations in this JSON structure:

{{
    "overall_assessment": {{
        "client_readiness": "not_ready|considering|leaning_toward_action|ready_to_invest",
        "recommended_approach": "education|information_gathering|guided_selection|action_oriented",
        "key_insights": ["insight1", "insight2", "insight3"]
    }},
    
    "investment_recommendations": [
        {{
            "type": "stock|bond|index_fund|etf|mutual_fund|target_date_fund|balanced_fund|sector_fund|real_estate|alternative|education|action",
            "category": "product|education|next_step",
            "recommendation": "Specific recommendation text",
            "rationale": "Why this recommendation fits the client",
            "confidence": <float 0.0-1.0>,
            "risk_level": "low|moderate|high|very_high",
            "priority": "high|medium|low",
            "suitable_for": {{
                "risk_tolerance": ["conservative|moderate|aggressive|very_aggressive"],
                "investment_readiness": <float 0.0-1.0 minimum threshold>,
                "time_horizon": "short_term|medium_term|long_term"
            }},
            "implementation_steps": ["step1", "step2"],
            "expected_outcome": "What this achieves",
            "disclosure_required": true|false,
            "compliance_notes": ["any compliance considerations"]
        }}
    ],
    
    "education_recommendations": [
        {{
            "topic": "Topic to learn about",
            "resource_type": "article|video|tool|meeting|course",
            "description": "What this covers",
            "priority": "high|medium|low",
            "estimated_time": "Time to complete"
        }}
    ],
    
    "next_best_actions": [
        {{
            "action": "Specific action for advisor or client",
            "timeline": "immediate|this_week|this_month|next_meeting",
            "responsible": "advisor|client|both",
            "expected_outcome": "What this achieves"
        }}
    ],
    
    "conversation_guidance": {{
        "suggested_topics": ["topic1", "topic2"],
        "questions_to_explore": ["question1", "question2"],
        "concerns_to_address": ["concern1", "concern2"]
    }},
    
    "compliance_considerations": [
        "Any suitability, disclosure, or regulatory notes"
    ],
    
    "summary": "2-3 sentence summary of recommendations and strategy"
}}

IMPORTANT GUIDELINES:
1. **Investment Readiness Alignment**: Only recommend investment products if readiness > 0.5
2. **Risk Tolerance Matching**: Match products to stated risk tolerance (conservative→bonds, aggressive→stocks)
3. **Compliance First**: If compliance flags exist, err on conservative side
4. **Suitability**: Ensure recommendations match client goals, timeline, and circumstances
5. **Education Priority**: If client shows confusion or low readiness, prioritize education
6. **Specificity**: Be specific (e.g., "S&P 500 index fund" not just "fund")
7. **Balanced View**: Include both opportunities and risks
8. **Actionable**: Provide clear next steps

Generate thoughtful, personalized recommendations based strictly on the conversation context and sentiment data."""
        
        return prompt
    
    def _apply_compliance_filters(
        self,
        recommendations: Dict[str, Any],
        compliance_flags: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply compliance filtering to recommendations."""
        
        # Check severity of compliance concerns
        has_critical = any(
            flag.get("severity") in ["critical", "high"]
            for flag in compliance_flags
        )
        
        if has_critical:
            logger.warning(
                "Critical compliance concerns detected - filtering aggressive recommendations",
                flag_count=len(compliance_flags)
            )
            
            # Filter out high-risk recommendations
            filtered_recs = []
            for rec in recommendations.get("investment_recommendations", []):
                if rec.get("risk_level") not in ["very_high", "high"]:
                    # Keep lower-risk recommendations
                    filtered_recs.append(rec)
                    
                    # Add compliance note
                    if "compliance_notes" not in rec:
                        rec["compliance_notes"] = []
                    rec["compliance_notes"].append(
                        "Filtered for suitability due to conversation compliance concerns"
                    )
            
            recommendations["investment_recommendations"] = filtered_recs
            
            # Add overall compliance note
            if "compliance_considerations" not in recommendations:
                recommendations["compliance_considerations"] = []
            
            recommendations["compliance_considerations"].insert(
                0,
                "CRITICAL: Compliance concerns detected in conversation. Recommendations filtered to conservative options only. Recommend compliance review before proceeding."
            )
        
        return recommendations
    
    async def filter_recommendations_by_risk(
        self,
        recommendations: List[Dict[str, Any]],
        risk_tolerance: str
    ) -> List[Dict[str, Any]]:
        """Filter recommendations to match risk tolerance."""
        
        filtered = []
        for rec in recommendations:
            suitable_for = rec.get("suitable_for", {})
            suitable_risk = suitable_for.get("risk_tolerance", [])
            
            if risk_tolerance in suitable_risk:
                filtered.append(rec)
            else:
                logger.debug(
                    "Filtering out recommendation due to risk mismatch",
                    recommendation=rec.get("recommendation", "")[:50],
                    client_risk=risk_tolerance,
                    suitable_for=suitable_risk
                )
        
        return filtered
    
    async def prioritize_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        max_count: int = 5
    ) -> List[Dict[str, Any]]:
        """Prioritize and limit recommendations by confidence and priority."""
        
        # Sort by priority (high first) and confidence (high first)
        priority_map = {"high": 3, "medium": 2, "low": 1}
        
        sorted_recs = sorted(
            recommendations,
            key=lambda r: (
                priority_map.get(r.get("priority", "low"), 1),
                r.get("confidence", 0.0)
            ),
            reverse=True
        )
        
        return sorted_recs[:max_count]
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for the planner."""
        return {
            "agent_name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "product_categories": list(self.product_categories.keys()),
            "output_formats": ["json"],
            "specialized_features": [
                "sentiment_aware_timing",
                "risk_tolerance_matching",
                "compliance_filtering",
                "investment_readiness_gating"
            ]
        }

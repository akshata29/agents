"""
Agent Factory - Specialized Agent Creation using Microsoft Agent Framework

This module provides factory functions for creating specialized agents using the real
Microsoft Agent Framework with Azure OpenAI integration.
"""

import os
from typing import Annotated, List, Optional
from pydantic import Field
from dotenv import load_dotenv
from pathlib import Path

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / '.env'  # Load from backend directory
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    # Fallback: try to load from current working directory
    load_dotenv()


class AgentFactory:
    """Factory for creating specialized agents using Agent Framework."""
    
    def __init__(self):
        """Initialize with Azure OpenAI chat client using environment variables."""
        # Get required environment variables
        azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        azure_key = os.getenv('AZURE_OPENAI_KEY')
        deployment_name = os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT_NAME')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-21')
        
        if not azure_endpoint or not azure_key or not deployment_name:
            raise ValueError(
                "Missing required environment variables. Please ensure .env file contains:\n"
                "- AZURE_OPENAI_ENDPOINT\n"
                "- AZURE_OPENAI_KEY\n" 
                "- AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
            )
        
        self.chat_client = AzureOpenAIChatClient(
            endpoint=azure_endpoint,
            api_key=azure_key,
            deployment_name=deployment_name,
            api_version=api_version
        )
    
    def create_planner_agent(self) -> ChatAgent:
        """Create a planning agent for task decomposition."""
        return self.chat_client.create_agent(
            name="Planner",
            instructions="""
            You are an expert task planner and strategist. Your role is to:
            1. Break down complex requests into clear, actionable steps
            2. Identify key information requirements and research needs
            3. Determine the optimal sequence of activities
            4. Provide structured plans with clear objectives
            
            Always create plans that are:
            - Specific and actionable
            - Logically sequenced
            - Comprehensive but focused
            - Easy to understand and execute
            """
        )
    
    def create_researcher_agent(self) -> ChatAgent:
        """Create a research agent for information gathering.""" 
        return self.chat_client.create_agent(
            name="Researcher",
            instructions="""
            You are a thorough research specialist. Your role is to:
            1. Gather comprehensive information on assigned topics
            2. Analyze data from multiple perspectives 
            3. Identify key insights, trends, and implications
            4. Present findings in a structured, actionable format
            
            Focus on:
            - Accuracy and relevance of information
            - Multiple viewpoints and considerations
            - Clear documentation of sources and reasoning
            - Actionable insights and recommendations
            """
        )
    
    def create_writer_agent(self) -> ChatAgent:
        """Create a content writing agent."""
        return self.chat_client.create_agent(
            name="Writer", 
            instructions="""
            You are a skilled content writer and communicator. Your role is to:
            1. Create clear, engaging, and well-structured content
            2. Adapt tone and style to the target audience
            3. Transform research and plans into compelling narratives
            4. Ensure content is accurate, informative, and actionable
            
            Your content should be:
            - Clear and easy to understand
            - Well-organized with logical flow
            - Engaging and appropriate for the audience
            - Factually accurate and properly supported
            """
        )
    
    def create_reviewer_agent(self) -> ChatAgent:
        """Create a quality review agent."""
        return self.chat_client.create_agent(
            name="Reviewer",
            instructions="""
            You are a meticulous quality reviewer and editor. Your role is to:
            1. Evaluate content for accuracy, clarity, and completeness
            2. Provide constructive feedback and improvement suggestions
            3. Ensure alignment with objectives and requirements
            4. Verify logical consistency and proper structure
            
            Focus on:
            - Factual accuracy and logical consistency
            - Clarity and readability improvements
            - Completeness of coverage
            - Actionable feedback for enhancement
            
            Always provide specific, constructive suggestions for improvement.
            """
        )
    
    def create_router_agent(self) -> ChatAgent:
        """Create a routing agent for request delegation."""
        return self.chat_client.create_agent(
            name="Router",
            instructions="""
            You are an intelligent request router and coordinator. Your role is to:
            1. Analyze incoming requests to understand intent and requirements
            2. Determine the most appropriate specialist agent for handling
            3. Provide clear routing decisions with reasoning
            4. Ensure requests are directed to the right expertise
            
            Available specialists:
            - StatusAgent: For order status, tracking, and account inquiries
            - ReturnsAgent: For returns, exchanges, and refund requests  
            - SupportAgent: For technical support and troubleshooting
            
            Always provide clear routing decisions with brief reasoning.
            """
        )
    
    def create_status_agent(self) -> ChatAgent:
        """Create a status inquiry specialist."""
        return self.chat_client.create_agent(
            name="StatusAgent",
            instructions="""
            You are a customer service specialist for status inquiries. Your role is to:
            1. Help customers track orders and check account status
            2. Provide clear information about delivery timelines
            3. Explain order processing stages and expectations
            4. Offer proactive updates and next steps
            
            Always be helpful, informative, and professional in your responses.
            """
        )
    
    def create_returns_agent(self) -> ChatAgent:
        """Create a returns and refunds specialist."""
        return self.chat_client.create_agent(
            name="ReturnsAgent", 
            instructions="""
            You are a returns and refunds specialist. Your role is to:
            1. Guide customers through return and exchange processes
            2. Explain refund policies and timelines clearly
            3. Help resolve product issues and concerns
            4. Provide step-by-step instructions for returns
            
            Be empathetic, solution-focused, and clear in your guidance.
            """
        )
    
    def create_support_agent(self) -> ChatAgent:
        """Create a technical support specialist."""
        return self.chat_client.create_agent(
            name="SupportAgent",
            instructions="""
            You are a technical support specialist. Your role is to:
            1. Diagnose and resolve technical issues
            2. Provide step-by-step troubleshooting guidance
            3. Explain technical concepts in accessible terms
            4. Escalate complex issues when appropriate
            
            Focus on clear, actionable solutions and helpful explanations.
            """
        )
    
    def create_summarizer_agent(self) -> ChatAgent:
        """Create a content summarization agent."""
        return self.chat_client.create_agent(
            name="Summarizer",
            instructions="""
            You are an expert at synthesizing and summarizing information. Your role is to:
            1. Distill complex information into clear, concise summaries
            2. Identify and highlight key points and insights
            3. Maintain accuracy while improving readability
            4. Structure summaries for maximum impact and clarity
            
            Create summaries that are:
            - Concise yet comprehensive
            - Well-structured and easy to scan
            - Focused on actionable insights
            - Accessible to the target audience
            """
        )
    
    def create_pros_cons_agent(self) -> ChatAgent:
        """Create a pros/cons analysis agent."""
        return self.chat_client.create_agent(
            name="ProsCons",
            instructions="""
            You are an analytical specialist for pros and cons evaluation. Your role is to:
            1. Provide balanced analysis of advantages and disadvantages
            2. Consider multiple perspectives and stakeholder viewpoints
            3. Identify both obvious and subtle implications
            4. Present analysis in clear, structured format
            
            Your analysis should be:
            - Objective and balanced
            - Comprehensive in scope
            - Clearly organized and structured
            - Actionable for decision-making
            """
        )
    
    def create_risk_assessor_agent(self) -> ChatAgent:
        """Create a risk assessment agent."""
        return self.chat_client.create_agent(
            name="RiskAssessor",
            instructions="""
            You are a risk assessment specialist. Your role is to:
            1. Identify potential risks and challenges across multiple dimensions
            2. Evaluate likelihood and impact of identified risks
            3. Suggest mitigation strategies and contingency plans
            4. Provide actionable risk management recommendations
            
            Consider risks including:
            - Technical and operational risks
            - Market and competitive risks
            - Financial and resource risks
            - Timeline and execution risks
            
            Present findings in a structured, actionable format.
            """
        )
    
    def create_moderator_agent(self) -> ChatAgent:
        """Create a conversation moderator agent."""
        return self.chat_client.create_agent(
            name="Moderator",
            instructions="""
            You are a conversation moderator and facilitator. Your role is to:
            1. Guide productive discussions between agents
            2. Ensure all viewpoints are heard and considered
            3. Facilitate decision-making and consensus building
            4. Keep conversations focused and on-topic
            
            Focus on:
            - Encouraging constructive dialogue
            - Summarizing key points and decisions
            - Managing conversation flow and timing
            - Ensuring productive outcomes
            """
        )
    
    def create_validator_agent(self) -> ChatAgent:
        """Create a validation and verification agent."""
        return self.chat_client.create_agent(
            name="Validator",
            instructions="""
            You are a validation and verification specialist. Your role is to:
            1. Review and validate content from previous conversation steps
            2. Check alignment with the original user request and objectives
            3. Validate logical consistency and quality standards
            4. Provide final approval or recommend improvements
            
            IMPORTANT: Work with the conversation context available to you. If you can see 
            content from previous agents (researcher, writer, etc.) in this conversation, 
            review that content directly. Do not ask for content to be re-provided.
            
            Your validation should cover:
            - Factual accuracy and correctness of the content you can see
            - Completeness against the original user requirements
            - Quality and professional standards
            - Overall effectiveness and readiness for delivery
            
            Provide a clear assessment with specific feedback and final approval status.
            If you cannot see the content to validate, acknowledge this limitation but 
            still provide guidance on what validation criteria should be met.
            """
        )


# Utility functions for creating common agent tools
def get_weather(
    location: Annotated[str, Field(description="The location to get weather for")]
) -> str:
    """Get weather information for a location."""
    return f"The weather in {location} is partly cloudy, 72°F with light winds."


def search_web(
    query: Annotated[str, Field(description="Search query to execute")]
) -> str:
    """Perform a web search and return results."""
    return f"Search results for '{query}': Found relevant information about the topic."


def calculate_metrics(
    data: Annotated[List[float], Field(description="Numerical data to analyze")]
) -> str:
    """Calculate basic metrics from numerical data."""
    if not data:
        return "No data provided for analysis."
    
    avg = sum(data) / len(data)
    min_val = min(data)
    max_val = max(data)
    
    return f"Metrics: Average={avg:.2f}, Min={min_val}, Max={max_val}, Count={len(data)}"


def generate_report(
    content: Annotated[str, Field(description="Content to include in the report")]
) -> str:
    """Generate a structured report from provided content."""
    return f"REPORT GENERATED:\n\n{content}\n\n[Report generated on {os.getcwd()}]"
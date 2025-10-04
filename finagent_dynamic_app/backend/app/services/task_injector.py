"""
Task Injection Module

Handles intelligent task injection into existing plans with:
- Duplicate detection
- Capability validation
- Smart positioning (beginning, middle, end)
- Dependency resolution
"""

import uuid
import structlog
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ChatMessage, Role

from app.models.task_models import Step, StepStatus, AgentType
from app.infra.settings import Settings

logger = structlog.get_logger(__name__)

# Initialize settings
settings = Settings()


class TaskInjector:
    """
    Intelligent task injection service.
    
    Analyzes user requests and determines:
    1. If task already exists (duplicate)
    2. If we have capabilities (agents/tools)
    3. Where to insert (beginning, middle, end)
    4. What dependencies to set
    """
    
    def __init__(self):
        logger.info("TaskInjector: Initializing LLM client")
        logger.info("TaskInjector: Settings - endpoint exists", has_endpoint=bool(settings.azure_openai_endpoint))
        logger.info("TaskInjector: Settings - api_key exists", has_key=bool(settings.azure_openai_api_key))
        logger.info("TaskInjector: Settings - deployment", deployment=settings.azure_openai_deployment)
        
        self.llm_client = AzureOpenAIChatClient(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment_name=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
        )
        logger.info("TaskInjector: LLM client created", client_type=type(self.llm_client).__name__)
        
        # Define available agents and their capabilities
        self.agent_capabilities = {
            "Company_Agent": {
                "tools": ["get_yahoo_finance_news", "get_recommendations", "get_stock_info", "get_historical_prices"],
                "description": "Company information, news, recommendations, stock data"
            },
            "Forecaster_Agent": {
                "tools": ["predict_stock_movement", "analyze_positive_developments", "analyze_potential_concerns", "technical_analysis"],
                "description": "Stock predictions, forecasts, technical analysis"
            },
            "Summarizer_Agent": {
                "tools": ["generate_sentiment_summary", "summarize_information", "create_news_summary", "synthesize_findings"],
                "description": "Sentiment analysis, summaries, synthesis"
            },
            "Report_Agent": {
                "tools": ["document_generation", "data_aggregation", "pattern_analysis"],
                "description": "Comprehensive reports, research briefs"
            },
            "SEC_Agent": {
                "tools": ["sec_filings", "form_10k", "form_10q"],
                "description": "SEC filings and regulatory documents"
            },
            "EarningCall_Agent": {
                "tools": ["earnings_data", "transcripts", "earnings_calendar"],
                "description": "Earnings reports and call transcripts"
            },
            "Fundamentals_Agent": {
                "tools": ["financial_ratios", "income_statement", "balance_sheet"],
                "description": "Fundamental financial analysis"
            },
            "Technicals_Agent": {
                "tools": ["price_data", "indicators", "chart_patterns"],
                "description": "Technical analysis and chart patterns"
            }
        }
    
    async def analyze_injection_request(
        self,
        task_request: str,
        objective: str,
        current_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze the task injection request using LLM.
        
        Args:
            task_request: User's request to add a task
            objective: Original plan objective
            current_steps: List of current steps in the plan
            
        Returns:
            Analysis result with action, message, position, etc.
        """
        logger.info("TaskInjector: Starting analysis", task_request=task_request, step_count=len(current_steps))
        
        # Build the analysis prompt
        logger.info("TaskInjector: Building analysis prompt")
        analysis_prompt = self._build_analysis_prompt(task_request, objective, current_steps)
        logger.info("TaskInjector: Prompt built", prompt_length=len(analysis_prompt))
        
        # Call LLM for analysis
        logger.info("TaskInjector: Preparing LLM messages")
        messages = [
            ChatMessage(role=Role.SYSTEM, text="You are a task planning assistant. Analyze user requests for adding tasks to existing plans."),
            ChatMessage(role=Role.USER, text=analysis_prompt)
        ]
        logger.info("TaskInjector: Messages prepared, calling LLM")
        
        try:
            logger.info("TaskInjector: Calling LLM client get_response")
            response = await self.llm_client.get_response(
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            logger.info("TaskInjector: LLM response received", response_type=type(response).__name__)
            
            analysis_text = response.text
            logger.info("LLM analysis completed", analysis_length=len(analysis_text))
            
            # Parse the analysis
            logger.info("TaskInjector: Parsing LLM response")
            result = self._parse_analysis(analysis_text, current_steps)
            logger.info("TaskInjector: Parse complete", result_type=type(result).__name__, action=result.get('action'))
            return result
            
        except Exception as e:
            logger.error("Error in LLM analysis", error=str(e), exc_info=True)
            return {
                "action": "unsupported",
                "message": f"Error analyzing request: {str(e)}",
                "success": False
            }
    
    def _build_analysis_prompt(
        self,
        task_request: str,
        objective: str,
        current_steps: List[Dict[str, Any]]
    ) -> str:
        """Build the LLM prompt for task analysis."""
        # Format current steps
        steps_text = "\n".join([
            f"Step {step['order']}: {step['action']} (Agent: {step['agent']}, Status: {step['status']})"
            for step in sorted(current_steps, key=lambda x: x['order'])
        ])
        
        # Format available capabilities
        capabilities_text = "\n".join([
            f"- {agent}: {info['description']} (Tools: {', '.join(info['tools'])})"
            for agent, info in self.agent_capabilities.items()
        ])
        
        return f"""
OBJECTIVE: {objective}

CURRENT PLAN:
{steps_text}

AVAILABLE CAPABILITIES:
{capabilities_text}

USER REQUEST: "{task_request}"

ANALYSIS TASK:
Analyze if the user's request can be added to the plan. Provide your analysis in this EXACT format:

ACTION: [one of: DUPLICATE, UNSUPPORTED, ADD_BEGINNING, ADD_MIDDLE, ADD_END, CLARIFICATION]

REASONING: [Your reasoning for the action]

NEW_TASK: [If ACTION is ADD_*, describe the exact task to add]

AGENT: [If ACTION is ADD_*, specify which agent should handle it]

FUNCTION: [If ACTION is ADD_*, specify which tool/function to use]

INSERT_AFTER: [If ACTION is ADD_MIDDLE, specify the step number to insert after]

DEPENDENCIES: [If ACTION is ADD_*, list step numbers this task depends on, comma-separated, or "none"]

MESSAGE: [User-friendly message explaining the action]

RULES:
1. If the request is already covered in current steps, use ACTION: DUPLICATE
2. If we don't have the agent/tool for it, use ACTION: UNSUPPORTED
3. If it's a data gathering task, use ACTION: ADD_BEGINNING
4. If it's an analysis/synthesis task that needs previous data, use ACTION: ADD_MIDDLE or ADD_END
5. If request is unclear, use ACTION: CLARIFICATION

EXAMPLES:
- "get latest news" when news step exists → ACTION: DUPLICATE
- "execute a trade" when no trading agent → ACTION: UNSUPPORTED  
- "add stock prediction" when news exists → ACTION: ADD_END (depends on news)
- "get analyst recommendations" when no such step → ACTION: ADD_BEGINNING (data gathering)
"""
    
    def _parse_analysis(self, analysis_text: str, current_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse the LLM analysis response."""
        lines = analysis_text.strip().split('\n')
        result = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()
                
                if key == 'ACTION':
                    result['action'] = value.lower().replace('add_', '')
                elif key == 'REASONING':
                    result['reasoning'] = value
                elif key == 'NEW_TASK':
                    result['new_task'] = value
                elif key == 'AGENT':
                    result['agent'] = value
                elif key == 'FUNCTION':
                    result['function'] = value
                elif key == 'INSERT_AFTER':
                    try:
                        result['insert_after'] = int(value) if value.lower() != 'none' else None
                    except:
                        result['insert_after'] = None
                elif key == 'DEPENDENCIES':
                    if value.lower() == 'none':
                        result['dependencies'] = []
                    else:
                        try:
                            result['dependencies'] = [int(d.strip()) for d in value.split(',')]
                        except:
                            result['dependencies'] = []
                elif key == 'MESSAGE':
                    result['message'] = value
        
        # Map action to success/failure
        action = result.get('action', 'unsupported')
        if action in ['beginning', 'middle', 'end']:
            result['success'] = True
            result['action'] = 'added'
        elif action == 'duplicate':
            result['success'] = False
            result['message'] = result.get('message', 'This task is already in your plan.')
        elif action == 'unsupported':
            result['success'] = False
            result['message'] = result.get('message', 'This capability is not currently supported.')
        elif action == 'clarification':
            result['success'] = False
            result['action'] = 'clarification_needed'
            result['message'] = result.get('message', 'Could you provide more details about what you want?')
        
        logger.info("Parsed analysis", action=result.get('action'), success=result.get('success'))
        return result
    
    def create_new_step(
        self,
        analysis: Dict[str, Any],
        current_steps: List[Step],
        plan_id: str,
        session_id: str,
        user_id: str
    ) -> Tuple[Step, int]:
        """
        Create a new step based on analysis.
        
        Returns:
            Tuple of (new_step, insert_position)
        """
        # Determine insertion position
        if analysis.get('insert_after'):
            insert_position = analysis['insert_after'] + 1
        elif 'beginning' in str(analysis.get('action', '')):
            insert_position = 1
        else:
            insert_position = len(current_steps) + 1
        
        # Map dependencies from step numbers to step IDs
        dependency_ids = []
        if analysis.get('dependencies'):
            for dep_order in analysis['dependencies']:
                dep_step = next((s for s in current_steps if s.order == dep_order), None)
                if dep_step:
                    dependency_ids.append(dep_step.id)
        
        # Create the new step
        new_step = Step(
            id=str(uuid.uuid4()),
            plan_id=plan_id,
            session_id=session_id,
            user_id=user_id,
            order=insert_position,
            action=analysis.get('new_task', ''),
            agent=AgentType(analysis.get('agent', 'Generic_Agent')),
            status=StepStatus.PLANNED,
            dependencies=dependency_ids,
            tools=[analysis.get('function', '')],
            manually_injected=True,  # Mark as manually injected
            timestamp=datetime.utcnow(),
            data_type="step"
        )
        
        logger.info(
            "Created new step via injection",
            step_id=new_step.id,
            order=new_step.order,
            agent=new_step.agent.value,
            dependencies=len(dependency_ids),
            manually_injected=True
        )
        
        return new_step, insert_position

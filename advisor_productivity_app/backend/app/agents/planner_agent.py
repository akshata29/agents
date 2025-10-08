"""
Planner Agent for Advisor Productivity

Orchestrates the workflow of all agents to analyze advisor-client conversations.
Manages dependencies, execution order, and data flow between agents.
"""

from typing import Any, Dict, List, Optional, AsyncIterator
import asyncio
from datetime import datetime
import structlog

from agent_framework import BaseAgent
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)


class PlannerAgent(BaseAgent):
    """
    Planner Agent that orchestrates the advisor productivity workflow.
    
    Standard workflow:
    1. Speech Transcription (continuous, real-time)
    2. Sentiment Analysis (triggered by transcript updates)
    3. Entity/PII Extraction (triggered by transcript updates)
    4. Recommendation Generation (on-demand or auto-triggered)
    5. Session Summarization (triggered at session end)
    
    Capabilities:
    - Workflow orchestration
    - Agent dependency management
    - Dynamic plan generation
    - Progress tracking
    - Error handling and recovery
    """
    
    def __init__(self, settings: Settings):
        super().__init__(
            name="planner_agent",
            description="Orchestrates advisor productivity workflow and manages agent execution",
            settings=settings
        )
        self.settings = settings
        logger.info("PlannerAgent initialized")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return {
            "name": self.name,
            "description": self.description,
            "version": "1.0.0",
            "capabilities": [
                "workflow_orchestration",
                "agent_coordination",
                "dynamic_planning",
                "dependency_management",
                "progress_tracking",
                "error_recovery",
                "session_management"
            ],
            "supported_workflows": [
                "standard_advisor_session",
                "compliance_review",
                "quick_analysis",
                "full_analysis"
            ]
        }
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the planner agent.
        
        Args:
            input_data: {
                "workflow_type": "standard_advisor_session" | "compliance_review" | "quick_analysis" | "full_analysis",
                "session_id": "session_xxx",
                "transcript_text": "...",  # Optional: pre-loaded transcript
                "auto_recommendations": bool,  # Default: False
                "auto_summary": bool,  # Default: True
                "enable_pii_detection": bool,  # Default: True
            }
        
        Returns:
            {
                "plan": {...},
                "status": "completed" | "in_progress" | "failed",
                "steps_completed": [...],
                "results": {...},
                "errors": [...]
            }
        """
        try:
            workflow_type = input_data.get("workflow_type", "standard_advisor_session")
            session_id = input_data.get("session_id")
            
            if not session_id:
                return {
                    "error": "session_id is required",
                    "status": "failed"
                }
            
            # Generate execution plan
            plan = self._generate_plan(workflow_type, input_data)
            
            logger.info(
                "Executing workflow plan",
                workflow_type=workflow_type,
                session_id=session_id,
                steps=len(plan["steps"])
            )
            
            # Execute plan steps
            results = await self._execute_plan(plan, input_data)
            
            return {
                "plan": plan,
                "status": results["status"],
                "steps_completed": results["completed_steps"],
                "results": results["step_results"],
                "errors": results.get("errors", []),
                "execution_time": results["execution_time"]
            }
        
        except Exception as e:
            logger.error("Error in planner agent", error=str(e), exc_info=True)
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def run_stream(self, input_data: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream execution progress.
        
        Yields progress updates as each step completes.
        """
        try:
            workflow_type = input_data.get("workflow_type", "standard_advisor_session")
            session_id = input_data.get("session_id")
            
            if not session_id:
                yield {
                    "type": "error",
                    "error": "session_id is required",
                    "status": "failed"
                }
                return
            
            # Generate execution plan
            plan = self._generate_plan(workflow_type, input_data)
            
            yield {
                "type": "plan_generated",
                "plan": plan,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Execute plan steps with streaming updates
            async for update in self._execute_plan_stream(plan, input_data):
                yield update
        
        except Exception as e:
            logger.error("Error in planner agent streaming", error=str(e), exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "status": "failed"
            }
    
    def _generate_plan(
        self,
        workflow_type: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate execution plan based on workflow type."""
        
        # Common configuration
        session_id = input_data.get("session_id")
        auto_recommendations = input_data.get("auto_recommendations", False)
        auto_summary = input_data.get("auto_summary", True)
        enable_pii = input_data.get("enable_pii_detection", True)
        
        # Define workflow templates
        workflows = {
            "standard_advisor_session": {
                "name": "Standard Advisor Session",
                "description": "Full workflow for advisor-client meetings",
                "steps": [
                    {
                        "id": "transcription",
                        "agent": "speech_transcription_agent",
                        "description": "Real-time speech transcription",
                        "mode": "continuous",
                        "required": True,
                        "dependencies": []
                    },
                    {
                        "id": "sentiment",
                        "agent": "sentiment_analysis_agent",
                        "description": "Analyze conversation sentiment",
                        "mode": "triggered",
                        "trigger": "transcription_update",
                        "required": True,
                        "dependencies": ["transcription"]
                    },
                    {
                        "id": "entity_pii",
                        "agent": "entity_pii_agent",
                        "description": "Extract entities and detect PII",
                        "mode": "triggered",
                        "trigger": "transcription_update",
                        "required": enable_pii,
                        "dependencies": ["transcription"]
                    },
                    {
                        "id": "recommendations",
                        "agent": "recommendation_engine_agent",
                        "description": "Generate investment recommendations",
                        "mode": "on_demand" if not auto_recommendations else "triggered",
                        "trigger": "sentiment_ready" if auto_recommendations else "manual",
                        "required": False,
                        "dependencies": ["transcription", "sentiment"]
                    },
                    {
                        "id": "summary",
                        "agent": "summarization_agent",
                        "description": "Generate session summary",
                        "mode": "on_demand" if not auto_summary else "end_of_session",
                        "trigger": "session_end" if auto_summary else "manual",
                        "required": auto_summary,
                        "dependencies": ["transcription", "sentiment", "entity_pii"]
                    }
                ]
            },
            
            "compliance_review": {
                "name": "Compliance Review",
                "description": "Focus on compliance and PII detection",
                "steps": [
                    {
                        "id": "transcription",
                        "agent": "speech_transcription_agent",
                        "description": "Transcribe conversation",
                        "mode": "continuous",
                        "required": True,
                        "dependencies": []
                    },
                    {
                        "id": "entity_pii",
                        "agent": "entity_pii_agent",
                        "description": "Extract entities and detect PII",
                        "mode": "triggered",
                        "trigger": "transcription_complete",
                        "required": True,
                        "dependencies": ["transcription"]
                    },
                    {
                        "id": "sentiment",
                        "agent": "sentiment_analysis_agent",
                        "description": "Analyze compliance risk",
                        "mode": "triggered",
                        "trigger": "transcription_complete",
                        "required": True,
                        "dependencies": ["transcription"]
                    },
                    {
                        "id": "summary",
                        "agent": "summarization_agent",
                        "description": "Compliance-focused summary",
                        "mode": "end_of_session",
                        "trigger": "session_end",
                        "required": True,
                        "dependencies": ["transcription", "sentiment", "entity_pii"],
                        "config": {"persona": "compliance"}
                    }
                ]
            },
            
            "quick_analysis": {
                "name": "Quick Analysis",
                "description": "Fast sentiment and entity extraction",
                "steps": [
                    {
                        "id": "transcription",
                        "agent": "speech_transcription_agent",
                        "description": "Transcribe conversation",
                        "mode": "continuous",
                        "required": True,
                        "dependencies": []
                    },
                    {
                        "id": "sentiment",
                        "agent": "sentiment_analysis_agent",
                        "description": "Quick sentiment analysis",
                        "mode": "triggered",
                        "trigger": "transcription_complete",
                        "required": True,
                        "dependencies": ["transcription"]
                    }
                ]
            },
            
            "full_analysis": {
                "name": "Full Analysis",
                "description": "Complete analysis with all agents",
                "steps": [
                    {
                        "id": "transcription",
                        "agent": "speech_transcription_agent",
                        "description": "Real-time speech transcription",
                        "mode": "continuous",
                        "required": True,
                        "dependencies": []
                    },
                    {
                        "id": "sentiment",
                        "agent": "sentiment_analysis_agent",
                        "description": "Comprehensive sentiment analysis",
                        "mode": "triggered",
                        "trigger": "transcription_update",
                        "required": True,
                        "dependencies": ["transcription"]
                    },
                    {
                        "id": "entity_pii",
                        "agent": "entity_pii_agent",
                        "description": "Extract all entities and PII",
                        "mode": "triggered",
                        "trigger": "transcription_update",
                        "required": True,
                        "dependencies": ["transcription"]
                    },
                    {
                        "id": "recommendations",
                        "agent": "recommendation_engine_agent",
                        "description": "Generate recommendations",
                        "mode": "triggered",
                        "trigger": "sentiment_ready",
                        "required": True,
                        "dependencies": ["transcription", "sentiment"]
                    },
                    {
                        "id": "summary",
                        "agent": "summarization_agent",
                        "description": "Multi-persona summary",
                        "mode": "end_of_session",
                        "trigger": "session_end",
                        "required": True,
                        "dependencies": ["transcription", "sentiment", "entity_pii", "recommendations"],
                        "config": {"personas": ["advisor", "compliance", "client"]}
                    }
                ]
            }
        }
        
        # Get workflow template
        workflow = workflows.get(workflow_type, workflows["standard_advisor_session"])
        
        return {
            "workflow_type": workflow_type,
            "name": workflow["name"],
            "description": workflow["description"],
            "session_id": session_id,
            "steps": workflow["steps"],
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def _execute_plan(
        self,
        plan: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the plan synchronously (returns when complete)."""
        start_time = datetime.utcnow()
        completed_steps = []
        step_results = {}
        errors = []
        
        for step in plan["steps"]:
            if not step["required"]:
                continue
            
            try:
                logger.info(
                    "Executing step",
                    step_id=step["id"],
                    agent=step["agent"]
                )
                
                # Simulate step execution (in real implementation, call actual agents)
                # This would integrate with actual agent instances
                result = {
                    "step_id": step["id"],
                    "agent": step["agent"],
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                completed_steps.append(step["id"])
                step_results[step["id"]] = result
                
            except Exception as e:
                logger.error(
                    "Step execution failed",
                    step_id=step["id"],
                    error=str(e)
                )
                errors.append({
                    "step_id": step["id"],
                    "error": str(e)
                })
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        status = "completed" if len(errors) == 0 else "completed_with_errors"
        
        return {
            "status": status,
            "completed_steps": completed_steps,
            "step_results": step_results,
            "errors": errors,
            "execution_time": execution_time
        }
    
    async def _execute_plan_stream(
        self,
        plan: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute the plan with streaming updates."""
        start_time = datetime.utcnow()
        completed_steps = []
        
        for step in plan["steps"]:
            if not step["required"]:
                continue
            
            try:
                yield {
                    "type": "step_started",
                    "step_id": step["id"],
                    "agent": step["agent"],
                    "description": step["description"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Simulate step execution
                await asyncio.sleep(0.1)  # Simulate processing
                
                result = {
                    "step_id": step["id"],
                    "agent": step["agent"],
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                completed_steps.append(step["id"])
                
                yield {
                    "type": "step_completed",
                    "step_id": step["id"],
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(
                    "Step execution failed",
                    step_id=step["id"],
                    error=str(e)
                )
                
                yield {
                    "type": "step_failed",
                    "step_id": step["id"],
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        yield {
            "type": "execution_completed",
            "completed_steps": completed_steps,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat()
        }

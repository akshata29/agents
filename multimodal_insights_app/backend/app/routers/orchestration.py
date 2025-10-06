"""
Orchestration Router - Multimodal Insights Application

REST API endpoints for plan creation and execution.
Built from scratch for multimodal content processing.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status, Request
from typing import Optional, List
import structlog

from ..models.task_models import (
    InputTask, PlanWithSteps, ExecutionStatusResponse,
    ActionRequest, ActionResponse, PlanExecutionResponse
)
from ..services.task_orchestrator import TaskOrchestrator
from ..services.file_handler import FileHandler
from ..infra.settings import Settings
from ..auth.auth_utils import get_authenticated_user_details

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])

# Dependency to get orchestrator instance
# This will be set by main.py during startup
_orchestrator: Optional[TaskOrchestrator] = None


def set_orchestrator(orchestrator: TaskOrchestrator):
    """Set the orchestrator instance (called from main.py)."""
    global _orchestrator
    _orchestrator = orchestrator


def get_orchestrator() -> TaskOrchestrator:
    """Dependency to get orchestrator instance."""
    if _orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized"
        )
    return _orchestrator


@router.post("/plans", response_model=PlanWithSteps, status_code=status.HTTP_201_CREATED)
async def create_plan(
    input_task: InputTask,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator)
):
    """
    Create a new execution plan from user objective and uploaded files.
    
    The planner will analyze the objective and files to create a structured
    plan with appropriate agent steps.
    
    Args:
        input_task: Task with objective, file IDs, session ID, and metadata
    
    Returns:
        Plan with all steps
    """
    logger.info(
        "Creating plan via API",
        objective=input_task.description[:100],
        file_count=len(input_task.file_ids) if input_task.file_ids else 0
    )
    
    try:
        plan = await orchestrator.create_plan_from_objective(input_task)
        
        logger.info(
            "Plan created successfully via API",
            plan_id=plan.id,
            steps_count=len(plan.steps)
        )
        
        return plan
        
    except ValueError as e:
        logger.error(f"Validation error creating plan", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create plan", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create plan: {str(e)}"
        )


@router.post("/plans/{plan_id}/execute", response_model=ActionResponse)
async def execute_plan(
    plan_id: str,
    action_request: ActionRequest,
    background_tasks: BackgroundTasks,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator)
):
    """
    Execute a plan in the background.
    
    The plan will be executed asynchronously. Use the status endpoint
    to monitor progress.
    
    Args:
        plan_id: Plan ID to execute
        action_request: Request with session ID and optional parameters
        background_tasks: FastAPI background tasks
    
    Returns:
        Action response with execution started confirmation
    """
    logger.info("Executing plan via API", plan_id=plan_id)
    
    try:
        # Verify plan exists
        plan = await orchestrator.get_plan_with_steps(
            plan_id,
            action_request.session_id
        )
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan {plan_id} not found"
            )
        
        # Start execution in background
        background_tasks.add_task(
            orchestrator.execute_plan,
            plan_id,
            action_request.session_id
        )
        
        logger.info("Plan execution started in background", plan_id=plan_id)
        
        return ActionResponse(
            status="accepted",
            message=f"Plan execution started for plan {plan_id}",
            data={
                "plan_id": plan_id,
                "session_id": action_request.session_id,
                "total_steps": plan.total_steps
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute plan", error=str(e), plan_id=plan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute plan: {str(e)}"
        )


@router.get("/plans/{plan_id}", response_model=PlanWithSteps)
async def get_plan(
    plan_id: str,
    session_id: str,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator)
):
    """
    Get a plan with all its steps.
    
    Args:
        plan_id: Plan ID
        session_id: Session ID
    
    Returns:
        Plan with steps
    """
    logger.info("Getting plan via API", plan_id=plan_id)
    
    try:
        plan = await orchestrator.get_plan_with_steps(plan_id, session_id)
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan {plan_id} not found"
            )
        
        return plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plan", error=str(e), plan_id=plan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get plan: {str(e)}"
        )


@router.get("/plans/{plan_id}/status", response_model=ExecutionStatusResponse)
async def get_execution_status(
    plan_id: str,
    session_id: str,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator)
):
    """
    Get current execution status of a plan.
    
    Returns real-time progress information including:
    - Overall status
    - Current executing step
    - Progress percentage
    - Recent messages
    
    Args:
        plan_id: Plan ID
        session_id: Session ID
    
    Returns:
        Execution status with progress information
    """
    logger.info("Getting execution status via API", plan_id=plan_id)
    
    try:
        status_response = await orchestrator.get_execution_status(plan_id, session_id)
        return status_response
        
    except ValueError as e:
        logger.error(f"Plan not found", error=str(e), plan_id=plan_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get execution status", error=str(e), plan_id=plan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution status: {str(e)}"
        )


@router.post("/execute-direct", response_model=PlanExecutionResponse)
async def execute_direct(
    request: Request,
    input_task: InputTask,
    background_tasks: BackgroundTasks,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator)
):
    """
    Create plan and execute in one call (convenience endpoint).
    
    This endpoint combines plan creation and execution for a streamlined
    workflow. The plan is created, then execution starts in the background.
    
    Args:
        request: FastAPI request (for extracting authenticated user)
        input_task: Task with objective, file IDs, and metadata
        background_tasks: FastAPI background tasks
    
    Returns:
        Action response with plan ID and execution confirmation
    """
    # Extract authenticated user from headers
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    # Override user_id from authentication (ignore frontend value)
    input_task.user_id = user_id
    
    logger.info(
        "Direct execution via API",
        objective=input_task.description[:100],
        user_id=user_id
    )
    
    try:
        # Create plan
        plan = await orchestrator.create_plan_from_objective(input_task)
        
        # Start execution in background
        background_tasks.add_task(
            orchestrator.execute_plan,
            plan.id,
            plan.session_id
        )
        
        logger.info(
            "Plan created and execution started",
            plan_id=plan.id,
            steps_count=len(plan.steps)
        )
        
        return PlanExecutionResponse(
            status="accepted",
            message=f"Plan created and execution started",
            data={
                "plan_id": plan.id,
                "session_id": plan.session_id,
                "total_steps": plan.total_steps,
                "steps": [
                    {
                        "order": step.order,
                        "action": step.action,
                        "agent": step.agent.value
                    }
                    for step in plan.steps
                ]
            }
        )
        
    except ValueError as e:
        logger.error(f"Validation error in direct execution", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed direct execution", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute: {str(e)}"
        )

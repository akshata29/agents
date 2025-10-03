"""
Orchestration API Router

REST API endpoints for task planning, approval workflow, and execution.
Uses TaskOrchestrator service to bridge framework patterns with Cosmos storage.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
import structlog

from ..models.task_models import (
    InputTask, Plan, Step, HumanFeedback, AgentMessage,
    PlanWithSteps, TaskListItem, ActionResponse, StepStatus
)
from ..services.task_orchestrator import TaskOrchestrator
from ..persistence.cosmos_memory import CosmosMemoryStore
from ..auth.auth_utils import get_authenticated_user_details
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["orchestration"])

# Dependency to get TaskOrchestrator instance
_task_orchestrator: Optional[TaskOrchestrator] = None


async def get_task_orchestrator() -> TaskOrchestrator:
    """Dependency to get TaskOrchestrator singleton."""
    global _task_orchestrator
    
    if _task_orchestrator is None:
        settings = Settings()
        _task_orchestrator = TaskOrchestrator(settings)
        await _task_orchestrator.initialize()
    
    return _task_orchestrator


@router.post("/input_task", response_model=PlanWithSteps)
async def create_plan_from_objective(
    input_task: InputTask,
    request: Request,
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    Create an execution plan from user objective.
    
    Uses framework's DynamicPlanner to generate a structured plan with steps.
    Each step must be approved before execution.
    Automatically extracts user_id from authentication headers.
    
    **Request Body:**
    ```json
    {
      "objective": "Analyze MSFT stock comprehensively",
      "user_id": "user123",
      "session_id": "session-abc-123",
      "metadata": {
        "ticker": "MSFT"
      }
    }
    ```
    
    **Response:**
    Returns a Plan with pending steps awaiting approval.
    """
    # Extract user_id from authentication headers
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    
    if not user_id:
        logger.error("API: No user_principal_id found in headers")
        raise HTTPException(status_code=400, detail="User authentication required")
    
    # Override user_id in input_task with authenticated user
    input_task.user_id = user_id
    
    logger.info(
        "API: Creating plan from objective",
        description=input_task.description[:100],
        session_id=input_task.session_id,
        ticker=input_task.ticker,
        user_id=user_id
    )

    try:
        plan = await orchestrator.create_plan_from_objective(input_task)
        
        logger.info(
            "API: Plan created successfully",
            plan_id=plan.id,
            steps_count=len(plan.steps),
            user_id=user_id
        )
        
        return plan

    except Exception as e:
        logger.error(
            "API: Failed to create plan",
            error=str(e),
            description=input_task.description[:100],
            user_id=user_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create plan: {str(e)}"
        )


@router.get("/plans/{session_id}/{plan_id}", response_model=PlanWithSteps)
async def get_plan_details(
    session_id: str,
    plan_id: str,
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    Retrieve plan with all steps.
    
    **Path Parameters:**
    - `session_id`: Session identifier (partition key)
    - `plan_id`: Plan identifier
    
    **Response:**
    Returns full plan details including all steps and their current status.
    """
    logger.info(
        "API: Retrieving plan",
        plan_id=plan_id,
        session_id=session_id
    )

    try:
        plan = await orchestrator.get_plan_with_steps(plan_id, session_id)
        
        if not plan:
            raise HTTPException(
                status_code=404,
                detail=f"Plan {plan_id} not found in session {session_id}"
            )
        
        logger.info(
            "API: Plan retrieved",
            plan_id=plan_id,
            steps_count=len(plan.steps) if plan.steps else 0
        )
        
        return plan

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "API: Failed to retrieve plan",
            error=str(e),
            plan_id=plan_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve plan: {str(e)}"
        )


@router.get("/tasks", response_model=List[TaskListItem])
async def list_all_tasks(
    limit: int = Query(50, description="Maximum number of tasks to return"),
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    List all research tasks across all sessions.
    
    **Query Parameters:**
    - `limit`: Maximum number of tasks to return (default: 50)
    
    **Response:**
    Returns list of all task summaries, ordered by creation time (most recent first).
    """
    logger.info("API: Listing all tasks", limit=limit)

    try:
        # Get all sessions from Cosmos
        sessions = await orchestrator.cosmos.get_all_sessions(limit=limit)
        
        # For each session, get the plan and build TaskListItem
        task_list = []
        for session in sessions:
            # Get plan for this session
            plan = await orchestrator.cosmos.get_plan_by_session(session.session_id)
            
            if plan:
                # Get steps to calculate progress
                steps = await orchestrator.cosmos.get_steps_by_plan(plan.id, session.session_id)
                
                completed_steps = sum(1 for s in steps if s.status == StepStatus.COMPLETED)
                
                task_item = TaskListItem(
                    id=plan.id,
                    session_id=session.session_id,
                    initial_goal=plan.initial_goal[:200],  # Truncate if too long
                    overall_status=plan.overall_status,
                    total_steps=plan.total_steps,
                    completed_steps=completed_steps,
                    timestamp=plan.timestamp,
                    ticker=plan.ticker
                )
                task_list.append(task_item)
        
        logger.info("API: All tasks listed", count=len(task_list))
        
        return task_list

    except Exception as e:
        logger.error("API: Failed to list all tasks", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tasks: {str(e)}"
        )


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_user_history(
    request: Request,
    limit: int = Query(20, description="Maximum number of history items to return"),
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    Retrieve user's task history with objectives and status.
    
    Automatically extracts user_id from authentication headers for multi-user isolation.
    
    **Query Parameters:**
    - `limit`: Maximum number of history items to return (default: 20)
    
    **Response:**
    Returns list of user's tasks/plans with:
    - session_id: Session identifier
    - plan_id: Plan identifier
    - objective: The task objective/goal
    - status: Overall plan status
    - created_at: When the plan was created
    - steps_count: Number of steps in the plan
    
    Ordered by most recent first.
    """
    # Extract user_id from authentication headers
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]
    
    if not user_id:
        logger.error("API: No user_principal_id found in headers")
        raise HTTPException(status_code=400, detail="User authentication required")
    
    logger.info("API: Retrieving user history", user_id=user_id, limit=limit)

    try:
        # Create a temporary memory store instance with user_id
        cosmos = CosmosMemoryStore(
            endpoint=orchestrator.cosmos.endpoint,
            database_name=orchestrator.cosmos.database_name,
            container_name=orchestrator.cosmos.container_name,
            user_id=user_id,  # Set user_id for filtering
            tenant_id=orchestrator.cosmos.tenant_id,
            client_id=orchestrator.cosmos.client_id,
            client_secret=orchestrator.cosmos.client_secret,
        )
        
        await cosmos.initialize()
        
        # Get user history
        history = await cosmos.get_user_history(limit=limit)
        
        await cosmos.close()
        
        logger.info("API: User history retrieved", user_id=user_id, count=len(history))
        
        return history

    except Exception as e:
        logger.error("API: Failed to retrieve user history", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user history: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    Delete a session and all related data from CosmosDB.
    
    **Path Parameters:**
    - `session_id`: Session identifier to delete
    
    **Response:**
    Returns success message when session and all related items are deleted.
    """
    logger.info("API: Deleting session", session_id=session_id)

    try:
        # Delete session and all related items (plans, steps, messages)
        await orchestrator.cosmos.delete_session(session_id)
        
        logger.info("API: Session deleted successfully", session_id=session_id)
        
        return {"message": f"Session {session_id} deleted successfully"}

    except Exception as e:
        logger.error("API: Failed to delete session", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/plans/{session_id}", response_model=List[TaskListItem])
async def list_plans_for_session(
    session_id: str,
    user_id: str = Query(..., description="User identifier"),
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    List all plans for a user session.
    
    **Path Parameters:**
    - `session_id`: Session identifier
    
    **Query Parameters:**
    - `user_id`: User identifier
    
    **Response:**
    Returns list of plan summaries for the session.
    """
    logger.info(
        "API: Listing plans for session",
        session_id=session_id,
        user_id=user_id
    )

    try:
        # Get all plans for session from Cosmos
        plans_data = await orchestrator.cosmos.get_plan_by_session(session_id)
        
        # Convert to TaskListItem summaries
        task_list = []
        for plan_data in plans_data:
            plan = Plan(**plan_data)
            
            # Get steps to calculate progress
            steps_data = await orchestrator.cosmos.get_steps_by_plan(plan.id, session_id)
            steps = [Step(**s) for s in steps_data]
            
            completed_steps = sum(1 for s in steps if s.status == "completed")
            
            task_item = TaskListItem(
                id=plan.id,
                objective=plan.objective,
                status=plan.status,
                created_at=plan.created_at,
                total_steps=plan.total_steps,
                completed_steps=completed_steps
            )
            task_list.append(task_item)
        
        logger.info(
            "API: Plans listed",
            session_id=session_id,
            count=len(task_list)
        )
        
        return task_list

    except Exception as e:
        logger.error(
            "API: Failed to list plans",
            error=str(e),
            session_id=session_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list plans: {str(e)}"
        )


@router.post("/approve_step", response_model=ActionResponse)
async def approve_or_reject_step(
    feedback: HumanFeedback,
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    Approve or reject a step for execution.
    
    When approved, the step is executed using framework's HandoffPattern or GroupChatPattern.
    When rejected, the step is marked as rejected with the provided reason.
    
    **Request Body:**
    ```json
    {
      "step_id": "step-123",
      "plan_id": "plan-456",
      "session_id": "session-abc-123",
      "approved": true,
      "human_feedback": "Optional feedback or additional context",
      "updated_action": "Optional updated action if modifying the step"
    }
    ```
    
    **Response:**
    Returns execution results if approved, or rejection confirmation if rejected.
    """
    logger.info(
        "API: Processing step approval",
        step_id=feedback.step_id,
        approved=feedback.approved,
        session_id=feedback.session_id
    )

    try:
        result = await orchestrator.handle_step_approval(feedback)
        
        logger.info(
            "API: Step approval processed",
            step_id=feedback.step_id,
            success=result.success
        )
        
        return result

    except ValueError as e:
        logger.warning(
            "API: Invalid step approval request",
            error=str(e),
            step_id=feedback.step_id
        )
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "API: Failed to process step approval",
            error=str(e),
            step_id=feedback.step_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process step approval: {str(e)}"
        )


@router.post("/approve_steps", response_model=List[ActionResponse])
async def approve_or_reject_multiple_steps(
    feedbacks: List[HumanFeedback],
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    Approve or reject multiple steps in bulk.
    
    Processes each step approval independently and returns individual results.
    Failed approvals do not stop processing of remaining steps.
    
    **Request Body:**
    Array of HumanFeedback objects.
    
    **Response:**
    Array of ActionResponse objects, one per step.
    """
    logger.info(
        "API: Processing bulk step approvals",
        count=len(feedbacks)
    )

    results = []
    
    for feedback in feedbacks:
        try:
            result = await orchestrator.handle_step_approval(feedback)
            results.append(result)
            
        except Exception as e:
            logger.error(
                "API: Failed to process step in bulk approval",
                error=str(e),
                step_id=feedback.step_id
            )
            # Add error result instead of stopping
            results.append(ActionResponse(
                success=False,
                result={"error": str(e)},
                agent_name="unknown",
                error=str(e)
            ))
    
    logger.info(
        "API: Bulk approvals processed",
        total=len(feedbacks),
        successful=sum(1 for r in results if r.success)
    )
    
    return results


@router.get("/steps/{session_id}/{plan_id}", response_model=List[Step])
async def get_steps_for_plan(
    session_id: str,
    plan_id: str,
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    Retrieve all steps for a specific plan.
    
    **Path Parameters:**
    - `session_id`: Session identifier (partition key)
    - `plan_id`: Plan identifier
    
    **Response:**
    Returns list of all steps in the plan with their current status.
    """
    logger.info(
        "API: Retrieving steps for plan",
        plan_id=plan_id,
        session_id=session_id
    )

    try:
        steps_data = await orchestrator.cosmos.get_steps_by_plan(plan_id, session_id)
        steps = [Step(**step_data) for step_data in steps_data]
        
        logger.info(
            "API: Steps retrieved",
            plan_id=plan_id,
            count=len(steps)
        )
        
        return steps

    except Exception as e:
        logger.error(
            "API: Failed to retrieve steps",
            error=str(e),
            plan_id=plan_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve steps: {str(e)}"
        )


@router.get("/messages/{session_id}", response_model=List[AgentMessage])
async def get_conversation_history(
    session_id: str,
    plan_id: Optional[str] = Query(None, description="Filter by plan ID"),
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator)
):
    """
    Retrieve conversation history for a session.
    
    **Path Parameters:**
    - `session_id`: Session identifier
    
    **Query Parameters:**
    - `plan_id`: Optional plan ID to filter messages
    
    **Response:**
    Returns chronological list of all agent messages in the conversation.
    """
    logger.info(
        "API: Retrieving conversation history",
        session_id=session_id,
        plan_id=plan_id
    )

    try:
        if plan_id:
            messages = await orchestrator.cosmos.get_messages_by_plan(plan_id)
        else:
            messages = await orchestrator.cosmos.get_messages_by_session(session_id)
        
        logger.info(
            "API: Messages retrieved",
            session_id=session_id,
            count=len(messages)
        )
        
        return messages

    except Exception as e:
        logger.error(
            "API: Failed to retrieve messages",
            error=str(e),
            session_id=session_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve messages: {str(e)}"
        )


# Startup event to initialize orchestrator
@router.on_event("startup")
async def startup_event():
    """Initialize TaskOrchestrator on startup."""
    logger.info("API Router: Starting up")
    # Trigger initialization
    await get_task_orchestrator()
    logger.info("API Router: Startup complete")


# Shutdown event to cleanup
@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup TaskOrchestrator on shutdown."""
    logger.info("API Router: Shutting down")
    global _task_orchestrator
    if _task_orchestrator:
        await _task_orchestrator.shutdown()
        _task_orchestrator = None
    logger.info("API Router: Shutdown complete")

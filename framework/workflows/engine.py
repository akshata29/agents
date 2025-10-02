"""
Workflow Engine - Declarative Workflow Processing

Provides YAML-based workflow definition and execution with support for
conditional logic, parallel processing, and dynamic task orchestration.
"""

import asyncio
import yaml
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import structlog
from pydantic import BaseModel, Field, validator

from ..config.settings import Settings
from ..core.observability import ObservabilityService
from ..core.registry import AgentRegistry
from ..mcp_integration.client import MCPClient

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Types of workflow tasks."""
    AGENT = "agent"
    MCP_TOOL = "mcp_tool"
    FUNCTION = "function"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    DELAY = "delay"


class ConditionOperator(str, Enum):
    """Condition operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    EXISTS = "exists"
    AND = "and"
    OR = "or"
    NOT = "not"


class WorkflowVariable(BaseModel):
    """Workflow variable definition."""
    name: str
    type: str = "string"  # string, number, boolean, object, array
    default: Optional[Any] = None
    description: str = ""
    required: bool = False


class TaskCondition(BaseModel):
    """Task execution condition."""
    variable: str
    operator: ConditionOperator
    value: Optional[Any] = None
    conditions: Optional[List['TaskCondition']] = None  # For AND/OR/NOT operations

    class Config:
        use_enum_values = True


class TaskRetry(BaseModel):
    """Task retry configuration."""
    max_attempts: int = 1
    delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 60.0


class WorkflowTask(BaseModel):
    """Workflow task definition."""
    id: str
    name: str
    type: TaskType
    description: str = ""
    
    # Task configuration
    agent: Optional[str] = None
    tool: Optional[str] = None
    function: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Dependencies and conditions
    depends_on: List[str] = Field(default_factory=list)
    condition: Optional[TaskCondition] = None
    timeout: Optional[int] = None
    retry: Optional[TaskRetry] = None
    
    # Parallel/Sequential task groups
    tasks: Optional[List['WorkflowTask']] = None
    
    # Output mapping
    outputs: Dict[str, str] = Field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    @validator('depends_on')
    def validate_dependencies(cls, v):
        """Validate task dependencies don't create cycles."""
        # Basic validation - more sophisticated cycle detection needed
        return list(set(v))  # Remove duplicates


class WorkflowDefinition(BaseModel):
    """Complete workflow definition."""
    name: str
    version: str = "1.0"
    description: str = ""
    
    # Workflow configuration
    variables: List[WorkflowVariable] = Field(default_factory=list)
    timeout: Optional[int] = None
    max_parallel_tasks: int = 10
    
    # Task definitions
    tasks: List[WorkflowTask]
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('tasks')
    def validate_tasks(cls, v):
        """Validate task definitions and dependencies."""
        if not v:
            raise ValueError("Workflow must have at least one task")
        
        # Validate unique task IDs
        task_ids = [task.id for task in v]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task IDs must be unique")
        
        # Validate dependencies reference existing tasks
        for task in v:
            for dep in task.depends_on:
                if dep not in task_ids:
                    raise ValueError(f"Task '{task.id}' depends on non-existent task '{dep}'")
        
        return v


@dataclass
class TaskExecution:
    """Task execution state."""
    task_id: str
    task_name: str = ""  # Added for better tracking
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    attempt: int = 0
    outputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Workflow execution state."""
    execution_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None  # Error message if workflow failed
    
    # Task executions
    task_executions: Dict[str, TaskExecution] = field(default_factory=dict)
    
    # Runtime variables
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowEngine:
    """
    Declarative workflow engine for YAML-based workflow processing.
    
    Supports conditional logic, parallel processing, agent orchestration,
    and MCP tool integration with comprehensive monitoring and retry logic.
    """

    def __init__(
        self,
        settings: Settings,
        agent_registry: AgentRegistry,
        mcp_client: MCPClient,
        observability: Optional[ObservabilityService] = None
    ):
        """Initialize workflow engine."""
        self.settings = settings
        self.agent_registry = agent_registry
        self.mcp_client = mcp_client
        self.observability = observability
        
        # Workflow definitions
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._workflows_lock = asyncio.Lock()
        
        # Active executions
        self._executions: Dict[str, WorkflowExecution] = {}
        self._executions_lock = asyncio.Lock()
        
        # Function registry for custom functions
        self._functions: Dict[str, Callable] = {}
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        
        logger.info("WorkflowEngine initialized")

    async def initialize(self) -> None:
        """Initialize workflow engine."""
        logger.info("Initializing WorkflowEngine")
        
        # Load workflows from directory if configured
        if self.settings.workflow_dir:
            await self._load_workflows_from_directory(self.settings.workflow_dir)
        
        # Register default functions
        await self._register_default_functions()
        
        # Start execution monitoring task
        self._background_tasks.append(
            asyncio.create_task(self._execution_monitor_loop())
        )
        
        logger.info("WorkflowEngine initialization complete")

    async def shutdown(self) -> None:
        """Shutdown workflow engine."""
        logger.info("Shutting down WorkflowEngine")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Cancel active executions
        async with self._executions_lock:
            for execution in self._executions.values():
                if execution.status == WorkflowStatus.RUNNING:
                    execution.status = WorkflowStatus.CANCELLED
        
        logger.info("WorkflowEngine shutdown complete")

    # Workflow Management

    async def register_workflow(
        self,
        workflow_def: Union[WorkflowDefinition, Dict[str, Any], str, Path]
    ) -> None:
        """Register a workflow definition."""
        if isinstance(workflow_def, (str, Path)):
            # Load from file
            workflow_def = await self._load_workflow_from_file(workflow_def)
        elif isinstance(workflow_def, dict):
            # Parse from dictionary
            workflow_def = WorkflowDefinition(**workflow_def)
        
        async with self._workflows_lock:
            self._workflows[workflow_def.name] = workflow_def
        
        logger.info("Workflow registered", workflow_name=workflow_def.name)

    async def unregister_workflow(self, name: str) -> bool:
        """Unregister a workflow."""
        async with self._workflows_lock:
            if name in self._workflows:
                del self._workflows[name]
                logger.info("Workflow unregistered", workflow_name=name)
                return True
        
        return False

    async def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition."""
        async with self._workflows_lock:
            return self._workflows.get(name)

    async def list_workflows(self) -> List[WorkflowDefinition]:
        """List all registered workflows."""
        async with self._workflows_lock:
            return list(self._workflows.values())

    # Workflow Execution

    async def execute_workflow(
        self,
        workflow_name: str,
        variables: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> str:
        """Start workflow execution."""
        import uuid
        
        # Get workflow definition
        workflow_def = await self.get_workflow(workflow_name)
        if not workflow_def:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        # Create execution
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_name=workflow_name,
            variables=variables or {}
        )
        
        # Initialize task executions
        for task in workflow_def.tasks:
            execution.task_executions[task.id] = TaskExecution(
                task_id=task.id,
                task_name=task.name
            )
        
        # Store execution
        async with self._executions_lock:
            self._executions[execution_id] = execution
        
        # Start execution in background
        self._background_tasks.append(
            asyncio.create_task(self._execute_workflow_background(workflow_def, execution))
        )
        
        logger.info("Workflow execution started", workflow_name=workflow_name, execution_id=execution_id)
        
        return execution_id

    async def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status."""
        async with self._executions_lock:
            return self._executions.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel workflow execution."""
        async with self._executions_lock:
            execution = self._executions.get(execution_id)
            if execution and execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.CANCELLED
                logger.info("Workflow execution cancelled", execution_id=execution_id)
                return True
        
        return False

    async def list_executions(
        self,
        workflow_name: Optional[str] = None,
        status: Optional[WorkflowStatus] = None
    ) -> List[WorkflowExecution]:
        """List workflow executions with optional filtering."""
        async with self._executions_lock:
            executions = []
            for execution in self._executions.values():
                if workflow_name and execution.workflow_name != workflow_name:
                    continue
                if status and execution.status != status:
                    continue
                executions.append(execution)
            
            return executions

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed execution status for monitoring."""
        execution = await self.get_execution(execution_id)
        if not execution:
            return None
        
        # Calculate progress
        total_tasks = len(execution.task_executions)
        completed_tasks = sum(
            1 for task_exec in execution.task_executions.values()
            if task_exec.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED]
        )
        progress = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        
        # Determine current phase
        running_tasks = [
            task_id for task_id, task_exec in execution.task_executions.items()
            if task_exec.status == TaskStatus.RUNNING
        ]
        current_phase = running_tasks[0] if running_tasks else "Waiting"
        
        return {
            "execution_id": execution.execution_id,
            "workflow_name": execution.workflow_name,
            "status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
            "progress": progress,
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "current_phase": current_phase,
            "running_tasks": running_tasks,
            "start_time": execution.start_time.isoformat() if execution.start_time else None,
            "duration": execution.duration,
            "error": execution.error
        }

    # Function Management

    async def register_function(self, name: str, func: Callable) -> None:
        """Register a custom function for use in workflows."""
        self._functions[name] = func
        logger.info("Workflow function registered", function_name=name)

    # Private Methods

    async def _execute_workflow_background(
        self,
        workflow_def: WorkflowDefinition,
        execution: WorkflowExecution
    ) -> None:
        """Execute workflow in background."""
        try:
            execution.status = WorkflowStatus.RUNNING
            execution.start_time = datetime.utcnow()
            
            # Initialize variables with defaults
            for var_def in workflow_def.variables:
                if var_def.name not in execution.variables and var_def.default is not None:
                    execution.variables[var_def.name] = var_def.default
            
            # Execute tasks
            await self._execute_tasks(workflow_def, execution)
            
            # Determine final status
            failed_tasks = [
                task_exec for task_exec in execution.task_executions.values()
                if task_exec.status == TaskStatus.FAILED
            ]
            
            if failed_tasks:
                execution.status = WorkflowStatus.FAILED
                execution.error = f"Tasks failed: {', '.join([t.task_name for t in failed_tasks])}"
            elif execution.status != WorkflowStatus.CANCELLED:
                execution.status = WorkflowStatus.SUCCESS
            
        except asyncio.CancelledError:
            execution.status = WorkflowStatus.CANCELLED
            execution.error = "Workflow was cancelled"
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            logger.error("Workflow execution failed", execution_id=execution.execution_id, error=str(e))
        
        finally:
            execution.end_time = datetime.utcnow()
            if execution.start_time:
                execution.duration = (execution.end_time - execution.start_time).total_seconds()

    async def _execute_tasks(
        self,
        workflow_def: WorkflowDefinition,
        execution: WorkflowExecution
    ) -> None:
        """Execute workflow tasks with dependency resolution."""
        executed_tasks = set()
        running_tasks = {}
        
        while len(executed_tasks) < len(workflow_def.tasks):
            if execution.status == WorkflowStatus.CANCELLED:
                break
            
            # Find ready tasks
            ready_tasks = []
            for task in workflow_def.tasks:
                if (task.id not in executed_tasks and 
                    task.id not in running_tasks and
                    self._are_dependencies_complete(task, execution)):
                    
                    # Check condition
                    if task.condition and not await self._evaluate_condition(task.condition, execution):
                        # Skip task
                        task_exec = execution.task_executions[task.id]
                        task_exec.status = TaskStatus.SKIPPED
                        executed_tasks.add(task.id)
                        continue
                    
                    ready_tasks.append(task)
            
            if not ready_tasks and not running_tasks:
                # No progress possible - check for circular dependencies
                pending_tasks = [
                    task.id for task in workflow_def.tasks 
                    if task.id not in executed_tasks
                ]
                logger.error(
                    "Circular dependency detected or all tasks blocked",
                    pending_tasks=pending_tasks
                )
                break
            
            # Start ready tasks (respect parallel limit)
            available_slots = workflow_def.max_parallel_tasks - len(running_tasks)
            for task in ready_tasks[:available_slots]:
                running_tasks[task.id] = asyncio.create_task(
                    self._execute_single_task(task, execution)
                )
            
            if running_tasks:
                # Wait for at least one task to complete
                done, pending = await asyncio.wait(
                    running_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed tasks
                for task_future in done:
                    # Find task ID
                    completed_task_id = None
                    for tid, fut in running_tasks.items():
                        if fut == task_future:
                            completed_task_id = tid
                            break
                    
                    if completed_task_id:
                        executed_tasks.add(completed_task_id)
                        del running_tasks[completed_task_id]
            else:
                # No running tasks, brief wait to avoid busy loop
                await asyncio.sleep(0.1)

    async def _execute_single_task(
        self,
        task: WorkflowTask,
        execution: WorkflowExecution
    ) -> None:
        """Execute a single workflow task."""
        task_exec = execution.task_executions[task.id]
        
        # Handle retry logic
        max_attempts = task.retry.max_attempts if task.retry else 1
        delay = task.retry.delay_seconds if task.retry else 0
        
        for attempt in range(1, max_attempts + 1):
            try:
                task_exec.attempt = attempt
                task_exec.status = TaskStatus.RUNNING
                task_exec.start_time = datetime.utcnow()
                
                # Execute based on task type
                result = await self._execute_task_by_type(task, execution)
                
                # Success
                task_exec.status = TaskStatus.SUCCESS
                task_exec.result = result
                
                # Process outputs
                if task.outputs:
                    for output_name, variable_path in task.outputs.items():
                        if isinstance(result, dict) and output_name in result:
                            execution.variables[variable_path] = result[output_name]
                        else:
                            execution.variables[variable_path] = result
                
                break  # Success, no retry needed
                
            except Exception as e:
                task_exec.error = str(e)
                
                if attempt < max_attempts:
                    # Retry with backoff
                    await asyncio.sleep(delay)
                    if task.retry:
                        delay = min(
                            delay * task.retry.backoff_multiplier,
                            task.retry.max_delay_seconds
                        )
                else:
                    # Final failure
                    task_exec.status = TaskStatus.FAILED
                    logger.error(
                        "Task execution failed",
                        task_id=task.id,
                        attempt=attempt,
                        error=str(e)
                    )
            
            finally:
                task_exec.end_time = datetime.utcnow()
                if task_exec.start_time:
                    task_exec.duration = (task_exec.end_time - task_exec.start_time).total_seconds()

    async def _execute_task_by_type(
        self,
        task: WorkflowTask,
        execution: WorkflowExecution
    ) -> Any:
        """Execute task based on its type."""
        if task.type == TaskType.AGENT:
            return await self._execute_agent_task(task, execution)
        elif task.type == TaskType.MCP_TOOL:
            return await self._execute_mcp_tool_task(task, execution)
        elif task.type == TaskType.FUNCTION:
            return await self._execute_function_task(task, execution)
        elif task.type == TaskType.CONDITION:
            return await self._execute_condition_task(task, execution)
        elif task.type == TaskType.PARALLEL:
            return await self._execute_parallel_task(task, execution)
        elif task.type == TaskType.SEQUENTIAL:
            return await self._execute_sequential_task(task, execution)
        elif task.type == TaskType.DELAY:
            return await self._execute_delay_task(task, execution)
        else:
            raise ValueError(f"Unknown task type: {task.type}")

    async def _execute_agent_task(self, task: WorkflowTask, execution: WorkflowExecution) -> Any:
        """Execute agent task."""
        if not task.agent:
            raise ValueError("Agent name is required for agent task")
        
        agent = await self.agent_registry.get_agent(task.agent)
        if not agent:
            raise ValueError(f"Agent '{task.agent}' not found")
        
        # Resolve parameters
        resolved_params = self._resolve_parameters(task.parameters, execution.variables)
        
        # Build message from parameters
        from ..agents.base import AgentMessage
        
        # Get the task content - could be in 'task', 'message', 'content', etc.
        message_content = resolved_params.get('task') or resolved_params.get('message') or resolved_params.get('content', '')
        
        # Build context from other parameters
        context = {k: v for k, v in resolved_params.items() if k not in ['task', 'message', 'content']}
        if 'context' in resolved_params:
            # Merge explicit context
            if isinstance(resolved_params['context'], dict):
                context.update(resolved_params['context'])
        
        # Create message
        message = AgentMessage(content=str(message_content))
        
        # Execute agent - agent.process() returns string content directly
        result = await agent.process(message, context)
        
        # Return the result (which is already a string)
        return result


    async def _execute_mcp_tool_task(self, task: WorkflowTask, execution: WorkflowExecution) -> Any:
        """Execute MCP tool task."""
        if not task.tool:
            raise ValueError("Tool name is required for MCP tool task")
        
        # Resolve parameters
        resolved_params = self._resolve_parameters(task.parameters, execution.variables)
        
        # Execute MCP tool
        result = await self.mcp_client.call_tool(task.tool, resolved_params)
        
        return result

    async def _execute_function_task(self, task: WorkflowTask, execution: WorkflowExecution) -> Any:
        """Execute function task."""
        if not task.function:
            raise ValueError("Function name is required for function task")
        
        func = self._functions.get(task.function)
        if not func:
            raise ValueError(f"Function '{task.function}' not found")
        
        # Resolve parameters
        resolved_params = self._resolve_parameters(task.parameters, execution.variables)
        
        # Execute function
        if asyncio.iscoroutinefunction(func):
            result = await func(resolved_params)
        else:
            result = func(resolved_params)
        
        return result

    async def _execute_condition_task(self, task: WorkflowTask, execution: WorkflowExecution) -> Any:
        """Execute condition task."""
        if not task.condition:
            raise ValueError("Condition is required for condition task")
        
        result = await self._evaluate_condition(task.condition, execution)
        return {"result": result}

    async def _execute_parallel_task(self, task: WorkflowTask, execution: WorkflowExecution) -> Any:
        """Execute parallel task group."""
        if not task.tasks:
            return {"results": []}
        
        # Execute subtasks in parallel
        subtasks = [
            self._execute_task_by_type(subtask, execution)
            for subtask in task.tasks
        ]
        
        results = await asyncio.gather(*subtasks, return_exceptions=True)
        
        return {"results": results}

    async def _execute_sequential_task(self, task: WorkflowTask, execution: WorkflowExecution) -> Any:
        """Execute sequential task group."""
        if not task.tasks:
            return {"results": []}
        
        results = []
        for subtask in task.tasks:
            result = await self._execute_task_by_type(subtask, execution)
            results.append(result)
        
        return {"results": results}

    async def _execute_delay_task(self, task: WorkflowTask, execution: WorkflowExecution) -> Any:
        """Execute delay task."""
        delay_seconds = task.parameters.get("seconds", 1)
        await asyncio.sleep(delay_seconds)
        return {"delayed_seconds": delay_seconds}

    def _are_dependencies_complete(self, task: WorkflowTask, execution: WorkflowExecution) -> bool:
        """Check if all task dependencies are complete."""
        for dep_id in task.depends_on:
            dep_exec = execution.task_executions.get(dep_id)
            if not dep_exec or dep_exec.status not in [TaskStatus.SUCCESS, TaskStatus.SKIPPED]:
                return False
        
        return True

    async def _evaluate_condition(
        self,
        condition: TaskCondition,
        execution: WorkflowExecution
    ) -> bool:
        """Evaluate task condition."""
        if condition.operator == ConditionOperator.EXISTS:
            return condition.variable in execution.variables
        
        # Get variable value
        if condition.variable not in execution.variables:
            return False
        
        var_value = execution.variables[condition.variable]
        
        if condition.operator == ConditionOperator.EQUALS:
            return var_value == condition.value
        elif condition.operator == ConditionOperator.NOT_EQUALS:
            return var_value != condition.value
        elif condition.operator == ConditionOperator.GREATER_THAN:
            return var_value > condition.value
        elif condition.operator == ConditionOperator.LESS_THAN:
            return var_value < condition.value
        elif condition.operator == ConditionOperator.CONTAINS:
            return condition.value in var_value
        elif condition.operator == ConditionOperator.AND:
            if not condition.conditions:
                return True
            return all(await self._evaluate_condition(cond, execution) for cond in condition.conditions)
        elif condition.operator == ConditionOperator.OR:
            if not condition.conditions:
                return False
            return any(await self._evaluate_condition(cond, execution) for cond in condition.conditions)
        elif condition.operator == ConditionOperator.NOT:
            if not condition.conditions:
                return True
            return not await self._evaluate_condition(condition.conditions[0], execution)
        
        return False

    def _substitute_variables_in_string(self, text: str, variables: Dict[str, Any]) -> str:
        """Substitute ${variable} placeholders in a string with actual values."""
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return str(variables.get(var_name, match.group(0)))
        
        # Replace all ${variable} patterns
        return re.sub(r'\$\{([^}]+)\}', replace_var, text)

    def _resolve_parameters(
        self,
        parameters: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve parameter values with variable substitution."""
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str):
                # Handle both full variable references and embedded variables
                if value.startswith("${") and value.endswith("}"):
                    # Full variable reference
                    var_name = value[2:-1]
                    resolved[key] = variables.get(var_name, value)
                else:
                    # String with possible embedded variables
                    resolved[key] = self._substitute_variables_in_string(value, variables)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_parameters(value, variables)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_parameters({"item": item}, variables)["item"] if isinstance(item, dict)
                    else self._substitute_variables_in_string(item, variables) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved

    async def _load_workflow_from_file(self, file_path: Union[str, Path]) -> WorkflowDefinition:
        """Load workflow definition from YAML file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_data = yaml.safe_load(f)
        
        return WorkflowDefinition(**workflow_data)

    async def _load_workflows_from_directory(self, directory: Union[str, Path]) -> None:
        """Load all workflow definitions from directory."""
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning("Workflow directory not found", directory=str(directory))
            return
        
        for yaml_file in directory.glob("*.yaml"):
            try:
                workflow_def = await self._load_workflow_from_file(yaml_file)
                await self.register_workflow(workflow_def)
            except Exception as e:
                logger.error("Failed to load workflow", file=str(yaml_file), error=str(e))

    async def _register_default_functions(self) -> None:
        """Register default workflow functions."""
        
        def log_message(params: Dict[str, Any]) -> Dict[str, Any]:
            message = params.get("message", "")
            level = params.get("level", "info")
            
            if level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
            else:
                logger.info(message)
            
            return {"logged": True, "message": message, "level": level}
        
        await self.register_function("log", log_message)
        
        def set_variable(params: Dict[str, Any]) -> Dict[str, Any]:
            # This would be handled differently in actual execution context
            return {"success": True}
        
        await self.register_function("set_variable", set_variable)

    async def _execution_monitor_loop(self) -> None:
        """Monitor workflow executions for timeouts and cleanup."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.utcnow()
                expired_executions = []
                
                async with self._executions_lock:
                    for execution_id, execution in self._executions.items():
                        # Clean up old completed executions (older than 24 hours)
                        if (execution.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED] and
                            execution.end_time and
                            (current_time - execution.end_time) > timedelta(hours=24)):
                            expired_executions.append(execution_id)
                    
                    for execution_id in expired_executions:
                        del self._executions[execution_id]
                        logger.info("Cleaned up old workflow execution", execution_id=execution_id)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in execution monitor loop", error=str(e))
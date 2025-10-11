"""Small, dependency-light workflow engine for the Deep Research backend."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import structlog
import yaml

from agent_framework import ChatMessage

from ..mcp_client import MCPClient
from ..observability import ObservabilityService
from ..registry import AgentRegistry
from ..settings import Settings

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(slots=True)
class WorkflowVariable:
    name: str
    type: str = "string"
    default: Any = None
    description: str = ""
    required: bool = False


@dataclass(slots=True)
class WorkflowTask:
    id: str
    name: str
    type: str
    description: str = ""
    agent: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    outputs: Dict[str, str] = field(default_factory=dict)
    timeout: Optional[int] = None
    retry: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class WorkflowDefinition:
    name: str
    version: str = "1.0"
    description: str = ""
    variables: List[WorkflowVariable] = field(default_factory=list)
    tasks: List[WorkflowTask] = field(default_factory=list)
    timeout: Optional[int] = None
    max_parallel_tasks: int = 1
    outputs: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskExecution:
    task_id: str
    task_name: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowExecution:
    execution_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    task_executions: Dict[str, TaskExecution] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)


class WorkflowEngine:
    """A pragmatic workflow engine tailored to the Deep Research YAML workflow."""

    def __init__(
        self,
        *,
        settings: Optional[Settings] = None,
        agent_registry: Optional[AgentRegistry] = None,
        mcp_client: Optional[MCPClient] = None,
        observability: Optional[ObservabilityService] = None,
    ) -> None:
        self._settings = settings or Settings()
        self._registry = agent_registry or AgentRegistry(self._settings)
        self._mcp = mcp_client or MCPClient(self._settings)
        self._observability = observability or ObservabilityService(self._settings)

        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._workflows_lock = asyncio.Lock()
        self._executions: Dict[str, WorkflowExecution] = {}
        self._executions_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Workflow management
    # ------------------------------------------------------------------
    async def register_workflow(self, workflow_def: Union[str, Path, Dict[str, Any]]) -> None:
        definition = await self._load_definition(workflow_def)
        async with self._workflows_lock:
            self._workflows[definition.name] = definition
        logger.info("Workflow registered", workflow=definition.name)

    async def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        async with self._workflows_lock:
            return self._workflows.get(name)

    async def list_workflows(self) -> List[WorkflowDefinition]:
        async with self._workflows_lock:
            return list(self._workflows.values())

    # ------------------------------------------------------------------
    # Execution entry points
    # ------------------------------------------------------------------
    async def execute_workflow(
        self,
        *,
        workflow_name: str,
        variables: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
    ) -> str:
        definition = await self.get_workflow(workflow_name)
        if not definition:
            raise ValueError(f"Workflow '{workflow_name}' not registered")

        exec_id = execution_id or str(uuid.uuid4())
        execution = WorkflowExecution(
            execution_id=exec_id,
            workflow_name=workflow_name,
            variables=dict(variables or {}),
        )
        for task in definition.tasks:
            execution.task_executions[task.id] = TaskExecution(task_id=task.id, task_name=task.name)

        async with self._executions_lock:
            self._executions[exec_id] = execution

        asyncio.create_task(self._run_workflow(definition, execution))
        logger.info("Workflow execution started", workflow=workflow_name, execution_id=exec_id)
        return exec_id

    async def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        async with self._executions_lock:
            return self._executions.get(execution_id)

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        execution = await self.get_execution(execution_id)
        if not execution:
            return None

        total = len(execution.task_executions)
        completed = sum(1 for t in execution.task_executions.values() if t.status == TaskStatus.SUCCESS)
        failed = sum(1 for t in execution.task_executions.values() if t.status == TaskStatus.FAILED)
        running = sum(1 for t in execution.task_executions.values() if t.status == TaskStatus.RUNNING)
        progress = (completed / total * 100) if total else 0

        return {
            "status": execution.status.value,
            "progress": progress,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "running_tasks": running,
            "total_tasks": total,
            "error": execution.error,
        }

    # ------------------------------------------------------------------
    # Internal execution logic
    # ------------------------------------------------------------------
    async def _run_workflow(self, definition: WorkflowDefinition, execution: WorkflowExecution) -> None:
        execution.status = WorkflowStatus.RUNNING
        execution.start_time = datetime.utcnow()
        variables = self._initialise_variables(definition, execution.variables)

        try:
            for task in definition.tasks:
                task_execution = execution.task_executions[task.id]
                await self._run_task(task, task_execution, execution, variables)

            # Persist the final variable state so external consumers can access all outputs
            execution.variables = dict(variables)
            execution.result = self._collect_outputs(definition, variables)
            execution.status = WorkflowStatus.SUCCESS
        except Exception as exc:  # pragma: no cover - defensive guard
            execution.status = WorkflowStatus.FAILED
            execution.error = str(exc)
            logger.exception("Workflow execution failed", execution_id=execution.execution_id)
        finally:
            execution.end_time = datetime.utcnow()
            if execution.start_time:
                execution.duration = (execution.end_time - execution.start_time).total_seconds()

    async def _run_task(
        self,
        task: WorkflowTask,
        task_execution: TaskExecution,
        execution: WorkflowExecution,
        variables: Dict[str, Any],
    ) -> None:
        dependencies = [execution.task_executions[dep] for dep in task.depends_on if dep in execution.task_executions]
        for dep in dependencies:
            while dep.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
                await asyncio.sleep(0.05)
            if dep.status != TaskStatus.SUCCESS:
                task_execution.status = TaskStatus.SKIPPED
                task_execution.error = f"Skipped due to dependency '{dep.task_id}' in status {dep.status.value}"
                logger.warning("Task skipped", task=task.id, reason=task_execution.error)
                return

        task_execution.status = TaskStatus.RUNNING
        task_execution.start_time = datetime.utcnow()

        try:
            if task.type.lower() == "agent":
                outputs = await self._run_agent_task(task, variables)
            else:
                raise ValueError(f"Unsupported task type: {task.type}")

            task_execution.result = outputs
            task_execution.outputs.update(outputs)
            for output_name, variable_name in task.outputs.items():
                variables[variable_name] = outputs.get(output_name)

            task_execution.status = TaskStatus.SUCCESS
        except Exception as exc:
            task_execution.status = TaskStatus.FAILED
            task_execution.error = str(exc)
            logger.exception("Task execution failed", task=task.id)
            raise
        finally:
            task_execution.end_time = datetime.utcnow()
            if task_execution.start_time:
                task_execution.duration = (task_execution.end_time - task_execution.start_time).total_seconds()

    async def _run_agent_task(self, task: WorkflowTask, variables: Dict[str, Any]) -> Dict[str, Any]:
        if not task.agent:
            raise ValueError(f"Task '{task.id}' is missing an agent")

        agent = await self._registry.get_agent(task.agent)
        params = self._render(task.parameters, variables)

        task_prompt = params.get("task")
        content = params.get("content")
        context = params.get("context", {})
        supplemental = params.get("supplemental_data")

        prompt_parts: List[str] = []
        if isinstance(task_prompt, str):
            prompt_parts.append(task_prompt)
        if isinstance(content, str) and content:
            prompt_parts.append(content)
        if isinstance(supplemental, str) and supplemental:
            prompt_parts.append(supplemental)

        message: Union[str, Sequence[ChatMessage]]
        if prompt_parts:
            message = "\n\n".join(prompt_parts)
        else:
            message = ""

        response = await agent.run(messages=message, context=context)
        text = ""
        if response and getattr(response, "messages", None):
            last_message = response.messages[-1]
            text = getattr(last_message, "text", str(last_message))

        logger.info("Agent task completed", task=task.id, agent=task.agent)
        return {"result": text, "raw_response": response}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _load_definition(self, source: Union[str, Path, Dict[str, Any]]) -> WorkflowDefinition:
        if isinstance(source, (str, Path)):
            path = Path(source)
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            data = dict(source)

        variables = [
            WorkflowVariable(
                name=item["name"],
                type=item.get("type", "string"),
                default=item.get("default"),
                description=item.get("description", ""),
                required=item.get("required", False),
            )
            for item in data.get("variables", [])
        ]

        tasks = [
            WorkflowTask(
                id=item["id"],
                name=item.get("name", item["id"]),
                type=item.get("type", "agent"),
                description=item.get("description", ""),
                agent=item.get("agent"),
                parameters=item.get("parameters", {}),
                depends_on=item.get("depends_on", []),
                outputs=item.get("outputs", {}),
                timeout=item.get("timeout"),
                retry=item.get("retry"),
            )
            for item in data.get("tasks", [])
        ]

        return WorkflowDefinition(
            name=data["name"],
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            variables=variables,
            tasks=tasks,
            timeout=data.get("timeout"),
            max_parallel_tasks=data.get("max_parallel_tasks", 1),
            outputs=data.get("outputs", {}),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _initialise_variables(definition: WorkflowDefinition, overrides: Dict[str, Any]) -> Dict[str, Any]:
        variables = {var.name: var.default for var in definition.variables if var.default is not None}
        variables.update(overrides)
        return variables

    @staticmethod
    def _collect_outputs(definition: WorkflowDefinition, variables: Dict[str, Any]) -> Dict[str, Any]:
        collected: Dict[str, Any] = {}
        for output_name, variable_name in definition.outputs.items():
            collected[output_name] = variables.get(variable_name)
        return collected

    @staticmethod
    def _render(value: Any, variables: Dict[str, Any]) -> Any:
        if isinstance(value, str):
            return WorkflowEngine._interpolate(value, variables)
        if isinstance(value, list):
            return [WorkflowEngine._render(item, variables) for item in value]
        if isinstance(value, dict):
            return {k: WorkflowEngine._render(v, variables) for k, v in value.items()}
        return value

    @staticmethod
    def _interpolate(text: str, variables: Dict[str, Any]) -> str:
        result = text
        for key, val in variables.items():
            placeholder = f"${{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(val))
        return result


__all__ = [
    "WorkflowEngine",
    "WorkflowStatus",
    "TaskStatus",
    "WorkflowDefinition",
    "WorkflowExecution",
]

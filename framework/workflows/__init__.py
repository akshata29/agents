"""
Workflows Package - Declarative Workflow Processing

Provides YAML-based workflow definition and execution capabilities
for the Foundation Framework.
"""

from .engine import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowTask,
    WorkflowExecution,
    TaskType,
    TaskStatus,
    WorkflowStatus,
    ConditionOperator,
    TaskCondition,
    TaskRetry,
    WorkflowVariable
)

__all__ = [
    "WorkflowEngine",
    "WorkflowDefinition", 
    "WorkflowTask",
    "WorkflowExecution",
    "TaskType",
    "TaskStatus",
    "WorkflowStatus",
    "ConditionOperator",
    "TaskCondition",
    "TaskRetry",
    "WorkflowVariable"
]
"""
Hierarchical Orchestration Pattern

Custom implementation of a hierarchical (manager-worker) pattern where a manager agent
coordinates multiple worker agents, delegates tasks, and aggregates results.

This is NOT in MAF - custom implementation like ReAct.
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum
import asyncio

from ..core.orchestrator import OrchestrationPattern


class TaskAllocationStrategy(str, Enum):
    """Strategy for allocating tasks to workers."""
    ROUND_ROBIN = "round_robin"  # Distribute evenly
    EXPERTISE_BASED = "expertise"  # Based on worker specialization
    LOAD_BALANCED = "load_balanced"  # Based on current workload
    FIRST_AVAILABLE = "first_available"  # First worker to respond


class WorkerTask(BaseModel):
    """A task assigned to a worker agent."""
    task_id: str
    worker_agent: str
    task_description: str
    priority: int = Field(default=0, description="Task priority (higher = more important)")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs this depends on")
    status: str = Field(default="pending", description="Task status")
    result: Optional[Any] = None
    error: Optional[str] = None
    
    class Config:
        use_enum_values = True


class HierarchicalPattern(OrchestrationPattern):
    """
    Hierarchical (manager-worker) orchestration pattern implementation.
    
    Implements a two-tier hierarchy where:
    1. A manager agent receives the overall task
    2. Manager breaks down the task into subtasks
    3. Manager delegates subtasks to specialized worker agents
    4. Workers execute their assigned tasks
    5. Manager aggregates worker results into final output
    
    This pattern is ideal for:
    - Complex tasks requiring decomposition
    - Parallel work distribution
    - Specialized teams (research, analysis, writing, etc.)
    - Resource management and load balancing
    """
    
    # Hierarchical-specific configuration as Pydantic fields
    manager_agent: str = Field(description="Manager agent coordinating workers")
    worker_agents: List[str] = Field(description="Worker agents performing tasks")
    allocation_strategy: str = Field(
        default="expertise",
        description="Task allocation strategy"
    )
    max_workers_per_task: int = Field(
        default=1,
        description="Maximum workers assigned to a single task"
    )
    enable_worker_collaboration: bool = Field(
        default=False,
        description="Whether workers can collaborate with each other"
    )
    require_manager_approval: bool = Field(
        default=False,
        description="Whether manager must approve worker outputs"
    )
    timeout_per_worker: int = Field(
        default=300,
        description="Timeout in seconds for each worker task"
    )
    
    def __init__(
        self,
        manager_agent: str,
        worker_agents: List[str],
        worker_expertise: Optional[Dict[str, List[str]]] = None,
        name: str = "hierarchical",
        description: str = "",
        tools: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize hierarchical pattern.
        
        Args:
            manager_agent: Name of the manager agent
            worker_agents: List of worker agent names
            worker_expertise: Optional dict mapping worker names to their areas of expertise
            name: Pattern name
            description: Pattern description
            tools: Optional MCP tools to use
            config: Optional pattern configuration with:
                - allocation_strategy: 'round_robin', 'expertise', 'load_balanced', 'first_available'
                - max_workers_per_task: Max workers per task (default: 1)
                - enable_worker_collaboration: Allow worker-to-worker communication (default: False)
                - require_manager_approval: Manager approves outputs (default: False)
                - timeout_per_worker: Timeout per worker task in seconds (default: 300)
        """
        if not worker_agents:
            raise ValueError("At least one worker agent is required")
        
        # Extract hierarchical-specific config
        _config = config or {}
        allocation_strategy = _config.get("allocation_strategy", "expertise")
        max_workers_per_task = _config.get("max_workers_per_task", 1)
        enable_worker_collaboration = _config.get("enable_worker_collaboration", False)
        require_manager_approval = _config.get("require_manager_approval", False)
        timeout_per_worker = _config.get("timeout_per_worker", 300)
        
        # Store worker expertise
        self.worker_expertise = worker_expertise or {}
        
        # All agents = manager + workers
        all_agents = [manager_agent] + worker_agents
        
        super().__init__(
            name=name,
            pattern_type="hierarchical",
            agents=all_agents,
            description=description or "Hierarchical pattern with manager-worker coordination",
            tools=tools,
            config=config,
            manager_agent=manager_agent,
            worker_agents=worker_agents,
            allocation_strategy=allocation_strategy,
            max_workers_per_task=max_workers_per_task,
            enable_worker_collaboration=enable_worker_collaboration,
            require_manager_approval=require_manager_approval,
            timeout_per_worker=timeout_per_worker
        )
    
    def allocate_tasks(
        self,
        tasks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[WorkerTask]]:
        """
        Allocate tasks to workers based on the configured strategy.
        
        Args:
            tasks: List of task descriptions with metadata
            context: Optional context for allocation decisions
            
        Returns:
            Dict mapping worker names to their assigned tasks
        """
        allocations: Dict[str, List[WorkerTask]] = {worker: [] for worker in self.worker_agents}
        
        if self.allocation_strategy == "round_robin":
            return self._allocate_round_robin(tasks, allocations)
        elif self.allocation_strategy == "expertise":
            return self._allocate_by_expertise(tasks, allocations)
        elif self.allocation_strategy == "load_balanced":
            return self._allocate_load_balanced(tasks, allocations, context)
        elif self.allocation_strategy == "first_available":
            return self._allocate_first_available(tasks, allocations)
        else:
            # Default to round-robin
            return self._allocate_round_robin(tasks, allocations)
    
    def _allocate_round_robin(
        self,
        tasks: List[Dict[str, Any]],
        allocations: Dict[str, List[WorkerTask]]
    ) -> Dict[str, List[WorkerTask]]:
        """Allocate tasks in round-robin fashion."""
        worker_index = 0
        for i, task in enumerate(tasks):
            worker = self.worker_agents[worker_index]
            worker_task = WorkerTask(
                task_id=f"task_{i}",
                worker_agent=worker,
                task_description=task.get("description", ""),
                priority=task.get("priority", 0),
                dependencies=task.get("dependencies", [])
            )
            allocations[worker].append(worker_task)
            worker_index = (worker_index + 1) % len(self.worker_agents)
        
        return allocations
    
    def _allocate_by_expertise(
        self,
        tasks: List[Dict[str, Any]],
        allocations: Dict[str, List[WorkerTask]]
    ) -> Dict[str, List[WorkerTask]]:
        """Allocate tasks based on worker expertise."""
        for i, task in enumerate(tasks):
            task_requirements = task.get("requirements", [])
            best_worker = self._find_best_worker(task_requirements)
            
            worker_task = WorkerTask(
                task_id=f"task_{i}",
                worker_agent=best_worker,
                task_description=task.get("description", ""),
                priority=task.get("priority", 0),
                dependencies=task.get("dependencies", [])
            )
            allocations[best_worker].append(worker_task)
        
        return allocations
    
    def _find_best_worker(self, requirements: List[str]) -> str:
        """Find worker with best matching expertise."""
        best_worker = self.worker_agents[0]
        best_score = 0
        
        for worker in self.worker_agents:
            expertise = self.worker_expertise.get(worker, [])
            # Calculate match score
            score = len(set(requirements) & set(expertise))
            if score > best_score:
                best_score = score
                best_worker = worker
        
        return best_worker
    
    def _allocate_load_balanced(
        self,
        tasks: List[Dict[str, Any]],
        allocations: Dict[str, List[WorkerTask]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[WorkerTask]]:
        """Allocate tasks based on current worker load."""
        # Sort workers by current load (ascending)
        worker_loads = {worker: len(tasks) for worker, tasks in allocations.items()}
        
        for i, task in enumerate(tasks):
            # Find worker with least load
            least_loaded = min(worker_loads, key=worker_loads.get)
            
            worker_task = WorkerTask(
                task_id=f"task_{i}",
                worker_agent=least_loaded,
                task_description=task.get("description", ""),
                priority=task.get("priority", 0),
                dependencies=task.get("dependencies", [])
            )
            allocations[least_loaded].append(worker_task)
            worker_loads[least_loaded] += 1
        
        return allocations
    
    def _allocate_first_available(
        self,
        tasks: List[Dict[str, Any]],
        allocations: Dict[str, List[WorkerTask]]
    ) -> Dict[str, List[WorkerTask]]:
        """Allocate all tasks to first worker (will be executed sequentially)."""
        first_worker = self.worker_agents[0]
        
        for i, task in enumerate(tasks):
            worker_task = WorkerTask(
                task_id=f"task_{i}",
                worker_agent=first_worker,
                task_description=task.get("description", ""),
                priority=task.get("priority", 0),
                dependencies=task.get("dependencies", [])
            )
            allocations[first_worker].append(worker_task)
        
        return allocations
    
    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the hierarchical pattern.
        
        Process:
        1. Manager receives input and creates execution plan
        2. Manager breaks down into subtasks
        3. Tasks allocated to workers based on strategy
        4. Workers execute tasks (potentially in parallel)
        5. Manager aggregates results
        6. Optional: Manager review/approval of outputs
        
        Args:
            input_data: Initial task or problem statement
            context: Optional execution context
            
        Returns:
            Final aggregated result from manager
        """
        # The actual execution is handled by the orchestrator
        # This is a custom implementation similar to ReAct
        return await self._execute_with_orchestrator(input_data, context)
    
    def validate(self) -> bool:
        """
        Validate the hierarchical configuration.
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        if not self.worker_agents:
            raise ValueError("At least one worker agent is required")
        
        if self.manager_agent in self.worker_agents:
            raise ValueError("Manager agent cannot also be a worker agent")
        
        if self.max_workers_per_task < 1:
            raise ValueError("max_workers_per_task must be at least 1")
        
        if self.timeout_per_worker < 1:
            raise ValueError("timeout_per_worker must be at least 1")
        
        if self.allocation_strategy not in ["round_robin", "expertise", "load_balanced", "first_available"]:
            raise ValueError("Invalid allocation_strategy")
        
        # Validate worker expertise references
        for worker, expertise in self.worker_expertise.items():
            if worker not in self.worker_agents:
                raise ValueError(f"Worker '{worker}' in expertise map not in worker_agents list")
        
        return True
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of hierarchical configuration."""
        return {
            "pattern_type": "hierarchical",
            "manager": self.manager_agent,
            "workers": self.worker_agents,
            "worker_count": len(self.worker_agents),
            "allocation_strategy": self.allocation_strategy,
            "max_workers_per_task": self.max_workers_per_task,
            "enable_collaboration": self.enable_worker_collaboration,
            "require_approval": self.require_manager_approval,
            "timeout_per_worker": self.timeout_per_worker,
            "worker_expertise": self.worker_expertise
        }
    
    def get_worker_info(self, worker_name: str) -> Dict[str, Any]:
        """
        Get information about a specific worker.
        
        Args:
            worker_name: Name of the worker agent
            
        Returns:
            Dict with worker information
        """
        if worker_name not in self.worker_agents:
            raise ValueError(f"Worker '{worker_name}' not found")
        
        return {
            "name": worker_name,
            "expertise": self.worker_expertise.get(worker_name, []),
            "manager": self.manager_agent,
            "can_collaborate": self.enable_worker_collaboration
        }


# Helper functions for common hierarchical patterns

def create_research_team(
    manager: str = "research_manager",
    researchers: Optional[List[str]] = None
) -> HierarchicalPattern:
    """
    Create a research team hierarchical pattern.
    
    Args:
        manager: Name of research manager agent
        researchers: List of researcher agent names
        
    Returns:
        Configured HierarchicalPattern
    """
    if researchers is None:
        researchers = ["primary_researcher", "secondary_researcher", "fact_checker"]
    
    expertise = {
        "primary_researcher": ["research", "analysis", "synthesis"],
        "secondary_researcher": ["research", "data_collection"],
        "fact_checker": ["verification", "fact_checking", "validation"]
    }
    
    return HierarchicalPattern(
        manager_agent=manager,
        worker_agents=researchers,
        worker_expertise={k: v for k, v in expertise.items() if k in researchers},
        name="research_team",
        description="Research team with specialized researchers",
        config={
            "allocation_strategy": "expertise",
            "enable_worker_collaboration": True
        }
    )


def create_content_team(
    manager: str = "content_manager",
    content_workers: Optional[List[str]] = None
) -> HierarchicalPattern:
    """
    Create a content creation team hierarchical pattern.
    
    Args:
        manager: Name of content manager agent
        content_workers: List of content worker agent names
        
    Returns:
        Configured HierarchicalPattern
    """
    if content_workers is None:
        content_workers = ["researcher", "writer", "editor", "reviewer"]
    
    expertise = {
        "researcher": ["research", "data_collection", "sourcing"],
        "writer": ["writing", "content_creation", "storytelling"],
        "editor": ["editing", "proofreading", "style"],
        "reviewer": ["review", "quality_assurance", "feedback"]
    }
    
    return HierarchicalPattern(
        manager_agent=manager,
        worker_agents=content_workers,
        worker_expertise={k: v for k, v in expertise.items() if k in content_workers},
        name="content_team",
        description="Content creation team with specialized roles",
        config={
            "allocation_strategy": "expertise",
            "require_manager_approval": True,
            "enable_worker_collaboration": False
        }
    )


def create_analysis_team(
    manager: str = "analysis_manager",
    analysts: Optional[List[str]] = None
) -> HierarchicalPattern:
    """
    Create an analysis team hierarchical pattern.
    
    Args:
        manager: Name of analysis manager agent
        analysts: List of analyst agent names
        
    Returns:
        Configured HierarchicalPattern
    """
    if analysts is None:
        analysts = ["data_analyst", "statistical_analyst", "business_analyst"]
    
    expertise = {
        "data_analyst": ["data_processing", "data_cleaning", "visualization"],
        "statistical_analyst": ["statistics", "modeling", "hypothesis_testing"],
        "business_analyst": ["business_analysis", "insights", "recommendations"]
    }
    
    return HierarchicalPattern(
        manager_agent=manager,
        worker_agents=analysts,
        worker_expertise={k: v for k, v in expertise.items() if k in analysts},
        name="analysis_team",
        description="Analysis team with specialized analysts",
        config={
            "allocation_strategy": "expertise",
            "enable_worker_collaboration": True,
            "max_workers_per_task": 2
        }
    )


# Example usage patterns
EXAMPLE_MANAGER_WORKER_CONFIG = {
    "allocation_strategy": "expertise",
    "max_workers_per_task": 1,
    "enable_worker_collaboration": False,
    "require_manager_approval": False,
    "timeout_per_worker": 300
}

EXAMPLE_COLLABORATIVE_TEAM_CONFIG = {
    "allocation_strategy": "load_balanced",
    "max_workers_per_task": 2,
    "enable_worker_collaboration": True,
    "require_manager_approval": True,
    "timeout_per_worker": 600
}

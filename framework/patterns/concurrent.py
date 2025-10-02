"""
Concurrent Orchestration Pattern

Implementation of concurrent agent execution where multiple agents work
simultaneously on the same task with result aggregation and synchronization.
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from ..core.orchestrator import OrchestrationPattern


class ConcurrentPattern(OrchestrationPattern):
    """
    Concurrent orchestration pattern implementation.
    
    Executes multiple agents simultaneously on the same input and
    aggregates their results for comprehensive analysis.
    """
    
    # Concurrent-specific configuration as Pydantic fields
    max_concurrent: Optional[int] = Field(default=None, description="Maximum number of agents to run concurrently")
    timeout_per_agent: int = Field(default=300, description="Timeout in seconds for each agent")
    require_all_success: bool = Field(default=False, description="Whether all agents must succeed")
    aggregation_method: str = Field(default="merge", description="Method for aggregating results")
    wait_for_all: bool = Field(default=True, description="Whether to wait for all agents to complete")
    
    def __init__(
        self,
        agents: List[str],
        name: str = "concurrent",
        description: str = "",
        tools: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize concurrent pattern.
        
        Args:
            agents: List of agent names to execute concurrently
            name: Pattern name
            description: Pattern description
            tools: Optional MCP tools to use
            config: Optional pattern configuration
        """
        # Extract concurrent-specific config
        _config = config or {}
        max_concurrent = _config.get("max_concurrent", len(agents))
        timeout_per_agent = _config.get("timeout_per_agent", 300)
        require_all_success = _config.get("require_all_success", False)
        aggregation_method = _config.get("aggregation_method", "merge")
        wait_for_all = _config.get("wait_for_all", True)
        
        super().__init__(
            name=name,
            description=description or f"Concurrent execution of {len(agents)} agents",
            agents=agents,
            tools=tools,
            config=_config,
            max_concurrent=max_concurrent,
            timeout_per_agent=timeout_per_agent,
            require_all_success=require_all_success,
            aggregation_method=aggregation_method,
            wait_for_all=wait_for_all
        )

    def validate(self) -> tuple[bool, List[str]]:
        """Validate the concurrent pattern configuration."""
        issues = []
        
        if not self.agents:
            issues.append("No agents specified for concurrent pattern")
        
        if len(self.agents) < 2:
            issues.append("Concurrent pattern requires at least 2 agents")
        
        if self.max_concurrent < 1:
            issues.append("max_concurrent must be at least 1")
        
        if self.max_concurrent > 20:  # Reasonable upper limit
            issues.append("max_concurrent should not exceed 20 for performance reasons")
        
        if self.timeout_per_agent < 10:
            issues.append("timeout_per_agent should be at least 10 seconds")
        
        valid_aggregation_methods = ["merge", "vote", "weighted", "first_success", "best_score"]
        if self.aggregation_method not in valid_aggregation_methods:
            issues.append(f"aggregation_method must be one of: {valid_aggregation_methods}")
        
        return len(issues) == 0, issues

    def get_execution_plan(self) -> Dict[str, Any]:
        """Get execution plan for this concurrent pattern."""
        # Group agents into batches based on max_concurrent limit
        batches = []
        current_batch = []
        
        for i, agent in enumerate(self.agents):
            current_batch.append(agent)
            
            if len(current_batch) >= self.max_concurrent or i == len(self.agents) - 1:
                batches.append(current_batch)
                current_batch = []
        
        steps = []
        for batch_num, batch_agents in enumerate(batches):
            step = {
                "step_number": batch_num + 1,
                "agents": batch_agents,
                "description": f"Execute batch {batch_num + 1} with {len(batch_agents)} agents concurrently",
                "depends_on": [batch_num] if batch_num > 0 else [],
                "parallel": True,
                "timeout": self.timeout_per_agent
            }
            steps.append(step)
        
        return {
            "pattern": self.name,
            "type": "concurrent",
            "steps": steps,
            "total_batches": len(batches),
            "total_agents": len(self.agents),
            "estimated_time": len(batches) * self.timeout_per_agent,
            "config": {
                "max_concurrent": self.max_concurrent,
                "timeout_per_agent": self.timeout_per_agent,
                "require_all_success": self.require_all_success,
                "aggregation_method": self.aggregation_method,
                "wait_for_all": self.wait_for_all
            }
        }

    def get_agent_batches(self) -> List[List[str]]:
        """Get agents grouped into execution batches."""
        batches = []
        current_batch = []
        
        for agent in self.agents:
            current_batch.append(agent)
            
            if len(current_batch) >= self.max_concurrent:
                batches.append(current_batch)
                current_batch = []
        
        if current_batch:
            batches.append(current_batch)
        
        return batches

    def should_continue_on_failure(self, failed_agents: Set[str]) -> bool:
        """Determine if execution should continue when some agents fail."""
        if self.require_all_success:
            return len(failed_agents) == 0
        
        # Continue if at least one agent succeeded
        successful_agents = len(self.agents) - len(failed_agents)
        return successful_agents > 0

    def aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from concurrent agent execution."""
        if not results:
            return {
                "aggregated_result": "No results to aggregate",
                "aggregation_method": self.aggregation_method,
                "agent_count": 0
            }
        
        if self.aggregation_method == "merge":
            return self._merge_results(results)
        elif self.aggregation_method == "vote":
            return self._vote_on_results(results)
        elif self.aggregation_method == "weighted":
            return self._weighted_aggregation(results)
        elif self.aggregation_method == "first_success":
            return self._first_success_result(results)
        elif self.aggregation_method == "best_score":
            return self._best_score_result(results)
        else:
            # Default to merge
            return self._merge_results(results)

    def calculate_progress(self, completed_agents: Set[str]) -> float:
        """Calculate completion progress (0.0 to 1.0)."""
        if not self.agents:
            return 1.0
        
        return len(completed_agents) / len(self.agents)

    def get_remaining_agents(self, completed_agents: Set[str]) -> List[str]:
        """Get list of remaining agents to execute."""
        return [agent for agent in self.agents if agent not in completed_agents]

    def estimate_completion_time(self, completed_agents: Set[str]) -> float:
        """Estimate remaining completion time in seconds."""
        remaining_count = len(self.agents) - len(completed_agents)
        
        if remaining_count <= 0:
            return 0.0
        
        # Calculate how many batches are needed for remaining agents
        batches_needed = (remaining_count + self.max_concurrent - 1) // self.max_concurrent
        
        return batches_needed * self.timeout_per_agent

    # Private aggregation methods

    def _merge_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Simple merge of all results."""
        merged_content = []
        metadata = {"agents": list(results.keys())}
        
        for agent, result in results.items():
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
            else:
                content = str(result)
            
            merged_content.append(f"**{agent}**: {content}")
        
        return {
            "aggregated_result": "\n\n".join(merged_content),
            "aggregation_method": "merge",
            "agent_count": len(results),
            "metadata": metadata
        }

    def _vote_on_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Vote-based aggregation (simplified)."""
        # For now, just return the most common result
        # In production, implement proper voting logic
        
        result_counts = {}
        for agent, result in results.items():
            content = result.get("content", str(result)) if isinstance(result, dict) else str(result)
            result_counts[content] = result_counts.get(content, 0) + 1
        
        if result_counts:
            winning_result = max(result_counts.items(), key=lambda x: x[1])
            return {
                "aggregated_result": winning_result[0],
                "aggregation_method": "vote",
                "vote_count": winning_result[1],
                "total_votes": len(results),
                "agent_count": len(results)
            }
        
        return {
            "aggregated_result": "No consensus reached",
            "aggregation_method": "vote",
            "agent_count": len(results)
        }

    def _weighted_aggregation(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Weighted aggregation based on agent reliability or other metrics."""
        # Simplified implementation - in production, use actual agent weights
        agent_weights = {agent: 1.0 for agent in results.keys()}  # Equal weights for now
        
        weighted_content = []
        total_weight = sum(agent_weights.values())
        
        for agent, result in results.items():
            weight = agent_weights.get(agent, 1.0)
            content = result.get("content", str(result)) if isinstance(result, dict) else str(result)
            
            weighted_content.append({
                "agent": agent,
                "content": content,
                "weight": weight,
                "normalized_weight": weight / total_weight
            })
        
        # Sort by weight (highest first)
        weighted_content.sort(key=lambda x: x["weight"], reverse=True)
        
        # Create aggregated result with weight information
        aggregated_parts = []
        for item in weighted_content:
            weight_pct = item["normalized_weight"] * 100
            aggregated_parts.append(f"**{item['agent']}** (weight: {weight_pct:.1f}%): {item['content']}")
        
        return {
            "aggregated_result": "\n\n".join(aggregated_parts),
            "aggregation_method": "weighted",
            "agent_count": len(results),
            "weights": {item["agent"]: item["weight"] for item in weighted_content}
        }

    def _first_success_result(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Return the first successful result."""
        for agent, result in results.items():
            if isinstance(result, dict):
                if result.get("success", True):  # Default to True if not specified
                    return {
                        "aggregated_result": result.get("content", str(result)),
                        "aggregation_method": "first_success",
                        "selected_agent": agent,
                        "agent_count": len(results)
                    }
            else:
                # Non-dict results are considered successful
                return {
                    "aggregated_result": str(result),
                    "aggregation_method": "first_success",
                    "selected_agent": agent,
                    "agent_count": len(results)
                }
        
        # No successful results found
        return {
            "aggregated_result": "No successful results found",
            "aggregation_method": "first_success",
            "selected_agent": None,
            "agent_count": len(results)
        }

    def _best_score_result(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Return the result with the best score."""
        best_result = None
        best_score = -float('inf')
        best_agent = None
        
        for agent, result in results.items():
            # Extract score from result
            score = 0.0
            if isinstance(result, dict):
                score = result.get("score", 0.0)
                if "quality_score" in result:
                    score = result["quality_score"]
                elif "confidence" in result:
                    score = result["confidence"]
            
            if score > best_score:
                best_score = score
                best_result = result
                best_agent = agent
        
        if best_result is not None:
            content = best_result.get("content", str(best_result)) if isinstance(best_result, dict) else str(best_result)
            
            return {
                "aggregated_result": content,
                "aggregation_method": "best_score",
                "selected_agent": best_agent,
                "best_score": best_score,
                "agent_count": len(results)
            }
        
        # Fallback to first result if no scores available
        first_agent, first_result = next(iter(results.items()))
        content = first_result.get("content", str(first_result)) if isinstance(first_result, dict) else str(first_result)
        
        return {
            "aggregated_result": content,
            "aggregation_method": "best_score",
            "selected_agent": first_agent,
            "best_score": 0.0,
            "agent_count": len(results),
            "note": "No scores available, selected first result"
        }

    def __str__(self) -> str:
        """String representation of the pattern."""
        return f"ConcurrentPattern(agents={self.agents}, max_concurrent={self.max_concurrent})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"ConcurrentPattern("
            f"name='{self.name}', "
            f"agents={self.agents}, "
            f"max_concurrent={self.max_concurrent}, "
            f"aggregation_method='{self.aggregation_method}', "
            f"tools={self.tools})"
        )
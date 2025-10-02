"""
Orchestration Patterns

Implementation of various multi-agent orchestration patterns including:
- Sequential: Chain-based execution with context passing
- Concurrent: Parallel agent execution with result aggregation
- ReAct: Reasoning and acting with dynamic plan updates (custom)
- Group Chat: Multi-agent collaborative conversations (MAF wrapper)
- Handoff: Dynamic agent delegation (MAF wrapper)
- Hierarchical: Manager-worker coordination (custom)
"""

from .sequential import SequentialPattern
from .concurrent import ConcurrentPattern
from .react import ReActPattern
from .group_chat import GroupChatPattern, RoundRobinManager
from .handoff import HandoffPattern, create_triage_pattern, create_escalation_pattern
from .hierarchical import (
    HierarchicalPattern,
    create_research_team,
    create_content_team,
    create_analysis_team
)

__all__ = [
    # Core patterns
    "SequentialPattern",
    "ConcurrentPattern",
    "ReActPattern",
    "GroupChatPattern",
    "HandoffPattern",
    "HierarchicalPattern",
    
    # Group chat utilities
    "RoundRobinManager",
    
    # Handoff utilities
    "create_triage_pattern",
    "create_escalation_pattern",
    
    # Hierarchical utilities
    "create_research_team",
    "create_content_team",
    "create_analysis_team",
]
"""
Performance monitoring middleware for Microsoft Agent Framework.

Based on: agent_and_run_level_middleware.py sample
"""

import time
from typing import Callable, Awaitable
from agent_framework import AgentRunContext


async def performance_monitor_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Agent-level performance monitoring for all runs."""
    print("[PerformanceMonitor] Starting performance monitoring...")
    
    start_time = time.time()
    context.metadata["start_time"] = start_time
    
    try:
        await next(context)
    finally:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"[PerformanceMonitor] Total execution time: {duration:.3f}s")
        context.metadata["execution_time"] = duration
        context.metadata["end_time"] = end_time
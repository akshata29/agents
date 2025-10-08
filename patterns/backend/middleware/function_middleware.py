"""
Function logging middleware for Microsoft Agent Framework.

Based on: agent_and_run_level_middleware.py sample
"""

from typing import Callable, Awaitable
from agent_framework import FunctionInvocationContext


async def function_logging_middleware(
    context: FunctionInvocationContext,
    next: Callable[[FunctionInvocationContext], Awaitable[None]],
) -> None:
    """Function middleware that logs all function calls."""
    function_name = context.function.name
    args = context.arguments
    
    print(f"[FunctionLog] Calling function: {function_name} with args: {args}")
    
    try:
        await next(context)
        print(f"[FunctionLog] Function {function_name} completed successfully")
    except Exception as e:
        print(f"[FunctionLog] Function {function_name} failed: {e}")
        raise
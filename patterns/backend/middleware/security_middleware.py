"""
Security middleware implementation for Microsoft Agent Framework.

Based on: agent_and_run_level_middleware.py sample
"""

from typing import Callable, Awaitable
from agent_framework import AgentMiddleware, AgentRunContext


class SecurityAgentMiddleware(AgentMiddleware):
    """Agent-level security middleware that validates all requests."""
    
    def __init__(self, blocked_terms: list[str] = None):
        """
        Initialize security middleware.
        
        Args:
            blocked_terms: List of terms to block in queries
        """
        super().__init__()
        self.blocked_terms = blocked_terms or [
            "password", "secret", "credentials", "hack", "exploit", "token"
        ]
    
    async def process(self, context: AgentRunContext, next: Callable[[AgentRunContext], Awaitable[None]]) -> None:
        """Validate security of incoming requests."""
        print("[SecurityMiddleware] Checking security for all requests...")
        
        # Check for security violations in the last user message
        last_message = context.messages[-1] if context.messages else None
        if last_message and last_message.text:
            query = last_message.text.lower()
            
            # Check for blocked terms
            for term in self.blocked_terms:
                if term in query:
                    print(f"[SecurityMiddleware] Security violation detected: '{term}' - Blocking request.")
                    context.metadata["security_violation"] = term
                    return  # Don't call next() to prevent execution
        
        print("[SecurityMiddleware] Security check passed.")
        context.metadata["security_validated"] = True
        await next(context)
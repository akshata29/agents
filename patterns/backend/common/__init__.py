"""
Microsoft Agent Framework - Multi-Agent Orchestration Patterns
Common module providing agent factory and utilities.
"""

from .agents import AgentFactory, get_weather, search_web, calculate_metrics, generate_report

__all__ = [
    'AgentFactory',
    'get_weather', 
    'search_web',
    'calculate_metrics',
    'generate_report'
]
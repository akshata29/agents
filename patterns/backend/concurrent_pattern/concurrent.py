"""
Concurrent Orchestration Pattern using Microsoft Agent Framework

This pattern demonstrates concurrent agent orchestration following the documented
best practices for parallel multi-agent execution. Multiple specialized agents
work independently on the same task, providing diverse perspectives that are
aggregated into a comprehensive analysis.

Pattern Architecture: Summarizer ⟺ ProsCons ⟺ RiskAssessor (parallel execution)

Key Characteristics:
- Agents execute simultaneously without dependencies
- Each agent provides specialized analysis (summary, pros/cons, risk assessment)  
- Results are automatically aggregated by ConcurrentBuilder
- Ideal for multi-perspective decision-making and ensemble reasoning
- Reduces overall processing time through true parallel execution

Implementation follows the documented 6-step process:
1. Create chat client (via AgentFactory)
2. Define specialized agents with distinct expertise areas
3. Build concurrent workflow using ConcurrentBuilder
4. Run workflow with parallel agent execution
5. Process aggregated results from all agents
6. Handle combined responses with author identification

Uses ConcurrentBuilder from the official Microsoft Agent Framework.
"""

import asyncio
from datetime import datetime
from typing import Any, cast

from agent_framework import ConcurrentBuilder, WorkflowOutputEvent, ChatMessage
from azure.identity import AzureCliCredential

from common.agents import AgentFactory


async def run_concurrent_orchestration(task: str = None) -> list:
    """
    Demonstrates concurrent orchestration following Microsoft Agent Framework best practices.
    
    This implementation follows the documented 6-step concurrent pattern process:
    1. Create chat client (via AgentFactory) 
    2. Define specialized agents with distinct analysis capabilities
    3. Build concurrent workflow using ConcurrentBuilder class
    4. Run workflow - all agents execute in parallel
    5. Process results - extract outputs from aggregated conversations  
    6. Handle aggregated responses - process messages with author identification
    
    The concurrent pattern is ideal for:
    - Tasks benefiting from multiple specialized perspectives
    - Independent analyses that can run simultaneously
    - Ensemble decision-making and multi-agent brainstorming
    - Scenarios where speed matters and parallel execution reduces wait time
    
    Args:
        task (str, optional): The business task to analyze through concurrent agents.
                            If None, uses a default workplace policy evaluation scenario.
    
    Returns:
        list: Formatted responses from all agents containing:
              [
                {
                  "agent": str,        # Agent name (Summarizer, ProsCons, RiskAssessor)
                  "input": str,        # Original task input
                  "output": str,       # Agent's analysis output
                  "timestamp": str     # ISO timestamp of completion
                }
              ]
    
    Raises:
        Exception: If Azure OpenAI client initialization fails
        Exception: If workflow execution encounters unrecoverable errors
        
    Example:
        >>> task = "Evaluate implementing 4-day work week for tech company"
        >>> results = await run_concurrent_orchestration(task)
        >>> print(f"Concurrent analysis completed with {len(results)} agent perspectives")
        
    Note:
        This implementation ensures true parallel execution where agents work
        independently and results are aggregated, following documented concurrent
        orchestration best practices exactly.
    """
    if task is None:
        task = "Evaluate the feasibility and implications of implementing a 4-day work week policy in a mid-size technology company with 200 employees."
    
    print("=" * 80)
    print("CONCURRENT ORCHESTRATION PATTERN")
    print("=" * 80)
    print(f"Task: {task}")
    print()
    
    # STEP 1: Create your chat client (via AgentFactory)
    # AgentFactory encapsulates Azure OpenAI client setup with proper credentials
    # and configuration management, following documented best practices
    factory = AgentFactory()
    
    # STEP 2: Define your agents
    # Create specialized agents with distinct analysis capabilities
    # Each agent will work independently and provide unique perspectives
    print("Creating specialized analysis agents...")
    
    summarizer = factory.create_summarizer_agent()      # 📊 Executive summary & key insights
    pros_cons = factory.create_pros_cons_agent()        # ⚖️  Balanced pros/cons analysis
    risk_assessor = factory.create_risk_assessor_agent() # 🚨 Risk identification & mitigation
    
    print("✓ Summarizer Agent: Key insights and overview")
    print("✓ Pros/Cons Agent: Balanced advantage/disadvantage analysis") 
    print("✓ Risk Assessor Agent: Risk identification and mitigation")
    print()
    
    # STEP 3: Build the concurrent workflow
    # Use ConcurrentBuilder to create workflow that runs multiple agents in parallel
    # Add agent instances as participants using participants() method
    print("Building concurrent workflow...")
    
    workflow = ConcurrentBuilder().participants([
        summarizer,    # 📊 Independent executive summary analysis
        pros_cons,     # ⚖️  Parallel pros/cons evaluation
        risk_assessor  # 🚨 Concurrent risk assessment
    ]).build()
    
    # Workflow is now configured for true parallel execution
    print("✓ Concurrent workflow configured: All agents execute in parallel")
    print()
    
    # STEP 4: Run the workflow  
    # Call workflow's run method - runs all agents concurrently and returns events
    # All agents execute simultaneously on the same task input
    print("Executing concurrent orchestration...")
    print("-" * 60)
    
    outputs = []
    
    # Stream execution events to capture real-time progress from parallel agents
    # Each agent works independently without waiting for others to complete
    async for event in workflow.run_stream(task):
        # STEP 5: Process the results
        # Handle workflow output events containing aggregated conversations
        if isinstance(event, WorkflowOutputEvent):
            outputs.append(cast(list[ChatMessage], event.data))
        
        # Optional: Track individual agent progress for monitoring
        # if hasattr(event, 'agent_id'):
        #     print(f"Event from {event.agent_id}")
    
    # Display results from all agents
    if outputs:
        print("\n" + "=" * 80)
        print("CONCURRENT ORCHESTRATION RESULTS")
        print("=" * 80)
        
        # STEP 5: Process the results (continued)
        # Extract outputs from workflow events - results contain combined conversations
        # The ConcurrentBuilder automatically aggregates all agent responses
        aggregated_messages = outputs[0] if outputs else []
        
        # STEP 6: Handle the aggregated responses
        # Process aggregated messages from all agents
        # Each message includes author name and content for identification
        agent_responses = {}
        
        for message in aggregated_messages:
            agent_name = message.author_name or "assistant"
            if agent_name not in agent_responses:
                agent_responses[agent_name] = []
            if message.role.value != "user":  # Skip user messages in display
                agent_responses[agent_name].append(message.text)
        
        # Display each agent's contribution
        for agent_name, responses in agent_responses.items():
            print(f"\n📊 {agent_name.upper()} ANALYSIS")
            print("-" * 60)
            for response in responses:
                print(response)
                print()
    else:
        print("No output received from workflow.")
    
    print("=" * 80)
    print("Concurrent orchestration completed!")
    print("All agents have provided their parallel analysis.")
    print("=" * 80)
    
    # Return the agent outputs for API consumption
    if aggregated_messages:
        agent_responses_for_api = []
        agent_responses = {}
        
        for message in aggregated_messages:
            agent_name = message.author_name or "assistant"
            if agent_name not in agent_responses:
                agent_responses[agent_name] = []
            if message.role.value != "user":
                agent_responses[agent_name].append(message.text)
        
        for agent_name, responses in agent_responses.items():
            for response in responses:
                agent_responses_for_api.append({
                    "agent": agent_name,
                    "input": task,
                    "output": response,
                    "timestamp": datetime.now().isoformat()
                })
        
        return agent_responses_for_api
    else:
        return []


async def main():
    """Main function for standalone execution."""
    await run_concurrent_orchestration()


if __name__ == "__main__":
    asyncio.run(main())
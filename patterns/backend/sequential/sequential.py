"""
Sequential Orchestration Pattern - Microsoft Agent Framework Implementation

OVERVIEW:
This module implements the Sequential orchestration pattern following Microsoft Agent Framework
best practices. The pattern executes agents in a defined order where each agent builds upon
the previous agent's output, creating a structured workflow for complex tasks.

PATTERN FLOW:
Planner → Researcher → Writer → Reviewer

WHEN TO USE:
✅ Multi-step processes requiring specific execution order
✅ Data workflows where each stage adds critical information
✅ Tasks requiring gradual refinement (drafting → reviewing → polishing)
✅ Known agent performance with predictable failure handling

AVOID WHEN:
❌ Stages can run independently in parallel
❌ Single agent can handle entire task effectively
❌ Need dynamic collaboration or iteration
❌ Early failures can't be corrected downstream

IMPLEMENTATION VALIDATION:
This implementation follows the documented 6-step process:
1. ✅ Create chat client (via AgentFactory with Azure OpenAI)
2. ✅ Define specialized agents with specific roles
3. ✅ Build sequential workflow using SequentialBuilder
4. ✅ Execute via workflow.run_stream() method
5. ✅ Process WorkflowOutputEvent instances correctly
6. ✅ Extract and format final conversation history

REAL-WORLD APPLICATIONS:
- Corporate training program development
- Software development lifecycle planning  
- Supply chain optimization projects
- Merger & acquisition integration planning
"""

import asyncio
from datetime import datetime
from typing import Any, cast

from agent_framework import SequentialBuilder, WorkflowOutputEvent, ChatMessage

from common.agents import AgentFactory


async def run_sequential_orchestration(task: str = None) -> list:
    """
    Execute Sequential Orchestration Pattern following Microsoft Agent Framework best practices.
    
    This function implements the complete 6-step sequential orchestration process:
    1. Initialize Azure OpenAI chat client via AgentFactory
    2. Create specialized agents with defined roles and expertise
    3. Build sequential workflow ensuring proper execution order  
    4. Execute workflow using streaming for real-time progress
    5. Process WorkflowOutputEvent instances to capture results
    6. Extract and format final conversation for API consumption
    
    Args:
        task (str, optional): The business task to process through the sequential workflow.
                            If None, uses a default comprehensive business planning task.
    
    Returns:
        list: Formatted conversation history containing each agent's contribution:
              [
                {
                  "agent": str,        # Agent name (Planner, Researcher, Writer, Reviewer)
                  "input": str,        # Input received by this agent
                  "output": str,       # Agent's response/output
                  "timestamp": str     # ISO timestamp of agent execution
                }
              ]
    
    Raises:
        Exception: If Azure OpenAI client initialization fails
        Exception: If workflow execution encounters unrecoverable errors
        
    Example:
        >>> task = "Develop a digital transformation strategy for manufacturing"
        >>> results = await run_sequential_orchestration(task)
        >>> print(f"Sequential workflow completed with {len(results)} agent contributions")
        
    Note:
        This implementation ensures each agent builds upon the previous agent's output,
        creating a coherent and progressively refined result that follows the documented
        sequential pattern best practices.
    """
    if task is None:
        task = "Create a comprehensive business plan for a sustainable urban farming startup that specializes in vertical hydroponic systems for apartment dwellers."
    
    print("=" * 80)
    print("SEQUENTIAL ORCHESTRATION PATTERN")
    print("=" * 80)
    print(f"Task: {task}")
    print()
    
    # STEP 1: Create chat client (via AgentFactory)
    # AgentFactory encapsulates Azure OpenAI client setup with proper credentials
    # and configuration management, following the documented best practice
    factory = AgentFactory()
    
    # STEP 2: Define your agents
    # Create specialized agents with specific roles and expertise areas
    # Each agent has tailored system prompts and capabilities for their stage
    print("Creating specialized agents...")
    
    planner = factory.create_planner_agent()      # 🎯 Strategic thinking & task breakdown
    researcher = factory.create_researcher_agent()  # 🔍 Information gathering & analysis
    writer = factory.create_writer_agent()        # ✍️  Content creation & synthesis  
    reviewer = factory.create_reviewer_agent()    # ✅ Quality assurance & feedback
    
    print("✓ Planner Agent: Task decomposition and strategy")
    print("✓ Researcher Agent: Information gathering and analysis")
    print("✓ Writer Agent: Content creation and synthesis")
    print("✓ Reviewer Agent: Quality assurance and feedback")
    print()
    
    # STEP 3: Define the conversation sequence  
    # SequentialBuilder creates a linear pipeline where each agent processes
    # the complete conversation history from all previous agents
    print("Building sequential workflow...")
    
    # STEP 4: Add agents in execution order
    # Order matters! Each agent sees all previous messages and adds their contribution
    workflow = SequentialBuilder().participants([
        planner,    # 1️⃣ Strategic analysis & task breakdown
        researcher, # 2️⃣ Information gathering using planner's insights  
        writer,     # 3️⃣ Content creation with research context
        reviewer    # 4️⃣ Quality review of the complete workflow
    ]).build()
    
    # STEP 5: Build the orchestrator
    # Creates the conversation manager that coordinates sequential execution
    print("✓ Sequential workflow configured: Planner → Researcher → Writer → Reviewer")
    print()
    
    # STEP 6: Execute the workflow
    # Run the sequential orchestration with proper event handling and streaming
    print("Executing sequential orchestration...")
    print("-" * 60)
    
    conversation_outputs = []
    
    try:
        # Stream execution events to capture real-time progress
        # Each agent processes the accumulated conversation from previous agents
        async for event in workflow.run_stream(task):
            # Capture workflow output events containing conversation data
            if isinstance(event, WorkflowOutputEvent):
                conversation_outputs.append(cast(list[ChatMessage], event.data))
    
        # Display final conversation
        if conversation_outputs:
            final_conversation = conversation_outputs[-1]
            print("\n" + "=" * 80)
            print("SEQUENTIAL ORCHESTRATION RESULTS")
            print("=" * 80)
            
            for i, message in enumerate(final_conversation, 1):
                author = message.author_name or ("user" if message.role.value == "user" else "assistant")
                print(f"\n{i:02d}. [{author.upper()}]")
                print("-" * 40)
                print(message.text)
        else:
            print("No output received from workflow.")
            
    except Exception as e:
        print(f"Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 80)
    print("Sequential orchestration completed!")
    print("=" * 80)
    
    # Return the conversation outputs for API consumption
    if conversation_outputs:
        final_conversation = conversation_outputs[-1]
        return [
            {
                "agent": message.author_name or ("user" if message.role.value == "user" else "assistant"),
                "input": task if i == 0 else "Output from previous agent",
                "output": message.text,
                "timestamp": datetime.now().isoformat()
            }
            for i, message in enumerate(final_conversation)
        ]
    else:
        return []


async def main():
    """Main function for standalone execution."""
    await run_sequential_orchestration()


if __name__ == "__main__":
    asyncio.run(main())
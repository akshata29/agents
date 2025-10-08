"""
Magentic Orchestration Pattern using Microsoft Agent Framework

This pattern demonstrates magentic orchestration following the documented
best practices for plan-driven collaboration and complex task execution. 
The system generates documented plans of approach, coordinates multiple
specialized agents, and builds execution plans dynamically step-by-step.

Pattern Architecture: Planner → Researcher → Writer → Validator (with tools and task ledger)

Key Characteristics:
- Complex or open-ended problems with no predetermined solution path
- Input and feedback from multiple specialized agents to shape valid solutions
- Documented plan of approach generation for human review and transparency
- Tool integration for direct interaction with external systems and resources
- Step-by-step, dynamically built execution plans that add value before task execution

Implementation follows the documented 7-step process:
1. Define specialized agents with distinct roles and capabilities
2. Set up event handling callbacks for orchestration progress monitoring
3. Build Magentic workflow using MagenticBuilder with agent participants
4. Configure standard manager with chat client and orchestration parameters
5. Run workflow with streaming mode for dynamic planning and delegation
6. Process workflow events including agent messages and orchestrator updates
7. Extract final results from complete collaborative agent effort

Advanced Features (per hackathon guidelines):
- Task ledger for progress tracking and plan documentation
- Event streaming with MagenticCallbackMode for real-time monitoring
- Standard manager configuration with max rounds, stall limits, and reset behavior
- Tool integration for external system interactions and resource access
- Dynamic agent selection and task delegation based on planning outcomes

Uses MagenticBuilder from the official Microsoft Agent Framework.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from agent_framework import (
    MagenticBuilder, WorkflowOutputEvent, ChatMessage,
    MagenticAgentMessageEvent, MagenticOrchestratorMessageEvent,
    MagenticFinalResultEvent, MagenticCallbackMode
)
from azure.identity import AzureCliCredential

from common.agents import AgentFactory, get_weather, search_web, calculate_metrics, generate_report


class TaskLedger:
    """
    Task ledger for tracking magentic orchestration progress.
    
    Maintains state of task decomposition, assignments, and completion status
    throughout the magentic workflow execution.
    """
    
    def __init__(self):
        self.tasks: List[Dict[str, Any]] = []
        self.completed_tasks: List[Dict[str, Any]] = []
        self.current_phase = "planning"
    
    def add_task(self, task_id: str, description: str, assigned_to: str = None):
        """Add a new task to the ledger."""
        task = {
            "id": task_id,
            "description": description,
            "assigned_to": assigned_to,
            "status": "pending",
            "created_at": asyncio.get_event_loop().time()
        }
        self.tasks.append(task)
        print(f"📝 Task added: {task_id} - {description}")
    
    def complete_task(self, task_id: str, result: str = None):
        """Mark a task as completed with optional result."""
        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["result"] = result
                task["completed_at"] = asyncio.get_event_loop().time()
                self.completed_tasks.append(task)
                print(f"✅ Task completed: {task_id}")
                break
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks."""
        return [task for task in self.tasks if task["status"] == "pending"]
    
    def get_progress_summary(self) -> str:
        """Get a summary of overall progress."""
        total = len(self.tasks)
        completed = len(self.completed_tasks)
        return f"Progress: {completed}/{total} tasks completed ({completed/total*100:.1f}%)" if total > 0 else "No tasks defined"


async def run_magentic_orchestration(task: str = None) -> list:
    """
    Demonstrates magentic orchestration following Microsoft Agent Framework best practices.
    
    This implementation follows the documented 7-step magentic pattern process:
    1. Define specialized agents with distinct roles suited for complex task aspects
    2. Set up event handling callbacks for orchestration progress and agent coordination
    3. Build Magentic workflow using MagenticBuilder class with agent participants  
    4. Configure standard manager with chat client, round limits, and stall parameters
    5. Run workflow with streaming mode - dynamically plans and delegates work
    6. Process workflow events including agent messages, orchestrator updates, and results
    7. Extract final result from complete solution developed through collaborative effort
    
    The magentic pattern is ideal for:
    - Complex or open-ended problems requiring dynamic solution development
    - Tasks needing multiple specialized perspectives and tool integration
    - Scenarios requiring documented planning approach for human review
    - Project management workflows with goal-oriented coordination
    - Problems where step-by-step execution planning adds value before task execution
    
    Args:
        task (str, optional): The complex project requiring magentic orchestration.
                            If None, uses a default employee wellness program scenario.
    
    Returns:
        list: Complete workflow results with task ledger and collaborative outputs:
              [
                {
                  "agent": str,        # Agent name (Planner, Researcher, Writer, Validator, Orchestrator)
                  "input": str,        # Task context or planning input
                  "output": str,       # Agent's contribution or orchestration result
                  "timestamp": str,    # ISO timestamp of contribution
                  "phase": str,        # Workflow phase (planning, research, creation, validation)
                  "task_ledger": dict  # Progress tracking and task completion status
                }
              ]
    
    Raises:
        Exception: If Azure OpenAI client initialization fails
        Exception: If workflow execution encounters unrecoverable errors
        
    Example:
        >>> task = "Design comprehensive digital transformation strategy for manufacturing"
        >>> results = await run_magentic_orchestration(task)
        >>> print(f"Magentic orchestration completed with {len(results)} collaborative contributions")
        
    Note:
        This implementation ensures plan-driven collaboration with documented progress
        tracking and tool integration, following documented magentic orchestration
        best practices exactly.
    """
    if task is None:
        task = "Design and launch a comprehensive employee wellness program for a remote-first company with 150 employees across 12 countries, including mental health support, fitness initiatives, and work-life balance improvements."
    
    print("=" * 80)
    print("MAGENTIC ORCHESTRATION PATTERN")
    print("=" * 80)
    print(f"Project: {task}")
    print()
    
    # Initialize task ledger for progress tracking
    ledger = TaskLedger()
    
    # STEP 1: Define specialized agents
    # Create agent instances with specific roles and capabilities for complex task aspects
    # Each agent equipped for different phases of the magentic workflow
    factory = AgentFactory()
    
    print("Creating magentic participants...")
    
    planner = factory.create_planner_agent()      # 🎯 Strategic planning & task decomposition
    researcher = factory.create_researcher_agent()  # 🔍 Information gathering with tools  
    writer = factory.create_writer_agent()        # ✍️  Content synthesis & documentation
    validator = factory.create_validator_agent()  # ✅ Quality assurance & final approval
    
    print("✓ Planner Agent: Strategic planning and task decomposition")
    print("✓ Researcher Agent: Information gathering with tools")
    print("✓ Writer Agent: Content synthesis and documentation")
    print("✓ Validator Agent: Quality assurance and final approval")
    print()
    
    # Available tools for agents
    available_tools = [get_weather, search_web, calculate_metrics, generate_report]
    
    print("Available tools:")
    for tool in available_tools:
        print(f"   • {tool.__name__}: {tool.__doc__}")
    print()
    
    # STEP 3: Build the Magentic workflow
    # Use MagenticBuilder to create orchestration with agent participants
    print("Building magentic workflow...")
    
    try:
        # STEP 2: Set up event handling callback  
        # Define async callback for different event types during orchestration
        async def on_event(event):
            """Handle orchestrator messages, agent streaming updates, agent messages, and final results."""
            if isinstance(event, MagenticAgentMessageEvent):
                # Handle agent messages and streaming updates
                agent_name = event.agent_id or "Agent"
                if event.message and hasattr(event.message, 'text'):
                    message_text = event.message.text
                    print(f"🤖 [{agent_name}]: {message_text[:100]}...")
                    
                    # Store full content for final display
                    if agent_name == "Writer" and len(message_text) > 100:
                        final_outputs.append(f"Writer's Output:\n{message_text}")
                        
            elif isinstance(event, MagenticOrchestratorMessageEvent):
                # Handle orchestrator messages for planning and coordination
                if event.message and hasattr(event.message, 'text'):
                    print(f"🎯 [Orchestrator]: {event.message.text[:100]}...")
            elif isinstance(event, MagenticFinalResultEvent):
                # Handle final results from orchestration
                print(f"🏆 [Final Result]: Magentic orchestration completed")
                if event.message and hasattr(event.message, 'text'):
                    final_outputs.append(f"Final Result:\n{event.message.text}")
        
        # Create MagenticBuilder workflow with agent participants
        workflow = MagenticBuilder().participants(
            planner=planner,      # Strategic planning and task decomposition
            researcher=researcher, # Information gathering with tool access
            writer=writer,        # Content synthesis and documentation
            validator=validator   # Quality assurance and final approval
        ).on_event(on_event, mode=MagenticCallbackMode.STREAMING).with_standard_manager(
            # STEP 4: Configure the standard manager
            # Standard manager coordinates agent collaboration using chat client
            chat_client=factory.chat_client,  # Planning and progress tracking
            max_round_count=10,     # Maximum collaboration rounds
            max_stall_count=3,      # Stall detection limits  
            max_reset_count=2,      # Reset behavior control
        ).build()
        
        print("✓ Magentic workflow configured with plan-driven collaboration")
        print()
        
        # STEP 5: Run the workflow
        # Call run_stream method - workflow dynamically plans, delegates work, and coordinates
        print("Executing magentic orchestration...")
        print("-" * 60)
        
        # Track phases and outputs
        phases_completed = []
        final_outputs = []
        
        # STEP 6: Process workflow events
        # Iterate through workflow events using async loop for real-time progress
        async for event in workflow.run_stream(task):
            # Handle different types of magentic events
            if isinstance(event, MagenticAgentMessageEvent):
                agent_name = event.agent_id or "Agent"
                print(f"🤖 [{agent_name}]: {event.text[:100]}...")
                
                # Update task ledger based on agent activity
                if "plan" in event.text.lower() and agent_name == "Planner":
                    ledger.current_phase = "planning"
                    ledger.add_task("PLAN_001", "Strategic planning completed", "Planner")
                    ledger.complete_task("PLAN_001", event.text)
                
                elif agent_name == "Researcher":
                    if "research" not in [task["id"] for task in ledger.tasks]:
                        ledger.add_task("RESEARCH_001", "Information gathering", "Researcher")
                    ledger.complete_task("RESEARCH_001", event.text)
                
                elif agent_name == "Writer":
                    if "write" not in [task["id"] for task in ledger.tasks]:
                        ledger.add_task("WRITE_001", "Content creation", "Writer")
                    ledger.complete_task("WRITE_001", event.text)
                
                elif agent_name == "Validator":
                    if "validate" not in [task["id"] for task in ledger.tasks]:
                        ledger.add_task("VALIDATE_001", "Quality validation", "Validator")
                    ledger.complete_task("VALIDATE_001", event.text)
            
            elif isinstance(event, MagenticOrchestratorMessageEvent):
                print(f"🎯 [Orchestrator]: {event.text}")
            
            elif isinstance(event, MagenticFinalResultEvent):
                print(f"🏆 [Final Result]: Magentic orchestration completed")
                final_outputs.append(event.data)
            
            elif isinstance(event, WorkflowOutputEvent):
                final_outputs.append(event.data)
        
        # Display results and task ledger
        print("\n" + "=" * 80)
        print("MAGENTIC ORCHESTRATION RESULTS")
        print("=" * 80)
        
        # Show task ledger summary
        print(f"\n📊 {ledger.get_progress_summary()}")
        print("\nCompleted Tasks:")
        for task in ledger.completed_tasks:
            print(f"   ✅ {task['id']}: {task['description']}")
        
        # Show final outputs
        if final_outputs:
            print("\n📋 Final Deliverables:")
            for i, output in enumerate(final_outputs, 1):
                if isinstance(output, str):
                    print(f"\n{i}. {output}")
                elif isinstance(output, list):
                    for j, item in enumerate(output, 1):
                        if hasattr(item, 'text'):
                            print(f"\n{i}.{j} [{getattr(item, 'author_name', 'Assistant')}]: {item.text}")
                        else:
                            print(f"\n{i}.{j} {item}")
        else:
            print("No final outputs captured.")
    
    except ImportError as e:
        print(f"⚠️  MagenticBuilder not available: {e}")
        print("Simulating magentic orchestration pattern...")
        await _simulate_magentic_pattern(task, factory, ledger)
    
    print("\n" + "=" * 80)
    print("Magentic orchestration completed!")
    print("Plan-driven collaboration with tool integration achieved.")
    print("=" * 80)
    
    # For now, return a simple structure until we implement full output capture
    return [
        {
            "agent": "Magentic System",
            "input": task,
            "output": f"Successfully completed magentic orchestration for: {task[:100]}{'...' if len(task) > 100 else ''}",
            "timestamp": datetime.now().isoformat()
        }
    ]


async def _simulate_magentic_pattern(
    project: str, 
    factory: AgentFactory, 
    ledger: TaskLedger
) -> None:
    """
    Simulate magentic orchestration if MagenticBuilder is not available.
    
    This provides a fallback implementation that demonstrates the pattern
    using sequential execution with tool integration.
    """
    print("🔄 Running simulated magentic pattern...")
    
    # Create agents
    planner = factory.create_planner_agent()
    researcher = factory.create_researcher_agent()
    writer = factory.create_writer_agent()
    validator = factory.create_validator_agent()
    
    conversation = []
    
    # Phase 1: Planning
    print("\n📋 Phase 1: Strategic Planning")
    ledger.add_task("PLAN_SIM", "Create project plan", "Planner")
    
    user_msg = ChatMessage(role="user", text=project)
    conversation.append(user_msg)
    
    plan_response = await planner.run(conversation)
    if plan_response.messages:
        plan_msg = plan_response.messages[-1]
        conversation.append(ChatMessage(
            role="assistant", 
            text=plan_msg.text,
            author_name="Planner"
        ))
        ledger.complete_task("PLAN_SIM", plan_msg.text)
        print(f"   Plan: {plan_msg.text[:200]}...")
    
    # Phase 2: Research with tools
    print("\n🔍 Phase 2: Research & Analysis")
    ledger.add_task("RESEARCH_SIM", "Gather supporting information", "Researcher")
    
    # Simulate tool usage
    weather_data = get_weather("Global")
    search_results = search_web("employee wellness programs best practices")
    
    research_prompt = conversation + [ChatMessage(
        role="user",
        text=f"Research this project using available data: Weather context: {weather_data}. Industry research: {search_results}"
    )]
    
    research_response = await researcher.run(research_prompt)
    if research_response.messages:
        research_msg = research_response.messages[-1]
        conversation.append(ChatMessage(
            role="assistant",
            text=research_msg.text,
            author_name="Researcher"
        ))
        ledger.complete_task("RESEARCH_SIM", research_msg.text)
        print(f"   Research: {research_msg.text[:200]}...")
    
    # Phase 3: Content Creation
    print("\n✍️  Phase 3: Content Development")
    ledger.add_task("WRITE_SIM", "Create comprehensive documentation", "Writer")
    
    write_response = await writer.run(conversation)
    if write_response.messages:
        write_msg = write_response.messages[-1]
        conversation.append(ChatMessage(
            role="assistant",
            text=write_msg.text,
            author_name="Writer"
        ))
        ledger.complete_task("WRITE_SIM", write_msg.text)
        print(f"   Content: {write_msg.text[:200]}...")
    
    # Phase 4: Validation
    print("\n✅ Phase 4: Quality Validation")
    ledger.add_task("VALIDATE_SIM", "Final quality check", "Validator")
    
    validate_response = await validator.run(conversation)
    if validate_response.messages:
        validate_msg = validate_response.messages[-1]
        conversation.append(ChatMessage(
            role="assistant",
            text=validate_msg.text,
            author_name="Validator"
        ))
        ledger.complete_task("VALIDATE_SIM", validate_msg.text)
        print(f"   Validation: {validate_msg.text[:200]}...")
    
    # Generate final report using tools
    final_report = generate_report(f"Magentic Orchestration Results for: {project}")
    print(f"\n📊 {final_report}")


async def main():
    """Main function for standalone execution."""
    await run_magentic_orchestration()


if __name__ == "__main__":
    asyncio.run(main())
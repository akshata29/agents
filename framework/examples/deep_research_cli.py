"""
Deep Research CLI - Comprehensive Multi-Agent Research Workflow

This script executes a complete deep research workflow using the Foundation Framework.
It demonstrates real agent orchestration with Azure OpenAI to produce comprehensive research reports.

Usage:
    python deep_research_cli.py
    
The workflow includes:
1. Research Planning - Strategic breakdown of the topic
2. Parallel Investigation - Multiple research perspectives
3. Synthesis - Comprehensive report generation
4. Validation - Quality assurance
5. Executive Summary - Key insights extraction
"""

import asyncio
import sys
import os
import platform
import warnings
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Set UTF-8 encoding for Windows console
if platform.system() == 'Windows':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Suppress warnings
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Fix for Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import framework
try:
    from magentic_foundation import create_app, MagenticFoundation
    from magentic_foundation.agents.base import BaseAgent, AgentMessage, AgentResponse
    print("[OK] Successfully imported Foundation Framework")
except ImportError as e:
    print(f"[ERROR] Failed to import framework: {e}")
    sys.exit(1)


class SimpleResearchAgent(BaseAgent):
    """
    Simple research agent that uses Azure OpenAI for actual research tasks.
    """
    
    async def _process_message(
        self,
        message: AgentMessage,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process research message using Azure OpenAI."""
        try:
            # Import Azure OpenAI client
            from agent_framework import ChatAgent
            from agent_framework.azure import AzureOpenAIChatClient
            from agent_framework import ChatMessage, Role
            
            # Get settings from agent
            endpoint = self.settings.azure_openai.endpoint
            api_key = self.settings.azure_openai.api_key
            deployment = self.settings.azure_openai.chat_deployment_name
            api_version = self.settings.azure_openai.api_version
            
            # Create chat client
            chat_client = AzureOpenAIChatClient(
                endpoint=endpoint,
                api_key=api_key,
                deployment_name=deployment,
                api_version=api_version
            )
            
            # Build the prompt with context
            prompt = message.content
            if context:
                prompt += "\n\nContext:\n"
                for key, value in context.items():
                    if value and key != 'research_plan':  # Don't include massive context
                        prompt += f"- {key}: {str(value)[:200]}...\n"
            
            # Create agent
            system_message = self.description or "You are a helpful research assistant."
            agent = ChatAgent(
                name=self.name,
                system_message=system_message,
                chat_client=chat_client
            )
            
            # Process message
            chat_message = ChatMessage(role=Role.USER, content=prompt)
            response = await agent.process_message(chat_message)
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            return AgentResponse(
                success=True,
                content=content,
                metadata={
                    "agent_type": "research_agent",
                    "model": deployment
                }
            )
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"Agent processing failed: {e}\n{error_details}")
            
            return AgentResponse(
                success=False,
                content="",
                error=str(e),
                metadata={"error_details": error_details}
            )


async def register_research_agents(app: MagenticFoundation):
    """Register all agents needed for the research workflow."""
    
    print("\n[Registering Research Agents...]")
    
    agents_to_register = {
        "planner": (
            "You are an expert research planner. Your role is to analyze research topics "
            "and create structured, comprehensive research plans. Break down topics into "
            "key subtopics, identify critical research questions, and suggest effective "
            "investigation approaches. Be thorough, strategic, and well-organized."
        ),
        "researcher": (
            "You are an expert researcher with deep knowledge across multiple domains. "
            "Your role is to investigate topics thoroughly, find authoritative information, "
            "analyze sources critically, and present findings clearly. Focus on accuracy, "
            "credibility, and comprehensive coverage. When researching, consider multiple "
            "perspectives and cite key insights."
        ),
        "writer": (
            "You are an expert technical writer and research synthesizer. Your role is to "
            "take complex research findings and synthesize them into clear, well-structured, "
            "comprehensive reports. Organize information logically, use clear headings, "
            "maintain academic tone, and ensure the narrative flows smoothly. Include "
            "citations when requested and present information in an accessible yet thorough manner."
        ),
        "reviewer": (
            "You are an expert research reviewer and quality validator. Your role is to "
            "critically review research reports for accuracy, completeness, coherence, and quality. "
            "Identify gaps, inconsistencies, unsupported claims, and areas for improvement. "
            "Provide constructive feedback and validation. Be thorough but fair in your assessment."
        ),
        "summarizer": (
            "You are an expert at creating concise, impactful executive summaries. Your role "
            "is to distill complex research reports into clear, actionable summaries that "
            "highlight key findings, insights, and conclusions. Focus on the most important "
            "information while maintaining accuracy and clarity."
        )
    }
    
    for agent_name, description in agents_to_register.items():
        # Check if agent already exists
        existing_agent = await app.agent_registry.get_agent(agent_name)
        if existing_agent:
            print(f"  * Agent '{agent_name}' already registered, skipping")
            continue
        
        # Create and register new agent
        agent = SimpleResearchAgent(
            name=agent_name,
            description=description,
            settings=app.settings
        )
        await app.agent_registry.register_agent(agent_name, agent)
        print(f"  + Registered: {agent_name.title()} Agent")
    
    print(f"\n[All research agents ready]\n")


async def execute_deep_research(
    topic: str,
    depth: str = "comprehensive",
    max_sources: int = 10,
    include_citations: bool = True
) -> Dict[str, Any]:
    """Execute the deep research workflow."""
    
    print("=" * 80)
    print("🔬 DEEP RESEARCH WORKFLOW")
    print("=" * 80)
    print(f"\n📋 Research Topic: {topic}")
    print(f"   Depth Level: {depth}")
    print(f"   Max Sources: {max_sources}")
    print(f"   Citations: {'Enabled' if include_citations else 'Disabled'}")
    print()
    
    # Initialize framework
    print("[Initializing Foundation Framework...]")
    app = create_app()
    await app.initialize()
    print("[OK] Framework initialized\n")
    
    try:
        # Register agents
        await register_research_agents(app)
        
        # Load and register workflow
        print("[Loading Deep Research Workflow...]")
        workflow_file = Path(__file__).parent / "workflows" / "deep_research.yaml"
        
        if not workflow_file.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_file}")
        
        await app.workflow_engine.register_workflow(str(workflow_file))
        print("[OK] Workflow registered\n")
        
        # Prepare workflow inputs
        workflow_inputs = {
            "research_topic": topic,
            "research_depth": depth,
            "max_sources": max_sources,
            "include_citations": include_citations
        }
        
        print("🎬 Starting Research Workflow Execution...")
        print("=" * 80)
        print()
        
        start_time = datetime.now()
        
        # Execute workflow
        execution_id = await app.workflow_engine.execute_workflow(
            workflow_name="deep_research_workflow",
            variables=workflow_inputs
        )
        
        print(f"[Execution ID: {execution_id}]")
        print()
        
        # Monitor execution
        print("[Workflow Progress:]")
        print("-" * 80)
        
        execution_complete = False
        last_status = None
        
        while not execution_complete:
            # Get execution status
            status = await app.workflow_engine.get_execution_status(execution_id)
            
            if status and status != last_status:
                # Print status update
                current_phase = status.get("current_phase", "Unknown")
                progress = status.get("progress", 0)
                completed_tasks = status.get("completed_tasks", 0)
                total_tasks = status.get("total_tasks", 0)
                
                print(f"  Phase: {current_phase}")
                print(f"  Progress: {progress}% ({completed_tasks}/{total_tasks} tasks)")
                print()
                
                last_status = status
                
                # Check if complete (status comes as lowercase enum values)
                workflow_status = status.get("status", "").lower()
                if workflow_status in ["success", "failed", "cancelled"]:
                    execution_complete = True
                    
                    if workflow_status == "success":
                        print("[OK] Workflow completed successfully!")
                    elif workflow_status == "failed":
                        print("[ERROR] Workflow failed!")
                        error = status.get("error", "Unknown error")
                        print(f"   Error: {error}")
                    else:
                        print("[WARNING] Workflow was cancelled")
                    break
            
            # Wait before checking again
            await asyncio.sleep(2)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print()
        print("=" * 80)
        print(f"⏱️  Total execution time: {duration:.1f} seconds")
        print()
        
        # Get final results
        execution = await app.workflow_engine.get_execution(execution_id)
        
        if execution and str(execution.status).lower() in ["success", "workflowstatus.success"]:
            results = execution.variables
            
            print("=" * 80)
            print("[RESEARCH RESULTS]")
            print("=" * 80)
            print()
            
            # Executive Summary
            if "executive_summary" in results:
                print("[EXECUTIVE SUMMARY]")
                print("-" * 80)
                print(results["executive_summary"])
                print()
            
            # Final Report
            if "final_report" in results:
                print("=" * 80)
                print("[FULL RESEARCH REPORT]")
                print("=" * 80)
                print()
                print(results["final_report"])
                print()
            
            # Validation Results
            if "validation_results" in results:
                print("=" * 80)
                print("[QUALITY VALIDATION]")
                print("=" * 80)
                print(results["validation_results"])
                print()
            
            return results
        else:
            print("[WARNING] No results available")
            return {}
            
    except Exception as e:
        print(f"\n[ERROR] Error during research execution: {e}")
        import traceback
        traceback.print_exc()
        return {}
        
    finally:
        # Cleanup
        print("\n[Shutting down framework...]")
        await app.shutdown()
        print("[OK] Shutdown complete")


def print_welcome():
    """Print welcome message."""
    print()
    print("=" * 80)
    print(" " * 20 + "[DEEP RESEARCH - AI Research Assistant]")
    print("=" * 80)
    print()
    print("This tool uses multi-agent AI orchestration to perform comprehensive research")
    print("on any topic you provide. The workflow includes:")
    print()
    print("  1. [Planning] Research Planning - Strategic topic breakdown")
    print("  2. [Investigation] Parallel Investigation - Multiple research perspectives")
    print("  3. [Synthesis] Comprehensive report generation")
    print("  4. [Validation] Quality assurance review")
    print("  5. [Summary] Executive insights extraction")
    print()
    print("=" * 80)
    print()


async def main():
    """Main CLI function."""
    print_welcome()
    
    # Get research topic from user
    print("Please enter your research topic:")
    print("(e.g., 'The impact of artificial intelligence on healthcare')")
    print()
    topic = input("Research Topic: ").strip()
    
    if not topic:
        print("[ERROR] No topic provided. Exiting.")
        return
    
    print()
    print("Research Depth Level:")
    print("  1. Quick (fast overview)")
    print("  2. Standard (balanced research)")
    print("  3. Comprehensive (detailed analysis) [DEFAULT]")
    print("  4. Exhaustive (maximum depth)")
    print()
    depth_choice = input("Select depth (1-4) [3]: ").strip() or "3"
    
    depth_map = {
        "1": "quick",
        "2": "standard",
        "3": "comprehensive",
        "4": "exhaustive"
    }
    depth = depth_map.get(depth_choice, "comprehensive")
    
    # Execute research
    await execute_deep_research(
        topic=topic,
        depth=depth,
        max_sources=10,
        include_citations=True
    )
    
    print()
    print("=" * 80)
    print("Thank you for using Deep Research! 🎉")
    print("=" * 80)
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[WARNING] Research interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()

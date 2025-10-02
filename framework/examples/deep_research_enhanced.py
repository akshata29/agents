"""
Enhanced Deep Research CLI with Real AI Capabilities
Uses Azure OpenAI for LLM and Tavily for web search
"""
import asyncio
import os
import sys
import platform
import warnings
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Suppress warnings
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Fix for Windows event loop
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from dotenv import load_dotenv
from tavily import TavilyClient

from magentic_foundation import MagenticFoundation, create_app
from magentic_foundation.agents.base import BaseAgent, AgentResponse
from magentic_foundation.agents.factory import AgentFactory
from openai import AzureOpenAI


class TavilySearchAgent(BaseAgent):
    """Research agent with Tavily web search capabilities."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        tavily_client: TavilyClient,
        azure_client: AzureOpenAI,
        model: str
    ):
        super().__init__(agent_id, name, description)
        self.tavily = tavily_client
        self.azure_client = azure_client
        self.model = model
    
    async def _process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Required abstract method from BaseAgent."""
        result = await self.process(message, context)
        return AgentResponse(
            success=True,
            content=result,
            metadata={"agent_id": self.agent_id, "type": "tavily_search"}
        )
    
    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process research request with web search and synthesis."""
        try:
            # Handle AgentMessage object
            if hasattr(message, 'content'):
                message_content = message.content
            else:
                message_content = str(message)
            
            # Extract task and context
            context = context or {}
            task = context.get('task', message_content)
            aspect = context.get('aspect', 'general')
            
            # DEBUG: Print what we received
            print(f"  [DEBUG] Received task: {task[:100]}")
            
            # Perform web search using Tavily
            search_query = self._extract_search_query(task)
            print(f"  [SEARCH] {aspect}: {search_query}")
            
            search_results = self.tavily.search(
                query=search_query,
                search_depth="advanced",
                max_results=5,
                include_answer=True,
                include_raw_content=False
            )
            
            # Synthesize findings using Azure OpenAI
            synthesis_prompt = self._build_synthesis_prompt(task, search_results)
            
            response = self.azure_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert research analyst who synthesizes information from multiple sources into comprehensive, well-structured reports."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content
            print(f"  [OK] Completed: {aspect}")
            return result
            
        except Exception as e:
            print(f"  [ERROR] Research failed: {e}")
            return f"Research error: {str(e)}"
    
    def _extract_search_query(self, task: str) -> str:
        """Extract concise search query from task."""
        # Simple extraction - could be enhanced with LLM
        if "Research" in task or "Investigate" in task:
            return task.split(":", 1)[1].strip() if ":" in task else task
        return task
    
    def _build_synthesis_prompt(self, task: str, search_results: Dict) -> str:
        """Build prompt for synthesizing search results."""
        answer = search_results.get('answer', '')
        results = search_results.get('results', [])
        
        sources_text = "\n\n".join([
            f"Source {i+1}: {r['title']}\nURL: {r['url']}\n{r['content']}"
            for i, r in enumerate(results[:5])
        ])
        
        prompt = f"""Task: {task}

Tavily Search Answer: {answer}

Detailed Sources:
{sources_text}

Based on the above search results, provide a comprehensive, well-researched response to the task. 
Include specific facts, statistics, and insights from the sources. Structure your response clearly 
with key points and supporting evidence. Cite sources where appropriate using [Source N] notation."""
        
        return prompt


class AIResearchAgent(BaseAgent):
    """AI-powered research agent using Azure OpenAI."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        azure_client: AzureOpenAI,
        model: str,
        system_prompt: str
    ):
        super().__init__(agent_id, name, description)
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = system_prompt
    
    async def _process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Required abstract method from BaseAgent."""
        result = await self.process(message, context)
        return AgentResponse(
            success=True,
            content=result,
            metadata={"agent_id": self.agent_id, "type": "ai_research"}
        )
    
    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process request using Azure OpenAI."""
        try:
            # Handle AgentMessage object
            if hasattr(message, 'content'):
                message_content = message.content
            else:
                message_content = str(message)
            
            context = context or {}
            
            # DEBUG: Print what we received
            print(f"  [DEBUG AI] Message: {message_content[:100]}")
            
            # Build context-aware prompt
            user_prompt = self._build_prompt(message_content, context)
            
            response = self.azure_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"  [ERROR] AI processing failed: {e}")
            return f"AI error: {str(e)}"
    
    def _build_prompt(self, message: str, context: Dict[str, Any]) -> str:
        """Build context-aware prompt."""
        prompt_parts = [message]
        
        # Add relevant context
        for key, value in context.items():
            if key not in ['task', 'agent_id'] and value:
                prompt_parts.append(f"\n{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(prompt_parts)


async def setup_enhanced_agents(app: MagenticFoundation) -> None:
    """Setup AI-powered research agents with Tavily search."""
    
    # Load environment variables
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "chat4o")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if not all([azure_endpoint, azure_api_key, tavily_api_key]):
        raise ValueError("Missing required environment variables: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, TAVILY_API_KEY")
    
    # Initialize clients
    azure_client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version=os.getenv("AZURE_OPENAI_VERSION", "2024-10-21")
    )
    
    tavily_client = TavilyClient(api_key=tavily_api_key)
    
    print("[Registering AI-Powered Research Agents...]")
    
    # 1. Research Planner
    try:
        planner = AIResearchAgent(
            agent_id="planner",
            name="Research Planner",
            description="AI agent that creates comprehensive research plans",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="""You are an expert research planner and strategist. Your role is to:
1. Analyze research topics and break them down into key subtopics
2. Identify the most important research questions to answer
3. Suggest effective investigation approaches and methodologies
4. Create structured, actionable research plans

Provide detailed, well-organized research plans that cover all aspects of the topic systematically."""
        )
        await app.agent_registry.register_agent("planner", planner)
        print("  * Registered 'planner' (AI-powered)")
    except ValueError:
        print("  * 'planner' already registered, skipping")
    
    # 2. Web Researcher (with Tavily)
    try:
        researcher = TavilySearchAgent(
            agent_id="researcher",
            name="Web Researcher",
            description="AI agent that performs web research using Tavily search",
            tavily_client=tavily_client,
            azure_client=azure_client,
            model=azure_deployment
        )
        await app.agent_registry.register_agent("researcher", researcher)
        print("  * Registered 'researcher' (Tavily + Azure OpenAI)")
    except ValueError:
        print("  * 'researcher' already registered, skipping")
    
    # 3. Report Writer
    try:
        writer = AIResearchAgent(
            agent_id="writer",
            name="Report Writer",
            description="AI agent that synthesizes research into comprehensive reports",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="""You are an expert research report writer. Your role is to:
1. Synthesize findings from multiple research sources into cohesive narratives
2. Structure information logically with clear sections and flow
3. Write in a clear, professional, and engaging style
4. Integrate citations and evidence appropriately
5. Create comprehensive reports that inform and persuade

Produce well-structured, insightful reports that effectively communicate research findings."""
        )
        await app.agent_registry.register_agent("writer", writer)
        print("  * Registered 'writer' (AI-powered)")
    except ValueError:
        print("  * 'writer' already registered, skipping")
    
    # 4. Quality Reviewer
    try:
        reviewer = AIResearchAgent(
            agent_id="reviewer",
            name="Quality Reviewer",
            description="AI agent that reviews and validates research quality",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="""You are an expert research quality reviewer and editor. Your role is to:
1. Evaluate research reports for accuracy, completeness, and coherence
2. Identify gaps, inconsistencies, or areas needing improvement
3. Assess the quality of sources and evidence
4. Provide constructive, specific feedback
5. Validate that conclusions are well-supported

Provide thorough, actionable reviews that improve research quality."""
        )
        await app.agent_registry.register_agent("reviewer", reviewer)
        print("  * Registered 'reviewer' (AI-powered)")
    except ValueError:
        print("  * 'reviewer' already registered, skipping")
    
    # 5. Executive Summarizer
    try:
        summarizer = AIResearchAgent(
            agent_id="summarizer",
            name="Executive Summarizer",
            description="AI agent that creates concise executive summaries",
            azure_client=azure_client,
            model=azure_deployment,
            system_prompt="""You are an expert at creating executive summaries. Your role is to:
1. Distill complex research reports into concise summaries
2. Highlight the most important findings and insights
3. Present key conclusions and recommendations clearly
4. Write in an accessible style for executive audiences
5. Maintain accuracy while being brief

Create compelling executive summaries that capture the essence of research findings."""
        )
        await app.agent_registry.register_agent("summarizer", summarizer)
        print("  * Registered 'summarizer' (AI-powered)")
    except ValueError:
        print("  * 'summarizer' already registered, skipping")
    
    print("\n[All AI research agents ready with real capabilities]")


async def execute_enhanced_research(
    app: MagenticFoundation,
    topic: str,
    depth: str = "comprehensive",
    max_sources: int = 10
) -> Dict[str, Any]:
    """Execute enhanced deep research workflow with AI and web search."""
    
    try:
        print("\n" + "=" * 80)
        print("[ENHANCED DEEP RESEARCH WORKFLOW]")
        print("=" * 80)
        print()
        print(f"[RESEARCH TOPIC] {topic}")
        print(f"   Depth Level: {depth}")
        print(f"   Max Sources: {max_sources}")
        print(f"   AI Model: Azure OpenAI")
        print(f"   Search Tool: Tavily")
        print()
        
        # Setup AI agents
        await setup_enhanced_agents(app)
        
        # Load workflow
        print("[Loading Deep Research Workflow...]")
        workflow_path = Path(__file__).parent / "workflows" / "deep_research.yaml"
        await app.workflow_engine.register_workflow(str(workflow_path))
        print("[OK] Workflow registered")
        
        # Execute workflow
        print("\n[STARTING AI-POWERED RESEARCH]")
        print("=" * 80)
        print()
        
        start_time = datetime.now()
        
        execution_id = await app.workflow_engine.execute_workflow(
            workflow_name="deep_research_workflow",
            variables={
                "research_topic": topic,
                "research_depth": depth,
                "max_sources": max_sources,
                "include_citations": True
            }
        )
        
        print(f"[Execution ID: {execution_id}]")
        print()
        
        # Monitor progress with enhanced display
        print("[Workflow Progress:]")
        print("-" * 80)
        
        execution_complete = False
        last_progress = -1
        last_phase = None
        
        while not execution_complete:
            status = await app.workflow_engine.get_execution_status(execution_id)
            
            if status:
                progress = status.get("progress", 0)
                completed = status.get("completed_tasks", 0)
                total = status.get("total_tasks", 0)
                
                # Show progress updates
                if progress != last_progress:
                    # Determine current phase
                    execution = await app.workflow_engine.get_execution(execution_id)
                    current_phase = "Waiting"
                    
                    if execution and execution.task_executions:
                        # task_executions could be a list or dict
                        task_list = execution.task_executions if isinstance(execution.task_executions, list) else list(execution.task_executions.values())
                        running_tasks = [t for t in task_list if hasattr(t, 'status') and str(t.status).lower() == "running"]
                        if running_tasks:
                            current_phase = running_tasks[0].task_name if hasattr(running_tasks[0], 'task_name') else "Running"
                    
                    if current_phase != last_phase:
                        print(f"  Phase: {current_phase}")
                        last_phase = current_phase
                    
                    print(f"  Progress: {progress}% ({completed}/{total} tasks)")
                    print()
                    last_progress = progress
                
                # Check if complete
                workflow_status = status.get("status", "").lower()
                if workflow_status in ["success", "failed", "cancelled", "workflowstatus.success"]:
                    execution_complete = True
                    
                    if "success" in workflow_status:
                        print("[OK] AI Research Workflow completed successfully!")
                    elif workflow_status == "failed":
                        print("[ERROR] Workflow failed!")
                        error = status.get("error", "Unknown error")
                        print(f"   Error: {error}")
                    else:
                        print("[WARNING] Workflow was cancelled")
                    break
            
            await asyncio.sleep(2)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print()
        print("=" * 80)
        print(f"   Total execution time: {duration:.1f} seconds")
        print()
        
        # Get final results
        execution = await app.workflow_engine.get_execution(execution_id)
        
        if execution and str(execution.status).lower() in ["success", "workflowstatus.success"]:
            results = execution.variables
            
            print("=" * 80)
            print("[AI RESEARCH RESULTS]")
            print("=" * 80)
            print()
            
            # Executive Summary
            if "executive_summary" in results:
                print("[EXECUTIVE SUMMARY]")
                print("-" * 80)
                print(results["executive_summary"])
                print()
            
            # Research Plan
            if "research_plan" in results:
                print("=" * 80)
                print("[RESEARCH PLAN]")
                print("=" * 80)
                print(results["research_plan"])
                print()
            
            # Key Findings (show one aspect as example)
            if "current_state" in results:
                print("=" * 80)
                print("[SAMPLE RESEARCH FINDING: Current State]")
                print("=" * 80)
                print(results["current_state"][:1000] + "..." if len(results["current_state"]) > 1000 else results["current_state"])
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
        print("\n[Shutting down framework...]")
        await app.shutdown()
        print("[OK] Shutdown complete")


async def main():
    """Main entry point for enhanced deep research."""
    
    # Load environment variables
    load_dotenv()
    
    print("=" * 80)
    print("AI-POWERED DEEP RESEARCH")
    print("=" * 80)
    print()
    print("Using:")
    print(f"  * Azure OpenAI: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"  * Model: {os.getenv('AZURE_OPENAI_DEPLOYMENT', 'chat4o')}")
    print(f"  * Tavily Search: {os.getenv('TAVILY_API_BASE_URL', 'https://api.tavily.com')}")
    print()
    
    # Initialize framework
    print("[Initializing Magentic Foundation Framework...]")
    app = create_app()
    await app.initialize()
    print("[OK] Framework initialized")
    print()
    
    # Example research topic
    topic = "The future of quantum computing in cybersecurity"
    
    print(f"[RESEARCH TOPIC]")
    print(f"  {topic}")
    print()
    
    # Execute enhanced research
    results = await execute_enhanced_research(
        app=app,
        topic=topic,
        depth="comprehensive",
        max_sources=10
    )
    
    if results:
        print("\n" + "=" * 80)
        print("[SUCCESS] AI-powered deep research completed!")
        print("=" * 80)
        print()
        print(f"Generated {len(results)} research outputs:")
        for key in results.keys():
            if not key.startswith('research_') or key in ['research_plan', 'research_findings']:
                value = results[key]
                length = len(str(value)) if value else 0
                print(f"  * {key}: {length} characters")
    else:
        print("\n[WARNING] Research completed with no results")


if __name__ == "__main__":
    asyncio.run(main())

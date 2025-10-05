"""
Task Orchestrator - Multimodal Insights Application

Orchestrates the entire workflow from plan creation to execution using Microsoft Agent Framework.
Built from scratch for multimodal content processing.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import structlog
import sys
from pathlib import Path

# Add framework to path
repo_root = Path(__file__).parent.parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Framework imports
from framework.core.planning import DynamicPlanner
from framework.core.orchestrator import MagenticOrchestrator
from framework.agents.factory import AgentFactory
from framework.config.settings import Settings as FrameworkSettings

from ..models.task_models import (
    InputTask, Plan, Step, AgentMessage, PlanStatus, StepStatus,
    AgentType, PlanWithSteps, ExecutionStatusResponse
)
from ..persistence.cosmos_memory import CosmosMemoryStore
from ..services.file_handler import FileHandler
from ..agents import (
    MultimodalProcessorAgent,
    SentimentAgent,
    SummarizerAgent,
    AnalyticsAgent
)
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)


class TaskOrchestrator:
    """
    Orchestrates task planning and execution for multimodal content processing.
    
    Workflow:
    1. User uploads files and provides objective
    2. Planner creates execution plan (ReAct pattern)
    3. Files are processed by Multimodal Processor Agent
    4. Content is analyzed by specialized agents (Sentiment, Summarizer, Analytics)
    5. Results are aggregated and returned
    """
    
    def __init__(self, settings: Settings, file_handler: FileHandler):
        """Initialize task orchestrator."""
        self.settings = settings
        self.file_handler = file_handler
        
        # Initialize persistence
        self.memory_store = CosmosMemoryStore(settings)
        
        # Initialize agents
        self.multimodal_processor = MultimodalProcessorAgent(settings)
        self.sentiment_agent = SentimentAgent(settings)
        self.summarizer_agent = SummarizerAgent(settings)
        self.analytics_agent = AnalyticsAgent(settings)
        
        # Framework components
        framework_settings = self._create_framework_settings()
        self.planner = DynamicPlanner(framework_settings)
        self.orchestrator = MagenticOrchestrator(framework_settings)
        
        # Initialize agent factory and create planning agent
        self.agent_factory = AgentFactory(framework_settings)
        self.planning_agent = self.agent_factory.create_agent(
            agent_type="planner",
            name="multimodal_planner"
        )
        
        logger.info("Task Orchestrator initialized")
    
    async def initialize_agents(self):
        """Initialize and register MAF-compatible agents with the orchestrator registry."""
        from framework.core.registry import AgentMetadata, AgentCapability as RegistryCapability
        
        # MAF agents don't need initialization - they're ready to use
        # Register agents with orchestrator's agent registry
        logger.info("Registering MAF-compliant agents with orchestrator")
        
        # Register multimodal_processor
        await self.orchestrator.agent_registry.register_agent(
            name="multimodal_processor",
            agent=self.multimodal_processor,
            metadata=AgentMetadata(
                id="multimodal_processor",
                name="multimodal_processor",
                description="Processes audio, video, and PDF files",
                capabilities=[
                    RegistryCapability(
                        name=cap,
                        description=f"{cap} capability",
                        parameters={},
                        required_tools=[]
                    )
                    for cap in self.multimodal_processor.capabilities
                ]
            )
        )
        logger.info("Registered multimodal_processor agent")
        
        # Register sentiment agent
        await self.orchestrator.agent_registry.register_agent(
            name="sentiment",
            agent=self.sentiment_agent,
            metadata=AgentMetadata(
                id="sentiment",
                name="sentiment",
                description="Analyzes sentiment, emotions, and tone",
                capabilities=[
                    RegistryCapability(
                        name=cap,
                        description=f"{cap} capability",
                        parameters={},
                        required_tools=[]
                    )
                    for cap in self.sentiment_agent.capabilities
                ]
            )
        )
        logger.info("Registered sentiment agent")
        
        # Register summarizer agent
        await self.orchestrator.agent_registry.register_agent(
            name="summarizer",
            agent=self.summarizer_agent,
            metadata=AgentMetadata(
                id="summarizer",
                name="summarizer",
                description="Creates flexible summaries with persona-based customization",
                capabilities=[
                    RegistryCapability(
                        name=cap,
                        description=f"{cap} capability",
                        parameters={},
                        required_tools=[]
                    )
                    for cap in self.summarizer_agent.capabilities
                ]
            )
        )
        logger.info("Registered summarizer agent")
        
        # Register analytics agent
        await self.orchestrator.agent_registry.register_agent(
            name="analytics",
            agent=self.analytics_agent,
            metadata=AgentMetadata(
                id="analytics",
                name="analytics",
                description="Performs dynamic analytics and insight extraction",
                capabilities=[
                    RegistryCapability(
                        name=cap,
                        description=f"{cap} capability",
                        parameters={},
                        required_tools=[]
                    )
                    for cap in self.analytics_agent.capabilities
                ]
            )
        )
        logger.info("Registered analytics agent")
        
        logger.info("All MAF-compliant agents registered successfully")
    
    def _create_framework_settings(self) -> FrameworkSettings:
        """Create framework settings from app settings."""
        return FrameworkSettings(
            azure_openai_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            azure_openai_key=self.settings.AZURE_OPENAI_API_KEY,
            azure_openai_deployment=self.settings.AZURE_OPENAI_DEPLOYMENT,
            azure_openai_api_version=self.settings.AZURE_OPENAI_API_VERSION
        )
    
    async def initialize(self):
        """Initialize orchestrator resources."""
        await self.memory_store.initialize()
        logger.info("Task Orchestrator ready")
    
    async def shutdown(self):
        """Cleanup orchestrator resources."""
        await self.memory_store.close()
        logger.info("Task Orchestrator shutdown")
    
    async def create_plan_from_objective(
        self,
        input_task: InputTask
    ) -> PlanWithSteps:
        """
        Create execution plan from user objective and files.
        
        Uses framework's Dynamic Planner to analyze the objective and uploaded files,
        then creates a structured plan with steps.
        """
        logger.info(
            "Creating plan from objective",
            objective=input_task.description[:100],
            file_count=len(input_task.file_ids) if input_task.file_ids else 0
        )
        
        try:
            # Get or create session
            session_id = input_task.session_id or str(uuid.uuid4())
            user_id = input_task.user_id
            
            # Ensure session exists in Cosmos DB
            existing_session = await self.memory_store.get_session(session_id)
            if not existing_session:
                from ..models.task_models import Session as SessionModel
                new_session = SessionModel(
                    session_id=session_id,
                    user_id=user_id
                )
                await self.memory_store.create_session(new_session)
                logger.info("Created new session in Cosmos DB", session_id=session_id)
            
            # Get all files for this session (files are uploaded before plan creation)
            session_files = await self.memory_store.get_files_for_session(session_id)
            
            # Build file information from session files
            files_info = []
            file_ids = []
            if session_files:
                logger.info(f"Found {len(session_files)} files in session",
                           session_id=session_id)
                for file_meta in session_files:
                    files_info.append({
                        "file_id": file_meta.id,
                        "filename": file_meta.filename,
                        "file_type": file_meta.file_type.value
                    })
                    file_ids.append(file_meta.id)
                    logger.info(f"Including file in plan",
                               file_id=file_meta.id,
                               filename=file_meta.filename,
                               file_type=file_meta.file_type.value)
            else:
                logger.warning(f"No files found in session", session_id=session_id)
            
            # Build context for planner
            planning_context = self._build_planning_context(
                input_task.description,
                files_info
            )
            
            logger.info(f"Planning context built",
                       files_info_count=len(files_info),
                       file_ids=[f.get("file_id") for f in files_info])
            
            # Use planner to create execution plan
            steps_plan = await self._generate_plan_with_planner(
                planning_context,
                files_info,
                summary_type=input_task.summary_type,
                persona=input_task.persona
            )
            
            logger.info(f"Steps plan generated",
                       steps_count=len(steps_plan),
                       step_agents=[s.get("agent") for s in steps_plan])
            
            # Create Plan object
            plan = Plan(
                session_id=session_id,
                user_id=user_id,
                initial_goal=input_task.description,
                file_ids=file_ids,  # Use files from session, not input_task
                total_steps=len(steps_plan),
                metadata=input_task.metadata
            )
            
            # Save plan to Cosmos
            plan = await self.memory_store.create_plan(plan)
            
            # Create and save steps
            steps = []
            for idx, step_info in enumerate(steps_plan):
                step = Step(
                    plan_id=plan.id,
                    session_id=session_id,
                    user_id=user_id,
                    action=step_info["action"],
                    agent=AgentType(step_info["agent"]),
                    order=idx,
                    file_ids=step_info.get("file_ids", []),
                    parameters=step_info.get("parameters", {})
                )
                step = await self.memory_store.create_step(step)
                steps.append(step)
            
            logger.info(
                "Plan created successfully",
                plan_id=plan.id,
                steps_count=len(steps)
            )
            
            # Return plan with steps
            return PlanWithSteps(
                id=plan.id,
                session_id=plan.session_id,
                user_id=plan.user_id,
                initial_goal=plan.initial_goal,
                summary=plan.summary,
                overall_status=plan.overall_status,
                file_ids=plan.file_ids,
                total_steps=plan.total_steps,
                completed_steps=plan.completed_steps,
                failed_steps=plan.failed_steps,
                timestamp=plan.timestamp,
                steps=steps
            )
            
        except Exception as e:
            logger.error(f"Failed to create plan", error=str(e))
            raise
    
    def _build_planning_context(
        self,
        objective: str,
        files_info: List[Dict[str, str]]
    ) -> str:
        """Build context string for the planner."""
        
        files_summary = ""
        if files_info:
            files_summary = "\n\nUploaded Files:\n"
            for f in files_info:
                files_summary += f"- {f['filename']} ({f['file_type']})\n"
        
        agent_capabilities = f"""
Available Agents:
1. Multimodal Processor Agent - Processes audio, video, and PDF files
   - Audio: Transcription via Azure Speech-to-Text
   - Video: Extract audio and transcribe
   - PDF: Extract content via Azure Document Intelligence

2. Sentiment Analysis Agent - Analyzes sentiment and emotions
   - Multi-dimensional sentiment analysis
   - Emotion detection
   - Tone analysis
   - Speaker tracking for conversations

3. Summarizer Agent - Creates flexible summaries
   - Multiple summary levels (brief, detailed, comprehensive)
   - Persona-based (executive, technical, general)
   - Multi-document synthesis

4. Analytics Agent - Performs deep analytics
   - Context-aware analysis
   - Pattern extraction
   - Product/service analysis
   - Recommendations and next-best-actions
"""
        
        context = f"""
User Objective: {objective}
{files_summary}

{agent_capabilities}

Based on the user's objective and uploaded files, create an execution plan that processes the files and achieves the objective.
"""
        return context
    
    async def _generate_plan_with_planner(
        self,
        context: str,
        files_info: List[Dict[str, str]],
        summary_type: str = "detailed",
        persona: str = "executive"
    ) -> List[Dict[str, Any]]:
        """
        Generate execution plan using LLM-powered DynamicPlanner.
        
        Args:
            context: Planning context with objective and files
            files_info: List of file information dictionaries
            summary_type: Type of summary (brief, detailed, comprehensive)
            persona: Target audience (executive, technical, general)
        
        Returns list of step dictionaries with action, agent, and parameters.
        """
        from framework.agents.base import AgentMessage
        
        # Detect file types for intelligent planning
        has_audio_video = any(f.get("file_type") in ["audio", "video"] for f in files_info)
        has_pdf = any(f.get("file_type") == "pdf" for f in files_info)
        
        # Extract just the objective from context (remove file list and capabilities)
        objective = context.split("User Objective:")[1].split("\n\n")[0].strip() if "User Objective:" in context else context
        
        # Build files summary for the planner
        files_summary = ""
        if files_info:
            files_summary = "Uploaded Files:\n"
            for f in files_info:
                files_summary += f"  - {f['filename']} ({f['file_type']})\n"
        
        # Determine step guidance based on objective and file types
        objective_lower = objective.lower()
        
        # Build intelligent guidance
        if has_pdf and not has_audio_video:
            # PDF document analysis
            if any(term in objective_lower for term in ["sec", "10-k", "10-q", "filing", "financial", "risk"]):
                step_guidance = "For SEC/financial document analysis: Step 1 processes ALL files together. Then create comprehensive executive summary addressing all objective points, then perform analytics with risk/financial focus. SKIP sentiment analysis unless explicitly requested."
            else:
                step_guidance = "For PDF documents: Step 1 processes ALL files together. Then summarize and analyze. SKIP sentiment analysis unless explicitly requested."
        elif has_audio_video and not has_pdf:
            # Audio/Video analysis
            step_guidance = "For audio/video files: Step 1 processes ALL files together (transcription via Speech-to-Text). Then analyze sentiment/emotions, summarize for intended audience, and extract insights."
        else:
            # Mixed files
            step_guidance = "For mixed file types: Step 1 processes ALL files together (audio via Speech-to-Text, PDF via Document Intelligence). Then create analysis plan that addresses the objective. Include sentiment analysis only for audio/video content or if explicitly requested."
        
        # Create detailed planning prompt
        planning_task = f"""Create a multimodal content analysis plan for:
{objective}

{files_summary}

⚠️ CRITICAL PLANNING RULES:
1. ALWAYS create EXACTLY ONE file processing step (Step 1) that processes ALL uploaded files together
2. Choose analysis agents based on file type and objective keywords:
   - Sentiment: ONLY for audio/video files OR if explicitly requested (keywords: sentiment, emotion, tone, feeling)
   - Summarizer: ALWAYS include for comprehensive analysis (use objective to determine persona and type)
   - Analytics: Include when analysis, insights, patterns, recommendations, or extraction is requested
3. Pass the FULL objective as "objective_context" parameter to Summarizer and Analytics agents
4. For SEC/financial documents: use comprehensive executive summary + analytics with risk/financial focus
5. All analysis steps work on the COMBINED content from all files

Available Agents:
1. MultimodalProcessor_Agent - File processing (ALWAYS Step 1, ONE STEP ONLY)
   Tools:
   - process_files: Process ALL uploaded files (audio, video, PDF) in a single step
   ⚠️ IMPORTANT: Create only ONE step that processes all files together, not separate steps per file

2. Sentiment_Agent - Sentiment and emotion analysis
   Tools:
   - analyze_sentiment: Multi-dimensional sentiment, emotions, tone
   Use ONLY for: audio/video files OR if sentiment explicitly requested

3. Summarizer_Agent - Flexible summarization
   Tools:
   - summarize: Create summaries (brief/detailed/comprehensive, executive/technical/general personas)
   Parameters: summary_type, persona, objective_context (MUST include)
   Use for: comprehensive analysis, requested summaries, executive insights

4. Analytics_Agent - Deep analytics
   Tools:
   - analyze: Extract insights, patterns, recommendations
   Parameters: analysis_focus (risk_analysis, financial_metrics, strategic_insights, etc.), objective_context (MUST include)
   Use for: analysis requests, insight extraction, pattern identification

{step_guidance}

CRITICAL FORMATTING RULES:
- Format EXACTLY as: "Step N: Action. Agent: AgentName. Tool: tool_name. Parameters: {{key: value}}"
- Agent names MUST match exactly: MultimodalProcessor_Agent, Sentiment_Agent, Summarizer_Agent, Analytics_Agent
- ALWAYS include Parameters field for Summarizer and Analytics with objective_context
- NO dependencies (sequential execution handles this automatically)
- Step 1 MUST be MultimodalProcessor_Agent and process ALL files in ONE step

EXACT FORMAT EXAMPLES:

Example 1 - SEC Document Analysis:
Step 1: Process uploaded files to extract content using appropriate Azure services (Speech-to-Text for audio, Document Intelligence for PDF). Agent: MultimodalProcessor_Agent. Tool: process_files
Step 2: Create {summary_type} {persona} summary covering all objective requirements (risk factors, financial metrics, strategic insights). Agent: Summarizer_Agent. Tool: summarize. Parameters: {{summary_type: {summary_type}, persona: {persona}, objective_context: <full_objective>}}
Step 3: Perform deep analytics focusing on risk analysis, financial metrics, and strategic insights as specified in objective. Agent: Analytics_Agent. Tool: analyze. Parameters: {{analysis_focus: [risk_analysis, financial_metrics, strategic_insights], objective_context: <full_objective>}}

Example 2 - Audio + PDF Analysis:
Step 1: Process uploaded files (audio transcription via Speech-to-Text, PDF extraction via Document Intelligence). Agent: MultimodalProcessor_Agent. Tool: process_files
Step 2: Analyze sentiment and emotions from the audio transcription. Agent: Sentiment_Agent. Tool: analyze_sentiment
Step 3: Create {summary_type} {persona} summary combining insights from both audio and document. Agent: Summarizer_Agent. Tool: summarize. Parameters: {{summary_type: {summary_type}, persona: {persona}, objective_context: <full_objective>}}
Step 4: Extract insights, patterns, and recommendations from combined content. Agent: Analytics_Agent. Tool: analyze. Parameters: {{analysis_focus: [strategic_insights, recommendations], objective_context: <full_objective>}}

USER PREFERENCES:
- Summary Type: {summary_type} (use this for all Summarizer_Agent steps)
- Persona: {persona} (use this for all Summarizer_Agent steps)

RULES:
- NO meta-planning, headers, or separators - ONLY numbered action steps
- Be specific about what each step does
- Include ALL required parameters
- Use exact agent and tool names
- Step 1 MUST process ALL files in ONE step

OUTPUT FORMAT - Return ONLY the numbered steps:
Step 1: [Action]. Agent: agent_name. Tool: tool_name
Step 2: [Action]. Agent: agent_name. Tool: tool_name. Parameters: {{param: value}}
..."""

        logger.info("Creating plan using planning agent", objective_length=len(objective))
        
        # Call the planning agent directly to generate the plan
        # The agent's process() method returns the LLM response as a string
        try:
            plan_text = await self.planning_agent.process(
                message=planning_task,
                context={}
            )
            
            logger.info(
                "Plan generation completed",
                content_length=len(plan_text) if plan_text else 0,
                preview=plan_text[:200] if plan_text else ""
            )
            
        except Exception as e:
            logger.error("Failed to create plan with planning agent", error=str(e))
            raise
        
        if not plan_text or len(plan_text.strip()) == 0:
            raise ValueError("Plan generation returned empty response")
        
        # Parse the plan from the LLM response
        steps_plan = await self._parse_multimodal_plan(plan_text, objective, files_info)
        
        logger.info(
            "Parsed plan from LLM",
            steps_count=len(steps_plan),
            step_agents=[s.get("agent") for s in steps_plan]
        )
        
        return steps_plan
    
    async def _parse_multimodal_plan(
        self,
        plan_text: str,
        objective: str,
        files_info: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Parse LLM plan text into step dictionaries.
        
        Expected format:
        Step 1: Action. Agent: AgentName. Tool: tool_name. Parameters: {key: value}
        """
        import re
        import ast
        
        # Extract plan content (look for FINAL ANSWER or use full text)
        if "FINAL ANSWER:" in plan_text.upper():
            plan_content = plan_text.split("FINAL ANSWER:")[-1].strip()
        else:
            plan_content = plan_text
        
        logger.info("Parsing plan content", preview=plan_content[:300])
        
        # Parse steps line by line
        step_lines = [line.strip() for line in plan_content.split('\n') if line.strip().startswith('Step')]
        
        logger.info(f"Found {len(step_lines)} step lines", preview=step_lines[:2] if step_lines else [])
        
        steps_plan = []
        
        for line in step_lines:
            try:
                # Pattern: "Step N: Action. Agent: agent. Tool: tool. Parameters: {params}"
                # Parameters is optional
                pattern = r'Step\s+\d+:\s*(.+?)\.\s*Agent:\s*(\w+)\.\s*Tool:\s*([^\.\s]+)(?:\.\s*Parameters:\s*\{([^\}]+)\})?'
                match = re.search(pattern, line, re.IGNORECASE)
                
                if match:
                    action = match.group(1).strip()
                    agent = match.group(2).strip()
                    tool = match.group(3).strip()
                    params_str = match.group(4)  # Can be None
                    
                    # Parse parameters if present
                    parameters = {}
                    if params_str:
                        # Try to parse as dict-like string
                        try:
                            # Clean up the params string and convert to valid dict
                            params_cleaned = "{" + params_str + "}"
                            # Replace single quotes with double quotes for JSON parsing
                            params_cleaned = params_cleaned.replace("'", '"')
                            # Try to eval as Python dict (safer than JSON for lists)
                            parameters = ast.literal_eval(params_cleaned.replace('"', "'"))
                        except:
                            logger.warning(f"Could not parse parameters", params_str=params_str)
                    
                    # Ensure objective_context is set if not present and agent needs it
                    if agent in ["Summarizer_Agent", "Analytics_Agent"]:
                        if "objective_context" not in parameters:
                            parameters["objective_context"] = objective
                    
                    # Map agent names to AgentType enum values
                    agent_map = {
                        "MultimodalProcessor_Agent": AgentType.MULTIMODAL_PROCESSOR.value,
                        "Sentiment_Agent": AgentType.SENTIMENT.value,
                        "Summarizer_Agent": AgentType.SUMMARIZER.value,
                        "Analytics_Agent": AgentType.ANALYTICS.value
                    }
                    
                    agent_value = agent_map.get(agent)
                    if not agent_value:
                        logger.warning(f"Unknown agent name: {agent}, skipping step")
                        continue
                    
                    # Build step dictionary
                    step_dict = {
                        "action": action,
                        "agent": agent_value,
                        "file_ids": [f["file_id"] for f in files_info] if agent == "MultimodalProcessor_Agent" else [],
                        "parameters": parameters
                    }
                    
                    steps_plan.append(step_dict)
                    
                    logger.info(
                        f"Parsed step successfully",
                        action=action[:50],
                        agent=agent_value,
                        tool=tool,
                        has_params=bool(parameters)
                    )
                else:
                    logger.warning(f"Could not parse step line", line=line[:100])
                    
            except Exception as e:
                logger.error(f"Error parsing step line", error=str(e), line=line[:100])
        
        # Fallback: if no steps parsed, create default plan
        if not steps_plan and files_info:
            logger.warning("No steps parsed from LLM, creating default plan")
            steps_plan = [
                {
                    "action": f"Process {len(files_info)} uploaded file(s) to extract content",
                    "agent": AgentType.MULTIMODAL_PROCESSOR.value,
                    "file_ids": [f["file_id"] for f in files_info],
                    "parameters": {}
                },
                {
                    "action": "Create comprehensive summary",
                    "agent": AgentType.SUMMARIZER.value,
                    "file_ids": [],
                    "parameters": {
                        "summary_type": "comprehensive",
                        "persona": "executive",
                        "objective_context": objective
                    }
                },
                {
                    "action": "Perform analytics and extract insights",
                    "agent": AgentType.ANALYTICS.value,
                    "file_ids": [],
                    "parameters": {
                        "analysis_focus": ["general"],
                        "objective_context": objective
                    }
                }
            ]
        
        return steps_plan
    
    async def execute_plan(self, plan_id: str, session_id: str):
        """
        Execute plan using MAF-inspired Sequential and Concurrent patterns.
        
        Note: While we use the pattern concepts from MAF (Sequential for file processing,
        Concurrent for analysis), we call agents directly because they need specific context
        (file paths, parameters) that doesn't fit the standard ChatMessage workflow.
        
        Phase 1: Sequential for file processing (one file at a time)
        Phase 2: Concurrent for analysis (parallel: sentiment, summarizer, analytics)
        """
        logger.info("Executing plan with Sequential→Concurrent pattern", plan_id=plan_id)
        
        try:
            # Get plan and steps
            plan = await self.memory_store.get_plan(plan_id, session_id)
            if not plan:
                raise ValueError(f"Plan {plan_id} not found")
            
            # Check if plan is already completed or in progress
            if plan.overall_status == PlanStatus.COMPLETED:
                logger.info("Plan already completed, skipping re-execution", plan_id=plan_id)
                return
            
            if plan.overall_status == PlanStatus.IN_PROGRESS:
                logger.warning("Plan already in progress, skipping duplicate execution", plan_id=plan_id)
                return
            
            steps = await self.memory_store.get_steps_for_plan(plan_id, session_id)
            if not steps:
                raise ValueError(f"No steps found for plan {plan_id}")
            
            logger.info(f"Retrieved steps for execution",
                       plan_id=plan_id,
                       steps_count=len(steps),
                       step_agents=[s.agent.value if hasattr(s.agent, 'value') else str(s.agent) for s in steps])
            
            # Update plan status
            plan.overall_status = PlanStatus.IN_PROGRESS
            await self.memory_store.update_plan(plan)
            
            # Context accumulator
            execution_context = {
                "extracted_content": {},
                "sentiment_results": {},
                "summary_results": {},
                "analytics_results": {}
            }
            
            # Separate file processing from analysis
            file_steps = [s for s in steps if s.agent == AgentType.MULTIMODAL_PROCESSOR]
            analysis_steps = [s for s in steps if s.agent != AgentType.MULTIMODAL_PROCESSOR]
            
            logger.info(f"Step separation complete",
                       total_steps=len(steps),
                       file_steps_count=len(file_steps),
                       analysis_steps_count=len(analysis_steps))
            
            # Phase 1: Sequential - File Processing (MAF Sequential Pattern concept)
            if file_steps:
                logger.info("Phase 1: Sequential file processing (one file at a time)")
                
                # Process files sequentially
                for step in file_steps:
                    try:
                        step.status = StepStatus.EXECUTING
                        await self.memory_store.update_step(step)
                        
                        # Process each file in the step
                        for file_id in step.file_ids:
                            file_meta = await self.memory_store.get_file_metadata(file_id, session_id)
                            if not file_meta:
                                logger.warning(f"File metadata not found for file_id: {file_id}")
                                continue
                            
                            logger.info(f"Processing file", 
                                       file_id=file_id, 
                                       filename=file_meta.filename,
                                       file_type=file_meta.file_type.value)
                            
                            # Call MAF-compliant agent with kwargs
                            result_response = await self.multimodal_processor.run(
                                messages=f"Process file: {file_meta.filename}",
                                file_path=file_meta.file_path,
                                file_type=file_meta.file_type.value,
                                session_id=session_id,
                                file_id=file_id
                            )
                            
                            # Extract result from MAF response
                            result_content = result_response.messages[0].text if result_response.messages else ""
                            
                            logger.info(f"File processing completed", 
                                       file_id=file_id, 
                                       result_length=len(result_content))
                            
                            # Parse the result and store in execution context
                            import json
                            try:
                                result_data = json.loads(result_content)
                                
                                # Check if extraction actually succeeded
                                has_content = False
                                if "transcript" in result_data or "text_content" in result_data or "transcription" in result_data:
                                    content_field = result_data.get("transcript") or result_data.get("text_content") or result_data.get("transcription")
                                    has_content = bool(content_field and len(str(content_field).strip()) > 50)  # At least 50 chars
                                
                                if not has_content:
                                    error_msg = f"Content extraction failed for {file_meta.filename} - no valid content extracted"
                                    logger.error(error_msg, file_id=file_id)
                                    raise ValueError(error_msg)
                                
                                execution_context.setdefault("extracted_content", {})[file_id] = result_data
                                logger.info(f"Parsed file processing result", 
                                           file_id=file_id,
                                           has_transcript="transcript" in result_data,
                                           has_text="text_content" in result_data)
                            except json.JSONDecodeError:
                                error_msg = f"Failed to parse result as JSON for {file_meta.filename}"
                                logger.error(error_msg, file_id=file_id, raw_result=result_content[:200])
                                raise ValueError(error_msg)
                        
                        # Update step with results - wrap in 'results' for frontend compatibility
                        extracted_content = execution_context.get("extracted_content", {})
                        step.agent_reply = json.dumps(
                            {
                                "results": extracted_content,
                                "processed_files": len(extracted_content)
                            },
                            ensure_ascii=False,
                            default=str
                        )
                        step.status = StepStatus.COMPLETED
                        await self.memory_store.update_step(step)
                        plan.completed_steps += 1
                        
                    except Exception as e:
                        logger.error("File processing failed", error=str(e), exc_info=True)
                        step.status = StepStatus.FAILED
                        step.error_message = str(e)
                        await self.memory_store.update_step(step)
                        plan.failed_steps += 1
                
                await self.memory_store.update_plan(plan)
            
            # Check if Phase 1 extraction succeeded before proceeding to Phase 2
            if file_steps and not execution_context.get("extracted_content"):
                error_msg = "Phase 1 content extraction failed - no valid content extracted from files. Stopping execution."
                logger.error(error_msg)
                plan.overall_status = PlanStatus.FAILED
                await self.memory_store.update_plan(plan)
                # Mark all remaining analysis steps as skipped
                for step in analysis_steps:
                    step.status = StepStatus.FAILED
                    step.error_message = "Skipped due to Phase 1 extraction failure"
                    await self.memory_store.update_step(step)
                return
            
            # Phase 2: Concurrent - Analysis Agents (MAF Concurrent Pattern concept)
            if analysis_steps and execution_context.get("extracted_content"):
                logger.info("Phase 2: Concurrent analysis (parallel execution)")
                
                # Get all extracted content for analysis
                all_content = []
                for file_id, content in execution_context["extracted_content"].items():
                    # Extract text from different content types
                    if isinstance(content, dict):
                        if "transcript" in content:
                            all_content.append(content["transcript"])
                        elif "text_content" in content:
                            all_content.append(content["text_content"])
                        elif "transcription" in content:
                            all_content.append(content["transcription"])
                        elif "raw_result" in content:
                            all_content.append(content["raw_result"])
                
                combined_text = "\n\n".join(all_content) if all_content else ""
                
                logger.info(f"Combined text for analysis",
                           content_length=len(combined_text),
                           num_files=len(execution_context["extracted_content"]))
                
                if not combined_text or len(combined_text.strip()) < 50:
                    error_msg = f"Insufficient text content for analysis (only {len(combined_text)} characters extracted)"
                    logger.error(error_msg)
                    plan.overall_status = PlanStatus.FAILED
                    await self.memory_store.update_plan(plan)
                    # Mark all analysis steps as failed
                    for step in analysis_steps:
                        step.status = StepStatus.FAILED
                        step.error_message = error_msg
                        await self.memory_store.update_step(step)
                    return
                
                # Run analysis agents concurrently using asyncio.gather (Concurrent Pattern)
                async def run_analysis_agent(step: Step, agent, context_overrides: Dict = None):
                    """Run a single analysis agent."""
                    try:
                        logger.info(f"Starting analysis agent", 
                                   agent_type=step.agent.value,
                                   agent_name=agent.name)
                        
                        step.status = StepStatus.EXECUTING
                        await self.memory_store.update_step(step)
                        
                        # Prepare kwargs for MAF agent
                        kwargs = {
                            "content": combined_text
                        }
                        
                        # Add context overrides
                        if context_overrides:
                            kwargs.update(context_overrides)
                        
                        # Add step-specific parameters (including objective_context)
                        if step.parameters:
                            kwargs.update(step.parameters)
                        
                        # Call MAF-compliant agent with kwargs
                        result_response = await agent.run(
                            messages=f"Analyze the extracted content",
                            **kwargs
                        )
                        
                        # Extract result from MAF response
                        result_content = result_response.messages[0].text if result_response.messages else ""
                        
                        logger.info(f"Analysis agent completed",
                                   agent_type=step.agent.value,
                                   result_length=len(result_content))
                        
                        # Parse and store results
                        try:
                            result_data = json.loads(result_content)
                        except json.JSONDecodeError:
                            result_data = {"raw_result": result_content}
                        
                        # Store in execution context
                        if step.agent == AgentType.SENTIMENT:
                            execution_context["sentiment_results"] = result_data
                        elif step.agent == AgentType.SUMMARIZER:
                            execution_context["summary_results"] = result_data
                        elif step.agent == AgentType.ANALYTICS:
                            execution_context["analytics_results"] = result_data
                        
                        step.agent_reply = json.dumps(result_data, ensure_ascii=False, default=str)
                        step.status = StepStatus.COMPLETED
                        await self.memory_store.update_step(step)
                        
                    except Exception as e:
                        logger.error(f"Analysis failed for {step.agent.value}", error=str(e), exc_info=True)
                        step.status = StepStatus.FAILED
                        step.error_message = str(e)
                        await self.memory_store.update_step(step)
                
                # Create concurrent tasks for each analysis agent
                analysis_tasks = []
                for step in analysis_steps:
                    if step.agent == AgentType.SENTIMENT:
                        task = run_analysis_agent(step, self.sentiment_agent)
                    elif step.agent == AgentType.SUMMARIZER:
                        task = run_analysis_agent(step, self.summarizer_agent)
                    elif step.agent == AgentType.ANALYTICS:
                        task = run_analysis_agent(step, self.analytics_agent)
                    else:
                        continue
                    analysis_tasks.append(task)
                
                # Execute all analysis agents concurrently (Concurrent Pattern)
                logger.info(f"Launching {len(analysis_tasks)} analysis agents in parallel")
                await asyncio.gather(*analysis_tasks, return_exceptions=True)
                
                # Update plan progress based on actual step statuses
                for step in analysis_steps:
                    if step.status == StepStatus.COMPLETED:
                        plan.completed_steps += 1
                    elif step.status == StepStatus.FAILED:
                        plan.failed_steps += 1
                
                await self.memory_store.update_plan(plan)
            
            # Update final status
            plan.overall_status = PlanStatus.COMPLETED if plan.failed_steps == 0 else PlanStatus.FAILED
            await self.memory_store.update_plan(plan)
            
            logger.info("Plan execution completed (Sequential→Concurrent pattern)", plan_id=plan_id)
            
        except Exception as e:
            logger.error(f"Failed to execute plan", error=str(e), plan_id=plan_id)
            if plan:
                plan.overall_status = PlanStatus.FAILED
                await self.memory_store.update_plan(plan)
            raise
    
    async def _execute_step(self, step: Step, context: Dict[str, Any]):
        """Execute a single step."""
        logger.info(
            "Executing step",
            step_id=step.id,
            agent=step.agent.value,
            action=step.action[:50]
        )
        
        try:
            # Update step status
            step.status = StepStatus.EXECUTING
            await self.memory_store.update_step(step)
            
            # Execute based on agent type
            if step.agent == AgentType.MULTIMODAL_PROCESSOR:
                result = await self._execute_multimodal_processing(step, context)
            elif step.agent == AgentType.SENTIMENT:
                result = await self._execute_sentiment_analysis(step, context)
            elif step.agent == AgentType.SUMMARIZER:
                result = await self._execute_summarization(step, context)
            elif step.agent == AgentType.ANALYTICS:
                result = await self._execute_analytics(step, context)
            else:
                raise ValueError(f"Unknown agent type: {step.agent}")
            
            # Update step with result - serialize to JSON for proper storage
            step.agent_reply = json.dumps(result, ensure_ascii=False, default=str)
            step.status = StepStatus.COMPLETED
            await self.memory_store.update_step(step)
            
            # Log message
            message = AgentMessage(
                session_id=step.session_id,
                user_id=step.user_id,
                plan_id=step.plan_id,
                step_id=step.id,
                content=step.agent_reply,
                source=step.agent.value
            )
            await self.memory_store.create_message(message)
            
            logger.info("Step completed successfully", step_id=step.id)
            
        except Exception as e:
            logger.error(f"Step execution failed", error=str(e), step_id=step.id)
            step.status = StepStatus.FAILED
            step.error_message = str(e)
            await self.memory_store.update_step(step)
    
    async def _execute_multimodal_processing(
        self,
        step: Step,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute multimodal file processing."""
        results = {}
        
        for file_id in step.file_ids:
            # Get file metadata
            file_meta = await self.memory_store.get_file_metadata(file_id, step.session_id)
            if not file_meta:
                continue
            
            # Process file
            extracted = await self.multimodal_processor.process_file(
                file_meta.file_path,
                file_meta.file_type.value,
                step.session_id,
                file_id
            )
            
            results[file_id] = extracted
            context["extracted_content"][file_id] = extracted
            
            # Update file metadata
            file_meta.processing_status = "completed"
            file_meta.processed_at = datetime.utcnow()
            await self.memory_store.update_file_metadata(file_meta)
        
        return {"processed_files": len(results), "results": results}
    
    async def _execute_sentiment_analysis(
        self,
        step: Step,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute sentiment analysis on extracted content."""
        extracted_content = context.get("extracted_content", {})
        plan = context.get("plan")
        
        # Combine all text content
        all_text = []
        for file_id, content in extracted_content.items():
            if content.get("text_content"):
                all_text.append(content["text_content"])
            elif content.get("transcription"):
                all_text.append(content["transcription"])
        
        combined_text = "\n\n".join(all_text)
        
        # Build context with objective
        analysis_context = {
            "file_type": "combined",
            "objective_context": plan.objective if plan else None
        }
        
        # Perform sentiment analysis with objective context
        result = await self.sentiment_agent.analyze_sentiment(combined_text, analysis_context)
        context["sentiment_results"] = result
        
        return result
    
    async def _execute_summarization(
        self,
        step: Step,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute summarization on extracted content."""
        extracted_content = context.get("extracted_content", {})
        
        # Combine all text content
        all_text = []
        for file_id, content in extracted_content.items():
            if content.get("text_content"):
                all_text.append(content["text_content"])
            elif content.get("transcription"):
                all_text.append(content["transcription"])
        
        combined_text = "\n\n".join(all_text)
        
        # Get parameters
        params = step.parameters or {}
        summary_type = params.get("summary_type", "detailed")
        persona = params.get("persona", "general")
        
        # Generate summary
        result = await self.summarizer_agent.summarize(
            combined_text,
            summary_type=summary_type,
            persona=persona
        )
        context["summary_results"] = result
        
        return result
    
    async def _execute_analytics(
        self,
        step: Step,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute analytics on extracted content."""
        extracted_content = context.get("extracted_content", {})
        
        # Combine all text content
        all_text = []
        for file_id, content in extracted_content.items():
            if content.get("text_content"):
                all_text.append(content["text_content"])
            elif content.get("transcription"):
                all_text.append(content["transcription"])
        
        combined_text = "\n\n".join(all_text)
        
        # Get parameters
        params = step.parameters or {}
        analysis_focus = params.get("analysis_focus", ["general"])
        
        # Perform analytics
        result = await self.analytics_agent.analyze(
            combined_text,
            analysis_focus=analysis_focus
        )
        context["analytics_results"] = result
        
        return result
    
    async def get_plan_with_steps(
        self,
        plan_id: str,
        session_id: str
    ) -> Optional[PlanWithSteps]:
        """Get plan with all steps."""
        return await self.memory_store.get_plan_with_steps(plan_id, session_id)
    
    async def get_execution_status(
        self,
        plan_id: str,
        session_id: str
    ) -> ExecutionStatusResponse:
        """Get current execution status of a plan."""
        plan = await self.memory_store.get_plan(plan_id, session_id)
        steps = await self.memory_store.get_steps_for_plan(plan_id, session_id)
        
        # Find current executing step
        current_step = None
        current_agent = None
        for step in steps:
            if step.status == StepStatus.EXECUTING:
                current_step = step.action
                current_agent = step.agent.value
                break
        
        # Get recent messages
        messages = await self.memory_store.get_messages_for_plan(plan_id, session_id)
        recent_messages = [msg.content[:200] for msg in messages[-5:]]  # Last 5 messages
        
        # Calculate progress
        progress_percentage = (plan.completed_steps / plan.total_steps * 100) if plan.total_steps > 0 else 0
        
        return ExecutionStatusResponse(
            plan_id=plan_id,
            session_id=session_id,
            overall_status=plan.overall_status,
            current_step=current_step,
            current_agent=current_agent,
            completed_steps=plan.completed_steps,
            total_steps=plan.total_steps,
            progress_percentage=progress_percentage,
            recent_messages=recent_messages
        )

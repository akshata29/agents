"""
Microsoft Agent Framework Workflows Implementation for Deep Research

This module implements graph-based workflows using MAF's Workflow system.
It demonstrates the executor/edge pattern with fan-out/fan-in for parallel processing.

Key Differences from Task-Based Workflows:
- Graph-based architecture (executors + edges)
- Conditional routing based on message content
- Fan-out/fan-in for parallel processing
- Type-safe message passing
- Built-in checkpointing and visualization
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

import structlog
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from tavily import TavilyClient

# Microsoft Agent Framework Workflow imports
from agent_framework import (
    WorkflowBuilder,
    Executor,
    WorkflowContext,
    handler,
    ChatAgent,
    WorkflowOutputEvent,
    WorkflowFailedEvent,
    ExecutorCompletedEvent,
)

logger = structlog.get_logger(__name__)


# ============================================================
# Message Types for Type-Safe Communication
# ============================================================

@dataclass
class ResearchRequest:
    """Initial research request message."""
    topic: str
    execution_id: str
    max_sources: int = 5
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ResearchPlan:
    """Research plan output from planner."""
    topic: str
    execution_id: str
    research_areas: List[str]
    strategy: str
    estimated_duration: int  # minutes
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ResearchFindings:
    """Research findings from individual research tasks."""
    topic: str
    execution_id: str
    area: str
    findings: str
    sources: List[str]
    confidence: float  # 0.0 to 1.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SynthesizedReport:
    """Synthesized report from all findings."""
    topic: str
    execution_id: str
    report: str
    findings_count: int
    quality_score: float  # 0.0 to 1.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ReviewedReport:
    """Reviewed and validated report."""
    topic: str
    execution_id: str
    final_report: str
    validation_notes: str
    quality_score: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class FinalOutput:
    """Final output with executive summary."""
    topic: str
    execution_id: str
    final_report: str
    executive_summary: str
    metadata: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


# ============================================================
# Custom Executors
# ============================================================

class ResearchPlannerExecutor(Executor):
    """
    Executor that creates a comprehensive research plan.
    
    Input: ResearchRequest
    Output: ResearchPlan
    """
    
    def __init__(self, azure_client: AzureOpenAI, model: str, executor_id: str = "planner"):
        super().__init__(id=executor_id)
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = """You are an expert research planner. 
Create comprehensive research plans by breaking down topics into key areas to investigate.
Identify 3-5 specific research areas that need to be explored.
Be strategic and thorough."""
    
    @handler
    async def run(
        self, 
        request: ResearchRequest, 
        ctx: WorkflowContext[ResearchPlan]
    ) -> None:
        """Create research plan from request."""
        logger.info(f"[{self.id}] Creating research plan", topic=request.topic)
        
        try:
            # Build prompt
            prompt = f"""Create a comprehensive research plan for the topic: "{request.topic}"

Break down the research into 3-5 key areas to investigate.
For each area, explain why it's important to understanding the topic.

Provide your response in this format:
RESEARCH AREAS:
1. [Area name]: [Why it's important]
2. [Area name]: [Why it's important]
...

STRATEGY:
[Overall research strategy]

ESTIMATED DURATION:
[Estimated time in minutes]"""
            
            # Call Azure OpenAI
            response = await asyncio.to_thread(
                self.azure_client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content
            
            # Parse research areas (simplified parsing)
            research_areas = []
            lines = result_text.split('\n')
            for line in lines:
                if line.strip() and any(line.startswith(f"{i}.") for i in range(1, 10)):
                    area = line.split(':', 1)[0].strip()
                    area = area[area.find('.')+1:].strip()
                    if area:
                        research_areas.append(area)
            
            # If parsing fails, create default areas
            if not research_areas:
                research_areas = [
                    "Core concepts and fundamentals",
                    "Current state and recent developments",
                    "Practical applications and use cases"
                ]
            
            # Create plan
            plan = ResearchPlan(
                topic=request.topic,
                execution_id=request.execution_id,
                research_areas=research_areas[:5],  # Limit to 5
                strategy=result_text,
                estimated_duration=len(research_areas) * 2  # 2 min per area
            )
            
            logger.info(
                f"[{self.id}] Research plan created",
                areas=len(plan.research_areas)
            )
            
            # Send to next executors
            await ctx.send_message(plan)
            
        except Exception as e:
            logger.error(f"[{self.id}] Error creating plan", error=str(e))
            # Send plan with default areas on error
            plan = ResearchPlan(
                topic=request.topic,
                execution_id=request.execution_id,
                research_areas=[
                    "Core concepts",
                    "Current state",
                    "Applications"
                ],
                strategy=f"Error occurred: {str(e)}. Using default plan.",
                estimated_duration=6
            )
            await ctx.send_message(plan)


class ResearchExecutor(Executor):
    """
    Executor that performs research on a specific area.
    Uses Tavily for web search and Azure OpenAI for synthesis.
    
    Input: ResearchPlan
    Output: ResearchFindings
    """
    
    def __init__(
        self,
        area_index: int,
        tavily: TavilyClient,
        azure_client: AzureOpenAI,
        model: str,
        executor_id: str = None
    ):
        super().__init__(id=executor_id or f"researcher_{area_index}")
        self.area_index = area_index
        self.tavily = tavily
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = """You are an expert researcher. 
Analyze web search results and synthesize comprehensive findings.
Be factual, cite sources, and provide well-structured insights."""
    
    @handler
    async def run(
        self,
        plan: ResearchPlan,
        ctx: WorkflowContext[ResearchFindings]
    ) -> None:
        """Perform research on assigned area."""
        
        # Check if we should research this area
        if self.area_index >= len(plan.research_areas):
            logger.info(
                f"[{self.id}] No area assigned",
                index=self.area_index,
                total_areas=len(plan.research_areas)
            )
            return
        
        area = plan.research_areas[self.area_index]
        logger.info(f"[{self.id}] Researching area", area=area)
        
        try:
            # Perform web search
            search_query = f"{plan.topic} {area}"
            search_results = await asyncio.to_thread(
                self.tavily.search,
                query=search_query,
                max_results=5
            )
            
            # Format search results
            sources = []
            sources_text = ""
            for idx, result in enumerate(search_results.get('results', []), 1):
                title = result.get('title', 'Unknown')
                url = result.get('url', '')
                content = result.get('content', '')
                sources.append(f"{title} - {url}")
                sources_text += f"\nSource {idx}: {title}\nURL: {url}\nContent: {content}\n"
            
            # Synthesize findings with AI
            synthesis_prompt = f"""Based on the following web search results, provide comprehensive research findings about:

Topic: {plan.topic}
Research Area: {area}

Search Results:
{sources_text}

Provide a well-structured synthesis of the key findings, insights, and important information."""
            
            response = await asyncio.to_thread(
                self.azure_client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            findings_text = response.choices[0].message.content
            
            # Create findings
            findings = ResearchFindings(
                topic=plan.topic,
                execution_id=plan.execution_id,
                area=area,
                findings=findings_text,
                sources=sources,
                confidence=0.85  # Could be calculated based on result quality
            )
            
            logger.info(
                f"[{self.id}] Research completed",
                area=area,
                sources_count=len(sources)
            )
            
            await ctx.send_message(findings)
            
        except Exception as e:
            logger.error(f"[{self.id}] Error during research", area=area, error=str(e))
            # Send findings with error info
            findings = ResearchFindings(
                topic=plan.topic,
                execution_id=plan.execution_id,
                area=area,
                findings=f"Error occurred during research: {str(e)}",
                sources=[],
                confidence=0.0
            )
            await ctx.send_message(findings)


class SynthesizerExecutor(Executor):
    """
    Executor that synthesizes all research findings into a comprehensive report.
    
    Input: List[ResearchFindings]
    Output: SynthesizedReport
    """
    
    def __init__(self, azure_client: AzureOpenAI, model: str, executor_id: str = "synthesizer"):
        super().__init__(id=executor_id)
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = """You are an expert research synthesizer and technical writer.
Create comprehensive, well-structured reports that integrate multiple research findings.
Use clear sections, cite sources, and provide actionable insights."""
    
    @handler
    async def run(
        self,
        findings_list: List[ResearchFindings],
        ctx: WorkflowContext[SynthesizedReport]
    ) -> None:
        """Synthesize all findings into comprehensive report."""
        logger.info(f"[{self.id}] Synthesizing report", findings_count=len(findings_list))
        
        if not findings_list:
            logger.warning(f"[{self.id}] No findings to synthesize")
            return
        
        try:
            # Get topic from first finding
            topic = findings_list[0].topic
            execution_id = findings_list[0].execution_id
            
            # Compile all findings
            compiled_findings = ""
            all_sources = []
            
            for idx, finding in enumerate(findings_list, 1):
                compiled_findings += f"\n\n## Research Area {idx}: {finding.area}\n"
                compiled_findings += f"Confidence: {finding.confidence:.0%}\n\n"
                compiled_findings += finding.findings
                compiled_findings += f"\n\nSources:\n"
                for source in finding.sources:
                    compiled_findings += f"- {source}\n"
                    all_sources.append(source)
            
            # Create synthesis prompt
            synthesis_prompt = f"""Synthesize the following research findings into a comprehensive, well-structured report about: "{topic}"

Research Findings:
{compiled_findings}

Create a report with the following structure:
1. Introduction
2. Key Findings (organized by theme, not by source)
3. Analysis and Insights
4. Implications
5. Conclusion

Make the report comprehensive, coherent, and cite sources where appropriate."""
            
            response = await asyncio.to_thread(
                self.azure_client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            report_text = response.choices[0].message.content
            
            # Calculate quality score based on findings confidence
            avg_confidence = sum(f.confidence for f in findings_list) / len(findings_list)
            quality_score = min(avg_confidence * 1.1, 1.0)  # Slight boost for synthesis
            
            # Create synthesized report
            report = SynthesizedReport(
                topic=topic,
                execution_id=execution_id,
                report=report_text,
                findings_count=len(findings_list),
                quality_score=quality_score
            )
            
            logger.info(
                f"[{self.id}] Report synthesized",
                quality_score=f"{quality_score:.0%}"
            )
            
            await ctx.send_message(report)
            
        except Exception as e:
            logger.error(f"[{self.id}] Error synthesizing report", error=str(e))
            # Send report with error
            report = SynthesizedReport(
                topic=findings_list[0].topic if findings_list else "Unknown",
                execution_id=findings_list[0].execution_id if findings_list else "error",
                report=f"Error during synthesis: {str(e)}",
                findings_count=len(findings_list),
                quality_score=0.0
            )
            await ctx.send_message(report)


class ReviewerExecutor(Executor):
    """
    Executor that reviews and validates the synthesized report.
    
    Input: SynthesizedReport
    Output: ReviewedReport
    """
    
    def __init__(self, azure_client: AzureOpenAI, model: str, executor_id: str = "reviewer"):
        super().__init__(id=executor_id)
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = """You are an expert quality reviewer and editor.
Review reports for accuracy, coherence, completeness, and clarity.
Provide constructive feedback and make improvements where needed."""
    
    @handler
    async def run(
        self,
        report: SynthesizedReport,
        ctx: WorkflowContext[ReviewedReport]
    ) -> None:
        """Review and validate the report."""
        logger.info(f"[{self.id}] Reviewing report", quality=f"{report.quality_score:.0%}")
        
        try:
            review_prompt = f"""Review the following research report for quality, accuracy, and completeness:

Topic: {report.topic}
Current Quality Score: {report.quality_score:.0%}

Report:
{report.report}

Provide:
1. Quality assessment (strengths and weaknesses)
2. Suggestions for improvement
3. A revised version that addresses any issues

Format your response as:
ASSESSMENT:
[Your assessment]

SUGGESTIONS:
[Your suggestions]

REVISED REPORT:
[The improved report]"""
            
            response = await asyncio.to_thread(
                self.azure_client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": review_prompt}
                ],
                temperature=0.5,  # Lower temperature for review
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            
            # Try to extract revised report
            if "REVISED REPORT:" in result_text:
                parts = result_text.split("REVISED REPORT:")
                validation_notes = parts[0].strip()
                final_report = parts[1].strip()
            else:
                # If parsing fails, use original report
                validation_notes = result_text
                final_report = report.report
            
            # Improve quality score slightly after review
            new_quality_score = min(report.quality_score * 1.05, 1.0)
            
            reviewed = ReviewedReport(
                topic=report.topic,
                execution_id=report.execution_id,
                final_report=final_report,
                validation_notes=validation_notes,
                quality_score=new_quality_score
            )
            
            logger.info(
                f"[{self.id}] Review completed",
                quality=f"{new_quality_score:.0%}"
            )
            
            await ctx.send_message(reviewed)
            
        except Exception as e:
            logger.error(f"[{self.id}] Error during review", error=str(e))
            # Send report without changes on error
            reviewed = ReviewedReport(
                topic=report.topic,
                execution_id=report.execution_id,
                final_report=report.report,
                validation_notes=f"Error during review: {str(e)}",
                quality_score=report.quality_score
            )
            await ctx.send_message(reviewed)


class SummarizerExecutor(Executor):
    """
    Executor that creates an executive summary.
    
    Input: ReviewedReport
    Output: FinalOutput
    """
    
    def __init__(self, azure_client: AzureOpenAI, model: str, executor_id: str = "summarizer"):
        super().__init__(id=executor_id)
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = """You are an expert at creating concise executive summaries.
Extract key insights and present them in a clear, actionable format for executives."""
    
    @handler
    async def run(
        self,
        reviewed: ReviewedReport,
        ctx: WorkflowContext[FinalOutput]
    ) -> None:
        """Create executive summary."""
        logger.info(f"[{self.id}] Creating executive summary")
        
        try:
            summary_prompt = f"""Create a concise executive summary of the following research report:

Topic: {reviewed.topic}

Full Report:
{reviewed.final_report}

Create an executive summary that:
1. Highlights the most important findings (3-5 key points)
2. Provides actionable insights
3. Is no more than 300 words
4. Uses clear, accessible language"""
            
            response = await asyncio.to_thread(
                self.azure_client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            exec_summary = response.choices[0].message.content
            
            # Create final output
            final = FinalOutput(
                topic=reviewed.topic,
                execution_id=reviewed.execution_id,
                final_report=reviewed.final_report,
                executive_summary=exec_summary,
                metadata={
                    "quality_score": reviewed.quality_score,
                    "workflow_type": "maf-workflow",
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"[{self.id}] Executive summary created")
            
            # Yield as final workflow output
            await ctx.yield_output(final)
            
        except Exception as e:
            logger.error(f"[{self.id}] Error creating summary", error=str(e))
            # Send final output without summary on error
            final = FinalOutput(
                topic=reviewed.topic,
                execution_id=reviewed.execution_id,
                final_report=reviewed.final_report,
                executive_summary=f"Error creating summary: {str(e)}",
                metadata={
                    "quality_score": reviewed.quality_score,
                    "error": str(e)
                }
            )
            # Yield as final workflow output
            await ctx.yield_output(final)


# ============================================================
# Workflow Builder
# ============================================================

async def create_research_workflow(
    azure_client: AzureOpenAI,
    tavily_client: TavilyClient,
    model: str = "chat4o",
    max_research_areas: int = 3
):
    """
    Create a MAF workflow for deep research.
    
    Workflow Structure:
    1. Planner creates research plan
    2. Fan-out to multiple researchers (parallel)
    3. Fan-in to synthesizer
    4. Sequential review and summarization
    
    Args:
        azure_client: Azure OpenAI client
        tavily_client: Tavily search client
        model: Azure OpenAI model deployment name
        max_research_areas: Maximum number of parallel research tasks
        
    Returns:
        Configured workflow ready for execution
    """
    logger.info("Building MAF research workflow")
    
    # Create executors
    planner = ResearchPlannerExecutor(azure_client, model, "planner")
    
    # Create multiple researchers for parallel execution
    researchers = [
        ResearchExecutor(i, tavily_client, azure_client, model, f"researcher_{i}")
        for i in range(max_research_areas)
    ]
    
    synthesizer = SynthesizerExecutor(azure_client, model, "synthesizer")
    reviewer = ReviewerExecutor(azure_client, model, "reviewer")
    summarizer = SummarizerExecutor(azure_client, model, "summarizer")
    
    # Build workflow graph
    workflow = (
        WorkflowBuilder()
        .set_start_executor(planner)
        # Fan-out: Send plan to all researchers
        .add_fan_out_edges(planner, researchers)
        # Fan-in: Collect all findings to synthesizer
        .add_fan_in_edges(researchers, synthesizer)
        # Sequential processing
        .add_edge(synthesizer, reviewer)
        .add_edge(reviewer, summarizer)
        .build()
    )
    
    logger.info(
        "MAF research workflow built",
        executors=1 + len(researchers) + 3,  # planner + researchers + 3 final
        parallel_researchers=len(researchers)
    )
    
    return workflow


# ============================================================
# Execution Function
# ============================================================

async def execute_maf_workflow_research(
    topic: str,
    execution_id: str,
    azure_client: AzureOpenAI,
    tavily_client: TavilyClient,
    model: str = "chat4o",
    max_sources: int = 5,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Execute research using MAF workflow.
    
    Args:
        topic: Research topic
        execution_id: Unique execution ID
        azure_client: Azure OpenAI client
        tavily_client: Tavily search client
        model: Azure OpenAI model deployment name
        max_sources: Maximum sources per research area
        progress_callback: Optional async callback for progress updates
        
    Returns:
        Dictionary with research results
    """
    logger.info(
        "Starting MAF workflow research",
        topic=topic,
        execution_id=execution_id
    )
    
    try:
        # Create workflow
        workflow = await create_research_workflow(
            azure_client=azure_client,
            tavily_client=tavily_client,
            model=model,
            max_research_areas=3  # 3 parallel researchers
        )
        
        # Create initial request
        request = ResearchRequest(
            topic=topic,
            execution_id=execution_id,
            max_sources=max_sources
        )
        
        # Execute workflow and collect results
        results = {
            "execution_id": execution_id,
            "topic": topic,
            "workflow_type": "maf-workflow",
            "started_at": datetime.utcnow().isoformat(),
            "events": []
        }
        
        final_output = None
        
        # Stream workflow execution
        async for event in workflow.run_stream(request):
            # Log event
            event_info = {
                "type": type(event).__name__,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if isinstance(event, WorkflowOutputEvent):
                event_info["executor_id"] = event.source_executor_id
                event_info["data_type"] = type(event.data).__name__
                logger.info(
                    "Workflow event",
                    executor=event.source_executor_id,
                    data_type=type(event.data).__name__
                )
                
                # Check if it's the final output
                if isinstance(event.data, FinalOutput):
                    final_output = event.data
            
            elif isinstance(event, ExecutorCompletedEvent):
                event_info["status"] = "executor_completed"
                executor_id = getattr(event, 'executor_id', 'unknown')
                event_info["executor_id"] = executor_id
                logger.info("Executor completed", executor_id=executor_id)
                
                # Call progress callback if provided
                if progress_callback:
                    await progress_callback("executor_completed", executor_id)
            
            elif isinstance(event, WorkflowFailedEvent):
                event_info["status"] = "failed"
                logger.error("Workflow failed")
            
            results["events"].append(event_info)
        
        # Extract final results
        if final_output:
            results.update({
                "final_report": final_output.final_report,
                "executive_summary": final_output.executive_summary,
                "metadata": final_output.metadata,
                "completed_at": datetime.utcnow().isoformat(),
                "status": "completed"
            })
        else:
            results["status"] = "no_output"
            results["error"] = "Workflow completed but no final output received"
        
        logger.info(
            "MAF workflow research completed",
            execution_id=execution_id,
            status=results.get("status")
        )
        
        return results
        
    except Exception as e:
        logger.error(
            "MAF workflow research failed",
            execution_id=execution_id,
            error=str(e)
        )
        return {
            "execution_id": execution_id,
            "topic": topic,
            "workflow_type": "maf-workflow",
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

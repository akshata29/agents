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
import json
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

# Import TavilySearchService for multi-query deep research
from .services.tavily_search_service import TavilySearchService, Source

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
    document_context: str = ""
    document_sources: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.document_sources is None:
            self.document_sources = []


@dataclass
class ResearchPlan:
    """Research plan output from planner."""
    topic: str
    execution_id: str
    research_areas: List[str]
    strategy: str
    estimated_duration: int  # minutes
    timestamp: datetime = None
    document_context: str = ""
    document_sources: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.document_sources is None:
            self.document_sources = []


@dataclass
class ResearchFindings:
    """Research findings from individual research tasks."""
    topic: str
    execution_id: str
    area: str
    findings: str
    sources: List[Any]  # List of Source objects or dicts
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
                estimated_duration=len(research_areas) * 2,  # 2 min per area
                document_context=request.document_context,
                document_sources=request.document_sources
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
                estimated_duration=6,
                document_context=request.document_context,
                document_sources=request.document_sources
            )
            await ctx.send_message(plan)


class ResearchExecutor(Executor):
    """
    Executor that performs multi-query deep research on a specific area.
    Uses TavilySearchService for web search with multiple queries per area.
    
    Input: ResearchPlan
    Output: ResearchFindings
    """
    
    def __init__(
        self,
        area_index: int,
        tavily_api_key: str,
        azure_client: AzureOpenAI,
        model: str,
        executor_id: str = None,
        queries_per_area: int = 2,
        results_per_query: int = 5
    ):
        super().__init__(id=executor_id or f"researcher_{area_index}")
        self.area_index = area_index
        self.tavily_service = TavilySearchService(api_key=tavily_api_key)
        self.azure_client = azure_client
        self.model = model
        self.queries_per_area = queries_per_area
        self.results_per_query = results_per_query
        self.system_prompt = """You are an expert researcher. 
Analyze web search results and synthesize comprehensive findings with proper citations.
Be factual, cite sources using [1], [2] format, and provide well-structured insights."""
    
    @handler
    async def run(
        self,
        plan: ResearchPlan,
        ctx: WorkflowContext[ResearchFindings]
    ) -> None:
        """Perform multi-query deep research on assigned area."""
        
        # Check if we should research this area
        if self.area_index >= len(plan.research_areas):
            logger.info(
                f"[{self.id}] No area assigned",
                index=self.area_index,
                total_areas=len(plan.research_areas)
            )
            return
        
        area = plan.research_areas[self.area_index]
        logger.info(f"[{self.id}] Researching area with multi-query approach", 
                   area=area, queries=self.queries_per_area)
        
        try:
            # Generate multiple queries for this research area
            query_generation_prompt = f"""Generate {self.queries_per_area} specific, focused search queries to research the following aspect of "{plan.topic}":

Research Area: {area}

Requirements:
- Each query should be specific and searchable (under 300 characters)
- Queries should cover different angles of this research area
- Make queries focused enough to get quality results
- Return ONLY a JSON array of query strings, nothing else

Example format:
["query 1", "query 2"]
"""
            
            response = await asyncio.to_thread(
                self.azure_client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research query generator. Return only valid JSON."},
                    {"role": "user", "content": query_generation_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            queries_text = response.choices[0].message.content.strip()
            
            # Parse queries
            try:
                queries = json.loads(queries_text)
                if not isinstance(queries, list):
                    queries = [f"{plan.topic} {area}"]
            except:
                queries = [f"{plan.topic} {area}"]
            
            # Execute each query and aggregate findings
            area_findings = []
            area_sources = []
            
            for query_idx, query in enumerate(queries[:self.queries_per_area]):
                logger.info(f"[{self.id}] Executing query {query_idx+1}/{len(queries)}: {query[:50]}...")
                
                # Perform Tavily search using the service
                search_results = await self.tavily_service.search_and_format(
                    query=query,
                    research_goal=area,
                    max_results=self.results_per_query
                )
                
                context = search_results["context"]
                sources = search_results["sources"]
                
                # Combine document context with web search context if available
                combined_context = context
                if plan.document_context:
                    combined_context = f"""## Uploaded Research Documents
{plan.document_context}
---
## Web Search Results
{context}"""
                
                # Synthesize findings with citations
                synthesis_prompt = f"""Based on the following search results for "{query}":

<CONTEXT>
{combined_context}
</CONTEXT>

Extract key learnings and insights. Be concise but information-dense.
Include citations using [1], [2] format from the context above.
Focus on factual information, metrics, and specific details."""
                
                synthesis_response = await asyncio.to_thread(
                    self.azure_client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": synthesis_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                
                findings = synthesis_response.choices[0].message.content
                area_findings.append(f"Query: {query}\n{findings}")
                area_sources.extend(sources)
                
                logger.info(f"[{self.id}] Query {query_idx+1} completed", sources_count=len(sources))
            
            # Aggregate all findings for this area
            aggregated_findings_text = "\n\n".join(area_findings)
            
            # Add document sources if available (only once per executor, not per query)
            if plan.document_sources:
                area_sources.extend(plan.document_sources)
            
            # Create findings object
            findings_obj = ResearchFindings(
                topic=plan.topic,
                execution_id=plan.execution_id,
                area=area,
                findings=aggregated_findings_text,
                sources=area_sources,  # Store Source objects + document sources
                confidence=0.85  # Could be calculated based on result quality
            )
            
            logger.info(
                f"[{self.id}] Research completed",
                area=area,
                web_sources=len([s for s in area_sources if isinstance(s, dict) and s.get("type") != "document"]),
                document_sources=len(plan.document_sources) if plan.document_sources else 0
            )
            
            await ctx.send_message(findings_obj)
            
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
        """Synthesize all findings into comprehensive report with sources."""
        logger.info(f"[{self.id}] Synthesizing report", findings_count=len(findings_list))
        
        if not findings_list:
            logger.warning(f"[{self.id}] No findings to synthesize")
            return
        
        try:
            # Get topic from first finding
            topic = findings_list[0].topic
            execution_id = findings_list[0].execution_id
            
            # Compile all findings and collect sources
            compiled_findings = ""
            all_sources = []
            
            for idx, finding in enumerate(findings_list, 1):
                compiled_findings += f"\n\n## Research Area {idx}: {finding.area}\n"
                compiled_findings += f"Confidence: {finding.confidence:.0%}\n\n"
                compiled_findings += finding.findings
                # Collect sources (they're Source objects from TavilySearchService)
                all_sources.extend(finding.sources)
            
            # Deduplicate sources by URL
            unique_sources = []
            seen_urls = set()
            for source in all_sources:
                source_url = source.url if hasattr(source, 'url') else str(source)
                if source_url and source_url not in seen_urls:
                    unique_sources.append(source)
                    seen_urls.add(source_url)
            
            logger.info(f"[{self.id}] Collected {len(unique_sources)} unique sources from {len(all_sources)} total")
            
            # Format sources list
            sources_list = "\n".join([
                f"[{idx+1}] {source.title if hasattr(source, 'title') else 'Unknown'}\n    {source.url if hasattr(source, 'url') else str(source)}"
                for idx, source in enumerate(unique_sources)
            ])
            
            # Create synthesis prompt with explicit sources requirement
            synthesis_prompt = f"""Synthesize the following research findings into a comprehensive, well-structured report about: "{topic}"

Research Findings:
{compiled_findings}

Sources ({len(unique_sources)} total):
{sources_list}

CRITICAL REQUIREMENT - SOURCES SECTION:
You MUST include a complete "## Sources" or "## References" section at the END of your report.
List ALL {len(unique_sources)} sources using this exact format:

## Sources

[1] Source Title
    URL

[2] Source Title
    URL

(etc. for all {len(unique_sources)} sources)

DO NOT skip the sources section. It is MANDATORY.

Create a report with the following structure:
1. Introduction
2. Key Findings (organized by theme, not by source)
3. Analysis and Insights
4. Implications
5. Conclusion
6. **Sources** (MANDATORY - use the numbered list provided above)

Make the report comprehensive, coherent, and cite sources using [1], [2] format in the text."""
            
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
                quality_score=f"{quality_score:.0%}",
                sources_count=len(unique_sources)
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
    Executor that enhances and refines the synthesized report.
    
    Input: SynthesizedReport
    Output: ReviewedReport
    """
    
    def __init__(self, azure_client: AzureOpenAI, model: str, executor_id: str = "reviewer"):
        super().__init__(id=executor_id)
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = """You are an expert research editor.
Your job is to take research content and enhance it - improve clarity, fix formatting, ensure logical flow, add structure.
PRESERVE all the research findings and content, especially the Sources section.
Return the IMPROVED REPORT, not feedback on it."""
    
    @handler
    async def run(
        self,
        report: SynthesizedReport,
        ctx: WorkflowContext[ReviewedReport]
    ) -> None:
        """Enhance and refine the report."""
        logger.info(f"[{self.id}] Enhancing report", quality=f"{report.quality_score:.0%}")
        
        try:
            review_prompt = f"""Take the research report and enhance it - improve clarity, structure, and flow while preserving all content.

Topic: {report.topic}

Report:
{report.report}

CRITICAL: The Sources/References section MUST be preserved in full. Do not remove or modify the sources.

Return the ENHANCED REPORT with improved clarity and structure, not commentary about it."""
            
            response = await asyncio.to_thread(
                self.azure_client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": review_prompt}
                ],
                temperature=0.5,  # Lower temperature for enhancement
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            
            # Use the enhanced report directly (no parsing needed)
            final_report = result_text.strip()
            validation_notes = "Report enhanced for clarity and structure"
            
            # Improve quality score slightly after enhancement
            new_quality_score = min(report.quality_score * 1.05, 1.0)
            
            reviewed = ReviewedReport(
                topic=report.topic,
                execution_id=report.execution_id,
                final_report=final_report,
                validation_notes=validation_notes,
                quality_score=new_quality_score
            )
            
            logger.info(
                f"[{self.id}] Enhancement completed",
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
        self.system_prompt = """You are an expert at extracting key insights from research reports and creating compelling executive summaries.
Focus on the KEY FINDINGS, not meta-commentary about the report quality."""
    
    @handler
    async def run(
        self,
        reviewed: ReviewedReport,
        ctx: WorkflowContext[FinalOutput]
    ) -> None:
        """Create executive summary of key findings."""
        logger.info(f"[{self.id}] Creating executive summary")
        
        try:
            summary_prompt = f"""Extract and present the key findings from the research report in a concise executive summary.

Topic: {reviewed.topic}

Full Report:
{reviewed.final_report}

Return the SUMMARY OF FINDINGS, not an evaluation of report quality.

Create an executive summary that:
1. Highlights the most important research findings (3-5 key points)
2. Provides actionable insights
3. Is no more than 300 words
4. Uses clear, accessible language
5. Focuses on WHAT was found, not how good the report is"""
            
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
    tavily_api_key: str,
    model: str = "chat4o",
    max_research_areas: int = 3,
    queries_per_area: int = 2,
    results_per_query: int = 5
):
    """
    Create a MAF workflow for deep research with multi-query approach.
    
    Workflow Structure:
    1. Planner creates research plan
    2. Fan-out to multiple researchers (parallel, each using multi-query)
    3. Fan-in to synthesizer
    4. Sequential enhancement and summarization
    
    Args:
        azure_client: Azure OpenAI client
        tavily_api_key: Tavily API key for search service
        model: Azure OpenAI model deployment name
        max_research_areas: Maximum number of parallel research tasks
        queries_per_area: Number of queries per research area (for deep research)
        results_per_query: Number of results per query
        
    Returns:
        Configured workflow ready for execution
    """
    logger.info("Building MAF research workflow with multi-query deep research")
    
    # Create executors
    planner = ResearchPlannerExecutor(azure_client, model, "planner")
    
    # Create multiple researchers for parallel execution with multi-query
    researchers = [
        ResearchExecutor(
            i, 
            tavily_api_key, 
            azure_client, 
            model, 
            f"researcher_{i}",
            queries_per_area=queries_per_area,
            results_per_query=results_per_query
        )
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
    tavily_api_key: str,
    model: str = "chat4o",
    max_sources: int = 5,
    queries_per_area: int = 2,
    results_per_query: int = 5,
    progress_callback: Optional[callable] = None,
    document_context: str = "",
    document_sources: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Execute research using MAF workflow with multi-query deep research.
    
    Args:
        topic: Research topic
        execution_id: Unique execution ID
        azure_client: Azure OpenAI client
        tavily_api_key: Tavily API key
        model: Azure OpenAI model deployment name
        max_sources: Maximum sources per research area (calculated from queries * results)
        queries_per_area: Number of queries per research area
        results_per_query: Number of results per query
        progress_callback: Optional async callback for progress updates
        document_context: Optional pre-uploaded document context
        document_sources: Optional list of document sources
        
    Returns:
        Dictionary with research results
    """
    logger.info(
        "Starting MAF workflow research with multi-query",
        topic=topic,
        execution_id=execution_id,
        queries_per_area=queries_per_area,
        results_per_query=results_per_query,
        has_documents=len(document_context) > 0 if document_context else False
    )
    
    try:
        # Create workflow with multi-query configuration
        workflow = await create_research_workflow(
            azure_client=azure_client,
            tavily_api_key=tavily_api_key,
            model=model,
            max_research_areas=3,  # 3 parallel researchers
            queries_per_area=queries_per_area,
            results_per_query=results_per_query
        )
        
        # Create initial request
        request = ResearchRequest(
            topic=topic,
            execution_id=execution_id,
            max_sources=max_sources,
            document_context=document_context or "",
            document_sources=document_sources or []
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

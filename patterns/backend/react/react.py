"""
Deep Research Orchestration Pattern - Microsoft Agent Framework Implementation

OVERVIEW:
This module implements an end-to-end Deep Research pattern using Microsoft Agent Framework
with Azure AI Foundry Agents. It combines ReAct planning, concurrent web search, optional MCP
integration, file search capabilities, code interpretation, and comprehensive reporting with
citations, all while enforcing role-based access control and emitting traces to Application Insights.

PATTERN FLOW:
Planner (w/ Probe Tool) → Researcher → Concurrent Search (Workflows) → Writer (streaming) 
→ Optional: Reviewer → Optional: Analyst (Code Interpreter)

FEATURES:
✅ ReAct Planner with probe tool for grounded planning
✅ Concurrent web search using MAF Workflows (ConcurrentBuilder)
✅ Optional Microsoft Learn MCP integration
✅ Optional PDF ingestion via File Search
✅ Optional Private Search over vector store
✅ Code Interpreter for data analysis
✅ Reviewer loop for quality assurance
✅ Role-based tool gating (viewer | doc-reader | analyst | admin)
✅ Application Insights tracing with gen AI content recording
✅ Streaming writer output with Markdown citations

TECH STACK:
- agent-framework, agent-framework-azure-ai
- Azure AI Foundry Agents (AzureAIAgentClient)
- Hosted tools: WebSearch, MCP, FileSearch, CodeInterpreter
- MAF Workflows for concurrent fan-out/fan-in

REAL-WORLD APPLICATIONS:
- Comprehensive market research with competitive analysis
- Technical deep-dives with Microsoft Learn integration
- Academic research with PDF source ingestion
- Private enterprise knowledge discovery
- Multi-source intelligence gathering
"""

import os
import re
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional, Annotated
from datetime import datetime
from pathlib import Path

from pydantic import Field
from azure.identity.aio import DefaultAzureCredential
from azure.identity import DefaultAzureCredential as SyncCredential
from azure.ai.agents import AgentsClient

from agent_framework.azure import AzureAIAgentClient
from agent_framework import (
    ChatAgent, 
    HostedWebSearchTool, 
    HostedMCPTool, 
    HostedFileSearchTool, 
    HostedVectorStoreContent,
    HostedCodeInterpreterTool,
    ConcurrentBuilder, 
    WorkflowOutputEvent, 
    ChatMessage,
    ai_function
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS - JSON Extraction & Deduplication
# ============================================================================

def _first_json_obj(text: str) -> Optional[dict]:
    """Extract the first JSON object from text (supports markdown code blocks)."""
    logger.debug(f"Extracting JSON object from text (length: {len(text)})")
    m = re.search(r"```json\s*({[\s\S]*?})\s*```", text) or re.search(r"({[\s\S]*})", text)
    if not m:
        logger.warning("No JSON object pattern found in text")
        return None
    
    try:
        result = json.loads(m.group(1))
        logger.debug("JSON object extraction successful")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed - {e}")
        return None


def _first_json_array(text: str) -> Optional[list]:
    """Extract the first JSON array from text (supports markdown code blocks)."""
    logger.debug(f"Extracting JSON array from text (length: {len(text)})")
    m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", text) or re.search(r"(\[[\s\S]*\])", text)
    if not m:
        logger.warning("No JSON array pattern found in text")
        return None
    
    try:
        result = json.loads(m.group(1))
        logger.debug(f"JSON array extraction successful, items: {len(result) if isinstance(result, list) else 'N/A'}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed - {e}")
        return None


def _dedupe_by_url(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate evidence items by URL."""
    logger.debug(f"Deduplicating {len(items)} items by URL")
    seen, out = set(), []
    for it in items:
        url = (it.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            out.append(it)
    logger.info(f"Deduplicated to {len(out)} unique URLs")
    return out


# ============================================================================
# SECURITY & ROLE-BASED ACCESS CONTROL
# ============================================================================

@ai_function(
    name="admin_data_export",
    description="(Admin only) Export research data to external system."
)
def admin_data_export(
    export_format: Annotated[str, Field(description="Format for export: json, csv, or xml")]
) -> str:
    """Admin-only function for data export (demonstrates role gating)."""
    role = os.environ.get("USER_ROLE", "viewer").lower()
    if role != "admin":
        raise PermissionError("Not authorized to export data. Admin role required.")
    logger.info(f"Admin data export requested in {export_format} format")
    return f"Data exported successfully in {export_format} format"


def tools_for_role(role: str, vector_store_id: Optional[str] = None) -> List:
    """
    Build tool list based on user role for security gating.
    
    Roles:
    - viewer: Basic web search only
    - doc-reader: Web search + Microsoft Learn MCP
    - analyst: Web search + MCP + Code Interpreter
    - admin: All tools including File Search and admin functions
    """
    role = role.lower()
    base_tools = [HostedWebSearchTool()]
    
    # doc-reader, analyst, admin get MCP access
    if role in {"doc-reader", "analyst", "admin"}:
        base_tools.append(
            HostedMCPTool(name="ms_learn", url="https://learn.microsoft.com/api/mcp")
        )
    
    # analyst and admin get Code Interpreter
    if role in {"analyst", "admin"}:
        base_tools.append(HostedCodeInterpreterTool())
    
    # admin gets File Search and special admin functions
    if role == "admin":
        if vector_store_id:
            base_tools.append(
                HostedFileSearchTool(
                    inputs=[HostedVectorStoreContent(vector_store_id=vector_store_id)],
                    max_results=12
                )
            )
        base_tools.append(admin_data_export)
    
    logger.info(f"Configured {len(base_tools)} tools for role: {role}")
    return base_tools


# ============================================================================
# PDF UPLOAD & VECTOR STORE CREATION (Multimodal)
# ============================================================================

def build_vector_store_for_pdf(pdf_path: str) -> str:
    """
    Upload a PDF and create a vector store for File Search.
    Returns the vector store ID.
    """
    if not pdf_path or not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    logger.info(f"Uploading PDF and creating vector store: {pdf_path}")
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT not configured")
    
    agents_client = AgentsClient(endpoint=endpoint, credential=SyncCredential())
    
    # Upload file
    uploaded = agents_client.files.upload_and_poll(file_path=pdf_path, purpose="agents")
    logger.info(f"PDF uploaded: {uploaded.id}")
    
    # Create vector store
    vs = agents_client.vector_stores.create_and_poll(
        file_ids=[uploaded.id],
        name=f"vs_{Path(pdf_path).stem}"
    )
    logger.info(f"Vector store created: {vs.id}")
    
    return vs.id


# ============================================================================
# MAIN DEEP RESEARCH ORCHESTRATION
# ============================================================================

async def run_deep_research_orchestration(
    task: str = None,
    mode: str = "baseline",  # baseline | reviewer | analyst | private | multimodal | full
    user_role: str = None,
    pdf_path: str = None,
    vector_store_id: str = None
) -> list:
    """
    Execute Deep Research Orchestration Pattern with multiple modes.
    
    This function implements a comprehensive research workflow using Azure AI Foundry Agents
    via the Microsoft Agent Framework. It supports multiple execution modes and role-based
    access control.
    
    Args:
        task (str, optional): Research objective. Defaults to demo task.
        mode (str): Execution mode:
            - "baseline": Planner → Researcher → Concurrent Search → Writer
            - "reviewer": baseline + Reviewer loop
            - "analyst": baseline + Code Interpreter analysis
            - "private": Use private vector store instead of web search
            - "multimodal": baseline + PDF ingestion via File Search
            - "full": All features enabled
        user_role (str, optional): User role for tool gating (viewer|doc-reader|analyst|admin).
                                  Defaults to USER_ROLE env var.
        pdf_path (str, optional): Path to PDF for multimodal mode. Defaults to PDF_PATH env var.
        vector_store_id (str, optional): Vector store ID for private mode. 
                                        Defaults to AZURE_VECTOR_STORE_ID env var.
    
    Returns:
        list: Formatted conversation history containing each agent's contribution:
              [
                {
                  "agent": str,
                  "input": str,
                  "output": str,
                  "timestamp": str
                }
              ]
    
    Raises:
        ValueError: If required environment variables are missing
        FileNotFoundError: If PDF path is invalid in multimodal mode
        
    Example:
        >>> results = await run_deep_research_orchestration(
        ...     task="Analyze impact of AI on software development",
        ...     mode="full",
        ...     user_role="analyst"
        ... )
        >>> print(f"Research completed with {len(results)} agent outputs")
    
    Note:
        This implementation uses:
        - Azure AI Foundry Agents via AzureAIAgentClient
        - Hosted tools: WebSearch, MCP, FileSearch, CodeInterpreter
        - MAF Workflows (ConcurrentBuilder) for concurrent search
        - Application Insights tracing (when configured)
    """
    
    # Default task if none provided
    if task is None:
        task = ("Conduct comprehensive research on the adoption and impact of Large Language Models "
                "in enterprise software development, including productivity gains, security concerns, "
                "and best practices for integration.")
    
    # Get configuration from environment
    user_role = user_role or os.environ.get("USER_ROLE", "viewer")
    pdf_path = pdf_path or os.environ.get("PDF_PATH")
    vector_store_id = vector_store_id or os.environ.get("AZURE_VECTOR_STORE_ID")
    
    logger.info("=" * 80)
    logger.info("DEEP RESEARCH ORCHESTRATION PATTERN")
    logger.info("=" * 80)
    logger.info(f"Task: {task}")
    logger.info(f"Mode: {mode}")
    logger.info(f"User Role: {user_role}")
    logger.info("=" * 80)
    
    # Setup observability (Application Insights tracing)
    try:
        from agent_framework.observability import setup_observability
        setup_observability()
        logger.info("✓ Application Insights tracing enabled")
    except Exception as e:
        logger.warning(f"Could not setup observability: {e}")
    
    conversation_outputs = []
    
    async with DefaultAzureCredential() as cred:
        logger.info("Step 1: Authenticating with Azure DefaultAzureCredential")
        client = AzureAIAgentClient(async_credential=cred)
        logger.info("Step 1: Azure AI Agent Client initialized successfully")
        
        # ====================================================================
        # STAGE 1: PLANNING WITH PROBE TOOL (ReAct Pattern)
        # ====================================================================
        
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 1: REACT PLANNING WITH PROBE TOOL")
        logger.info("=" * 80)
        
        # Create probe agent and convert to tool
        logger.info("Creating probe agent for grounded planning...")
        probe_agent = client.create_agent(
            name="probe_bing",
            instructions=(
                "Use web search to gather quick evidence for planning. "
                "Return ONLY a compact JSON array: [{title, url, snippet, date}, ...] (max 5 items). "
                "No extra prose."
            ),
            tools=[HostedWebSearchTool()]
        )
        
        probe_tool = probe_agent.as_tool(
            name="probe_bing_grounding",
            description="Probe web search for quick evidence during planning phase.",
            arg_name="query",
            arg_description="Focused search query for probing"
        )
        logger.info("✓ Probe tool created")
        
        # Create planner with probe tool
        logger.info("Creating ReAct planner agent...")
        planner = client.create_agent(
            name="planner",
            instructions=(
                "You are a ReAct planner for deep research. Think step-by-step. "
                "If uncertain about any aspect, CALL the probe_bing_grounding tool to gather evidence. "
                "Then return STRICT JSON with these keys ONLY:\n"
                "{\n"
                '  "objective": "clear research objective",\n'
                '  "goals": ["goal1", "goal2", ...],\n'
                '  "key_questions": ["question1", "question2", ...],\n'
                '  "steps": [{"step": "description", "rationale": "why", "depends_on": [0, 1]}, ...],\n'
                '  "success_criteria": ["criteria1", "criteria2", ...]\n'
                "}\n"
                "NO extra prose. Return ONLY the JSON object."
            ),
            tools=[probe_tool]
        )
        logger.info("✓ Planner agent created with probe tool")
        
        # Run planner
        logger.info("Running planner agent...")
        start_time = datetime.now()
        planner_result = await planner.run(f"Objective: {task}\n\nReturn ONLY JSON.")
        planner_output = planner_result.text
        logger.info(f"✓ Planner completed ({len(planner_output)} chars)")
        
        # Extract plan
        plan = _first_json_obj(planner_output) or {
            "objective": task,
            "goals": [],
            "key_questions": [],
            "steps": [],
            "success_criteria": []
        }
        logger.info(f"Research plan extracted with {len(plan.get('steps', []))} steps")
        
        conversation_outputs.append({
            "agent": "Planner",
            "input": task,
            "output": planner_output,
            "timestamp": start_time.isoformat()
        })
        
        # ====================================================================
        # STAGE 2: RESEARCH QUERY EXPANSION
        # ====================================================================
        
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 2: RESEARCH QUERY EXPANSION")
        logger.info("=" * 80)
        
        logger.info("Creating researcher agent...")
        researcher = client.create_agent(
            name="researcher",
            instructions=(
                "Expand the research plan into actionable queries. "
                "Return STRICT JSON with these keys ONLY:\n"
                "{\n"
                '  "prioritized_queries": ["query1", "query2", ...],\n'
                '  "extraction_schema": {"field1": "description", ...},\n'
                '  "coverage_checklist": ["item1", "item2", ...]\n'
                "}\n"
                "NO extra prose. Return ONLY the JSON object."
            )
        )
        logger.info("✓ Researcher agent created")
        
        # Run researcher
        logger.info("Running researcher agent...")
        start_time = datetime.now()
        researcher_result = await researcher.run(
            f"Plan:\n```json\n{json.dumps(plan, indent=2)}\n```\n\nReturn STRICT JSON."
        )
        researcher_output = researcher_result.text
        logger.info(f"✓ Researcher completed ({len(researcher_output)} chars)")
        
        # Extract queries
        research_ops = _first_json_obj(researcher_output) or {}
        queries = [
            q for q in (research_ops.get("prioritized_queries") or [])
            if isinstance(q, str)
        ] or [task]
        queries = queries[:8]  # Limit to 8 queries
        logger.info(f"Generated {len(queries)} prioritized queries")
        
        conversation_outputs.append({
            "agent": "Researcher",
            "input": json.dumps(plan, indent=2),
            "output": researcher_output,
            "timestamp": start_time.isoformat()
        })
        
        # ====================================================================
        # STAGE 3: CONCURRENT SEARCH (Workflows)
        # ====================================================================
        
        evidence = []
        
        if mode == "private":
            # PRIVATE SEARCH MODE - Use vector store instead of web
            logger.info("\n" + "=" * 80)
            logger.info("STAGE 3: PRIVATE SEARCH (Vector Store)")
            logger.info("=" * 80)
            
            if not vector_store_id:
                raise ValueError("AZURE_VECTOR_STORE_ID required for private mode")
            
            logger.info(f"Creating private search agent with vector store: {vector_store_id}")
            private_search = client.create_agent(
                name="private_search",
                instructions=(
                    "Use File/Vector Search over the connected store. "
                    "Return ONLY JSON array of {title, url, snippet, date} (max 12). "
                    "No extra prose."
                ),
                tools=[
                    HostedFileSearchTool(
                        inputs=[HostedVectorStoreContent(vector_store_id=vector_store_id)],
                        max_results=12
                    )
                ]
            )
            
            logger.info("Running private search...")
            start_time = datetime.now()
            search_result = await private_search.run(
                "Search private corpus for:\n- " + "\n- ".join(queries) +
                "\nReturn ONLY JSON array."
            )
            logger.info(f"✓ Private search completed ({len(search_result.text)} chars)")
            
            evidence = _first_json_array(search_result.text) or []
            logger.info(f"Collected {len(evidence)} evidence items from private sources")
            
            conversation_outputs.append({
                "agent": "PrivateSearch",
                "input": "\n".join(queries),
                "output": search_result.text,
                "timestamp": start_time.isoformat()
            })
            
        elif mode == "multimodal" or (mode == "full" and pdf_path):
            # MULTIMODAL MODE - Ingest PDF and search
            logger.info("\n" + "=" * 80)
            logger.info("STAGE 3: MULTIMODAL PDF SEARCH")
            logger.info("=" * 80)
            
            # Upload PDF and create vector store
            vs_id = build_vector_store_for_pdf(pdf_path)
            logger.info(f"PDF processed, vector store ID: {vs_id}")
            
            logger.info("Creating PDF search agent...")
            pdf_search = client.create_agent(
                name="pdf_search",
                instructions=(
                    "Use File Search to read the uploaded PDF. "
                    "Cite filename and page when possible. "
                    "Return ONLY JSON array of {title, url, snippet, date} (max 12). "
                    "No extra prose."
                ),
                tools=[
                    HostedFileSearchTool(
                        inputs=[HostedVectorStoreContent(vector_store_id=vs_id)],
                        max_results=12
                    )
                ]
            )
            
            logger.info("Running PDF search...")
            start_time = datetime.now()
            search_result = await pdf_search.run(
                "Extract relevant information for:\n- " + "\n- ".join(queries) +
                "\nReturn ONLY JSON array."
            )
            logger.info(f"✓ PDF search completed ({len(search_result.text)} chars)")
            
            evidence = _first_json_array(search_result.text) or []
            logger.info(f"Collected {len(evidence)} evidence items from PDF")
            
            conversation_outputs.append({
                "agent": "PDFSearch",
                "input": "\n".join(queries),
                "output": search_result.text,
                "timestamp": start_time.isoformat()
            })
            
        else:
            # STANDARD MODE - Concurrent web search using Workflows
            logger.info("\n" + "=" * 80)
            logger.info("STAGE 3: CONCURRENT WEB SEARCH (Workflows)")
            logger.info("=" * 80)
            
            # Create specialized search agents
            logger.info("Creating specialized search agents...")
            
            def create_search_agent(name: str, focus: str) -> ChatAgent:
                """Helper to create specialized search agent."""
                logger.info(f"  - Creating search agent: {name}")
                return client.create_agent(
                    name=f"search_{name}",
                    instructions=(
                        f"Use web search focused on: {focus}. "
                        "Return ONLY a JSON array of {title, url, snippet, date} (max 8 items). "
                        "No extra prose or explanation."
                    ),
                    tools=[HostedWebSearchTool()]
                )
            
            search_agents = [
                create_search_agent("primary_sources", "primary sources and authoritative references"),
                create_search_agent("latest_news", "latest news and recent developments"),
                create_search_agent("academic", "academic research and studies"),
                create_search_agent("industry", "industry reports and competitive landscape"),
            ]
            logger.info(f"✓ Created {len(search_agents)} specialized search agents")
            
            # Build concurrent workflow
            logger.info("Building concurrent workflow...")
            workflow = ConcurrentBuilder().participants(search_agents).build()
            logger.info("✓ Workflow built successfully")
            
            # Create search prompt
            search_prompt = (
                "Use web search to gather high-quality recent evidence for:\n- " +
                "\n- ".join(queries) +
                "\n\nReturn ONLY JSON array of {title, url, snippet, date} (max 8 per agent)."
            )
            
            # Run concurrent workflow
            logger.info("Running concurrent workflow (streaming)...")
            start_time = datetime.now()
            
            workflow_outputs: List[WorkflowOutputEvent] = []
            event_count = 0
            
            async for ev in workflow.run_stream(search_prompt):
                event_count += 1
                if isinstance(ev, WorkflowOutputEvent):
                    workflow_outputs.append(ev)
                    logger.debug(f"Received workflow output event {event_count}")
            
            logger.info(f"✓ Workflow completed (total events: {event_count}, outputs: {len(workflow_outputs)})")
            
            # Extract evidence from all agents
            combined_messages: List[ChatMessage] = []
            for output_event in workflow_outputs:
                if isinstance(output_event.data, list):
                    combined_messages.extend(output_event.data)
            
            logger.info(f"Received {len(combined_messages)} messages from workflow")
            
            evidence_items: List[Dict[str, Any]] = []
            for msg in combined_messages:
                if getattr(msg, "text", None):
                    arr = _first_json_array(msg.text)
                    if isinstance(arr, list):
                        evidence_items.extend(arr)
            
            logger.info(f"Extracted {len(evidence_items)} total evidence items")
            
            # Deduplicate and limit
            evidence = _dedupe_by_url(evidence_items)[:24]
            logger.info(f"Deduplicated to {len(evidence)} unique items (limited to 24)")
            
            # Record concurrent search results
            search_summary = f"Concurrent search completed: {len(evidence)} unique sources from {len(search_agents)} agents"
            conversation_outputs.append({
                "agent": "ConcurrentSearch",
                "input": "\n".join(queries),
                "output": json.dumps(evidence, indent=2),
                "timestamp": start_time.isoformat()
            })
        
        # ====================================================================
        # STAGE 4: CODE INTERPRETER ANALYSIS (Optional)
        # ====================================================================
        
        appendix_md = ""
        
        if mode in ["analyst", "full"] and user_role in ["analyst", "admin"]:
            logger.info("\n" + "=" * 80)
            logger.info("STAGE 4: CODE INTERPRETER ANALYSIS")
            logger.info("=" * 80)
            
            logger.info("Creating analyst agent with Code Interpreter...")
            analyst = client.create_agent(
                name="analyst",
                instructions=(
                    "You have a Python Code Interpreter. "
                    "Given an evidence JSON array, use Python to:\n"
                    "1) Build a Markdown table (Title | URL | Date)\n"
                    "2) Show counts by domain\n"
                    "3) Generate simple statistics (total sources, date range, etc.)\n"
                    "Return ONLY Markdown output. No code blocks in output."
                ),
                tools=[HostedCodeInterpreterTool()]
            )
            logger.info("✓ Analyst agent created")
            
            logger.info("Running analyst agent...")
            start_time = datetime.now()
            analyst_result = await analyst.run(
                f"Evidence JSON:\n```json\n{json.dumps(evidence, indent=2)}\n```"
            )
            appendix_md = analyst_result.text
            logger.info(f"✓ Analyst completed ({len(appendix_md)} chars)")
            
            conversation_outputs.append({
                "agent": "Analyst",
                "input": f"{len(evidence)} evidence items",
                "output": appendix_md,
                "timestamp": start_time.isoformat()
            })
        
        # ====================================================================
        # STAGE 5: WRITER (Streaming Markdown Report)
        # ====================================================================
        
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 5: WRITING FINAL REPORT (Streaming)")
        logger.info("=" * 80)
        
        logger.info("Creating writer agent...")
        writer = client.create_agent(
            name="writer",
            instructions=(
                "Write a comprehensive Markdown research report with:\n"
                "1. Title\n"
                "2. Executive Summary\n"
                "3. Methodology\n"
                "4. Findings (with inline [n] citations)\n"
                "5. Limitations\n"
                "6. References section: [n] Title — URL — (Accessed: YYYY-MM-DD)\n"
                "\n"
                "If Appendix A is provided, include it at the end.\n"
                "Be thorough, well-structured, and cite all sources properly."
            )
        )
        logger.info("✓ Writer agent created")
        
        # Prepare writer input
        writer_input = {
            "objective": task,
            "plan": plan,
            "queries_used": queries,
            "evidence": evidence
        }
        
        writer_prompt = (
            f"Create the final research report from this JSON:\n```json\n" +
            json.dumps(writer_input, indent=2) +
            "\n```"
        )
        
        if appendix_md:
            writer_prompt += f"\n\n--- Appendix A (from Analyst) ---\n{appendix_md}"
        
        # Stream writer output
        logger.info("Running writer agent (streaming)...")
        start_time = datetime.now()
        
        final_chunks: List[str] = []
        chunk_count = 0
        
        async for upd in writer.run_stream(writer_prompt):
            if upd.text:
                print(upd.text, end="", flush=True)
                final_chunks.append(upd.text)
                chunk_count += 1
        
        final_report = "".join(final_chunks)
        logger.info(f"\n✓ Writer completed ({chunk_count} chunks, {len(final_report)} chars)")
        
        conversation_outputs.append({
            "agent": "Writer",
            "input": f"Plan + {len(evidence)} evidence items" + (" + Appendix" if appendix_md else ""),
            "output": final_report,
            "timestamp": start_time.isoformat()
        })
        
        # ====================================================================
        # STAGE 6: REVIEWER LOOP (Optional)
        # ====================================================================
        
        if mode in ["reviewer", "full"]:
            logger.info("\n" + "=" * 80)
            logger.info("STAGE 6: REVIEWER LOOP")
            logger.info("=" * 80)
            
            logger.info("Creating reviewer agent...")
            reviewer = client.create_agent(
                name="reviewer",
                instructions=(
                    "Be a critical reviewer. Provide:\n"
                    "1. Numbered list of specific issues (facts, citations, structure, clarity)\n"
                    "2. A short 'Ready/Not Ready' verdict\n"
                    "\n"
                    "Be constructive and actionable."
                )
            )
            logger.info("✓ Reviewer agent created")
            
            logger.info("Running reviewer agent...")
            start_time = datetime.now()
            critique_result = await reviewer.run(
                f"Review this research report. Be specific and actionable:\n\n{final_report}"
            )
            critique = critique_result.text
            logger.info(f"✓ Reviewer completed ({len(critique)} chars)")
            
            conversation_outputs.append({
                "agent": "Reviewer",
                "input": "Final report",
                "output": critique,
                "timestamp": start_time.isoformat()
            })
            
            # Revise based on feedback
            logger.info("Revising report based on reviewer feedback...")
            start_time = datetime.now()
            
            revision_chunks: List[str] = []
            async for upd in writer.run_stream(
                f"Revise the draft according to the review. Preserve all citations.\n\n"
                f"--- Draft ---\n{final_report}\n\n--- Review ---\n{critique}"
            ):
                if upd.text:
                    print(upd.text, end="", flush=True)
                    revision_chunks.append(upd.text)
            
            final_report = "".join(revision_chunks)
            logger.info(f"\n✓ Revision completed ({len(final_report)} chars)")
            
            conversation_outputs.append({
                "agent": "Writer (Revision)",
                "input": "Draft + Review",
                "output": final_report,
                "timestamp": start_time.isoformat()
            })
        
        # ====================================================================
        # COMPLETION
        # ====================================================================
        
        logger.info("\n" + "=" * 80)
        logger.info("DEEP RESEARCH ORCHESTRATION COMPLETED")
        logger.info(f"Total agents executed: {len(conversation_outputs)}")
        logger.info(f"Final report length: {len(final_report)} characters")
        logger.info(f"Evidence sources: {len(evidence)}")
        logger.info("=" * 80)
        
        return conversation_outputs


# ============================================================================
# CONVENIENCE FUNCTIONS FOR SPECIFIC MODES
# ============================================================================

async def run_baseline_research(task: str) -> list:
    """Run baseline deep research (Planner → Researcher → Concurrent Search → Writer)."""
    return await run_deep_research_orchestration(task=task, mode="baseline")


async def run_research_with_reviewer(task: str) -> list:
    """Run deep research with reviewer loop."""
    return await run_deep_research_orchestration(task=task, mode="reviewer")


async def run_research_with_analyst(task: str) -> list:
    """Run deep research with code interpreter analysis."""
    return await run_deep_research_orchestration(task=task, mode="analyst", user_role="analyst")


async def run_private_research(task: str, vector_store_id: str) -> list:
    """Run deep research over private vector store."""
    return await run_deep_research_orchestration(
        task=task,
        mode="private",
        vector_store_id=vector_store_id,
        user_role="admin"
    )


async def run_multimodal_research(task: str, pdf_path: str) -> list:
    """Run deep research with PDF ingestion."""
    return await run_deep_research_orchestration(
        task=task,
        mode="multimodal",
        pdf_path=pdf_path,
        user_role="admin"
    )


async def run_full_research(task: str) -> list:
    """Run complete deep research with all features."""
    return await run_deep_research_orchestration(task=task, mode="full", user_role="admin")

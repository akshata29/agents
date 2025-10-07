"""
Advanced Research Techniques for Deep Research Application

Implements Phase 2 capabilities:
1. Multi-pass refinement with gap analysis
2. Multi-perspective analysis (Technical Expert, Business Analyst, Critic)
3. Fact-checking layer with claim verification
4. Source quality tiers and assessment
"""

import asyncio
import structlog
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


# ============================================================
# Source Quality Tier System
# ============================================================

class SourceTier(Enum):
    """Source quality tiers for research validation."""
    TIER_1 = "peer_reviewed"      # Academic journals, peer-reviewed papers
    TIER_2 = "primary_source"      # Official docs, whitepapers, research reports
    TIER_3 = "reputable_media"     # Established news, industry publications
    TIER_4 = "general_web"         # General web sources


SOURCE_TIER_INDICATORS = {
    SourceTier.TIER_1: {
        "domains": [
            ".edu", "arxiv.org", "nature.com", "science.org", "ieee.org",
            "springer.com", "elsevier.com", "wiley.com", "jstor.org",
            "plos.org", "nih.gov", "pubmed", "scholar.google"
        ],
        "keywords": ["journal", "research", "study", "peer-reviewed", "academia"],
        "score": 1.0
    },
    SourceTier.TIER_2: {
        "domains": [
            ".gov", ".org", "github.com", "microsoft.com", "aws.amazon.com",
            "cloud.google.com", "documentation", "whitepaper"
        ],
        "keywords": ["official", "documentation", "whitepaper", "technical report"],
        "score": 0.85
    },
    SourceTier.TIER_3: {
        "domains": [
            "nytimes.com", "wsj.com", "reuters.com", "bloomberg.com",
            "forbes.com", "techcrunch.com", "wired.com", "arstechnica.com"
        ],
        "keywords": ["news", "analysis", "report", "investigation"],
        "score": 0.7
    },
    SourceTier.TIER_4: {
        "domains": [],  # Everything else
        "keywords": [],
        "score": 0.5
    }
}


@dataclass
class SourceQualityAssessment:
    """Assessment of source quality."""
    url: str
    title: str
    tier: SourceTier
    score: float
    indicators: List[str]


def assess_source_quality(source: Any) -> SourceQualityAssessment:
    """
    Assess the quality tier of a research source.
    
    Args:
        source: Source object or dict with url and title
        
    Returns:
        SourceQualityAssessment with tier and score
    """
    url = source.url if hasattr(source, 'url') else source.get('url', '')
    title = source.title if hasattr(source, 'title') else source.get('title', '')
    
    url_lower = url.lower()
    title_lower = title.lower()
    
    # Check each tier in order of quality
    for tier in [SourceTier.TIER_1, SourceTier.TIER_2, SourceTier.TIER_3]:
        indicators_found = []
        tier_info = SOURCE_TIER_INDICATORS[tier]
        
        # Check domain indicators
        for domain in tier_info["domains"]:
            if domain in url_lower:
                indicators_found.append(f"domain:{domain}")
        
        # Check keyword indicators
        for keyword in tier_info["keywords"]:
            if keyword in url_lower or keyword in title_lower:
                indicators_found.append(f"keyword:{keyword}")
        
        if indicators_found:
            return SourceQualityAssessment(
                url=url,
                title=title,
                tier=tier,
                score=tier_info["score"],
                indicators=indicators_found
            )
    
    # Default to TIER_4
    return SourceQualityAssessment(
        url=url,
        title=title,
        tier=SourceTier.TIER_4,
        score=SOURCE_TIER_INDICATORS[SourceTier.TIER_4]["score"],
        indicators=["general_web"]
    )


def filter_sources_by_tier(sources: List[Any], min_tier: SourceTier = SourceTier.TIER_3) -> Tuple[List[Any], List[SourceQualityAssessment]]:
    """
    Filter sources by minimum quality tier.
    
    Args:
        sources: List of source objects
        min_tier: Minimum acceptable tier
        
    Returns:
        Tuple of (filtered sources, quality assessments)
    """
    tier_order = [SourceTier.TIER_1, SourceTier.TIER_2, SourceTier.TIER_3, SourceTier.TIER_4]
    min_tier_index = tier_order.index(min_tier)
    
    filtered_sources = []
    assessments = []
    
    for source in sources:
        assessment = assess_source_quality(source)
        assessments.append(assessment)
        
        source_tier_index = tier_order.index(assessment.tier)
        if source_tier_index <= min_tier_index:
            filtered_sources.append(source)
    
    logger.info(
        "Source quality filtering",
        total_sources=len(sources),
        filtered_sources=len(filtered_sources),
        min_tier=min_tier.value,
        tier_distribution={
            tier.value: len([a for a in assessments if a.tier == tier])
            for tier in tier_order
        }
    )
    
    return filtered_sources, assessments


# ============================================================
# Gap Analysis for Multi-pass Refinement
# ============================================================

async def analyze_research_gaps(
    topic: str,
    iteration: int,
    previous_findings: str,
    previous_sources: List[Any],
    azure_client: Any,
    model: str
) -> Dict[str, Any]:
    """
    Analyze gaps in current research to guide next iteration.
    
    Args:
        topic: Research topic
        iteration: Current iteration number
        previous_findings: Findings from previous iteration
        previous_sources: Sources from previous iteration
        azure_client: Azure OpenAI client
        model: Model deployment name
        
    Returns:
        Dict with gap analysis and next iteration focus areas
    """
    logger.info(f"🔍 Gap Analysis - Iteration {iteration}")
    
    # Assess source quality
    source_assessments = [assess_source_quality(s) for s in previous_sources]
    tier_counts = {
        "tier_1": len([a for a in source_assessments if a.tier == SourceTier.TIER_1]),
        "tier_2": len([a for a in source_assessments if a.tier == SourceTier.TIER_2]),
        "tier_3": len([a for a in source_assessments if a.tier == SourceTier.TIER_3]),
        "tier_4": len([a for a in source_assessments if a.tier == SourceTier.TIER_4])
    }
    
    gap_analysis_prompt = f"""You are a research quality analyst. Analyze the following research findings and identify gaps for deeper investigation.

Research Topic: {topic}
Iteration: {iteration}/5

Current Findings:
{previous_findings[:3000]}  # Truncate for context window

Source Quality Distribution:
- Tier 1 (Peer-reviewed): {tier_counts['tier_1']}
- Tier 2 (Primary sources): {tier_counts['tier_2']}
- Tier 3 (Reputable media): {tier_counts['tier_3']}
- Tier 4 (General web): {tier_counts['tier_4']}

Identify:
1. **Content Gaps**: What important aspects are missing or underdeveloped?
2. **Evidence Gaps**: Where do we need stronger sources (Tier 1-2)?
3. **Perspective Gaps**: What viewpoints or stakeholders are not represented?
4. **Depth Gaps**: Which areas need more detailed exploration?
5. **Recency Gaps**: Do we need more current data or developments?

Return your analysis in this format:
PRIORITY_GAPS:
- [List 3-5 specific gaps to address in next iteration]

RECOMMENDED_QUERIES:
- [List 3-5 targeted search queries to fill these gaps]

SOURCE_QUALITY_NEEDS:
- [Specify what types of sources we need: "more peer-reviewed", "official documentation", etc.]
"""
    
    response = await asyncio.to_thread(
        azure_client.chat.completions.create,
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert research analyst specializing in identifying knowledge gaps."},
            {"role": "user", "content": gap_analysis_prompt}
        ],
        temperature=0.3  # Lower temperature for analytical task
    )
    
    gap_analysis = response.choices[0].message.content
    
    logger.info(
        f"Gap analysis completed",
        iteration=iteration,
        source_tiers=tier_counts
    )
    
    return {
        "iteration": iteration,
        "gap_analysis": gap_analysis,
        "source_quality": tier_counts,
        "total_sources": len(previous_sources)
    }


# ============================================================
# Multi-Perspective Analysis
# ============================================================

class PerspectiveRole(Enum):
    """Different analytical perspectives for comprehensive review."""
    TECHNICAL_EXPERT = "technical_expert"
    BUSINESS_ANALYST = "business_analyst"
    CRITICAL_REVIEWER = "critical_reviewer"


PERSPECTIVE_PROMPTS = {
    PerspectiveRole.TECHNICAL_EXPERT: {
        "system": """You are a Senior Technical Expert with deep domain knowledge. Your role is to evaluate technical accuracy, depth, and rigor.

Focus on:
- Technical correctness and precision
- Depth of technical explanations
- Use of appropriate terminology
- Technical nuance and edge cases
- Latest technical developments
- Technical feasibility and limitations""",
        
        "task": """Review the following research report from a technical perspective:

{report}

Provide your technical expert review:

TECHNICAL ACCURACY: [Rate 1-10 and explain]
- Are technical claims accurate and well-supported?
- Are technical details explained correctly?

TECHNICAL DEPTH: [Rate 1-10 and explain]
- Is the technical depth appropriate?
- Are important technical details covered?

TECHNICAL GAPS: [List specific gaps]
- What technical aspects are missing?
- What technical details need clarification?

TECHNICAL ENHANCEMENTS: [Provide specific recommendations]
- How can technical accuracy be improved?
- What technical content should be added?"""
    },
    
    PerspectiveRole.BUSINESS_ANALYST: {
        "system": """You are a Strategic Business Analyst. Your role is to evaluate practical implications, business value, and real-world applicability.

Focus on:
- Business value and ROI
- Practical implementation considerations
- Market implications and opportunities
- Risk assessment
- Stakeholder impact
- Cost-benefit analysis""",
        
        "task": """Review the following research report from a business perspective:

{report}

Provide your business analyst review:

BUSINESS VALUE: [Rate 1-10 and explain]
- What is the practical business value?
- Are business implications clearly articulated?

PRACTICAL APPLICABILITY: [Rate 1-10 and explain]
- How actionable are the findings?
- Are implementation considerations addressed?

BUSINESS GAPS: [List specific gaps]
- What business aspects are missing?
- What practical considerations are overlooked?

BUSINESS ENHANCEMENTS: [Provide specific recommendations]
- How can business value be better articulated?
- What business analysis should be added?"""
    },
    
    PerspectiveRole.CRITICAL_REVIEWER: {
        "system": """You are a Critical Reviewer and Devil's Advocate. Your role is to identify weaknesses, biases, and missing perspectives.

Focus on:
- Logical consistency and argument quality
- Potential biases and assumptions
- Missing counterarguments
- Overlooked perspectives
- Evidence quality and gaps
- Alternative interpretations""",
        
        "task": """Review the following research report with critical scrutiny:

{report}

Provide your critical review:

ARGUMENT QUALITY: [Rate 1-10 and explain]
- Are arguments logically sound?
- Is evidence sufficient and well-cited?

BIAS ASSESSMENT: [Identify potential biases]
- What biases or assumptions are present?
- Are alternative viewpoints considered?

CRITICAL GAPS: [List specific weaknesses]
- What perspectives are missing?
- What counterarguments should be addressed?
- Where is evidence weak or lacking?

CRITICAL ENHANCEMENTS: [Provide specific recommendations]
- How can objectivity be improved?
- What alternative perspectives should be included?
- How can arguments be strengthened?"""
    }
}


async def multi_perspective_analysis(
    report: str,
    azure_client: Any,
    model: str
) -> Dict[str, str]:
    """
    Analyze research report from multiple expert perspectives.
    
    Args:
        report: Research report to analyze
        azure_client: Azure OpenAI client
        model: Model deployment name
        
    Returns:
        Dict with reviews from each perspective
    """
    logger.info("🎭 Starting multi-perspective analysis")
    
    perspectives = {}
    
    for role in PerspectiveRole:
        logger.info(f"  Analyzing from {role.value} perspective")
        
        prompt_config = PERSPECTIVE_PROMPTS[role]
        task_prompt = prompt_config["task"].format(report=report[:4000])  # Truncate for context
        
        response = await asyncio.to_thread(
            azure_client.chat.completions.create,
            model=model,
            messages=[
                {"role": "system", "content": prompt_config["system"]},
                {"role": "user", "content": task_prompt}
            ],
            temperature=0.4
        )
        
        perspectives[role.value] = response.choices[0].message.content
        logger.info(f"  ✓ {role.value} review completed")
    
    logger.info("✅ Multi-perspective analysis completed")
    return perspectives


# ============================================================
# Fact-Checking Layer
# ============================================================

async def fact_check_claims(
    report: str,
    sources: List[Any],
    azure_client: Any,
    model: str,
    tavily_search_service: Any
) -> Dict[str, Any]:
    """
    Extract and verify key claims from research report.
    
    Args:
        report: Research report
        sources: Original sources used
        azure_client: Azure OpenAI client
        model: Model deployment name
        tavily_search_service: Tavily search service for verification
        
    Returns:
        Dict with claim verification results
    """
    logger.info("✓ Starting fact-checking layer")
    
    # Step 1: Extract key claims
    extraction_prompt = f"""Extract the top 5-7 most important factual claims from this research report.

Report:
{report[:3000]}

For each claim, provide:
1. The specific claim (be precise and concise)
2. Why it's important to verify
3. Confidence level based on how well it's cited in the report

Format as:
CLAIM 1: [claim text]
IMPORTANCE: [why verify]
CITED: [Yes/Partially/No]

CLAIM 2: ...
"""
    
    claims_response = await asyncio.to_thread(
        azure_client.chat.completions.create,
        model=model,
        messages=[
            {"role": "system", "content": "You are a fact-checking analyst extracting verifiable claims."},
            {"role": "user", "content": extraction_prompt}
        ],
        temperature=0.2
    )
    
    extracted_claims = claims_response.choices[0].message.content
    logger.info("  Claims extracted for verification")
    
    # Step 2: Verify claims (simplified - in production would do actual verification searches)
    verification_prompt = f"""Review these extracted claims against the original sources and assess verification status.

Claims:
{extracted_claims}

Original Source Count: {len(sources)}
Source Quality: {len([s for s in sources if 'edu' in (s.url if hasattr(s, 'url') else s.get('url', ''))])} academic, {len(sources) - len([s for s in sources if 'edu' in (s.url if hasattr(s, 'url') else s.get('url', ''))])} other

For each claim, provide:
VERIFICATION_STATUS: [Verified/Partially Verified/Unverified]
CONFIDENCE_SCORE: [0-100]
EVIDENCE_QUALITY: [Strong/Moderate/Weak]
RECOMMENDATION: [Accept/Flag for review/Requires additional sources]
"""
    
    verification_response = await asyncio.to_thread(
        azure_client.chat.completions.create,
        model=model,
        messages=[
            {"role": "system", "content": "You are a fact-checking expert assessing claim verification."},
            {"role": "user", "content": verification_prompt}
        ],
        temperature=0.2
    )
    
    verification_results = verification_response.choices[0].message.content
    
    logger.info("✅ Fact-checking completed")
    
    return {
        "extracted_claims": extracted_claims,
        "verification_results": verification_results,
        "sources_analyzed": len(sources)
    }

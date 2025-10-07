"""
Research Depth Configuration

Defines depth-specific configurations for research execution.
Implements Phase 3: Production-Grade Enhancements from RESEARCH_DEPTH_ANALYSIS.md
"""

from typing import Dict, Any, List


# Depth-driven configuration
DEPTH_CONFIGS: Dict[str, Dict[str, Any]] = {
    "quick": {
        "max_sources": 5,
        "research_aspects": 2,  # Core concepts + current state only
        "queries_per_aspect": 1,
        "synthesis_iterations": 1,
        "report_min_words": 500,
        "report_max_words": 1500,
        "timeout": 300,  # 5 minutes
        "detail_level": "overview",
        "enable_fact_checking": False,
        "enable_multi_perspective": False,
        "enable_refinement": False
    },
    "standard": {
        "max_sources": 10,
        "research_aspects": 3,  # Add challenges
        "queries_per_aspect": 1,
        "synthesis_iterations": 2,
        "report_min_words": 1500,
        "report_max_words": 3000,
        "timeout": 900,  # 15 minutes
        "detail_level": "detailed",
        "enable_fact_checking": False,
        "enable_multi_perspective": False,
        "enable_refinement": False
    },
    "comprehensive": {
        "max_sources": 20,
        "research_aspects": 5,  # All 5 aspects
        "queries_per_aspect": 2,
        "synthesis_iterations": 3,
        "report_min_words": 3000,
        "report_max_words": 6000,
        "timeout": 2400,  # 40 minutes
        "detail_level": "comprehensive",
        "enable_fact_checking": True,
        "enable_multi_perspective": False,
        "enable_refinement": True
    },
    "exhaustive": {
        "max_sources": 50,
        "research_aspects": 5,
        "queries_per_aspect": 3,
        "synthesis_iterations": 5,  # Multiple refinement passes
        "report_min_words": 6000,
        "report_max_words": 15000,
        "timeout": 7200,  # 2 hours
        "detail_level": "exhaustive",
        "enable_fact_checking": True,
        "enable_multi_perspective": True,
        "enable_refinement": True,
        "enable_gap_analysis": True,
        "enable_cross_validation": True
    }
}


# Depth-specific prompts
DEPTH_PROMPTS: Dict[str, Dict[str, str]] = {
    "quick": {
        "planner": """Create a focused research plan covering the essential aspects of {topic}. 

Prioritize:
- Breadth over depth
- Key facts and main points
- Quick, actionable insights

Target: 500-1500 word report
Time: 5-10 minutes""",
        
        "researcher": """Provide a concise overview focusing on key facts and main points.
Extract the most important information efficiently.""",
        
        "writer": """Write a clear, concise report (500-1500 words) with essential insights.

Structure:
- Executive Summary
- Key Findings (3-5 bullet points)
- Conclusion

Focus on clarity and brevity.""",
        
        "reviewer": """Review for clarity and completeness. Ensure all key points are covered concisely.""",
        
        "summarizer": """Create a 2-3 sentence executive summary highlighting the most critical insights."""
    },
    
    "standard": {
        "planner": """Create a balanced research plan for {topic} covering major aspects with moderate depth.

Include:
- Core concepts and definitions
- Current state and trends
- Key challenges
- Practical applications

Target: 1500-3000 word report
Time: 15-20 minutes""",
        
        "researcher": """Provide detailed analysis with supporting evidence and examples.
Balance breadth and depth appropriately.""",
        
        "writer": """Write a comprehensive report (1500-3000 words) with analysis and insights.

Structure:
- Executive Summary
- Introduction
- Main Analysis (3-4 sections)
- Key Insights
- Conclusion
- References

Provide evidence-based analysis with clear explanations.""",
        
        "reviewer": """Review for accuracy, completeness, and logical flow. Enhance analysis with additional insights where appropriate.""",
        
        "summarizer": """Create a concise executive summary (150-200 words) covering main findings and implications."""
    },
    
    "comprehensive": {
        "planner": """Create a thorough research plan for {topic} examining all major dimensions.

Comprehensive coverage of:
- Core concepts and theoretical foundations
- Historical context and evolution
- Current state of the art
- Key challenges and limitations
- Future directions and implications
- Practical applications and case studies

Target: 3000-6000 word report
Time: 30-40 minutes""",
        
        "researcher": """Conduct deep investigation with extensive evidence, multiple perspectives, and critical analysis.
Provide comprehensive coverage with nuanced insights.""",
        
        "writer": """Write an in-depth research report (3000-6000 words) with detailed analysis, evidence, and nuanced insights.

Structure:
- Executive Summary
- Introduction & Background
- Methodology
- Detailed Analysis (5+ sections with subsections)
- Critical Evaluation
- Implications & Recommendations
- Conclusion
- Comprehensive References
- Appendices (if needed)

Requirements:
- Evidence-based analysis with extensive citations
- Multiple perspectives and viewpoints
- Critical evaluation of strengths and limitations
- Practical recommendations
- Clear, professional academic style""",
        
        "reviewer": """Conduct thorough review for:
- Factual accuracy and citation quality
- Depth and comprehensiveness of analysis
- Logical structure and flow
- Balanced perspective
- Clarity and professionalism

Enhance the report by:
- Adding missing perspectives
- Strengthening weak arguments
- Improving clarity and coherence
- Adding relevant examples and evidence""",
        
        "summarizer": """Create a comprehensive executive summary (300-400 words) that:
- Synthesizes key findings across all sections
- Highlights critical insights and implications
- Provides actionable recommendations
- Captures the essence of the full report for executive audiences"""
    },
    
    "exhaustive": {
        "planner": """Create an exhaustive research plan for {topic} covering all aspects, edge cases, and interconnections.

Comprehensive examination of:
- Theoretical foundations and conceptual frameworks
- Complete historical context and evolution
- Current state with cutting-edge developments
- All major challenges, limitations, and open problems
- Multiple future scenarios and implications
- Extensive practical applications and case studies
- Cross-disciplinary connections and insights
- Comparative analysis with related domains
- Methodological considerations
- Expert opinions and debates

Target: 6000-15000 word scholarly report
Time: 1-2 hours""",
        
        "researcher": """Conduct comprehensive investigation leaving no stone unturned.

Include:
- Historical context and evolution of thought
- Current state with latest developments (2023-2025)
- Future implications and scenarios
- Comparative analysis across domains
- Expert opinions and debates
- Primary sources and original research
- Multiple theoretical perspectives
- Practical applications with detailed case studies
- Methodological rigor

Provide extensive evidence from diverse, high-quality sources.""",
        
        "writer": """Write a scholarly research report (6000-15000 words) with comprehensive analysis, extensive evidence, multiple perspectives, critical evaluation, and actionable recommendations.

Structure:
- Abstract (150-200 words)
- Executive Summary (500 words)
- Introduction & Context
- Literature Review
- Methodology & Approach
- Comprehensive Analysis (10+ sections with detailed subsections)
  - Multiple perspectives and frameworks
  - Comparative analysis
  - Critical evaluation
- Multi-Perspective Evaluation
  - Technical perspective
  - Business/Practical perspective
  - Academic/Scholarly perspective
  - Critical/Contrarian perspective
- Future Directions & Scenarios
- Limitations & Constraints
- Practical Recommendations (actionable)
- Conclusion
- Extensive References (50+ high-quality sources)
- Detailed Appendices
- Glossary of key terms

Requirements:
- Scholarly depth with academic rigor
- Extensive evidence (50+ citations)
- Multiple theoretical frameworks
- Balanced critical analysis
- Synthesis across perspectives
- Original insights and connections
- Clear, professional academic style
- Actionable recommendations grounded in evidence""",
        
        "reviewer": """Conduct rigorous scholarly review:

Verify:
- Factual accuracy against multiple sources
- Citation quality and academic rigor
- Completeness of coverage
- Logical coherence and argumentation
- Balance of perspectives
- Depth of analysis in each section
- Quality of evidence and reasoning

Enhance by:
- Identifying and filling knowledge gaps
- Adding critical perspectives
- Strengthening arguments with additional evidence
- Improving clarity and scholarly tone
- Ensuring comprehensive coverage
- Adding nuanced insights
- Connecting ideas across sections
- Highlighting implications

Ensure the report meets highest academic standards.""",
        
        "summarizer": """Create a multi-tiered summary:

1. Abstract (150-200 words): Scholarly overview for academic audiences
2. Executive Summary (500 words): Comprehensive overview highlighting:
   - Research scope and methodology
   - Key findings across all major dimensions
   - Critical insights and novel contributions
   - Practical implications
   - Future directions
   - Actionable recommendations
3. Key Takeaways (10 bullet points): Most critical insights

Target executive, academic, and practitioner audiences simultaneously."""
    }
}


# Research aspect configurations by depth
RESEARCH_ASPECTS_CONFIG: Dict[str, List[str]] = {
    "quick": [
        "core_concepts",
        "current_state"
    ],
    "standard": [
        "core_concepts",
        "current_state",
        "challenges"
    ],
    "comprehensive": [
        "core_concepts",
        "current_state",
        "challenges",
        "applications",
        "future_directions"
    ],
    "exhaustive": [
        "core_concepts",
        "current_state",
        "challenges",
        "applications",
        "future_directions"
    ]
}


def get_depth_config(depth: str) -> Dict[str, Any]:
    """Get configuration for a specific depth level"""
    return DEPTH_CONFIGS.get(depth, DEPTH_CONFIGS["comprehensive"])


def get_depth_prompts(depth: str) -> Dict[str, str]:
    """Get prompts for a specific depth level"""
    return DEPTH_PROMPTS.get(depth, DEPTH_PROMPTS["comprehensive"])


def get_research_aspects(depth: str) -> List[str]:
    """Get research aspects for a specific depth level"""
    return RESEARCH_ASPECTS_CONFIG.get(depth, RESEARCH_ASPECTS_CONFIG["comprehensive"])

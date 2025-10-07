"""
Advanced prompting techniques for research depth enhancement.
Implements Chain-of-Thought and Self-Refinement patterns.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ChainOfThoughtConfig:
    """Configuration for Chain-of-Thought prompting"""
    enabled: bool
    steps: list[str]
    require_reasoning: bool
    
    
class AdvancedPromptingService:
    """Service for advanced AI prompting techniques"""
    
    # Chain-of-Thought prompt template for exhaustive research
    COT_RESEARCH_TEMPLATE = """
For this exhaustive research on "{topic}", think step-by-step:

1. **Identify Key Dimensions**: What are the fundamental aspects of {topic}?
2. **Historical Context**: How did {topic} evolve? What are the key milestones?
3. **Current State**: What is the present state of {topic}? Recent developments?
4. **Future Trends**: Where is {topic} heading? Emerging directions?
5. **Challenges & Opportunities**: What problems exist? What potential exists?
6. **Interconnections**: How do different aspects relate to each other?
7. **Knowledge Gaps**: What isn't well understood? What needs more research?
8. **Synthesis**: How do all these pieces come together into a coherent narrative?

**Provide your reasoning at each step before moving to the next.**

Context:
{context}

Research Query:
{query}
"""

    COT_SYNTHESIS_TEMPLATE = """
Synthesize the following research findings step-by-step:

<RESEARCH_CONTEXT>
{findings}
</RESEARCH_CONTEXT>

**Use this step-by-step process:**

**Step 1: Organize Information**
First, categorize the findings into major themes. What are the main topics covered?

**Step 2: Identify Patterns**
What patterns, trends, or recurring themes emerge across the sources?

**Step 3: Evaluate Evidence**
Which findings are well-supported by multiple sources? Which need more evidence?

**Step 4: Find Connections**
How do different findings relate to each other? What interconnections exist?

**Step 5: Critical Analysis**
What are the strengths and limitations of these findings? Any contradictions?

**Step 6: Synthesize with Citations**
Combine all insights into a comprehensive narrative. Use [1], [2] citation format.

**Show your reasoning at each step, then provide the final synthesis.**
"""

    REFINEMENT_CRITIQUE_TEMPLATE = """
You are an expert research critic. Review the following research draft and provide detailed, constructive criticism:

**Evaluation Criteria:**
1. **Accuracy**: Are claims well-supported by evidence?
2. **Completeness**: Are there missing perspectives or gaps?
3. **Depth**: Is the analysis sufficiently deep for the topic?
4. **Clarity**: Is the writing clear and well-organized?
5. **Citations**: Are sources properly cited and credible?
6. **Balance**: Are multiple perspectives considered?

**For each criterion, provide:**
- Current score (1-10)
- Specific issues identified
- Concrete suggestions for improvement

Research Draft:
{draft}

**Provide detailed, actionable feedback:**
"""

    REFINEMENT_IMPROVEMENT_TEMPLATE = """
Based on the critique below, suggest specific improvements to the research draft:

Original Draft:
{draft}

Critique:
{critique}

**Provide specific, actionable improvements:**
1. What content should be added?
2. What content should be removed or reduced?
3. What sections need reorganization?
4. What claims need better evidence?
5. What perspectives are missing?

**Format as a structured improvement plan.**
"""

    REFINEMENT_REVISION_TEMPLATE = """
Revise the following research draft based on the improvement plan:

Original Draft:
{draft}

Improvement Plan:
{improvements}

**Instructions:**
- Address ALL points in the improvement plan
- Maintain or improve existing quality
- Preserve accurate information
- Enhance depth and clarity
- Add missing perspectives
- Strengthen evidence and citations

**Provide the revised research draft:**
"""

    def get_chain_of_thought_prompt(
        self,
        topic: str,
        query: str,
        context: str = "",
        prompt_type: str = "research"
    ) -> str:
        """
        Get Chain-of-Thought prompt for exhaustive research.
        
        Args:
            topic: Research topic
            query: Specific research query
            context: Additional context
            prompt_type: Type of prompt ('research' or 'synthesis')
            
        Returns:
            Formatted Chain-of-Thought prompt
        """
        if prompt_type == "synthesis":
            return self.COT_SYNTHESIS_TEMPLATE.format(findings=context)
        
        return self.COT_RESEARCH_TEMPLATE.format(
            topic=topic,
            query=query,
            context=context or "No additional context provided."
        )
    
    def get_critique_prompt(self, draft: str) -> str:
        """
        Get prompt for critiquing research draft.
        
        Args:
            draft: Research draft to critique
            
        Returns:
            Formatted critique prompt
        """
        return self.REFINEMENT_CRITIQUE_TEMPLATE.format(draft=draft)
    
    def get_improvement_prompt(self, draft: str, critique: str) -> str:
        """
        Get prompt for suggesting improvements.
        
        Args:
            draft: Original research draft
            critique: Critique of the draft
            
        Returns:
            Formatted improvement suggestion prompt
        """
        return self.REFINEMENT_IMPROVEMENT_TEMPLATE.format(
            draft=draft,
            critique=critique
        )
    
    def get_revision_prompt(self, draft: str, improvements: str) -> str:
        """
        Get prompt for revising draft based on improvements.
        
        Args:
            draft: Original research draft
            improvements: Improvement plan
            
        Returns:
            Formatted revision prompt
        """
        return self.REFINEMENT_REVISION_TEMPLATE.format(
            draft=draft,
            improvements=improvements
        )
    
    def should_use_chain_of_thought(self, depth: str) -> bool:
        """
        Determine if Chain-of-Thought should be used for given depth.
        
        Args:
            depth: Research depth level
            
        Returns:
            True if CoT should be used
        """
        return depth == "exhaustive"
    
    def should_use_refinement(self, depth: str) -> bool:
        """
        Determine if Self-Refinement should be used for given depth.
        
        Args:
            depth: Research depth level
            
        Returns:
            True if refinement should be used
        """
        # Use refinement for comprehensive and exhaustive
        return depth in ["comprehensive", "exhaustive"]
    
    def get_refinement_iterations(self, depth: str) -> int:
        """
        Get number of refinement iterations for given depth.
        
        Args:
            depth: Research depth level
            
        Returns:
            Number of refinement iterations
        """
        refinement_map = {
            "quick": 0,
            "standard": 0,
            "comprehensive": 1,  # One refinement pass
            "exhaustive": 3      # Three refinement passes
        }
        return refinement_map.get(depth, 0)

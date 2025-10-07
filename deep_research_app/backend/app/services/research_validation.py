"""
Research Quality Validation Service

Validates research outputs against depth-specific quality requirements.
Implements Phase 3: Production-Grade Enhancements from RESEARCH_DEPTH_ANALYSIS.md
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re
from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result of research validation"""
    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {}


class SourceQualityTiers:
    """Source quality filtering by research depth"""
    
    TIERS = {
        "quick": ["wikipedia", "news", "blogs", "forums"],
        "standard": ["news", "industry_reports", "academic_blogs", "professional_sites"],
        "comprehensive": ["peer_reviewed", "industry_reports", "expert_blogs", "news", "government"],
        "exhaustive": ["peer_reviewed", "books", "patents", "expert_interviews", "primary_sources", "government", "industry_reports"]
    }
    
    QUALITY_SCORES = {
        "peer_reviewed": 1.0,
        "books": 0.95,
        "patents": 0.9,
        "government": 0.85,
        "industry_reports": 0.8,
        "expert_interviews": 0.75,
        "primary_sources": 0.75,
        "professional_sites": 0.7,
        "expert_blogs": 0.65,
        "academic_blogs": 0.6,
        "news": 0.5,
        "blogs": 0.3,
        "wikipedia": 0.4,
        "forums": 0.2
    }
    
    @classmethod
    def get_allowed_sources(cls, depth: str) -> List[str]:
        """Get allowed source types for a given depth"""
        return cls.TIERS.get(depth, cls.TIERS["comprehensive"])
    
    @classmethod
    def get_source_quality_score(cls, source_type: str) -> float:
        """Get quality score for a source type"""
        return cls.QUALITY_SCORES.get(source_type, 0.5)


class CitationRequirements:
    """Citation quality requirements by depth"""
    
    REQUIREMENTS = {
        "quick": {
            "min_sources": 3,
            "require_dates": False,
            "require_authors": False,
            "require_urls": True,
            "prefer_academic": False,
            "verify_credibility": False
        },
        "standard": {
            "min_sources": 8,
            "require_dates": True,
            "require_authors": False,
            "require_urls": True,
            "prefer_academic": False,
            "verify_credibility": False
        },
        "comprehensive": {
            "min_sources": 15,
            "require_dates": True,
            "require_authors": True,
            "require_urls": True,
            "prefer_academic": True,
            "min_academic_ratio": 0.3,  # 30% academic sources
            "verify_credibility": True
        },
        "exhaustive": {
            "min_sources": 25,
            "require_dates": True,
            "require_authors": True,
            "require_urls": True,
            "require_academic": True,
            "min_academic_ratio": 0.5,  # 50% academic sources
            "require_primary_sources": True,
            "min_primary_ratio": 0.2,  # 20% primary sources
            "verify_credibility": True,
            "require_diverse_sources": True  # Multiple domains/publishers
        }
    }
    
    @classmethod
    def get_requirements(cls, depth: str) -> Dict[str, Any]:
        """Get citation requirements for a given depth"""
        return cls.REQUIREMENTS.get(depth, cls.REQUIREMENTS["comprehensive"])


class ReportStructures:
    """Expected report structures by depth"""
    
    STRUCTURES = {
        "quick": [
            "Executive Summary",
            "Key Findings",
            "Conclusion"
        ],
        "standard": [
            "Executive Summary",
            "Introduction",
            "Main Analysis",
            "Key Insights",
            "Conclusion",
            "References"
        ],
        "comprehensive": [
            "Executive Summary",
            "Introduction",
            "Background",
            "Methodology",
            "Detailed Analysis",
            "Critical Evaluation",
            "Implications",
            "Recommendations",
            "Conclusion",
            "References",
            "Appendices"
        ],
        "exhaustive": [
            "Abstract",
            "Executive Summary",
            "Introduction",
            "Context",
            "Literature Review",
            "Methodology",
            "Comprehensive Analysis",
            "Multi-Perspective Evaluation",
            "Critical Discussion",
            "Future Directions",
            "Limitations",
            "Practical Recommendations",
            "Conclusion",
            "References",
            "Appendices",
            "Glossary"
        ]
    }
    
    @classmethod
    def get_required_sections(cls, depth: str) -> List[str]:
        """Get required sections for a given depth"""
        return cls.STRUCTURES.get(depth, cls.STRUCTURES["comprehensive"])


class ResearchValidator:
    """Validates research output quality"""
    
    def __init__(self):
        self.source_quality = SourceQualityTiers()
        self.citation_reqs = CitationRequirements()
        self.structures = ReportStructures()
    
    async def validate_research_quality(
        self,
        report: str,
        depth: str,
        sources: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Comprehensive validation of research quality
        
        Args:
            report: The generated research report
            depth: Research depth level (quick/standard/comprehensive/exhaustive)
            sources: List of sources used in research
            metadata: Additional metadata about the research
            
        Returns:
            ValidationResult with pass/fail, score, issues, and metrics
        """
        issues = []
        warnings = []
        metrics = {}
        
        # 1. Word count validation
        word_count_result = self._check_word_count(report, depth)
        metrics["word_count"] = word_count_result["count"]
        metrics["word_count_target"] = word_count_result["target"]
        if not word_count_result["passed"]:
            issues.append(word_count_result["message"])
        
        # 2. Source count validation
        source_count_result = self._check_source_count(sources, depth)
        metrics["source_count"] = source_count_result["count"]
        metrics["source_count_target"] = source_count_result["target"]
        if not source_count_result["passed"]:
            issues.append(source_count_result["message"])
        
        # 3. Structure validation
        structure_result = self._verify_structure(report, depth)
        metrics["structure_completeness"] = structure_result["completeness"]
        metrics["missing_sections"] = structure_result["missing"]
        if not structure_result["passed"]:
            warnings.append(structure_result["message"])
        
        # 4. Citation quality validation
        citation_result = self._verify_citations(report, sources, depth)
        metrics["citation_quality"] = citation_result["quality_score"]
        metrics["citation_issues"] = citation_result["issues"]
        if not citation_result["passed"]:
            for issue in citation_result["issues"]:
                warnings.append(issue)
        
        # 5. Source quality assessment
        source_quality_result = self._assess_source_quality(sources, depth)
        metrics["source_quality_score"] = source_quality_result["score"]
        metrics["source_distribution"] = source_quality_result["distribution"]
        if not source_quality_result["passed"]:
            warnings.append(source_quality_result["message"])
        
        # 6. Depth appropriateness
        depth_result = self._assess_analysis_depth(report, depth)
        metrics["analysis_depth_score"] = depth_result["score"]
        if not depth_result["passed"]:
            warnings.append(depth_result["message"])
        
        # Calculate overall score
        weights = {
            "word_count": 0.2,
            "source_count": 0.15,
            "structure": 0.15,
            "citations": 0.2,
            "source_quality": 0.15,
            "depth": 0.15
        }
        
        overall_score = (
            word_count_result["score"] * weights["word_count"] +
            source_count_result["score"] * weights["source_count"] +
            structure_result["score"] * weights["structure"] +
            citation_result["score"] * weights["citations"] +
            source_quality_result["score"] * weights["source_quality"] +
            depth_result["score"] * weights["depth"]
        )
        
        # Determine if validation passed
        # Critical issues (word count, source count) must pass
        critical_passed = word_count_result["passed"] and source_count_result["passed"]
        # Overall score must be above threshold
        score_threshold = 0.7 if depth in ["comprehensive", "exhaustive"] else 0.6
        score_passed = overall_score >= score_threshold
        
        passed = critical_passed and score_passed
        
        return ValidationResult(
            passed=passed,
            score=overall_score,
            issues=issues,
            warnings=warnings,
            metrics=metrics
        )
    
    def _check_word_count(self, report: str, depth: str) -> Dict[str, Any]:
        """Check if word count meets depth requirements"""
        from ..config.research_config import DEPTH_CONFIGS
        
        word_count = len(report.split())
        config = DEPTH_CONFIGS.get(depth, DEPTH_CONFIGS["comprehensive"])
        
        min_words = config["report_min_words"]
        max_words = config["report_max_words"]
        
        if word_count < min_words:
            return {
                "passed": False,
                "score": min(word_count / min_words, 1.0),
                "count": word_count,
                "target": f"{min_words}-{max_words}",
                "message": f"Word count too low: {word_count} words (minimum: {min_words})"
            }
        elif word_count > max_words * 1.2:  # Allow 20% buffer
            return {
                "passed": True,  # Don't fail for too many words
                "score": 1.0,
                "count": word_count,
                "target": f"{min_words}-{max_words}",
                "message": f"Word count exceeded target: {word_count} words (target: {max_words})"
            }
        else:
            return {
                "passed": True,
                "score": 1.0,
                "count": word_count,
                "target": f"{min_words}-{max_words}",
                "message": "Word count within target range"
            }
    
    def _check_source_count(self, sources: List[Dict], depth: str) -> Dict[str, Any]:
        """Check if source count meets depth requirements"""
        requirements = self.citation_reqs.get_requirements(depth)
        min_sources = requirements["min_sources"]
        source_count = len(sources)
        
        if source_count < min_sources:
            return {
                "passed": False,
                "score": min(source_count / min_sources, 1.0),
                "count": source_count,
                "target": min_sources,
                "message": f"Insufficient sources: {source_count} (minimum: {min_sources})"
            }
        else:
            return {
                "passed": True,
                "score": 1.0,
                "count": source_count,
                "target": min_sources,
                "message": f"Sufficient sources: {source_count}"
            }
    
    def _verify_structure(self, report: str, depth: str) -> Dict[str, Any]:
        """Verify report has required structural sections"""
        required_sections = self.structures.get_required_sections(depth)
        report_lower = report.lower()
        
        found_sections = []
        missing_sections = []
        
        for section in required_sections:
            # Look for section headers (flexible matching)
            section_patterns = [
                f"#{1,3}\\s*{section}",  # Markdown headers
                f"\\*\\*{section}\\*\\*",  # Bold text
                f"{section}:",  # Colon after section name
                f"{section}\\n",  # Section name on its own line
            ]
            
            found = any(re.search(pattern, report, re.IGNORECASE) for pattern in section_patterns)
            
            if found:
                found_sections.append(section)
            else:
                missing_sections.append(section)
        
        completeness = len(found_sections) / len(required_sections) if required_sections else 1.0
        
        # For quick/standard, 50% completeness is acceptable
        # For comprehensive/exhaustive, require 70%
        threshold = 0.7 if depth in ["comprehensive", "exhaustive"] else 0.5
        passed = completeness >= threshold
        
        return {
            "passed": passed,
            "score": completeness,
            "completeness": completeness,
            "found": found_sections,
            "missing": missing_sections,
            "message": f"Structure completeness: {completeness:.1%} (missing: {', '.join(missing_sections[:3])})" if missing_sections else "Structure complete"
        }
    
    def _verify_citations(self, report: str, sources: List[Dict], depth: str) -> Dict[str, Any]:
        """Verify citation quality meets requirements"""
        requirements = self.citation_reqs.get_requirements(depth)
        issues = []
        quality_score = 1.0
        
        # Check if sources have required metadata
        if requirements.get("require_dates"):
            sources_with_dates = sum(1 for s in sources if s.get("published_date"))
            if sources_with_dates < len(sources) * 0.7:  # 70% threshold
                issues.append(f"Only {sources_with_dates}/{len(sources)} sources have dates")
                quality_score -= 0.2
        
        if requirements.get("require_authors"):
            sources_with_authors = sum(1 for s in sources if s.get("author"))
            if sources_with_authors < len(sources) * 0.5:  # 50% threshold
                issues.append(f"Only {sources_with_authors}/{len(sources)} sources have authors")
                quality_score -= 0.2
        
        # Check academic source ratio
        if requirements.get("min_academic_ratio"):
            academic_sources = sum(1 for s in sources if self._is_academic_source(s))
            academic_ratio = academic_sources / len(sources) if sources else 0
            if academic_ratio < requirements["min_academic_ratio"]:
                issues.append(f"Academic sources: {academic_ratio:.1%} (target: {requirements['min_academic_ratio']:.1%})")
                quality_score -= 0.3
        
        # Check primary source ratio (for exhaustive)
        if requirements.get("min_primary_ratio"):
            primary_sources = sum(1 for s in sources if self._is_primary_source(s))
            primary_ratio = primary_sources / len(sources) if sources else 0
            if primary_ratio < requirements["min_primary_ratio"]:
                issues.append(f"Primary sources: {primary_ratio:.1%} (target: {requirements['min_primary_ratio']:.1%})")
                quality_score -= 0.2
        
        # Check source diversity (for exhaustive)
        if requirements.get("require_diverse_sources"):
            domains = set(self._extract_domain(s.get("url", "")) for s in sources if s.get("url"))
            if len(domains) < len(sources) * 0.5:  # At least 50% unique domains
                issues.append(f"Limited source diversity: {len(domains)} unique domains from {len(sources)} sources")
                quality_score -= 0.1
        
        quality_score = max(0.0, quality_score)
        passed = quality_score >= 0.7
        
        return {
            "passed": passed,
            "score": quality_score,
            "quality_score": quality_score,
            "issues": issues
        }
    
    def _assess_source_quality(self, sources: List[Dict], depth: str) -> Dict[str, Any]:
        """Assess overall source quality"""
        if not sources:
            return {
                "passed": False,
                "score": 0.0,
                "distribution": {},
                "message": "No sources provided"
            }
        
        # Calculate average source quality score
        total_score = 0.0
        distribution = {}
        
        for source in sources:
            source_type = self._classify_source(source)
            quality_score = self.source_quality.get_source_quality_score(source_type)
            total_score += quality_score
            distribution[source_type] = distribution.get(source_type, 0) + 1
        
        avg_score = total_score / len(sources)
        
        # Set thresholds by depth
        thresholds = {
            "quick": 0.4,
            "standard": 0.5,
            "comprehensive": 0.6,
            "exhaustive": 0.7
        }
        
        threshold = thresholds.get(depth, 0.5)
        passed = avg_score >= threshold
        
        return {
            "passed": passed,
            "score": avg_score,
            "distribution": distribution,
            "message": f"Average source quality: {avg_score:.2f} (threshold: {threshold})"
        }
    
    def _assess_analysis_depth(self, report: str, depth: str) -> Dict[str, Any]:
        """Assess if analysis depth is appropriate"""
        # Simple heuristics for depth assessment
        word_count = len(report.split())
        
        # Count evidence of deep analysis
        analysis_markers = [
            "however", "moreover", "furthermore", "consequently",
            "therefore", "although", "nevertheless", "alternatively",
            "in contrast", "on the other hand", "specifically",
            "for example", "for instance", "notably", "significantly"
        ]
        
        report_lower = report.lower()
        analysis_count = sum(report_lower.count(marker) for marker in analysis_markers)
        
        # Count questions (indicates critical thinking)
        question_count = report.count("?")
        
        # Count citations/references
        citation_count = report.count("[") + report.count("(")
        
        # Score based on markers per 1000 words
        markers_per_1k = (analysis_count * 1000) / word_count if word_count > 0 else 0
        
        # Thresholds by depth
        thresholds = {
            "quick": 5,
            "standard": 10,
            "comprehensive": 15,
            "exhaustive": 20
        }
        
        threshold = thresholds.get(depth, 10)
        score = min(markers_per_1k / threshold, 1.0)
        passed = score >= 0.6
        
        return {
            "passed": passed,
            "score": score,
            "markers_per_1k": markers_per_1k,
            "message": f"Analysis depth markers: {markers_per_1k:.1f} per 1000 words (target: {threshold})"
        }
    
    def _is_academic_source(self, source: Dict) -> bool:
        """Check if source is academic"""
        url = source.get("url", "").lower()
        title = source.get("title", "").lower()
        
        academic_indicators = [
            "arxiv.org", "ieee.org", "acm.org", "springer.com",
            "sciencedirect.com", "nature.com", "science.org",
            ".edu", "academic", "journal", "proceedings",
            "doi.org", "pubmed"
        ]
        
        return any(indicator in url or indicator in title for indicator in academic_indicators)
    
    def _is_primary_source(self, source: Dict) -> bool:
        """Check if source is a primary source"""
        url = source.get("url", "").lower()
        title = source.get("title", "").lower()
        
        primary_indicators = [
            "whitepaper", "technical report", "patent",
            "official documentation", "government",
            ".gov", "research paper", "study"
        ]
        
        return any(indicator in url or indicator in title for indicator in primary_indicators)
    
    def _classify_source(self, source: Dict) -> str:
        """Classify source type"""
        url = source.get("url", "").lower()
        
        if self._is_academic_source(source):
            return "peer_reviewed"
        elif ".gov" in url:
            return "government"
        elif "patent" in url:
            return "patents"
        elif any(x in url for x in ["reuters", "bloomberg", "wsj", "ft.com"]):
            return "news"
        elif "wikipedia" in url:
            return "wikipedia"
        elif "blog" in url or "medium.com" in url:
            return "blogs"
        else:
            return "professional_sites"
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        import re
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else ""


# Singleton instance
_validator_instance = None

def get_validator() -> ResearchValidator:
    """Get singleton validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ResearchValidator()
    return _validator_instance

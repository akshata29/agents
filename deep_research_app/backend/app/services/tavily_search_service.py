"""
Tavily Search Service for Deep Research application.

Provides search capabilities using Tavily API to retrieve web search results
and images for research queries.
"""

import aiohttp
import structlog
from typing import Dict, List, Optional, Any

logger = structlog.get_logger(__name__)


class Source:
    """Represents a text search result source"""
    
    def __init__(self, title: str, content: str, url: str):
        self.title = title
        self.content = content
        self.url = url


class ImageSource:
    """Represents an image search result"""
    
    def __init__(self, url: str, description: Optional[str] = None):
        self.url = url
        self.description = description


class TavilySearchService:
    """Service for performing web searches using Tavily API"""
    
    MAX_QUERY_LENGTH = 400  # Tavily API limit
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"
    
    def _truncate_query(self, query: str) -> str:
        """
        Truncate query to fit within Tavily's 400-character limit.
        
        Args:
            query: Original query string
            
        Returns:
            Truncated query that fits within API limits
        """
        if len(query) <= self.MAX_QUERY_LENGTH:
            return query
        
        # Try to truncate at word boundaries when possible
        truncated = query[:self.MAX_QUERY_LENGTH]
        
        # Find the last space to avoid cutting off mid-word
        last_space = truncated.rfind(' ')
        if last_space > self.MAX_QUERY_LENGTH * 0.8:  # Only if we don't lose too much
            truncated = truncated[:last_space]
        
        logger.warning(
            "Query truncated for Tavily API",
            original_length=len(query),
            truncated_length=len(truncated),
            original_query=query[:100] + "..." if len(query) > 100 else query
        )
        
        return truncated
    
    async def search(
        self, 
        query: str, 
        max_results: int = 5,
        search_depth: str = "advanced",
        topic: str = "general",
        include_images: bool = True
    ) -> Dict[str, Any]:
        """
        Perform a web search using Tavily API
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            search_depth: Search depth ('basic' or 'advanced')
            topic: Search topic/category
            include_images: Whether to include image results
            
        Returns:
            Dictionary containing search results with 'sources' and 'images' keys
        """
        if not self.api_key:
            logger.error("Tavily API key not configured")
            raise ValueError("Tavily API key is required but not configured")
            
        try:
            # Truncate query to fit within API limits
            truncated_query = self._truncate_query(query)
            
            # Prepare search parameters
            search_params = {
                "query": truncated_query.replace("\\", "").replace('"', ""),
                "search_depth": search_depth,
                "topic": topic,
                "max_results": max_results,
                "include_images": include_images,
                "include_image_descriptions": True,
                "include_answer": False,
                "include_raw_content": True
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/search",
                    json=search_params,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            "Tavily API request failed",
                            status=response.status,
                            error=error_text
                        )
                        raise Exception(f"Tavily API error ({response.status}): {error_text}")
                    
                    data = await response.json()
                    
                    # Parse results
                    results = data.get("results", [])
                    images = data.get("images", [])
                    
                    # Convert to our internal format
                    sources = []
                    for result in results:
                        if result.get("content") and result.get("url"):
                            # Use raw_content if available, but limit its size
                            raw_content = result.get("raw_content", "")
                            regular_content = result.get("content", "")
                            
                            # Choose content source and apply length limits
                            if raw_content and len(raw_content) <= 80000:  # 80KB limit per source
                                content = raw_content
                            elif regular_content and len(regular_content) <= 80000:
                                content = regular_content
                            elif raw_content:
                                # Truncate raw content at sentence boundary
                                truncated = raw_content[:80000]
                                last_period = truncated.rfind('.')
                                if last_period > 72000:  # Keep if we don't lose too much
                                    content = truncated[:last_period + 1]
                                else:
                                    content = truncated + "..."
                                logger.debug(
                                    "Raw content truncated for source",
                                    url=result.get("url", ""),
                                    original_length=len(raw_content),
                                    truncated_length=len(content)
                                )
                            else:
                                # Truncate regular content
                                truncated = regular_content[:80000]
                                last_period = truncated.rfind('.')
                                if last_period > 72000:
                                    content = truncated[:last_period + 1]
                                else:
                                    content = truncated + "..."
                                logger.debug(
                                    "Regular content truncated for source",
                                    url=result.get("url", ""),
                                    original_length=len(regular_content),
                                    truncated_length=len(content)
                                )
                            
                            source = Source(
                                title=result.get("title", ""),
                                content=content,
                                url=result.get("url", "")
                            )
                            sources.append(source)
                    
                    # Convert images
                    image_sources = []
                    for image in images:
                        if image.get("url"):
                            image_source = ImageSource(
                                url=image.get("url", ""),
                                description=image.get("description", "")
                            )
                            image_sources.append(image_source)
                    
                    logger.info(
                        "Tavily search completed",
                        original_query=query[:100] + "..." if len(query) > 100 else query,
                        truncated_query=truncated_query[:100] + "..." if len(truncated_query) > 100 else truncated_query,
                        results_count=len(sources),
                        images_count=len(image_sources)
                    )
                    
                    return {
                        "sources": sources,
                        "images": image_sources
                    }
                    
        except Exception as e:
            logger.error("Tavily search failed", query=query, error=str(e))
            raise Exception(f"Tavily search failed: {str(e)}")
    
    def format_context_for_llm(self, sources: List[Source], max_total_chars: int = 240000) -> str:
        """
        Format search results as context for LLM processing with content length limits
        
        Args:
            sources: List of search result sources
            max_total_chars: Maximum total characters for all content combined
            
        Returns:
            Formatted context string with citations, truncated if necessary
        """
        if not sources:
            return "No search results available."
        
        context_parts = []
        total_chars = 0
        max_chars_per_source = max_total_chars // max(len(sources), 1)  # Distribute evenly
        
        for idx, source in enumerate(sources, 1):
            # Calculate remaining space
            remaining_chars = max_total_chars - total_chars
            if remaining_chars <= 0:
                logger.warning(
                    "Context truncated - reached maximum character limit",
                    sources_processed=idx-1,
                    total_sources=len(sources),
                    total_chars=total_chars
                )
                break
            
            # Limit this source's content to available space or per-source limit
            source_char_limit = min(max_chars_per_source, remaining_chars - 100)  # Reserve space for metadata
            
            # Truncate content if necessary
            content = source.content
            if len(content) > source_char_limit:
                # Try to truncate at sentence boundary
                truncated = content[:source_char_limit]
                last_period = truncated.rfind('.')
                last_newline = truncated.rfind('\n')
                last_boundary = max(last_period, last_newline)
                
                if last_boundary > source_char_limit * 0.7:  # Only if we don't lose too much
                    content = truncated[:last_boundary + 1]
                else:
                    content = truncated + "..."
                
                logger.debug(
                    "Source content truncated",
                    source_index=idx,
                    original_length=len(source.content),
                    truncated_length=len(content)
                )
            
            # Format with citation number
            source_text = f"[{idx}] {source.title}\nURL: {source.url}\n{content}\n"
            context_parts.append(source_text)
            total_chars += len(source_text)
        
        return "\n".join(context_parts)
    
    async def search_and_format(
        self, 
        query: str, 
        research_goal: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Perform search and format results for LLM consumption
        
        Args:
            query: The search query
            research_goal: The research goal/objective
            max_results: Maximum number of results
            
        Returns:
            Dictionary with formatted context and metadata
        """
        search_results = await self.search(query, max_results=max_results)
        
        context = self.format_context_for_llm(search_results["sources"])
        
        return {
            "query": query,
            "research_goal": research_goal,
            "context": context,
            "sources": search_results["sources"],
            "images": search_results["images"],
            "sources_count": len(search_results["sources"])
        }

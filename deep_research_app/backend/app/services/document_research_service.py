"""
Document Research Service for Deep Research Application

Combines document content with web search results to create hybrid research context.
Manages document selection, content retrieval, and source attribution.
"""

import structlog
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..models.file_models import DocumentSource, ResearchContext, FileMetadata
from ..services.file_handler import FileHandler
from ..services.tavily_search_service import TavilySearchService, Source

logger = structlog.get_logger(__name__)


class DocumentResearchService:
    """
    Service for managing document-enhanced research.
    
    Responsibilities:
    - Retrieve document content
    - Combine document and web sources
    - Attribute sources properly
    - Create hybrid research context
    """
    
    def __init__(
        self,
        file_handler: FileHandler,
        tavily_service: TavilySearchService
    ):
        """Initialize document research service."""
        self.file_handler = file_handler
        self.tavily_service = tavily_service
        logger.info("Document research service initialized")
    
    async def get_available_documents(
        self,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of available processed documents for selection.
        
        Args:
            user_id: Optional user ID filter
            
        Returns:
            List of document summaries for UI dropdown
        """
        documents = await self.file_handler.list_documents(user_id=user_id)
        
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "upload_date": doc.upload_timestamp.isoformat(),
                "word_count": doc.metadata.get("word_count", 0),
                "page_count": doc.metadata.get("page_count", 0)
            }
            for doc in documents
        ]
    
    async def create_research_context(
        self,
        query: str,
        selected_document_ids: List[str],
        max_web_results: int = 5,
        search_depth: str = "advanced"
    ) -> ResearchContext:
        """
        Create hybrid research context combining documents and web search.
        
        Args:
            query: Research query
            selected_document_ids: IDs of documents to include
            max_web_results: Maximum web search results
            search_depth: Tavily search depth
            
        Returns:
            ResearchContext with combined sources
        """
        logger.info(
            "Creating research context",
            query=query,
            document_count=len(selected_document_ids)
        )
        
        # Gather document sources
        document_sources = []
        document_context_parts = []
        
        for doc_id in selected_document_ids:
            doc_source = await self._get_document_source(doc_id, query)
            if doc_source:
                document_sources.extend(doc_source["sources"])
                document_context_parts.append(doc_source["context"])
        
        # Perform web search
        web_search_result = await self.tavily_service.search(
            query=query,
            max_results=max_web_results,
            search_depth=search_depth
        )
        
        # Convert web sources to dictionary format
        web_sources = [
            {
                "title": source.title,
                "content": source.content,
                "url": source.url,
                "source_type": "web"
            }
            for source in web_search_result.get("sources", [])
        ]
        
        # Combine contexts
        combined_parts = []
        
        # Add document context first (prioritize uploaded documents)
        if document_context_parts:
            combined_parts.append("## Document Sources\n")
            combined_parts.extend(document_context_parts)
        
        # Add web search context
        if web_sources:
            combined_parts.append("\n## Web Sources\n")
            for source in web_sources:
                combined_parts.append(
                    f"### {source['title']}\n"
                    f"URL: {source['url']}\n"
                    f"{source['content']}\n"
                )
        
        combined_context = "\n".join(combined_parts)
        
        logger.info(
            "Research context created",
            document_sources=len(document_sources),
            web_sources=len(web_sources),
            combined_length=len(combined_context)
        )
        
        return ResearchContext(
            query=query,
            web_sources=web_sources,
            document_sources=document_sources,
            combined_context=combined_context
        )
    
    async def _get_document_source(
        self,
        file_id: str,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve and format document content as a research source.
        
        Args:
            file_id: File identifier
            query: Research query (for relevance scoring)
            
        Returns:
            Dictionary with sources and formatted context
        """
        try:
            # Get document metadata
            metadata = await self.file_handler.get_metadata(file_id)
            if not metadata:
                logger.warning("Document metadata not found", file_id=file_id)
                return None
            
            # Get markdown content
            markdown_content = await self.file_handler.get_document_content(file_id)
            if not markdown_content:
                logger.warning("Document content not found", file_id=file_id)
                return None
            
            # For now, use entire document as context
            # In future, could implement semantic chunking and relevance scoring
            content_preview = self._create_content_preview(markdown_content)
            
            # Create document source
            source = DocumentSource(
                file_id=file_id,
                filename=metadata.filename,
                content_excerpt=content_preview,
                page_number=None,
                relevance_score=1.0
            )
            
            # Format context
            context = (
                f"### {metadata.filename}\n"
                f"Type: {metadata.file_type.value.upper()} | "
                f"Pages: {metadata.metadata.get('page_count', 'N/A')} | "
                f"Words: {metadata.metadata.get('word_count', 'N/A')}\n\n"
                f"{markdown_content}\n"
            )
            
            return {
                "sources": [source],
                "context": context
            }
            
        except Exception as e:
            logger.error(
                "Failed to get document source",
                error=str(e),
                file_id=file_id
            )
            return None
    
    def _create_content_preview(
        self,
        content: str,
        max_length: int = 500
    ) -> str:
        """
        Create a preview excerpt from document content.
        
        Args:
            content: Full document content
            max_length: Maximum preview length
            
        Returns:
            Preview excerpt
        """
        if len(content) <= max_length:
            return content
        
        # Find a good breaking point (end of sentence)
        preview = content[:max_length]
        last_period = preview.rfind('.')
        
        if last_period > max_length * 0.7:  # Only if we don't lose too much
            preview = preview[:last_period + 1]
        
        return preview + "..."
    
    async def get_document_stats(
        self,
        document_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for selected documents.
        
        Args:
            document_ids: List of document IDs
            
        Returns:
            Dictionary with aggregated stats
        """
        total_pages = 0
        total_words = 0
        total_size = 0
        file_types = {}
        
        for doc_id in document_ids:
            metadata = await self.file_handler.get_metadata(doc_id)
            if metadata:
                total_pages += metadata.metadata.get("page_count", 0)
                total_words += metadata.metadata.get("word_count", 0)
                total_size += metadata.file_size
                
                file_type = metadata.file_type.value
                file_types[file_type] = file_types.get(file_type, 0) + 1
        
        return {
            "document_count": len(document_ids),
            "total_pages": total_pages,
            "total_words": total_words,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types
        }

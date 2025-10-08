"""
CosmosDB Memory Store for Advisor Productivity Application

Stores advisor-client conversation sessions in Cosmos DB with session_id as partition key.
Supports Azure AD authentication via service principal or managed identity.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from azure.cosmos.aio import CosmosClient
from azure.cosmos.partition_key import PartitionKey
from azure.identity.aio import (
    DefaultAzureCredential,
    ClientSecretCredential as AsyncClientSecretCredential
)
import structlog

from ..models.persistence_models import AdvisorSession, SessionSearchResult

logger = structlog.get_logger(__name__)


class CosmosMemoryStore:
    """
    CosmosDB-backed memory store for advisor productivity sessions.
    
    Uses session_id as partition key for efficient querying.
    Supports authentication via service principal or managed identity.
    """
    
    def __init__(
        self,
        endpoint: str,
        database_name: str,
        container_name: str,
        user_id: Optional[str] = "default_advisor",
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize Cosmos DB memory store.
        
        Args:
            endpoint: Cosmos DB endpoint URL
            database_name: Database name
            container_name: Container name
            user_id: Optional default user ID for operations
            tenant_id: Azure AD tenant ID (for service principal auth)
            client_id: Service principal client ID
            client_secret: Service principal client secret
        """
        self.endpoint = endpoint
        self.database_name = database_name
        self.container_name = container_name
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        
        self._client: Optional[CosmosClient] = None
        self._database = None
        self._container = None
        self._initialized = asyncio.Event()
    
    async def initialize(self) -> None:
        """Initialize CosmosDB client and container."""
        if self._initialized.is_set():
            return
        
        try:
            # Create client with appropriate credential
            if self.tenant_id and self.client_id and self.client_secret:
                # Use AsyncClientSecretCredential for service principal auth
                credential = AsyncClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                logger.info("Using ClientSecretCredential for CosmosDB")
            else:
                # Fallback to DefaultAzureCredential (uses managed identity, Azure CLI, etc.)
                credential = DefaultAzureCredential()
                logger.info("Using DefaultAzureCredential for CosmosDB")
            
            self._client = CosmosClient(self.endpoint, credential=credential)
            
            # Get database and container
            self._database = self._client.get_database_client(self.database_name)
            
            # Create container if it doesn't exist
            self._container = await self._database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/session_id"),
                offer_throughput=400
            )
            
            logger.info(
                "CosmosDB initialized successfully",
                endpoint=self.endpoint,
                database=self.database_name,
                container=self.container_name
            )
            
            self._initialized.set()
            
        except Exception as e:
            logger.error(f"Failed to initialize CosmosDB", error=str(e))
            raise
    
    async def ensure_initialized(self) -> None:
        """Ensure the store is initialized."""
        if not self._initialized.is_set():
            await self.initialize()
    
    async def close(self) -> None:
        """Close the Cosmos DB client."""
        if self._client:
            await self._client.close()
            logger.info("CosmosDB client closed")
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    async def create_session(self, session: AdvisorSession) -> AdvisorSession:
        """Create a new advisor session."""
        await self.ensure_initialized()
        
        try:
            session_dict = session.dict()
            # Ensure datetime objects are serialized
            session_dict["created_at"] = session.created_at.isoformat()
            if session.started_at:
                session_dict["started_at"] = session.started_at.isoformat()
            if session.ended_at:
                session_dict["ended_at"] = session.ended_at.isoformat()
            
            await self._container.create_item(body=session_dict)
            logger.info(
                "Advisor session created",
                session_id=session.session_id,
                user_id=session.user_id
            )
            return session
            
        except Exception as e:
            logger.error(
                "Failed to create session",
                error=str(e),
                session_id=session.session_id
            )
            raise
    
    async def get_session(self, session_id: str) -> Optional[AdvisorSession]:
        """Retrieve a session by ID."""
        await self.ensure_initialized()
        
        try:
            query = "SELECT * FROM c WHERE c.session_id=@session_id AND c.data_type='advisor_session'"
            parameters = [{"name": "@session_id", "value": session_id}]
            
            items = self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )
            
            async for item in items:
                # Parse datetime strings back to datetime objects
                if "created_at" in item and isinstance(item["created_at"], str):
                    item["created_at"] = datetime.fromisoformat(item["created_at"])
                if "started_at" in item and item["started_at"] and isinstance(item["started_at"], str):
                    item["started_at"] = datetime.fromisoformat(item["started_at"])
                if "ended_at" in item and item["ended_at"] and isinstance(item["ended_at"], str):
                    item["ended_at"] = datetime.fromisoformat(item["ended_at"])
                return AdvisorSession(**item)
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get session",
                error=str(e),
                session_id=session_id
            )
            return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Partially update a session with given fields."""
        await self.ensure_initialized()
        
        try:
            # Get existing session
            session = await self.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            # Convert to dict for upsert
            session_dict = session.dict()
            session_dict["created_at"] = session.created_at.isoformat()
            if session.started_at:
                session_dict["started_at"] = session.started_at.isoformat()
            if session.ended_at:
                session_dict["ended_at"] = session.ended_at.isoformat()
            
            await self._container.upsert_item(body=session_dict)
            logger.debug(
                "Session updated",
                session_id=session_id,
                updates=list(updates.keys())
            )
            
        except Exception as e:
            logger.error(
                "Failed to update session",
                error=str(e),
                session_id=session_id
            )
            raise
    
    async def save_session(self, session: AdvisorSession) -> AdvisorSession:
        """
        Save (upsert) a complete session.
        Creates if new, updates if exists.
        """
        await self.ensure_initialized()
        
        try:
            session_dict = session.dict()
            # Serialize datetime objects
            session_dict["created_at"] = session.created_at.isoformat()
            if session.started_at:
                session_dict["started_at"] = session.started_at.isoformat()
            if session.ended_at:
                session_dict["ended_at"] = session.ended_at.isoformat()
            
            await self._container.upsert_item(body=session_dict)
            logger.info(
                "Session saved successfully",
                session_id=session.session_id,
                status=session.status
            )
            return session
            
        except Exception as e:
            logger.error(
                "Failed to save session",
                error=str(e),
                session_id=session.session_id
            )
            raise
    
    async def get_all_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[SessionSearchResult]:
        """
        Retrieve all sessions, optionally filtered by user and status.
        Returns lightweight SessionSearchResult objects.
        """
        await self.ensure_initialized()
        
        try:
            query_parts = ["SELECT * FROM c WHERE c.data_type='advisor_session'"]
            parameters = []
            
            if user_id:
                query_parts.append("AND c.user_id=@user_id")
                parameters.append({"name": "@user_id", "value": user_id})
            
            if status:
                query_parts.append("AND c.status=@status")
                parameters.append({"name": "@status", "value": status})
            
            query_parts.append(f"ORDER BY c.created_at DESC OFFSET 0 LIMIT {limit}")
            query = " ".join(query_parts)
            
            items = []
            # Cross-partition query (no partition_key specified)
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    # Parse datetime strings
                    if "created_at" in item and isinstance(item["created_at"], str):
                        item["created_at"] = datetime.fromisoformat(item["created_at"])
                    if "ended_at" in item and item["ended_at"] and isinstance(item["ended_at"], str):
                        item["ended_at"] = datetime.fromisoformat(item["ended_at"])
                    
                    # Create lightweight search result
                    search_result = SessionSearchResult(
                        session_id=item["session_id"],
                        created_at=item["created_at"],
                        ended_at=item.get("ended_at"),
                        duration_seconds=item.get("duration_seconds"),
                        status=item.get("status", "unknown"),
                        client_name=item.get("client_name"),
                        advisor_name=item.get("advisor_name"),
                        exchange_count=item.get("exchange_count", 0),
                        investment_readiness_score=item.get("investment_readiness_score"),
                        key_topics=item.get("key_topics", [])
                    )
                    items.append(search_result)
                except Exception as e:
                    logger.warning(f"Failed to parse session: {e}")
                    continue
            
            logger.info(
                f"Retrieved {len(items)} sessions",
                user_id=user_id if user_id else "all",
                status=status if status else "all"
            )
            return items
            
        except Exception as e:
            logger.error(f"Failed to get sessions", error=str(e))
            return []
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        await self.ensure_initialized()
        
        try:
            # Find the session document
            query = "SELECT c.id FROM c WHERE c.session_id=@session_id AND c.data_type='advisor_session'"
            parameters = [{"name": "@session_id", "value": session_id}]
            
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )
            
            deleted = False
            async for item in query_iter:
                try:
                    await self._container.delete_item(
                        item=item["id"],
                        partition_key=session_id
                    )
                    deleted = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to delete session {item['id']}: {e}")
            
            if deleted:
                logger.info(
                    "Session deleted successfully",
                    session_id=session_id
                )
            else:
                logger.warning(
                    "Session not found for deletion",
                    session_id=session_id
                )
            
        except Exception as e:
            logger.error(
                "Failed to delete session",
                error=str(e),
                session_id=session_id
            )
            raise
    
    async def archive_session(self, session_id: str) -> None:
        """Archive a session (change status to 'archived')."""
        await self.ensure_initialized()
        
        try:
            await self.update_session(session_id, {"status": "archived"})
            logger.info("Session archived", session_id=session_id)
        except Exception as e:
            logger.error(
                "Failed to archive session",
                error=str(e),
                session_id=session_id
            )
            raise

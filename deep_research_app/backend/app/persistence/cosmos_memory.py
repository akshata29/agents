"""
CosmosDB Memory Store for Deep Research Application

Stores research sessions and runs in Cosmos DB with session_id as partition key.
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

from ..models.persistence_models import ResearchSession, ResearchRun

logger = structlog.get_logger(__name__)


class CosmosMemoryStore:
    """
    CosmosDB-backed memory store for deep research runs.
    
    Uses session_id as partition key for efficient querying.
    Supports authentication via service principal or managed identity.
    """
    
    def __init__(
        self,
        endpoint: str,
        database_name: str,
        container_name: str,
        user_id: Optional[str] = None,
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
    
    async def create_session(self, session: ResearchSession) -> ResearchSession:
        """Create a new research session."""
        await self.ensure_initialized()
        
        try:
            session_dict = session.dict()
            # Ensure datetime objects are serialized
            session_dict["created_at"] = session.created_at.isoformat()
            session_dict["last_active"] = session.last_active.isoformat()
            
            await self._container.create_item(body=session_dict)
            logger.info(f"Session created", session_id=session.session_id, user_id=session.user_id)
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session", error=str(e), session_id=session.session_id)
            raise
    
    async def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """Retrieve a session by ID."""
        await self.ensure_initialized()
        
        try:
            query = "SELECT * FROM c WHERE c.session_id=@session_id AND c.data_type='session'"
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
                if "last_active" in item and isinstance(item["last_active"], str):
                    item["last_active"] = datetime.fromisoformat(item["last_active"])
                return ResearchSession(**item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session", error=str(e), session_id=session_id)
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
            session_dict["last_active"] = session.last_active.isoformat()
            
            await self._container.upsert_item(body=session_dict)
            logger.debug(f"Session updated", session_id=session_id, updates=list(updates.keys()))
            
        except Exception as e:
            logger.error(f"Failed to update session", error=str(e), session_id=session_id)
            raise
    
    async def get_all_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[ResearchSession]:
        """Retrieve all sessions, optionally filtered by user."""
        await self.ensure_initialized()
        
        try:
            query_parts = ["SELECT * FROM c WHERE c.data_type='session'"]
            parameters = []
            
            if user_id:
                query_parts.append("AND c.user_id=@user_id")
                parameters.append({"name": "@user_id", "value": user_id})
            
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
                    if "last_active" in item and isinstance(item["last_active"], str):
                        item["last_active"] = datetime.fromisoformat(item["last_active"])
                    items.append(ResearchSession(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse session: {e}")
                    continue
            
            logger.info(f"Retrieved {len(items)} sessions", user_id=user_id if user_id else "all")
            return items
            
        except Exception as e:
            logger.error(f"Failed to get sessions", error=str(e))
            return []
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all its associated research runs."""
        await self.ensure_initialized()
        
        try:
            # First, delete all research runs for this session
            query = "SELECT c.id FROM c WHERE c.session_id=@session_id AND c.data_type='research_run'"
            parameters = [{"name": "@session_id", "value": session_id}]
            
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )
            
            deleted_runs = 0
            async for item in query_iter:
                try:
                    await self._container.delete_item(item=item["id"], partition_key=session_id)
                    deleted_runs += 1
                except Exception as e:
                    logger.warning(f"Failed to delete run {item['id']}: {e}")
            
            # Then delete the session document
            session_query = "SELECT c.id FROM c WHERE c.session_id=@session_id AND c.data_type='session'"
            session_iter = self._container.query_items(
                query=session_query,
                parameters=parameters,
                partition_key=session_id
            )
            
            deleted_session = False
            async for item in session_iter:
                try:
                    await self._container.delete_item(item=item["id"], partition_key=session_id)
                    deleted_session = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to delete session {item['id']}: {e}")
            
            logger.info(
                f"Session deleted successfully",
                session_id=session_id,
                deleted_runs=deleted_runs,
                deleted_session=deleted_session
            )
            
        except Exception as e:
            logger.error(f"Failed to delete session", error=str(e), session_id=session_id)
            raise
    
    # ========================================================================
    # Research Run Management
    # ========================================================================
    
    async def create_run(self, run: ResearchRun) -> ResearchRun:
        """Create a new research run."""
        await self.ensure_initialized()
        
        try:
            run_dict = run.dict()
            # Serialize datetime objects
            run_dict["started_at"] = run.started_at.isoformat()
            if run.completed_at:
                run_dict["completed_at"] = run.completed_at.isoformat()
            
            logger.info(f"📝 Creating ResearchRun document in Cosmos DB: run_id={run.run_id}, session_id={run.session_id}, topic={run.topic}")
            
            await self._container.create_item(body=run_dict)
            
            logger.info(f"✅ ResearchRun created successfully in Cosmos DB", run_id=run.run_id, topic=run.topic, user_id=run.user_id)
            return run
            
        except Exception as e:
            logger.error(f"❌ Failed to create ResearchRun in Cosmos DB", error=str(e), run_id=run.run_id, exc_info=True)
            raise
    
    async def get_run(self, run_id: str) -> Optional[ResearchRun]:
        """Retrieve a research run by ID."""
        await self.ensure_initialized()
        
        try:
            query = "SELECT * FROM c WHERE c.run_id=@run_id AND c.data_type='research_run'"
            parameters = [{"name": "@run_id", "value": run_id}]
            
            # Cross-partition query
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    # Parse datetime strings
                    if "started_at" in item and isinstance(item["started_at"], str):
                        item["started_at"] = datetime.fromisoformat(item["started_at"])
                    if "completed_at" in item and item["completed_at"] and isinstance(item["completed_at"], str):
                        item["completed_at"] = datetime.fromisoformat(item["completed_at"])
                    return ResearchRun(**item)
                except Exception as e:
                    logger.warning(f"Failed to parse run: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get run", error=str(e), run_id=run_id)
            return None
    
    async def update_run(self, run_id: str, updates: Dict[str, Any]) -> None:
        """Partially update a run with given fields."""
        await self.ensure_initialized()
        
        try:
            # Get existing run
            run = await self.get_run(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(run, key):
                    setattr(run, key, value)
            
            # Convert to dict for upsert
            run_dict = run.dict()
            # Serialize datetime objects
            run_dict["started_at"] = run.started_at.isoformat()
            if run.completed_at:
                run_dict["completed_at"] = run.completed_at.isoformat()
            
            await self._container.upsert_item(body=run_dict)
            logger.debug(f"Run updated", run_id=run_id, updates=list(updates.keys()))
            
        except Exception as e:
            logger.error(f"Failed to update run", error=str(e), run_id=run_id)
            raise
    
    async def get_runs_by_session(self, session_id: str) -> List[ResearchRun]:
        """Retrieve all runs for a session."""
        await self.ensure_initialized()
        
        try:
            query = """
            SELECT * FROM c 
            WHERE c.session_id=@session_id AND c.data_type='research_run'
            ORDER BY c.started_at DESC
            """
            parameters = [{"name": "@session_id", "value": session_id}]
            
            items = []
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )
            
            async for item in query_iter:
                try:
                    # Parse datetime strings
                    if "started_at" in item and isinstance(item["started_at"], str):
                        item["started_at"] = datetime.fromisoformat(item["started_at"])
                    if "completed_at" in item and item["completed_at"] and isinstance(item["completed_at"], str):
                        item["completed_at"] = datetime.fromisoformat(item["completed_at"])
                    items.append(ResearchRun(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse run: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get runs by session", error=str(e), session_id=session_id)
            return []
    
    async def get_runs_by_user(self, user_id: str, limit: int = 50) -> List[ResearchRun]:
        """Retrieve all runs for a user."""
        await self.ensure_initialized()
        
        try:
            query = f"""
            SELECT * FROM c 
            WHERE c.user_id=@user_id AND c.data_type='research_run'
            ORDER BY c.started_at DESC
            OFFSET 0 LIMIT {limit}
            """
            parameters = [{"name": "@user_id", "value": user_id}]
            
            items = []
            # Cross-partition query
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    # Parse datetime strings
                    if "started_at" in item and isinstance(item["started_at"], str):
                        item["started_at"] = datetime.fromisoformat(item["started_at"])
                    if "completed_at" in item and item["completed_at"] and isinstance(item["completed_at"], str):
                        item["completed_at"] = datetime.fromisoformat(item["completed_at"])
                    items.append(ResearchRun(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse run: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get runs by user", error=str(e), user_id=user_id)
            return []
    
    async def get_runs_by_topic(self, topic: str, user_id: Optional[str] = None, limit: int = 20) -> List[ResearchRun]:
        """Retrieve all runs for a specific topic, optionally filtered by user."""
        await self.ensure_initialized()
        
        try:
            query_parts = ["SELECT * FROM c WHERE c.topic=@topic AND c.data_type='research_run'"]
            parameters = [{"name": "@topic", "value": topic}]
            
            if user_id:
                query_parts.append("AND c.user_id=@user_id")
                parameters.append({"name": "@user_id", "value": user_id})
            
            query_parts.append(f"ORDER BY c.started_at DESC OFFSET 0 LIMIT {limit}")
            query = " ".join(query_parts)
            
            items = []
            # Cross-partition query
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    # Parse datetime strings
                    if "started_at" in item and isinstance(item["started_at"], str):
                        item["started_at"] = datetime.fromisoformat(item["started_at"])
                    if "completed_at" in item and item["completed_at"] and isinstance(item["completed_at"], str):
                        item["completed_at"] = datetime.fromisoformat(item["completed_at"])
                    items.append(ResearchRun(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse run: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get runs by topic", error=str(e), topic=topic)
            return []


# ========================================================================
# Singleton instance for dependency injection
# ========================================================================

_cosmos_store: Optional[CosmosMemoryStore] = None


def get_cosmos_store() -> CosmosMemoryStore:
    """
    Get or create singleton CosmosMemoryStore instance.
    
    Uses environment variables for configuration:
    - COSMOSDB_ENDPOINT: Cosmos DB endpoint URL
    - COSMOS_DB_DATABASE: Database name
    - COSMOS_DB_CONTAINER: Container name
    - AZURE_TENANT_ID: Azure AD tenant ID (optional)
    - AZURE_CLIENT_ID: Service principal client ID (optional)
    - AZURE_CLIENT_SECRET: Service principal client secret (optional)
    """
    global _cosmos_store
    
    if _cosmos_store is None:
        import os
        
        endpoint = os.getenv("COSMOSDB_ENDPOINT")
        database = os.getenv("COSMOS_DB_DATABASE")
        container = os.getenv("COSMOS_DB_CONTAINER")
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")
        
        if not endpoint or not database or not container:
            raise ValueError(
                "Missing required Cosmos DB configuration. "
                "Set COSMOSDB_ENDPOINT, COSMOS_DB_DATABASE, and COSMOS_DB_CONTAINER environment variables."
            )
        
        _cosmos_store = CosmosMemoryStore(
            endpoint=endpoint,
            database_name=database,
            container_name=container,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
    
    return _cosmos_store

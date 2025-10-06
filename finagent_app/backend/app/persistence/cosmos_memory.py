"""
CosmosDB implementation for research run persistence.

Stores research runs and sessions in Cosmos DB with session_id as partition key.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from azure.cosmos.aio import CosmosClient
from azure.cosmos.partition_key import PartitionKey
from azure.identity import DefaultAzureCredential
from azure.identity.aio import ClientSecretCredential as AsyncClientSecretCredential

from app.models.persistence_models import ResearchRun, ResearchSession
from app.persistence.memory_store_base import MemoryStoreBase

logger = logging.getLogger(__name__)


def _serialize_datetime(obj: Any) -> Any:
    """
    Recursively convert datetime objects to ISO format strings.
    
    Args:
        obj: Object to serialize (can be dict, list, datetime, or primitive)
        
    Returns:
        Serialized object with datetime converted to ISO strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetime(item) for item in obj]
    else:
        return obj


class CosmosMemoryStore(MemoryStoreBase):
    """
    CosmosDB-backed memory store for research runs.
    
    Uses session_id as partition key for efficient querying.
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
                # Use ClientSecretCredential for service principal auth
                credential = AsyncClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                logger.info("Using ClientSecretCredential for CosmosDB")
            else:
                # Fallback to DefaultAzureCredential
                credential = DefaultAzureCredential()
                logger.info("Using DefaultAzureCredential for CosmosDB")
            
            self._client = CosmosClient(self.endpoint, credential=credential)
            
            # Get database and container
            self._database = self._client.get_database_client(self.database_name)
            
            # Create container if it doesn't exist
            self._container = await self._database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/session_id"),
            )
            
            logger.info(f"CosmosDB initialized: {self.database_name}/{self.container_name}")
            self._initialized.set()
            
        except Exception as e:
            logger.error(f"Failed to initialize CosmosDB: {e}")
            raise
    
    async def ensure_initialized(self) -> None:
        """Ensure the store is initialized before operations."""
        if not self._initialized.is_set():
            await self.initialize()
    
    async def close(self) -> None:
        """Close Cosmos client."""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized.clear()
    
    # ========================================================================
    # Internal Helpers
    # ========================================================================
    
    async def _add_item(self, item: Any) -> None:
        """Add an item to Cosmos."""
        await self.ensure_initialized()
        
        try:
            document = item.model_dump()
            # Convert all datetime objects to ISO strings
            document = _serialize_datetime(document)
            
            await self._container.create_item(body=document)
            logger.debug(f"Added item {item.id} to Cosmos")
            
        except Exception as e:
            logger.error(f"Failed to add item to Cosmos: {e}")
            raise
    
    async def _update_item(self, item: Any) -> None:
        """Update an item in Cosmos (upsert)."""
        await self.ensure_initialized()
        
        try:
            document = item.model_dump()
            # Convert all datetime objects to ISO strings
            document = _serialize_datetime(document)
            
            await self._container.upsert_item(body=document)
            logger.debug(f"Updated item {item.id}")
            
        except Exception as e:
            logger.error(f"Failed to update item: {e}")
            raise
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    async def create_session(self, session: ResearchSession) -> None:
        """Create a new session (or update if exists)."""
        await self._update_item(session)
    
    async def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """Retrieve a session by ID."""
        await self.ensure_initialized()
        
        try:
            query = "SELECT * FROM c WHERE c.session_id=@session_id AND c.data_type='session'"
            parameters = [{"name": "@session_id", "value": session_id}]
            
            items = []
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    return ResearchSession(**item)
                except Exception as e:
                    logger.warning(f"Failed to parse session: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    async def update_session(self, session: ResearchSession) -> None:
        """Update an existing session."""
        await self._update_item(session)
    
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
            # Note: Not specifying partition_key allows cross-partition queries by default
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    items.append(ResearchSession(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse session: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    # ========================================================================
    # Research Run Management
    # ========================================================================
    
    async def add_run(self, run: ResearchRun) -> None:
        """Add a new research run."""
        await self._add_item(run)
    
    async def get_run(self, run_id: str) -> Optional[ResearchRun]:
        """Retrieve a research run by ID."""
        await self.ensure_initialized()
        
        try:
            query = "SELECT * FROM c WHERE c.run_id=@run_id AND c.data_type='research_run'"
            parameters = [{"name": "@run_id", "value": run_id}]
            
            # Cross-partition query (no partition_key specified)
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    return ResearchRun(**item)
                except Exception as e:
                    logger.warning(f"Failed to parse run: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get run: {e}")
            return None
    
    async def update_run(self, run: ResearchRun) -> None:
        """Update an existing research run."""
        await self._update_item(run)
    
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
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    items.append(ResearchRun(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse run: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get runs by session: {e}")
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
                    items.append(ResearchRun(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse run: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get runs by user: {e}")
            return []
    
    async def get_runs_by_ticker(self, ticker: str, user_id: Optional[str] = None, limit: int = 20) -> List[ResearchRun]:
        """Retrieve all runs for a specific ticker, optionally filtered by user."""
        await self.ensure_initialized()
        
        try:
            query_parts = ["SELECT * FROM c WHERE c.ticker=@ticker AND c.data_type='research_run'"]
            parameters = [{"name": "@ticker", "value": ticker.upper()}]
            
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
                    items.append(ResearchRun(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse run: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get runs by ticker: {e}")
            return []

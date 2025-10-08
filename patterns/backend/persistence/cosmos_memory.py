"""
CosmosDB Memory Store for Pattern Executions

Stores pattern execution sessions and runs in Cosmos DB with session_id as partition key.
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

from .persistence_models import PatternSession, PatternExecution

logger = logging.getLogger(__name__)


class CosmosMemoryStore:
    """
    CosmosDB-backed memory store for pattern executions.
    
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
                f"CosmosDB initialized successfully - endpoint={self.endpoint}, database={self.database_name}, container={self.container_name}"
            )
            
            self._initialized.set()
            
        except Exception as e:
            logger.error(f"Failed to initialize CosmosDB: {e}")
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
    
    async def create_session(self, session: PatternSession) -> PatternSession:
        """Create a new pattern session."""
        await self.ensure_initialized()
        
        try:
            session_dict = session.dict()
            # Ensure datetime objects are serialized
            session_dict["created_at"] = session.created_at.isoformat()
            session_dict["last_active"] = session.last_active.isoformat()
            
            await self._container.create_item(body=session_dict)
            logger.info(f"Session created: session_id={session.session_id}, user_id={session.user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}, session_id={session.session_id}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[PatternSession]:
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
                return PatternSession(**item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session: {e}, session_id={session_id}")
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
            logger.debug(f"Session updated: session_id={session_id}, updates={list(updates.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to update session: {e}, session_id={session_id}")
            raise
    
    async def get_all_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[PatternSession]:
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
                    items.append(PatternSession(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse session: {e}")
                    continue
            
            logger.info(f"Retrieved {len(items)} sessions, user_id={user_id if user_id else 'all'}")
            return items
            
        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all its associated pattern executions."""
        await self.ensure_initialized()
        
        try:
            # First, delete all pattern executions for this session
            query = "SELECT c.id FROM c WHERE c.session_id=@session_id AND c.data_type='pattern_execution'"
            parameters = [{"name": "@session_id", "value": session_id}]
            
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )
            
            deleted_executions = 0
            async for item in query_iter:
                try:
                    await self._container.delete_item(item=item["id"], partition_key=session_id)
                    deleted_executions += 1
                except Exception as e:
                    logger.warning(f"Failed to delete execution {item['id']}: {e}")
            
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
                f"Session deleted successfully: session_id={session_id}, deleted_executions={deleted_executions}, deleted_session={deleted_session}"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete session: {e}, session_id={session_id}")
            raise
    
    # ========================================================================
    # Pattern Execution Management
    # ========================================================================
    
    async def create_execution(self, execution: PatternExecution) -> PatternExecution:
        """Create a new pattern execution."""
        await self.ensure_initialized()
        
        try:
            execution_dict = execution.dict()
            # Serialize datetime objects
            execution_dict["started_at"] = execution.started_at.isoformat()
            if execution.completed_at:
                execution_dict["completed_at"] = execution.completed_at.isoformat()
            
            logger.info(f"📝 Creating PatternExecution in Cosmos DB: execution_id={execution.execution_id}, session_id={execution.session_id}, pattern={execution.pattern}")
            
            await self._container.create_item(body=execution_dict)
            
            logger.info(f"✅ PatternExecution created successfully in Cosmos DB: execution_id={execution.execution_id}, pattern={execution.pattern}, user_id={execution.user_id}")
            return execution
            
        except Exception as e:
            logger.error(f"❌ Failed to create PatternExecution in Cosmos DB: {e}, execution_id={execution.execution_id}", exc_info=True)
            raise
    
    async def get_execution(self, execution_id: str) -> Optional[PatternExecution]:
        """Retrieve a pattern execution by ID."""
        await self.ensure_initialized()
        
        try:
            query = "SELECT * FROM c WHERE c.execution_id=@execution_id AND c.data_type='pattern_execution'"
            parameters = [{"name": "@execution_id", "value": execution_id}]
            
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
                    return PatternExecution(**item)
                except Exception as e:
                    logger.warning(f"Failed to parse execution: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get execution: {e}, execution_id={execution_id}")
            return None
    
    async def update_execution(self, execution_id: str, updates: Dict[str, Any]) -> None:
        """Partially update an execution with given fields."""
        await self.ensure_initialized()
        
        try:
            # Get existing execution
            execution = await self.get_execution(execution_id)
            if not execution:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(execution, key):
                    setattr(execution, key, value)
            
            # Convert to dict for upsert
            execution_dict = execution.dict()
            # Serialize datetime objects
            execution_dict["started_at"] = execution.started_at.isoformat()
            if execution.completed_at:
                execution_dict["completed_at"] = execution.completed_at.isoformat()
            
            await self._container.upsert_item(body=execution_dict)
            logger.debug(f"Execution updated: execution_id={execution_id}, updates={list(updates.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to update execution: {e}, execution_id={execution_id}")
            raise
    
    async def get_executions_by_session(self, session_id: str) -> List[PatternExecution]:
        """Retrieve all executions for a session."""
        await self.ensure_initialized()
        
        try:
            query = """
            SELECT * FROM c 
            WHERE c.session_id=@session_id AND c.data_type='pattern_execution'
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
                    items.append(PatternExecution(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse execution: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get executions by session: {e}, session_id={session_id}")
            return []
    
    async def get_executions_by_user(self, user_id: str, limit: int = 50) -> List[PatternExecution]:
        """Retrieve all executions for a user."""
        await self.ensure_initialized()
        
        try:
            query = f"""
            SELECT * FROM c 
            WHERE c.user_id=@user_id AND c.data_type='pattern_execution'
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
                    items.append(PatternExecution(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse execution: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get executions by user: {e}")
            return []
    
    async def delete_execution(self, execution_id: str) -> None:
        """Delete a pattern execution."""
        await self.ensure_initialized()
        
        try:
            # Find the execution to get its session_id (partition key)
            execution = await self.get_execution(execution_id)
            if not execution:
                raise ValueError(f"Execution {execution_id} not found")
            
            # Delete using the id and partition key
            query = "SELECT c.id FROM c WHERE c.execution_id=@execution_id AND c.data_type='pattern_execution'"
            parameters = [{"name": "@execution_id", "value": execution_id}]
            
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=execution.session_id
            )
            
            async for item in query_iter:
                await self._container.delete_item(item=item["id"], partition_key=execution.session_id)
                logger.info(f"Execution deleted: execution_id={execution_id}")
                return
            
        except Exception as e:
            logger.error(f"Failed to delete execution: {e}, execution_id={execution_id}")
            raise

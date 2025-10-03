"""
CosmosDB implementation of MemoryStore for task orchestration.

Provides persistent storage for Plans, Steps, AgentMessages, and Sessions.
Optimized for the Group Chat and Hand-off patterns.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from azure.cosmos.aio import CosmosClient
from azure.cosmos.partition_key import PartitionKey
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.identity.aio import ClientSecretCredential as AsyncClientSecretCredential

from app.models.task_models import (
    AgentMessage,
    BaseDataModel,
    Plan,
    Session,
    Step,
)
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
    CosmosDB-backed memory store for task orchestration.
    
    Uses session_id as partition key for efficient querying.
    """
    
    def __init__(
        self,
        endpoint: str,
        database_name: str,
        container_name: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.endpoint = endpoint
        self.database_name = database_name
        self.container_name = container_name
        self.session_id = session_id
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
    
    async def _add_item(self, item: BaseDataModel) -> None:
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
    
    async def _update_item(self, item: BaseDataModel) -> None:
        """Update an item in Cosmos."""
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
    
    async def _query_items(
        self,
        query: str,
        parameters: List[Dict[str, Any]],
        model_class: Type[BaseDataModel],
    ) -> List[BaseDataModel]:
        """Execute a query and return typed results."""
        await self.ensure_initialized()
        
        try:
            items = []
            # Note: Removed enable_cross_partition_query as it's not needed 
            # when querying within a partition (session_id)
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters
            )
            
            async for item in query_iter:
                try:
                    items.append(model_class(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse item: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    async def create_session(self, session: Session) -> None:
        """Create a new session (or update if exists)."""
        # Use upsert to avoid conflicts if session already exists
        await self._update_item(session)
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        query = "SELECT * FROM c WHERE c.session_id=@session_id AND c.data_type='session'"
        parameters = [{"name": "@session_id", "value": session_id}]
        
        sessions = await self._query_items(query, parameters, Session)
        return sessions[0] if sessions else None
    
    async def update_session(self, session: Session) -> None:
        """Update an existing session."""
        await self._update_item(session)
    
    async def get_all_sessions(self, limit: int = 50) -> List[Session]:
        """Retrieve all sessions (most recent first)."""
        query = f"""
            SELECT * FROM c 
            WHERE c.data_type='session'
            ORDER BY c.created_at DESC
            OFFSET 0 LIMIT {limit}
        """
        parameters = []
        
        # Need to enable cross-partition query since we're not filtering by session_id
        await self.ensure_initialized()
        try:
            items = []
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters,
            )
            
            async for item in query_iter:
                try:
                    items.append(Session(**item))
                except Exception as e:
                    logger.warning(f"Failed to parse session item: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> None:
        """
        Delete a session and all related items (plans, steps, messages).
        
        Args:
            session_id: The session ID to delete
        """
        await self.ensure_initialized()
        try:
            # Query all items with this session_id (partition key)
            query = "SELECT c.id FROM c WHERE c.session_id=@session_id"
            parameters = [{"name": "@session_id", "value": session_id}]
            
            items = []
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id,
            )
            
            async for item in query_iter:
                items.append(item["id"])
            
            # Delete all items in this session
            for item_id in items:
                try:
                    await self._container.delete_item(
                        item=item_id,
                        partition_key=session_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete item {item_id}: {e}")
            
            logger.info(f"Deleted session {session_id} and {len(items)} related items")
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
    
    # ========================================================================
    # Plan Management
    # ========================================================================
    
    async def add_plan(self, plan: Plan) -> None:
        """Add a new plan."""
        await self._add_item(plan)
    
    async def get_plan(self, plan_id: str, session_id: str = None) -> Optional[Plan]:
        """Retrieve a plan by ID."""
        if session_id:
            # Use partition key for efficient query
            query = "SELECT * FROM c WHERE c.id=@plan_id AND c.session_id=@session_id AND c.data_type='plan'"
            parameters = [
                {"name": "@plan_id", "value": plan_id},
                {"name": "@session_id", "value": session_id}
            ]
        else:
            # Fallback to cross-partition query
            query = "SELECT * FROM c WHERE c.id=@plan_id AND c.data_type='plan'"
            parameters = [{"name": "@plan_id", "value": plan_id}]
        
        plans = await self._query_items(query, parameters, Plan)
        return plans[0] if plans else None
    
    async def get_plan_by_session(self, session_id: str) -> Optional[Plan]:
        """Retrieve the plan for a given session."""
        query = """
            SELECT * FROM c 
            WHERE c.session_id=@session_id 
            AND c.data_type='plan'
            ORDER BY c.timestamp DESC
        """
        parameters = [{"name": "@session_id", "value": session_id}]
        
        plans = await self._query_items(query, parameters, Plan)
        return plans[0] if plans else None
    
    async def get_all_plans(self, user_id: str, limit: int = 10) -> List[Plan]:
        """Retrieve all plans for a user (most recent first)."""
        query = f"""
            SELECT * FROM c 
            WHERE c.user_id=@user_id 
            AND c.data_type='plan'
            ORDER BY c.timestamp DESC
            OFFSET 0 LIMIT {limit}
        """
        parameters = [{"name": "@user_id", "value": user_id}]
        
        return await self._query_items(query, parameters, Plan)
    
    async def update_plan(self, plan: Plan) -> None:
        """Update an existing plan."""
        await self._update_item(plan)
    
    # ========================================================================
    # Step Management
    # ========================================================================
    
    async def add_step(self, step: Step) -> None:
        """Add a new step."""
        await self._add_item(step)
    
    async def get_step(self, step_id: str, session_id: str) -> Optional[Step]:
        """Retrieve a step by ID."""
        query = """
            SELECT * FROM c 
            WHERE c.id=@step_id 
            AND c.session_id=@session_id 
            AND c.data_type='step'
        """
        parameters = [
            {"name": "@step_id", "value": step_id},
            {"name": "@session_id", "value": session_id},
        ]
        
        steps = await self._query_items(query, parameters, Step)
        return steps[0] if steps else None
    
    async def get_steps_by_plan(self, plan_id: str, session_id: str = None) -> List[Step]:
        """Retrieve all steps for a plan (ordered by creation)."""
        if session_id:
            # Use partition key for efficient query
            query = """
                SELECT * FROM c 
                WHERE c.plan_id=@plan_id 
                AND c.session_id=@session_id
                AND c.data_type='step'
                ORDER BY c.timestamp ASC
            """
            parameters = [
                {"name": "@plan_id", "value": plan_id},
                {"name": "@session_id", "value": session_id}
            ]
        else:
            # Fallback to cross-partition query
            query = """
                SELECT * FROM c 
                WHERE c.plan_id=@plan_id 
                AND c.data_type='step'
                ORDER BY c.timestamp ASC
            """
            parameters = [{"name": "@plan_id", "value": plan_id}]
        
        return await self._query_items(query, parameters, Step)
    
    async def update_step(self, step: Step) -> None:
        """Update an existing step."""
        await self._update_item(step)
    
    # ========================================================================
    # Message Management
    # ========================================================================
    
    async def add_message(self, message: AgentMessage) -> None:
        """Add a new agent message."""
        await self._add_item(message)
    
    async def get_messages_by_session(
        self, 
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[AgentMessage]:
        """Retrieve all messages for a session (chronological order)."""
        query = """
            SELECT * FROM c 
            WHERE c.session_id=@session_id 
            AND c.data_type='message'
            ORDER BY c.timestamp ASC
        """
        
        if limit:
            query += f" OFFSET 0 LIMIT {limit}"
        
        parameters = [{"name": "@session_id", "value": session_id}]
        
        return await self._query_items(query, parameters, AgentMessage)
    
    async def get_messages_by_plan(self, plan_id: str) -> List[AgentMessage]:
        """Retrieve all messages for a plan."""
        query = """
            SELECT * FROM c 
            WHERE c.plan_id=@plan_id 
            AND c.data_type='message'
            ORDER BY c.timestamp ASC
        """
        parameters = [{"name": "@plan_id", "value": plan_id}]
        
        return await self._query_items(query, parameters, AgentMessage)
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    async def query_items(
        self,
        query: str,
        parameters: List[Dict[str, Any]],
        model_class: type,
    ) -> List[Any]:
        """Execute a custom query."""
        return await self._query_items(query, parameters, model_class)
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    async def delete_plan_and_related(self, plan_id: str, session_id: str) -> None:
        """
        Delete a plan and all related steps and messages.
        Useful for cleanup/testing.
        """
        await self.ensure_initialized()
        
        try:
            # Get all related items
            query = """
                SELECT c.id FROM c 
                WHERE c.session_id=@session_id 
                AND (c.plan_id=@plan_id OR c.id=@plan_id)
            """
            parameters = [
                {"name": "@session_id", "value": session_id},
                {"name": "@plan_id", "value": plan_id},
            ]
            
            items = []
            query_iter = self._container.query_items(
                query=query,
                parameters=parameters,
            )
            
            async for item in query_iter:
                items.append(item["id"])
            
            # Delete each item
            for item_id in items:
                try:
                    await self._container.delete_item(
                        item=item_id,
                        partition_key=session_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete item {item_id}: {e}")
            
            logger.info(f"Deleted plan {plan_id} and {len(items)} related items")
            
        except Exception as e:
            logger.error(f"Failed to delete plan: {e}")
    
    async def __aenter__(self):
        """Context manager support."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        await self.close()

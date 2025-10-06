"""
Cosmos DB Memory Store - Multimodal Insights Application

Handles all persistence operations for sessions, plans, steps, messages, and file metadata.
Built from scratch for multimodal content processing use case.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import structlog

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions
from azure.identity.aio import (
    DefaultAzureCredential,
    ClientSecretCredential as AsyncClientSecretCredential
)

from ..models.task_models import (
    Session, Plan, Step, AgentMessage, FileMetadata, ExtractedContent,
    DataType, PlanStatus, StepStatus, PlanWithSteps
)
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)


class CosmosMemoryStore:
    """
    CosmosDB memory store for multimodal insights application.
    
    Container structure:
    - Partition Key: session_id
    - Documents: Sessions, Plans, Steps, Messages, FileMetadata, ExtractedContent
    """
    
    def __init__(self, settings: Settings):
        """Initialize Cosmos DB client."""
        self.settings = settings
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.container = None
        
    async def initialize(self):
        """Initialize Cosmos DB connection and ensure database/container exist."""
        if not self.settings.cosmosdb_endpoint:
            logger.warning("CosmosDB not configured - using in-memory storage")
            return
        
        try:
            # Create credential based on available configuration
            if self.settings.azure_tenant_id and self.settings.azure_client_id and self.settings.azure_client_secret:
                # Use AsyncClientSecretCredential for service principal auth
                credential = AsyncClientSecretCredential(
                    tenant_id=self.settings.azure_tenant_id,
                    client_id=self.settings.azure_client_id,
                    client_secret=self.settings.azure_client_secret
                )
                logger.info("Using ClientSecretCredential for CosmosDB authentication")
            else:
                # Fallback to DefaultAzureCredential (uses managed identity, Azure CLI, etc.)
                credential = DefaultAzureCredential()
                logger.info("Using DefaultAzureCredential for CosmosDB authentication")
            
            # Create Cosmos client with credential
            self.client = CosmosClient(
                url=self.settings.cosmosdb_endpoint,
                credential=credential
            )
            
            # Get database client (assumes database already exists - no write permission needed)
            self.database = self.client.get_database_client(self.settings.cosmosdb_database)
            
            # Create container if not exists with session_id as partition key
            self.container = await self.database.create_container_if_not_exists(
                id=self.settings.cosmosdb_container,
                partition_key=PartitionKey(path="/session_id"),
                offer_throughput=400
            )
            
            logger.info(
                "Cosmos DB initialized",
                database=self.settings.cosmosdb_database,
                container=self.settings.cosmosdb_container
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB: {e}")
            logger.warning("Cosmos DB initialization failed - continuing with in-memory storage. Check RBAC permissions if persistence is required.")
            # Don't raise - allow app to continue without Cosmos DB
            self.client = None
            self.database = None
            self.container = None
    
    async def close(self):
        """Close Cosmos DB client."""
        if self.client:
            await self.client.close()
            logger.info("Cosmos DB connection closed")
    
    # ============= Session Operations =============
    
    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        try:
            doc = session.model_dump(mode='json')
            await self.container.create_item(body=doc)
            logger.info(f"Created session", session_id=session.session_id)
            return session
        except Exception as e:
            logger.error(f"Failed to create session", error=str(e))
            raise
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        try:
            query = "SELECT * FROM c WHERE c.session_id = @session_id AND c.data_type = @data_type"
            parameters = [
                {"name": "@session_id", "value": session_id},
                {"name": "@data_type", "value": DataType.SESSION.value}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )]
            
            if items:
                return Session(**items[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session", error=str(e), session_id=session_id)
            return None
    
    async def update_session(self, session: Session) -> Session:
        """Update session last_active timestamp."""
        try:
            session.last_active = datetime.utcnow()
            doc = session.model_dump(mode='json')
            await self.container.upsert_item(body=doc)
            logger.info(f"Updated session", session_id=session.session_id)
            return session
        except Exception as e:
            logger.error(f"Failed to update session", error=str(e))
            raise
    
    async def delete_session(self, session_id: str) -> None:
        """
        Delete a session and all related items (plans, steps, file_metadata).
        
        Args:
            session_id: The session ID to delete
        """
        if not self.container:
            logger.warning("Cosmos DB not initialized - cannot delete session")
            return
            
        try:
            # Query all items with this session_id (partition key)
            query = "SELECT c.id FROM c WHERE c.session_id=@session_id"
            parameters = [{"name": "@session_id", "value": session_id}]
            
            items = []
            query_iter = self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id,
            )
            
            async for item in query_iter:
                items.append(item["id"])
            
            # Delete all items in this session
            deleted_count = 0
            for item_id in items:
                try:
                    await self.container.delete_item(
                        item=item_id,
                        partition_key=session_id,
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete item {item_id}: {e}")
            
            logger.info(f"Deleted session and related items", session_id=session_id, items_deleted=deleted_count)
            
        except Exception as e:
            logger.error(f"Failed to delete session", error=str(e), session_id=session_id)
            raise
    
    async def list_sessions(self, user_id: str, limit: int = 50) -> List[Session]:
        """List sessions for a user."""
        try:
            query = """
                SELECT * FROM c 
                WHERE c.user_id = @user_id 
                AND c.data_type = @data_type 
                ORDER BY c.last_active DESC
                OFFSET 0 LIMIT @limit
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@data_type", "value": DataType.SESSION.value},
                {"name": "@limit", "value": limit}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters
            )]
            
            return [Session(**item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to list sessions", error=str(e))
            return []
    
    # ============= Plan Operations =============
    
    async def create_plan(self, plan: Plan) -> Plan:
        """Create a new plan."""
        try:
            doc = plan.model_dump(mode='json')
            await self.container.create_item(body=doc)
            logger.info(f"Created plan", plan_id=plan.id, session_id=plan.session_id)
            return plan
        except Exception as e:
            logger.error(f"Failed to create plan", error=str(e))
            raise
    
    async def get_plan(self, plan_id: str, session_id: str) -> Optional[Plan]:
        """Get plan by ID."""
        try:
            query = "SELECT * FROM c WHERE c.id = @plan_id AND c.data_type = @data_type"
            parameters = [
                {"name": "@plan_id", "value": plan_id},
                {"name": "@data_type", "value": DataType.PLAN.value}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )]
            
            if items:
                return Plan(**items[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get plan", error=str(e), plan_id=plan_id)
            return None
    
    async def update_plan(self, plan: Plan) -> Plan:
        """Update an existing plan."""
        try:
            doc = plan.model_dump(mode='json')
            await self.container.upsert_item(body=doc)
            logger.info(f"Updated plan", plan_id=plan.id)
            return plan
        except Exception as e:
            logger.error(f"Failed to update plan", error=str(e))
            raise
    
    async def list_plans(self, session_id: str) -> List[Plan]:
        """List all plans for a session."""
        try:
            query = "SELECT * FROM c WHERE c.session_id = @session_id AND c.data_type = @data_type"
            parameters = [
                {"name": "@session_id", "value": session_id},
                {"name": "@data_type", "value": DataType.PLAN.value}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )]
            
            return [Plan(**item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to list plans", error=str(e))
            return []
    
    # ============= Step Operations =============
    
    async def create_step(self, step: Step) -> Step:
        """Create a new step."""
        try:
            doc = step.model_dump(mode='json')
            await self.container.create_item(body=doc)
            logger.info(f"Created step", step_id=step.id, plan_id=step.plan_id)
            return step
        except Exception as e:
            logger.error(f"Failed to create step", error=str(e))
            raise
    
    async def get_step(self, step_id: str, session_id: str) -> Optional[Step]:
        """Get step by ID."""
        try:
            query = "SELECT * FROM c WHERE c.id = @step_id AND c.data_type = @data_type"
            parameters = [
                {"name": "@step_id", "value": step_id},
                {"name": "@data_type", "value": DataType.STEP.value}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )]
            
            if items:
                return Step(**items[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get step", error=str(e), step_id=step_id)
            return None
    
    async def update_step(self, step: Step) -> Step:
        """Update an existing step."""
        try:
            doc = step.model_dump(mode='json')
            await self.container.upsert_item(body=doc)
            logger.info(f"Updated step", step_id=step.id, status=step.status)
            return step
        except Exception as e:
            logger.error(f"Failed to update step", error=str(e))
            raise
    
    async def get_steps_for_plan(self, plan_id: str, session_id: str) -> List[Step]:
        """Get all steps for a plan, ordered by order field."""
        try:
            query = """
                SELECT * FROM c 
                WHERE c.plan_id = @plan_id 
                AND c.data_type = @data_type 
                ORDER BY c["order"]
            """
            parameters = [
                {"name": "@plan_id", "value": plan_id},
                {"name": "@data_type", "value": DataType.STEP.value}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )]
            
            return [Step(**item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to get steps for plan", error=str(e))
            return []
    
    # ============= Message Operations =============
    
    async def create_message(self, message: AgentMessage) -> AgentMessage:
        """Create a new message."""
        try:
            doc = message.model_dump(mode='json')
            await self.container.create_item(body=doc)
            logger.info(f"Created message", message_id=message.id, plan_id=message.plan_id)
            return message
        except Exception as e:
            logger.error(f"Failed to create message", error=str(e))
            raise
    
    async def get_messages_for_plan(self, plan_id: str, session_id: str) -> List[AgentMessage]:
        """Get all messages for a plan."""
        try:
            query = """
                SELECT * FROM c 
                WHERE c.plan_id = @plan_id 
                AND c.data_type = @data_type 
                ORDER BY c.timestamp
            """
            parameters = [
                {"name": "@plan_id", "value": plan_id},
                {"name": "@data_type", "value": DataType.MESSAGE.value}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )]
            
            return [AgentMessage(**item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to get messages for plan", error=str(e))
            return []
    
    # ============= File Operations =============
    
    async def create_file_metadata(self, file_metadata: FileMetadata) -> FileMetadata:
        """Create file metadata record."""
        try:
            doc = file_metadata.model_dump(mode='json')
            await self.container.create_item(body=doc)
            logger.info(f"Created file metadata", file_id=file_metadata.id)
            return file_metadata
        except Exception as e:
            logger.error(f"Failed to create file metadata", error=str(e))
            raise
    
    async def get_file_metadata(self, file_id: str, session_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID."""
        try:
            query = "SELECT * FROM c WHERE c.id = @file_id AND c.data_type = @data_type"
            parameters = [
                {"name": "@file_id", "value": file_id},
                {"name": "@data_type", "value": DataType.FILE_METADATA.value}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )]
            
            if items:
                return FileMetadata(**items[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file metadata", error=str(e))
            return None
    
    async def update_file_metadata(self, file_metadata: FileMetadata) -> FileMetadata:
        """Update file metadata."""
        try:
            doc = file_metadata.model_dump(mode='json')
            await self.container.upsert_item(body=doc)
            logger.info(f"Updated file metadata", file_id=file_metadata.id)
            return file_metadata
        except Exception as e:
            logger.error(f"Failed to update file metadata", error=str(e))
            raise
    
    async def get_files_for_session(self, session_id: str) -> List[FileMetadata]:
        """Get all files for a session."""
        try:
            query = "SELECT * FROM c WHERE c.session_id = @session_id AND c.data_type = @data_type"
            parameters = [
                {"name": "@session_id", "value": session_id},
                {"name": "@data_type", "value": DataType.FILE_METADATA.value}
            ]
            
            items = [item async for item in self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id
            )]
            
            return [FileMetadata(**item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to get files for session", error=str(e))
            return []
    
    async def get_all_sessions(self, limit: int = 50, user_id: Optional[str] = None) -> List[Session]:
        """
        Get all sessions ordered by timestamp descending.
        
        Args:
            limit: Maximum number of sessions to return
            user_id: Optional user ID to filter sessions (for security/multi-tenancy)
        """
        try:
            if user_id:
                # Filter by user_id for multi-user security
                query = """
                SELECT * FROM c 
                WHERE c.data_type = @data_type AND c.user_id = @user_id
                ORDER BY c.timestamp DESC
                OFFSET 0 LIMIT @limit
                """
                params = [
                    {"name": "@data_type", "value": DataType.SESSION.value},
                    {"name": "@user_id", "value": user_id},
                    {"name": "@limit", "value": limit}
                ]
            else:
                # Get all sessions (admin/development mode)
                query = """
                SELECT * FROM c 
                WHERE c.data_type = @data_type
                ORDER BY c.timestamp DESC
                OFFSET 0 LIMIT @limit
                """
                params = [
                    {"name": "@data_type", "value": DataType.SESSION.value},
                    {"name": "@limit", "value": limit}
                ]
            
            # Note: Not specifying partition_key allows cross-partition queries by default in async SDK
            items = self.container.query_items(
                query=query,
                parameters=params
            )
            
            sessions = []
            async for item in items:
                sessions.append(Session(**item))
            
            logger.info(f"Retrieved {len(sessions)} sessions", user_id=user_id if user_id else "all")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get all sessions", error=str(e))
            return []
    
    async def get_plans_for_session(self, session_id: str) -> List[Plan]:
        """Get all plans for a session."""
        try:
            query = """
            SELECT * FROM c 
            WHERE c.data_type = @data_type AND c.session_id = @session_id
            ORDER BY c.timestamp DESC
            """
            
            params = [
                {"name": "@data_type", "value": DataType.PLAN.value},
                {"name": "@session_id", "value": session_id}
            ]
            items = self.container.query_items(
                query=query,
                parameters=params,
                partition_key=session_id
            )
            
            plans = []
            async for item in items:
                plans.append(Plan(**item))
            
            return plans
            
        except Exception as e:
            logger.error(f"Failed to get plans for session", error=str(e), session_id=session_id)
            return []
    
    # ============= Composite Operations =============
    
    async def get_plan_with_steps(self, plan_id: str, session_id: str) -> Optional[PlanWithSteps]:
        """Get plan with all its steps."""
        try:
            plan = await self.get_plan(plan_id, session_id)
            if not plan:
                return None
            
            steps = await self.get_steps_for_plan(plan_id, session_id)
            
            return PlanWithSteps(
                id=plan.id,
                session_id=plan.session_id,
                user_id=plan.user_id,
                initial_goal=plan.initial_goal,
                summary=plan.summary,
                overall_status=plan.overall_status,
                file_ids=plan.file_ids,
                total_steps=plan.total_steps,
                completed_steps=plan.completed_steps,
                failed_steps=plan.failed_steps,
                timestamp=plan.timestamp,
                steps=steps
            )
            
        except Exception as e:
            logger.error(f"Failed to get plan with steps", error=str(e))
            return None

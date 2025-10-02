"""
Security Manager - Authentication, Authorization and Security

Provides comprehensive security features including authentication, authorization,
audit logging, and secure communication for the framework.
"""

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum

import structlog
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

from ..config.settings import Settings


logger = structlog.get_logger(__name__)


class SecurityRole(str, Enum):
    """Security roles for access control."""
    ADMIN = "admin"
    ORCHESTRATOR = "orchestrator"
    AGENT = "agent"
    USER = "user"
    READONLY = "readonly"


class SecurityPermission(str, Enum):
    """Security permissions."""
    EXECUTE_AGENTS = "execute_agents"
    MANAGE_AGENTS = "manage_agents"
    MANAGE_WORKFLOWS = "manage_workflows"
    ACCESS_MCP_TOOLS = "access_mcp_tools"
    VIEW_LOGS = "view_logs"
    MANAGE_SECURITY = "manage_security"


class SecurityContext(BaseModel):
    """Security context for operations."""
    user_id: str
    session_id: str
    roles: Set[SecurityRole] = Field(default_factory=set)
    permissions: Set[SecurityPermission] = Field(default_factory=set)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class AuditEvent(BaseModel):
    """Audit event for logging security-related actions."""
    event_id: str
    event_type: str
    user_id: str
    session_id: Optional[str] = None
    resource: str
    action: str
    result: str  # success, failure, denied
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None


class SecurityManager:
    """
    Security manager for authentication, authorization, and auditing.
    
    Provides comprehensive security features including role-based access control,
    audit logging, and secure communication capabilities.
    """

    def __init__(self, settings: Settings):
        """Initialize security manager."""
        self.settings = settings
        
        # Encryption
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
        
        # Session management
        self._active_sessions: Dict[str, SecurityContext] = {}
        self._session_lock = asyncio.Lock()
        
        # Role permissions mapping
        self._role_permissions = self._initialize_role_permissions()
        
        # Audit log storage
        self._audit_events: List[AuditEvent] = []
        self._audit_lock = asyncio.Lock()
        
        logger.info("SecurityManager initialized")

    async def initialize(self) -> None:
        """Initialize security manager."""
        logger.info("Initializing SecurityManager")
        
        # Start session cleanup task
        self._cleanup_task = asyncio.create_task(self._session_cleanup_loop())
        
        logger.info("SecurityManager initialization complete")

    async def shutdown(self) -> None:
        """Shutdown security manager."""
        logger.info("Shutting down SecurityManager")
        
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("SecurityManager shutdown complete")

    async def create_session(
        self,
        user_id: str,
        roles: Optional[List[SecurityRole]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new security session.
        
        Args:
            user_id: User identifier
            roles: User roles
            metadata: Optional session metadata
            
        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        
        # Set default roles if none provided
        if roles is None:
            roles = [SecurityRole.USER]
        
        # Calculate permissions based on roles
        permissions = set()
        for role in roles:
            permissions.update(self._role_permissions.get(role, set()))
        
        # Create security context
        context = SecurityContext(
            user_id=user_id,
            session_id=session_id,
            roles=set(roles),
            permissions=permissions,
            expires_at=datetime.utcnow() + timedelta(
                minutes=self.settings.security.access_token_expire_minutes
            ),
            metadata=metadata or {}
        )
        
        async with self._session_lock:
            self._active_sessions[session_id] = context
        
        # Log session creation
        await self._log_audit_event(
            event_type="session_created",
            user_id=user_id,
            session_id=session_id,
            resource="session",
            action="create",
            result="success"
        )
        
        logger.info(
            "Security session created",
            user_id=user_id,
            session_id=session_id,
            roles=roles,
            permissions=len(permissions)
        )
        
        return session_id

    async def get_session(self, session_id: str) -> Optional[SecurityContext]:
        """Get security context for a session."""
        async with self._session_lock:
            context = self._active_sessions.get(session_id)
            
            if context and datetime.utcnow() > context.expires_at:
                # Session expired
                del self._active_sessions[session_id]
                return None
            
            return context

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a security session."""
        async with self._session_lock:
            context = self._active_sessions.pop(session_id, None)
            
            if context:
                await self._log_audit_event(
                    event_type="session_revoked",
                    user_id=context.user_id,
                    session_id=session_id,
                    resource="session",
                    action="revoke",
                    result="success"
                )
                
                logger.info(
                    "Security session revoked",
                    user_id=context.user_id,
                    session_id=session_id
                )
                return True
            
            return False

    async def check_permission(
        self,
        session_id: str,
        permission: SecurityPermission,
        resource: Optional[str] = None
    ) -> bool:
        """
        Check if a session has a specific permission.
        
        Args:
            session_id: Session ID
            permission: Required permission
            resource: Optional resource identifier
            
        Returns:
            True if permission granted
        """
        context = await self.get_session(session_id)
        
        if not context:
            await self._log_audit_event(
                event_type="permission_check",
                user_id="unknown",
                session_id=session_id,
                resource=resource or "unknown",
                action=permission,
                result="denied_no_session"
            )
            return False
        
        has_permission = permission in context.permissions
        
        await self._log_audit_event(
            event_type="permission_check",
            user_id=context.user_id,
            session_id=session_id,
            resource=resource or "unknown",
            action=permission,
            result="granted" if has_permission else "denied"
        )
        
        return has_permission

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self._cipher.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self._cipher.decrypt(encrypted_data.encode()).decode()

    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, password_hash = hashed.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
        except (ValueError, IndexError):
            return False

    async def get_audit_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get audit events with optional filtering."""
        async with self._audit_lock:
            events = self._audit_events.copy()
        
        # Apply filters
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        return events[:limit]

    async def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        async with self._session_lock:
            active_sessions = len(self._active_sessions)
            
            role_counts = {}
            for context in self._active_sessions.values():
                for role in context.roles:
                    role_counts[role] = role_counts.get(role, 0) + 1
        
        async with self._audit_lock:
            total_events = len(self._audit_events)
            
            recent_events = [
                e for e in self._audit_events 
                if e.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ]
            
            event_types = {}
            for event in recent_events:
                event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        
        return {
            "active_sessions": active_sessions,
            "role_distribution": role_counts,
            "total_audit_events": total_events,
            "recent_events_24h": len(recent_events),
            "event_types_24h": event_types
        }

    # Private methods

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for data protection."""
        # In production, this should be stored securely (e.g., Azure Key Vault)
        key_material = self.settings.security.secret_key.encode()
        
        # Derive a proper Fernet key from the secret
        import base64
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'magentic_foundation_salt',  # Use a proper random salt in production
            iterations=100000
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(key_material))
        return key

    def _initialize_role_permissions(self) -> Dict[SecurityRole, Set[SecurityPermission]]:
        """Initialize role-to-permissions mapping."""
        return {
            SecurityRole.ADMIN: {
                SecurityPermission.EXECUTE_AGENTS,
                SecurityPermission.MANAGE_AGENTS,
                SecurityPermission.MANAGE_WORKFLOWS,
                SecurityPermission.ACCESS_MCP_TOOLS,
                SecurityPermission.VIEW_LOGS,
                SecurityPermission.MANAGE_SECURITY
            },
            SecurityRole.ORCHESTRATOR: {
                SecurityPermission.EXECUTE_AGENTS,
                SecurityPermission.MANAGE_WORKFLOWS,
                SecurityPermission.ACCESS_MCP_TOOLS,
                SecurityPermission.VIEW_LOGS
            },
            SecurityRole.AGENT: {
                SecurityPermission.EXECUTE_AGENTS,
                SecurityPermission.ACCESS_MCP_TOOLS
            },
            SecurityRole.USER: {
                SecurityPermission.EXECUTE_AGENTS,
                SecurityPermission.VIEW_LOGS
            },
            SecurityRole.READONLY: {
                SecurityPermission.VIEW_LOGS
            }
        }

    async def _log_audit_event(
        self,
        event_type: str,
        user_id: str,
        resource: str,
        action: str,
        result: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an audit event."""
        if not self.settings.security.enable_audit_logging:
            return
        
        event = AuditEvent(
            event_id=secrets.token_hex(16),
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            resource=resource,
            action=action,
            result=result,
            details=details or {}
        )
        
        async with self._audit_lock:
            self._audit_events.append(event)
            
            # Keep only recent events (last 10,000)
            if len(self._audit_events) > 10000:
                self._audit_events = self._audit_events[-5000:]

    async def _session_cleanup_loop(self):
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                current_time = datetime.utcnow()
                expired_sessions = []
                
                async with self._session_lock:
                    for session_id, context in list(self._active_sessions.items()):
                        if current_time > context.expires_at:
                            expired_sessions.append((session_id, context.user_id))
                            del self._active_sessions[session_id]
                
                # Log expired sessions
                for session_id, user_id in expired_sessions:
                    await self._log_audit_event(
                        event_type="session_expired",
                        user_id=user_id,
                        session_id=session_id,
                        resource="session",
                        action="expire",
                        result="success"
                    )
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in session cleanup loop", error=str(e))
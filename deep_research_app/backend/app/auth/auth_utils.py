"""
Authentication utilities for extracting user details from Azure EasyAuth headers.

Azure App Service Easy Auth injects headers with authenticated user information.
These utilities extract and validate that information.
"""

from typing import Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


def get_authenticated_user_details(request_headers: Dict[str, str]) -> Dict[str, Optional[str]]:
    """
    Extract authenticated user details from Azure EasyAuth headers.
    
    Azure App Service Easy Auth injects these headers:
    - x-ms-client-principal-id: Unique user ID (object ID from Azure AD)
    - x-ms-client-principal-name: User's email or username
    - x-ms-client-principal-idp: Identity provider (e.g., 'aad' for Azure AD)
    - x-ms-token-aad-id-token: Azure AD ID token
    
    Args:
        request_headers: Dictionary of HTTP request headers (case-insensitive)
    
    Returns:
        Dictionary with user details:
        {
            "user_principal_id": str,  # Unique user ID
            "user_name": str,          # Display name or email
            "identity_provider": str,  # Identity provider
            "token": str               # ID token (if available)
        }
    """
    # Normalize headers to lowercase for case-insensitive lookup
    headers_lower = {k.lower(): v for k, v in request_headers.items()}
    
    user_principal_id = headers_lower.get("x-ms-client-principal-id")
    user_name = headers_lower.get("x-ms-client-principal-name")
    identity_provider = headers_lower.get("x-ms-client-principal-idp")
    token = headers_lower.get("x-ms-token-aad-id-token")
    
    # Fallback for local development (no EasyAuth)
    if not user_principal_id:
        logger.warning("No Azure EasyAuth headers found, using development defaults")
        from .sample_user import get_sample_user
        return get_sample_user()
    
    logger.info(
        "Extracted user from EasyAuth headers",
        user_id=user_principal_id,
        user_name=user_name,
        idp=identity_provider
    )
    
    return {
        "user_principal_id": user_principal_id,
        "user_name": user_name or "Unknown User",
        "identity_provider": identity_provider or "unknown",
        "token": token
    }


def get_tenantid(request_headers: Dict[str, str]) -> Optional[str]:
    """
    Extract tenant ID from Azure EasyAuth headers.
    
    Args:
        request_headers: Dictionary of HTTP request headers
    
    Returns:
        Tenant ID string, or None if not found
    """
    headers_lower = {k.lower(): v for k, v in request_headers.items()}
    tenant_id = headers_lower.get("x-ms-client-principal-tenant-id")
    
    if not tenant_id:
        logger.debug("No tenant ID found in headers")
    
    return tenant_id

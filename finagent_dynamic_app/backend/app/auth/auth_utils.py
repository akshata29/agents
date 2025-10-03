"""
Authentication utilities for extracting user details from request headers.

Supports both Azure EasyAuth (deployed) and local development mode.
"""
import base64
import json
import logging

logger = logging.getLogger(__name__)


def get_authenticated_user_details(request_headers):
    """
    Extract user details from request headers.
    
    Args:
        request_headers: FastAPI Request.headers or dict of headers
        
    Returns:
        Dictionary containing:
        - user_principal_id: User's unique identifier
        - user_name: User's name/email
        - auth_provider: Identity provider (aad, google, etc.)
        - auth_token: Authentication token
        - client_principal_b64: Base64 encoded client principal
        - aad_id_token: AAD ID token
    """
    user_object = {}
    
    # Convert headers to dict if needed
    if hasattr(request_headers, 'items'):
        raw_headers = {k: v for k, v in request_headers.items()}
    else:
        raw_headers = dict(request_headers)
    
    # Check if running with Azure EasyAuth
    if "x-ms-client-principal-id" not in raw_headers:
        logger.info("No user principal found in headers - using mock user for local dev")
        # Local development mode - use sample user
        from . import sample_user
        raw_user_object = sample_user.sample_user
    else:
        # Production mode - extract from EasyAuth headers
        raw_user_object = raw_headers
    
    # Normalize headers to lowercase
    normalized_headers = {k.lower(): v for k, v in raw_user_object.items()}
    
    # Extract user details
    user_object["user_principal_id"] = normalized_headers.get("x-ms-client-principal-id")
    user_object["user_name"] = normalized_headers.get("x-ms-client-principal-name")
    user_object["auth_provider"] = normalized_headers.get("x-ms-client-principal-idp")
    user_object["auth_token"] = normalized_headers.get("x-ms-token-aad-id-token")
    user_object["client_principal_b64"] = normalized_headers.get("x-ms-client-principal")
    user_object["aad_id_token"] = normalized_headers.get("x-ms-token-aad-id-token")
    
    return user_object


def get_tenantid(client_principal_b64):
    """
    Extract tenant ID from base64 encoded client principal.
    
    Args:
        client_principal_b64: Base64 encoded client principal from headers
        
    Returns:
        Tenant ID string or empty string if not found
    """
    tenant_id = ""
    if client_principal_b64:
        try:
            # Decode the base64 header to get the JSON string
            decoded_bytes = base64.b64decode(client_principal_b64)
            decoded_string = decoded_bytes.decode("utf-8")
            # Convert the JSON string into a Python dictionary
            user_info = json.loads(decoded_string)
            # Extract the tenant ID
            tenant_id = user_info.get("tid", "")  # 'tid' typically holds the tenant ID
        except Exception as ex:
            logger.exception(f"Failed to extract tenant ID: {ex}")
    return tenant_id

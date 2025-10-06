"""
Sample user for local development (when Azure EasyAuth is not available).
"""

from typing import Dict, Optional


def get_sample_user() -> Dict[str, Optional[str]]:
    """
    Return a sample user for local development.
    
    Returns:
        Dictionary with sample user details matching EasyAuth structure
    """
    return {
        "user_principal_id": "dev-user@localhost",
        "user_name": "Development User",
        "identity_provider": "local",
        "token": None
    }

"""
Authentication module for extracting user details from Azure EasyAuth headers.
"""

from .auth_utils import get_authenticated_user_details, get_tenantid
from .sample_user import sample_user

__all__ = ['get_authenticated_user_details', 'get_tenantid', 'sample_user']

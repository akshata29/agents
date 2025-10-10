"""Sample user helpers for local development."""

from typing import Dict

_SAMPLE_USER: Dict[str, str] = {
    "x-ms-client-principal-id": "local-dev-user-001",
    "x-ms-client-principal-name": "dev@localhost.com",
    "x-ms-client-principal-idp": "local",
    "x-ms-token-aad-id-token": "local-dev-token",
    "x-ms-client-principal": "",  # Base64 encoded client principal (optional)
}


def get_sample_user() -> Dict[str, str]:
    """Return a copy of the sample EasyAuth headers used during local development."""

    return dict(_SAMPLE_USER)


# Backwards compatibility for legacy imports
sample_user = _SAMPLE_USER

__all__ = ["get_sample_user", "sample_user"]

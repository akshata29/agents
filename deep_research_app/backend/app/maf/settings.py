"""Application settings tailored for the Deep Research backend."""

from __future__ import annotations

from typing import List, Optional, Union

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration surface for the Deep Research backend.

    The settings mirror the environment variables that the application relies on
    today while keeping everything optional so local development remains simple.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Azure OpenAI
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: Optional[str] = Field(default="chat4o", alias="AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    azure_openai_api_version: Optional[str] = Field(default="2024-10-21", alias="AZURE_OPENAI_API_VERSION")

    # Azure authentication
    azure_tenant_id: Optional[str] = Field(default=None, alias="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, alias="AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = Field(default=None, alias="AZURE_CLIENT_SECRET")

    # Storage
    azure_blob_storage_name: Optional[str] = Field(default=None, alias="AZURE_BLOB_STORAGE_NAME")
    azure_storage_container: Optional[str] = Field(default="research-documents", alias="AZURE_STORAGE_CONTAINER")

    # Document Intelligence
    azure_document_intelligence_endpoint: Optional[str] = Field(default=None, alias="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    azure_document_intelligence_key: Optional[str] = Field(default=None, alias="AZURE_DOCUMENT_INTELLIGENCE_KEY")

    # Application Insights / observability
    applicationinsights_connection_string: Optional[str] = Field(
        default=None,
        alias="APPLICATIONINSIGHTS_CONNECTION_STRING",
    )

    # Workflow discovery
    workflow_dir: Optional[str] = Field(default=None, alias="WORKFLOW_DIR")

    # CORS configuration (FastAPI still parses env separately, but expose here for observability)
    cors_origins: Union[str, List[str], None] = Field(default=None, alias="CORS_ORIGINS")

    # Convenience properties for legacy camel-case access
    @property
    def AZURE_OPENAI_ENDPOINT(self) -> Optional[str]:  # noqa: N802 (legacy compatibility)
        return self.azure_openai_endpoint

    @property
    def AZURE_OPENAI_API_KEY(self) -> Optional[str]:  # noqa: N802
        return self.azure_openai_api_key

    @property
    def AZURE_OPENAI_CHAT_DEPLOYMENT_NAME(self) -> Optional[str]:  # noqa: N802
        return self.azure_openai_deployment

    @property
    def AZURE_OPENAI_API_VERSION(self) -> Optional[str]:  # noqa: N802
        return self.azure_openai_api_version

    @property
    def AZURE_STORAGE_CONTAINER(self) -> Optional[str]:  # noqa: N802
        return self.azure_storage_container


__all__ = ["Settings"]

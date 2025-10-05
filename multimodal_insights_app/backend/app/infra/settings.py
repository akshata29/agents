"""
Application Settings and Configuration

Loads environment variables and provides typed configuration for multimodal insights app.
"""

import os
from typing import Optional, List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Azure OpenAI
    azure_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="gpt-4o", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="2024-08-01-preview", alias="AZURE_OPENAI_API_VERSION")
    
    # Azure Speech Services
    azure_speech_key: str = Field(..., alias="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field(..., alias="AZURE_SPEECH_REGION")
    
    # Azure Document Intelligence
    azure_document_intelligence_endpoint: str = Field(..., alias="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    azure_document_intelligence_key: str = Field(..., alias="AZURE_DOCUMENT_INTELLIGENCE_KEY")
    
    # Azure Storage
    azure_storage_connection_string: Optional[str] = Field(
        default=None,
        alias="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_blob_storage_name: str = Field(..., alias="AZURE_BLOB_STORAGE_NAME")
    azure_storage_container: str = Field(
        default="multimodal",
        alias="AZURE_STORAGE_CONTAINER"
    )
    
    # Azure Cosmos DB
    cosmosdb_endpoint: Optional[str] = Field(default=None, alias="COSMOSDB_ENDPOINT")
    cosmosdb_key: Optional[str] = Field(default=None, alias="COSMOSDB_KEY")  # Optional - use Azure AD if not provided
    cosmosdb_database: str = Field(default="finagent", alias="COSMOS_DB_DATABASE")
    cosmosdb_container: str = Field(default="multimodal", alias="COSMOS_DB_CONTAINER")
    
    # Azure Authentication (for managed identity/service principal)
    azure_tenant_id: Optional[str] = Field(default=None, alias="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, alias="AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = Field(default=None, alias="AZURE_CLIENT_SECRET")
    
    # Application Insights
    applicationinsights_connection_string: Optional[str] = Field(
        default=None,
        alias="APPLICATIONINSIGHTS_CONNECTION_STRING"
    )
    
    # File Upload Configuration
    max_upload_size: int = Field(default=104857600, alias="MAX_UPLOAD_SIZE")  # 100MB
    allowed_audio_extensions: List[str] = Field(
        default=[".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma"],
        alias="ALLOWED_AUDIO_EXTENSIONS"
    )
    allowed_video_extensions: List[str] = Field(
        default=[".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv"],
        alias="ALLOWED_VIDEO_EXTENSIONS"
    )
    allowed_pdf_extensions: List[str] = Field(
        default=[".pdf"],
        alias="ALLOWED_PDF_EXTENSIONS"
    )
    upload_directory: str = Field(default="uploads", alias="UPLOAD_DIRECTORY")
    data_directory: str = Field(default="data", alias="DATA_DIRECTORY")
    
    # Backend Configuration
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    cors_origins: Union[str, List[str]] = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS"
    )
    
    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string to list."""
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(',') if origin.strip()]
            return origins
        elif isinstance(v, list):
            return v
        return [str(v)]
    
    # Agent Configuration
    max_concurrent_agents: int = Field(default=5, alias="MAX_CONCURRENT_AGENTS")
    default_agent_timeout: int = Field(default=300, alias="DEFAULT_AGENT_TIMEOUT")
    enable_agent_telemetry: bool = Field(default=True, alias="ENABLE_AGENT_TELEMETRY")
    
    # Execution Configuration
    max_sequential_steps: int = Field(default=10, alias="MAX_SEQUENTIAL_STEPS")
    handoff_max_iterations: int = Field(default=10, alias="HANDOFF_MAX_ITERATIONS")
    group_chat_max_turns: int = Field(default=40, alias="GROUP_CHAT_MAX_TURNS")
    
    # Uppercase aliases for compatibility
    @property
    def COSMOSDB_ENDPOINT(self) -> Optional[str]:
        return self.cosmosdb_endpoint
    
    @property
    def COSMOSDB_DATABASE(self) -> str:
        return self.cosmosdb_database
    
    @property
    def COSMOSDB_CONTAINER(self) -> str:
        return self.cosmosdb_container
    
    @property
    def AZURE_OPENAI_ENDPOINT(self) -> str:
        return self.azure_openai_endpoint
    
    @property
    def AZURE_OPENAI_API_KEY(self) -> str:
        return self.azure_openai_api_key
    
    @property
    def AZURE_OPENAI_API_VERSION(self) -> str:
        return self.azure_openai_api_version
    
    @property
    def AZURE_OPENAI_DEPLOYMENT(self) -> str:
        return self.azure_openai_deployment
    
    @property
    def AZURE_SPEECH_KEY(self) -> str:
        return self.azure_speech_key
    
    @property
    def AZURE_SPEECH_REGION(self) -> str:
        return self.azure_speech_region
    
    @property
    def AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT(self) -> str:
        return self.azure_document_intelligence_endpoint
    
    @property
    def AZURE_DOCUMENT_INTELLIGENCE_KEY(self) -> str:
        return self.azure_document_intelligence_key
    
    @property
    def LOG_LEVEL(self) -> str:
        return "INFO"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        return [self.cors_origins]

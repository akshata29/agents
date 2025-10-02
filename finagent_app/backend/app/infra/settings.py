"""
Application Settings and Configuration

Loads environment variables and provides typed configuration.
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
    
    # Financial Data APIs
    fmp_api_key: Optional[str] = Field(default=None, alias="FMP_API_KEY")
    yahoo_finance_enabled: bool = Field(default=True, alias="YAHOO_FINANCE_ENABLED")
    sec_api_key: Optional[str] = Field(default=None, alias="SEC_API_KEY")
    sec_user_agent: str = Field(
        default="FinAgent Research Bot contact@example.com",
        alias="SEC_USER_AGENT"
    )
    
    # Azure Storage
    azure_storage_connection_string: Optional[str] = Field(
        default=None,
        alias="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_storage_container: str = Field(
        default="financial-reports",
        alias="AZURE_STORAGE_CONTAINER"
    )
    
    # Azure Cosmos DB
    cosmos_db_endpoint: Optional[str] = Field(default=None, alias="COSMOS_DB_ENDPOINT")
    cosmos_db_key: Optional[str] = Field(default=None, alias="COSMOS_DB_KEY")
    cosmos_db_database: str = Field(default="finagent", alias="COSMOS_DB_DATABASE")
    cosmos_db_container: str = Field(default="sessions", alias="COSMOS_DB_CONTAINER")
    
    # Application Insights
    applicationinsights_connection_string: Optional[str] = Field(
        default=None,
        alias="APPLICATIONINSIGHTS_CONNECTION_STRING"
    )
    
    # MCP Configuration
    mcp_enabled: bool = Field(default=True, alias="MCP_ENABLED")
    mcp_server_port: int = Field(default=8100, alias="MCP_SERVER_PORT")
    
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
            # Split by comma and strip whitespace
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
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins

    def model_dump_safe(self) -> dict:
        """Dump settings without sensitive data."""
        data = self.model_dump()
        # Mask sensitive fields
        sensitive_fields = [
            'azure_openai_api_key', 'fmp_api_key', 'sec_api_key',
            'azure_storage_connection_string', 'cosmos_db_key',
            'applicationinsights_connection_string'
        ]
        for field in sensitive_fields:
            if field in data and data[field]:
                data[field] = "***REDACTED***"
        return data


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

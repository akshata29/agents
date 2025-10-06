"""
Application Settings and Configuration

Centralized configuration management using Pydantic settings with environment variable support.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureOpenAISettings(BaseSettings):
    """Azure OpenAI specific settings."""
    
    endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    api_key: str = Field(..., description="Azure OpenAI API key")
    api_version: str = Field(default="2024-10-21", description="Azure OpenAI API version")
    chat_deployment_name: str = Field(..., description="Chat model deployment name")
    embedding_deployment_name: Optional[str] = Field(default=None, description="Embedding model deployment name")
    
    model_config = SettingsConfigDict(
        env_prefix="AZURE_OPENAI_",
        env_file=[".env", "../.env", "../../.env"],  # Search for .env files
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from YAML
    )


class MCPSettings(BaseSettings):
    """Model Context Protocol settings."""
    
    enabled: bool = Field(default=True, description="Enable MCP integration")
    server_host: str = Field(default="localhost", description="MCP server host")
    server_port: int = Field(default=8080, description="MCP server port")
    tool_timeout: int = Field(default=60, description="Tool execution timeout in seconds")
    max_concurrent_tools: int = Field(default=10, description="Maximum concurrent tool executions")
    
    # Built-in tool configurations
    enable_web_search: bool = Field(default=True, description="Enable web search tool")
    enable_file_operations: bool = Field(default=True, description="Enable file operations tool")
    enable_database: bool = Field(default=False, description="Enable database tool")
    
    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        case_sensitive=False,
        extra="ignore"
    )


class SecuritySettings(BaseSettings):
    """Security and authentication settings."""
    
    secret_key: str = Field(default_factory=lambda: "change-me-in-production-" + str(os.urandom(16).hex()), description="Secret key for encryption")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    
    # API security
    enable_rate_limiting: bool = Field(default=True, description="Enable API rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    
    # Audit logging
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    audit_log_level: str = Field(default="INFO", description="Audit log level")
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        case_sensitive=False,
        extra="ignore"
    )


class ObservabilitySettings(BaseSettings):
    """Microsoft Agent Framework Observability settings (OpenTelemetry-based)."""
    
    enabled: bool = Field(default=True, description="Enable MAF observability")
    
    # Sensitive data logging (prompts, responses, function arguments)
    enable_sensitive_data: bool = Field(default=False, description="Enable logging of sensitive data")
    
    # OTLP endpoint (Jaeger, Zipkin, OpenTelemetry Collector, etc.)
    otlp_endpoint: Optional[str] = Field(default=None, description="OTLP endpoint URL (e.g., http://localhost:4317)")
    
    # Azure Application Insights
    applicationinsights_connection_string: Optional[str] = Field(
        default=None, 
        description="Azure Application Insights connection string"
    )
    
    # VS Code AI Toolkit extension port
    vs_code_extension_port: int = Field(default=4317, description="VS Code AI Toolkit extension port")
    
    model_config = SettingsConfigDict(
        env_prefix="OBSERVABILITY_",
        case_sensitive=False,
        extra="ignore"
    )


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(default="sqlite:///./magentic_foundation.db", description="Database URL")
    echo: bool = Field(default=False, description="Enable SQL echo")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum pool overflow")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")
    redis_db: int = Field(default=0, description="Redis database number")
    
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        case_sensitive=False,
        extra="ignore"
    )


class APISettings(BaseSettings):
    """API server settings."""
    
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # CORS settings
    cors_enabled: bool = Field(default=True, description="Enable CORS")
    cors_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    cors_methods: List[str] = Field(default=["*"], description="Allowed CORS methods")
    
    # Request limits
    max_request_size: int = Field(default=10 * 1024 * 1024, description="Max request size in bytes")
    request_timeout: int = Field(default=300, description="Request timeout in seconds")
    
    model_config = SettingsConfigDict(
        env_prefix="API_",
        case_sensitive=False,
        extra="ignore"
    )


class AgentSettings(BaseSettings):
    """Agent-specific settings."""
    
    # Execution limits
    max_concurrent_executions: int = Field(default=10, description="Maximum concurrent executions")
    execution_timeout: int = Field(default=600, description="Execution timeout in seconds")
    
    # Reasoning settings
    max_reasoning_steps: int = Field(default=50, description="Maximum reasoning steps in ReAct")
    reasoning_timeout: int = Field(default=300, description="Reasoning timeout in seconds")
    enable_backtracking: bool = Field(default=True, description="Enable plan backtracking")
    
    # Agent lifecycle
    agent_startup_timeout: int = Field(default=60, description="Agent startup timeout")
    agent_health_check_interval: int = Field(default=300, description="Agent health check interval")
    
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        case_sensitive=False,
        extra="ignore"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # File logging
    enable_file_logging: bool = Field(default=True, description="Enable file logging")
    log_file: str = Field(default="magentic_foundation.log", description="Log file path")
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Max log file size")
    backup_count: int = Field(default=5, description="Number of backup log files")
    
    # Structured logging
    structured_logging: bool = Field(default=True, description="Enable structured logging")
    json_logs: bool = Field(default=False, description="Use JSON log format")
    
    model_config = SettingsConfigDict(
        env_prefix="LOGGING_",
        case_sensitive=False,
        extra="ignore"
    )


class Settings(BaseSettings):
    """
    Main application settings.
    
    Combines all configuration sections and provides environment-based configuration
    with support for .env files and environment variables.
    """
    
    # Application metadata
    app_name: str = Field(default="Foundation Framework", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Configuration sections
    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    # Workflow settings
    workflow_dir: str = Field(default="./workflows", description="Directory for workflow definitions")
    max_concurrent_workflows: int = Field(default=10, description="Maximum concurrent workflows")
    workflow_timeout: int = Field(default=600, description="Workflow execution timeout in seconds")
    
    # Convenience properties for backward compatibility
    @property
    def max_reasoning_steps(self) -> int:
        return self.agents.max_reasoning_steps
    
    @property
    def reasoning_timeout(self) -> int:
        return self.agents.reasoning_timeout
    
    @property
    def enable_backtracking(self) -> bool:
        return self.agents.enable_backtracking
    
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env", "../../.env"],  # Search in current, parent, and grandparent directories
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__"  # Support nested environment variables like AZURE__OPENAI__ENDPOINT
    )
    
    def __init__(self, _env_file: Optional[Union[str, Path]] = None, **data):
        """Initialize settings with support for both .env and YAML config files."""
        # If a config file is provided and it's a YAML file, load it
        if _env_file and (str(_env_file).endswith('.yaml') or str(_env_file).endswith('.yml')):
            import yaml
            config_path = Path(_env_file) if isinstance(_env_file, str) else _env_file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    yaml_data = yaml.safe_load(f)
                    if yaml_data:
                        data.update(yaml_data)
        
        # Initialize with data (will also load from .env files in model_config)
        super().__init__(**data)
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        import logging
        import structlog
        from logging.handlers import RotatingFileHandler
        
        # Configure standard logging
        logging.basicConfig(
            level=getattr(logging, self.logging.level.upper()),
            format=self.logging.format
        )
        
        # Setup file logging if enabled
        if self.logging.enable_file_logging:
            file_handler = RotatingFileHandler(
                self.logging.log_file,
                maxBytes=self.logging.max_file_size,
                backupCount=self.logging.backup_count
            )
            file_handler.setFormatter(
                logging.Formatter(self.logging.format)
            )
            logging.getLogger().addHandler(file_handler)
        
        # Configure structured logging
        if self.logging.structured_logging:
            structlog.configure(
                processors=[
                    structlog.processors.TimeStamper(fmt="ISO"),
                    structlog.processors.add_log_level,
                    structlog.processors.StackInfoRenderer(),
                    structlog.dev.ConsoleRenderer() if not self.logging.json_logs 
                    else structlog.processors.JSONRenderer()
                ],
                wrapper_class=structlog.make_filtering_bound_logger(
                    getattr(logging, self.logging.level.upper())
                ),
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=True,
            )
    
    @classmethod
    def load_from_file(cls, config_file: Union[str, Path]) -> "Settings":
        """Load settings from a configuration file."""
        import yaml
        import json
        
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                config_data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        
        return cls(**config_data)
    
    def save_to_file(self, config_file: Union[str, Path], format: str = "yaml") -> None:
        """Save current settings to a configuration file."""
        import yaml
        import json
        
        config_path = Path(config_file)
        config_data = self.model_dump()
        
        with open(config_path, 'w') as f:
            if format.lower() in ['yaml', 'yml']:
                yaml.safe_dump(config_data, f, default_flow_style=False)
            elif format.lower() == 'json':
                json.dump(config_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")
    
    def model_dump(self, exclude_secrets: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Export model data with option to exclude sensitive information.
        
        Args:
            exclude_secrets: If True, excludes sensitive fields like API keys
            **kwargs: Additional arguments for model_dump
            
        Returns:
            Dictionary representation of the settings
        """
        data = super().model_dump(**kwargs)
        
        if exclude_secrets:
            # Remove sensitive fields
            sensitive_paths = [
                "azure_openai.api_key",
                "security.secret_key",
                "database.url",
                "redis_url"
            ]
            
            for path in sensitive_paths:
                keys = path.split('.')
                current = data
                for key in keys[:-1]:
                    if key in current and isinstance(current[key], dict):
                        current = current[key]
                    else:
                        break
                else:
                    if keys[-1] in current:
                        current[keys[-1]] = "***REDACTED***"
        
        return data
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
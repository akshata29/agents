"""
Application Settings and Configuration

Loads environment variables and provides typed configuration for advisor productivity app.
"""

import os
from typing import Optional, List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application configuration settings for Advisor Productivity App."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ========================================
    # Azure OpenAI Configuration
    # ========================================
    azure_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="gpt-4", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="2024-08-01-preview", alias="AZURE_OPENAI_API_VERSION")
    
    # ========================================
    # Azure Speech Services (for transcription)
    # ========================================
    azure_speech_key: Optional[str] = Field(default=None, alias="AZURE_SPEECH_KEY")
    azure_speech_region: Optional[str] = Field(default=None, alias="AZURE_SPEECH_REGION")
    azure_speech_language: str = Field(default="en-US", alias="AZURE_SPEECH_LANGUAGE")
    enable_speaker_diarization: bool = Field(default=True, alias="ENABLE_SPEAKER_DIARIZATION")
    
    # ========================================
    # Azure Language Service (for PII detection)
    # ========================================
    azure_language_key: Optional[str] = Field(default=None, alias="AZURE_LANGUAGE_KEY")
    azure_language_endpoint: Optional[str] = Field(default=None, alias="AZURE_LANGUAGE_ENDPOINT")
    
    # ========================================
    # Azure Cosmos DB (for session persistence)
    # ========================================
    cosmosdb_endpoint: Optional[str] = Field(default=None, alias="COSMOSDB_ENDPOINT")
    cosmosdb_key: Optional[str] = Field(default=None, alias="COSMOSDB_KEY")
    cosmosdb_database: str = Field(default="advisor_productivity", alias="COSMOS_DB_DATABASE")
    cosmosdb_container: str = Field(default="sessions", alias="COSMOS_DB_CONTAINER")
    
    # ========================================
    # Azure Storage (for audio file storage)
    # ========================================
    azure_storage_connection_string: Optional[str] = Field(
        default=None,
        alias="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_blob_storage_name: Optional[str] = Field(default=None, alias="AZURE_BLOB_STORAGE_NAME")
    azure_storage_container: str = Field(
        default="advisor-sessions",
        alias="AZURE_STORAGE_CONTAINER"
    )
    
    # ========================================
    # Azure Authentication (managed identity/service principal)
    # ========================================
    azure_tenant_id: Optional[str] = Field(default=None, alias="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, alias="AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = Field(default=None, alias="AZURE_CLIENT_SECRET")
    
    # ========================================
    # Application Insights (monitoring)
    # ========================================
    applicationinsights_connection_string: Optional[str] = Field(
        default=None,
        alias="APPLICATIONINSIGHTS_CONNECTION_STRING"
    )
    
    # ========================================
    # Audio Upload Configuration
    # ========================================
    max_upload_size: int = Field(default=524288000, alias="MAX_UPLOAD_SIZE")  # 500MB for long sessions
    allowed_audio_extensions: List[str] = Field(
        default=[".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma", ".aac"],
        alias="ALLOWED_AUDIO_EXTENSIONS"
    )
    upload_directory: str = Field(default="uploads", alias="UPLOAD_DIRECTORY")
    data_directory: str = Field(default="data", alias="DATA_DIRECTORY")
    
    # Audio processing
    audio_chunk_duration_ms: int = Field(default=5000, alias="AUDIO_CHUNK_DURATION_MS")  # 5 second chunks
    enable_real_time_transcription: bool = Field(default=True, alias="ENABLE_REAL_TIME_TRANSCRIPTION")
    
    # ========================================
    # Backend Configuration
    # ========================================
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
    
    # ========================================
    # Agent Configuration
    # ========================================
    max_concurrent_agents: int = Field(default=5, alias="MAX_CONCURRENT_AGENTS")
    default_agent_timeout: int = Field(default=300, alias="DEFAULT_AGENT_TIMEOUT")
    enable_agent_telemetry: bool = Field(default=True, alias="ENABLE_AGENT_TELEMETRY")
    
    # ========================================
    # Sentiment Analysis Configuration
    # ========================================
    sentiment_analysis_enabled: bool = Field(default=True, alias="SENTIMENT_ANALYSIS_ENABLED")
    sentiment_window_seconds: int = Field(default=30, alias="SENTIMENT_WINDOW_SECONDS")  # Analyze every 30s
    
    # Investment-specific emotions to track
    tracked_emotions: List[str] = Field(
        default=["confidence", "concern", "excitement", "confusion", "risk_averse", "risk_seeking"],
        alias="TRACKED_EMOTIONS"
    )
    
    # ========================================
    # Recommendation Engine Configuration
    # ========================================
    recommendation_enabled: bool = Field(default=True, alias="RECOMMENDATION_ENABLED")
    recommendation_confidence_threshold: float = Field(default=0.7, alias="RECOMMENDATION_CONFIDENCE_THRESHOLD")
    max_recommendations_per_session: int = Field(default=10, alias="MAX_RECOMMENDATIONS_PER_SESSION")
    
    # Recommendation types to enable
    enabled_recommendation_types: List[str] = Field(
        default=[
            "portfolio_allocation",
            "risk_mitigation",
            "retirement_planning",
            "rebalancing",
            "product_suggestion"
        ],
        alias="ENABLED_RECOMMENDATION_TYPES"
    )
    
    # ========================================
    # PII Protection Configuration
    # ========================================
    pii_detection_enabled: bool = Field(default=True, alias="PII_DETECTION_ENABLED")
    auto_redact_pii: bool = Field(default=True, alias="AUTO_REDACT_PII")
    
    # PII types to detect and redact
    pii_types_to_redact: List[str] = Field(
        default=["Person", "SSN", "CreditCardNumber", "BankAccountNumber", "PhoneNumber", "Email", "IPAddress"],
        alias="PII_TYPES_TO_REDACT"
    )
    
    # ========================================
    # Summarization Configuration
    # ========================================
    enable_auto_summarization: bool = Field(default=True, alias="ENABLE_AUTO_SUMMARIZATION")
    summary_trigger_threshold_minutes: int = Field(
        default=15,
        alias="SUMMARY_TRIGGER_THRESHOLD_MINUTES"
    )  # Auto-summarize after 15 mins
    
    default_summary_type: str = Field(default="detailed", alias="DEFAULT_SUMMARY_TYPE")  # brief, detailed, comprehensive
    default_summary_persona: str = Field(default="advisor", alias="DEFAULT_SUMMARY_PERSONA")  # advisor, compliance, client
    
    # ========================================
    # Compliance Configuration
    # ========================================
    compliance_mode_enabled: bool = Field(default=True, alias="COMPLIANCE_MODE_ENABLED")
    audit_trail_enabled: bool = Field(default=True, alias="AUDIT_TRAIL_ENABLED")
    require_recommendation_approval: bool = Field(default=True, alias="REQUIRE_RECOMMENDATION_APPROVAL")
    
    # ========================================
    # Session Configuration
    # ========================================
    max_session_duration_hours: int = Field(default=4, alias="MAX_SESSION_DURATION_HOURS")
    auto_end_session_on_inactivity_minutes: int = Field(
        default=30,
        alias="AUTO_END_SESSION_ON_INACTIVITY_MINUTES"
    )
    
    # ========================================
    # Execution Configuration
    # ========================================
    max_sequential_steps: int = Field(default=10, alias="MAX_SEQUENTIAL_STEPS")
    handoff_max_iterations: int = Field(default=10, alias="HANDOFF_MAX_ITERATIONS")
    group_chat_max_turns: int = Field(default=40, alias="GROUP_CHAT_MAX_TURNS")
    
    # ========================================
    # Logging Configuration
    # ========================================
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_debug_logging: bool = Field(default=False, alias="ENABLE_DEBUG_LOGGING")
    
    # ========================================
    # Uppercase Property Aliases (for compatibility)
    # ========================================
    
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
    def AZURE_LANGUAGE_KEY(self) -> str:
        return self.azure_language_key
    
    @property
    def AZURE_LANGUAGE_ENDPOINT(self) -> str:
        return self.azure_language_endpoint


# Singleton instance
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the settings singleton instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

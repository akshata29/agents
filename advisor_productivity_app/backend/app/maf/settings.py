"""Minimal settings structures for local Magentic orchestrator integration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AzureOpenAISettings(BaseModel):
    """Subset of Azure OpenAI configuration used by advisor orchestrator."""

    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    chat_deployment_name: Optional[str] = None
    api_version: Optional[str] = None


class FrameworkSettings(BaseModel):
    """Lightweight container mirroring the framework settings contract."""

    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)

    class Config:
        arbitrary_types_allowed = True

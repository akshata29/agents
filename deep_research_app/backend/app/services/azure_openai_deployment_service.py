"""
Azure OpenAI Deployment Management Service

This service fetches available Azure OpenAI deployments from Azure AI Foundry
using the Azure Management SDK for dynamic model configuration.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.cognitiveservices.aio import CognitiveServicesManagementClient
from azure.core.exceptions import AzureError

logger = logging.getLogger(__name__)


@dataclass
class DeploymentInfo:
    """Information about an Azure OpenAI deployment"""
    deployment_name: str  # The deployment name used for API calls
    model_name: str       # The actual model name (e.g., gpt-4o-mini)
    model_version: str    # Model version
    model_type: str       # 'chat' or 'embedding'
    sku_name: str         # SKU information (Standard, GlobalStandard, etc.)
    capacity: int         # Current capacity
    capabilities: Dict[str, Any]  # Model capabilities
    provisioning_state: str  # Deployment state (Succeeded, Creating, etc.)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class AzureOpenAIDeploymentService:
    """
    Service for managing Azure OpenAI deployments via Azure Management SDK.
    
    Uses azure-mgmt-cognitiveservices for listing deployments instead of raw REST API.
    """
    
    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        account_name: str
    ):
        """
        Initialize the deployment service.
        
        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            account_name: Azure OpenAI account name
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.account_name = account_name
        
        self.credential: Optional[DefaultAzureCredential] = None
        self.client: Optional[CognitiveServicesManagementClient] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.credential = DefaultAzureCredential()
        self.client = CognitiveServicesManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.close()
        if self.credential:
            await self.credential.close()
    
    async def get_deployments(self) -> List[DeploymentInfo]:
        """
        Fetch all deployments from Azure OpenAI account using Management SDK.
        
        Returns:
            List of DeploymentInfo objects with deployment details
        """
        if not self.client:
            logger.error("Client not initialized. Use async context manager.")
            return []
        
        try:
            logger.info(
                f"Fetching deployments for account: {self.account_name} "
                f"in resource group: {self.resource_group}"
            )
            
            deployments = []
            
            # Use SDK to list deployments
            async for deployment in self.client.deployments.list(
                resource_group_name=self.resource_group,
                account_name=self.account_name
            ):
                try:
                    deployment_info = self._parse_deployment(deployment)
                    if deployment_info:
                        deployments.append(deployment_info)
                        logger.debug(
                            f"Parsed deployment: {deployment_info.deployment_name} "
                            f"({deployment_info.model_name}, {deployment_info.model_type})"
                        )
                except Exception as e:
                    logger.warning(f"Failed to parse deployment: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(deployments)} deployments")
            return deployments
            
        except AzureError as e:
            logger.error(f"Azure error fetching deployments: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching deployments: {e}", exc_info=True)
            return []
    
    def _parse_deployment(self, deployment: Any) -> Optional[DeploymentInfo]:
        """
        Parse deployment object from Azure SDK response.
        
        Args:
            deployment: Deployment object from Azure SDK
            
        Returns:
            DeploymentInfo object or None if parsing fails
        """
        try:
            properties = deployment.properties
            model_info = properties.model if hasattr(properties, 'model') else {}
            sku = deployment.sku if hasattr(deployment, 'sku') else {}
            
            deployment_name = deployment.name or ""
            model_name = model_info.name if hasattr(model_info, 'name') else ""
            model_version = model_info.version if hasattr(model_info, 'version') else ""
            sku_name = sku.name if hasattr(sku, 'name') else ""
            capacity = sku.capacity if hasattr(sku, 'capacity') else 0
            
            # Get capabilities
            capabilities = {}
            if hasattr(properties, 'capabilities'):
                if isinstance(properties.capabilities, dict):
                    capabilities = properties.capabilities
                else:
                    # Convert capabilities object to dict
                    capabilities = {
                        k: str(v) for k, v in vars(properties.capabilities).items()
                        if not k.startswith('_')
                    }
            
            provisioning_state = properties.provisioning_state if hasattr(properties, 'provisioning_state') else ""
            
            # Determine model type based on model name
            model_type = self._determine_model_type(model_name)
            
            return DeploymentInfo(
                deployment_name=deployment_name,
                model_name=model_name,
                model_version=model_version,
                model_type=model_type,
                sku_name=sku_name,
                capacity=capacity,
                capabilities=capabilities,
                provisioning_state=provisioning_state
            )
            
        except Exception as e:
            logger.error(f"Failed to parse deployment: {e}")
            return None
    
    def _determine_model_type(self, model_name: str) -> str:
        """
        Determine model type from model name.
        
        Args:
            model_name: Model name (e.g., 'gpt-4o', 'text-embedding-3-large')
            
        Returns:
            'chat', 'embedding', or 'other'
        """
        model_name_lower = model_name.lower()
        
        if 'embedding' in model_name_lower:
            return 'embedding'
        elif any(keyword in model_name_lower for keyword in ['gpt', 'o1', 'o3']):
            return 'chat'
        else:
            return 'other'
    
    async def get_chat_deployments(self) -> List[DeploymentInfo]:
        """Get only chat model deployments"""
        all_deployments = await self.get_deployments()
        chat_deployments = [d for d in all_deployments if d.model_type == 'chat']
        logger.info(f"Found {len(chat_deployments)} chat model deployments")
        return chat_deployments
    
    async def get_embedding_deployments(self) -> List[DeploymentInfo]:
        """Get only embedding model deployments"""
        all_deployments = await self.get_deployments()
        embedding_deployments = [d for d in all_deployments if d.model_type == 'embedding']
        logger.info(f"Found {len(embedding_deployments)} embedding model deployments")
        return embedding_deployments
    
    async def get_deployments_summary(self) -> Dict[str, Any]:
        """
        Get a summary of available deployments grouped by type.
        
        Returns:
            Dictionary with deployment summary
        """
        deployments = await self.get_deployments()
        
        chat_models = [d for d in deployments if d.model_type == 'chat']
        embedding_models = [d for d in deployments if d.model_type == 'embedding']
        other_models = [d for d in deployments if d.model_type == 'other']
        
        return {
            "total_deployments": len(deployments),
            "chat_models": [d.to_dict() for d in chat_models],
            "embedding_models": [d.to_dict() for d in embedding_models],
            "other_models": [d.to_dict() for d in other_models],
            "account_info": {
                "account_name": self.account_name,
                "resource_group": self.resource_group,
                "subscription_id": self.subscription_id
            }
        }


# Singleton instance factory
_service_instance: Optional[AzureOpenAIDeploymentService] = None


def get_deployment_service(
    subscription_id: str,
    resource_group: str,
    account_name: str
) -> AzureOpenAIDeploymentService:
    """
    Get or create deployment service instance.
    
    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        account_name: Azure OpenAI account name
        
    Returns:
        AzureOpenAIDeploymentService instance
    """
    return AzureOpenAIDeploymentService(
        subscription_id=subscription_id,
        resource_group=resource_group,
        account_name=account_name
    )

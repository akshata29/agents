"""
Model Configuration Service

Manages model selection by research depth with intelligent fallback logic.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Model configuration for a specific research depth"""
    deployment_name: str
    model_name: str
    temperature: float
    max_tokens: int
    use_reasoning_model: bool = False
    top_p: float = 0.95
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


# Phase 4: Model Selection by Depth
# Different models optimized for different research depths
MODEL_CONFIGS_BY_DEPTH = {
    "quick": {
        "preferred_models": ["gpt-4o-mini", "gpt-35-turbo"],  # Faster, cheaper
        "temperature": 0.3,  # More focused
        "max_tokens": 2000,
        "use_reasoning_model": False,
        "description": "Fast models for quick overviews"
    },
    "standard": {
        "preferred_models": ["gpt-4o-mini", "gpt-4o"],
        "temperature": 0.5,  # Balanced
        "max_tokens": 4000,
        "use_reasoning_model": False,
        "description": "Balanced models for standard analysis"
    },
    "comprehensive": {
        "preferred_models": ["gpt-4o", "gpt-4-turbo"],  # More capable
        "temperature": 0.6,  # More creative
        "max_tokens": 6000,
        "use_reasoning_model": False,
        "description": "Advanced models for deep analysis"
    },
    "exhaustive": {
        "preferred_models": ["gpt-4o", "o1-preview", "o3-mini"],  # Most capable
        "temperature": 0.7,  # Most creative
        "max_tokens": 8000,
        "use_reasoning_model": True,  # Use reasoning models when available
        "description": "Most capable models including reasoning models"
    }
}


class ModelConfigService:
    """
    Service for selecting appropriate models based on research depth.
    
    Features:
    - Depth-specific model preferences
    - Intelligent fallback to available models
    - Temperature and token limits by depth
    - Support for reasoning models (o1, o3)
    """
    
    def __init__(self, available_deployments: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize model config service.
        
        Args:
            available_deployments: List of available deployment info dicts
        """
        self.available_deployments = available_deployments or []
        self._deployment_map = self._build_deployment_map()
    
    def _build_deployment_map(self) -> Dict[str, str]:
        """
        Build a map from model names to deployment names.
        
        Returns:
            Dictionary mapping model_name -> deployment_name
        """
        deployment_map = {}
        for deployment in self.available_deployments:
            model_name = deployment.get("model_name", "")
            deployment_name = deployment.get("deployment_name", "")
            if model_name and deployment_name:
                deployment_map[model_name] = deployment_name
                logger.debug(f"Mapped model '{model_name}' to deployment '{deployment_name}'")
        
        return deployment_map
    
    def get_model_config_for_depth(
        self,
        depth: str,
        override_model: Optional[str] = None
    ) -> ModelConfig:
        """
        Get optimal model configuration for a research depth.
        
        Args:
            depth: Research depth (quick, standard, comprehensive, exhaustive)
            override_model: Optional manual model selection override
            
        Returns:
            ModelConfig with selected model and parameters
        """
        depth_config = MODEL_CONFIGS_BY_DEPTH.get(depth, MODEL_CONFIGS_BY_DEPTH["comprehensive"])
        
        # If manual override provided, use it
        if override_model:
            deployment_name = self._find_deployment_for_model(override_model)
            if deployment_name:
                logger.info(f"Using manual override model: {override_model} -> {deployment_name}")
                return ModelConfig(
                    deployment_name=deployment_name,
                    model_name=override_model,
                    temperature=depth_config["temperature"],
                    max_tokens=depth_config["max_tokens"],
                    use_reasoning_model=self._is_reasoning_model(override_model)
                )
            else:
                logger.warning(f"Override model '{override_model}' not found in deployments, using auto-select")
        
        # Auto-select best available model for depth
        selected_model = self._select_best_model(depth_config["preferred_models"])
        
        if not selected_model:
            # Fallback to any available chat model
            logger.warning(f"No preferred models found for depth '{depth}', using fallback")
            selected_model = self._get_fallback_model()
        
        deployment_name = self._find_deployment_for_model(selected_model)
        
        logger.info(
            f"Selected model for depth '{depth}': {selected_model} -> {deployment_name} "
            f"(temp={depth_config['temperature']}, max_tokens={depth_config['max_tokens']})"
        )
        
        return ModelConfig(
            deployment_name=deployment_name or selected_model,
            model_name=selected_model,
            temperature=depth_config["temperature"],
            max_tokens=depth_config["max_tokens"],
            use_reasoning_model=depth_config.get("use_reasoning_model", False)
        )
    
    def _select_best_model(self, preferred_models: List[str]) -> Optional[str]:
        """
        Select the best available model from preferred list.
        
        Args:
            preferred_models: List of model names in order of preference
            
        Returns:
            Best available model name or None
        """
        for model_name in preferred_models:
            # Check if model name exists in deployments (exact or partial match)
            if self._is_model_available(model_name):
                logger.debug(f"Found preferred model: {model_name}")
                return model_name
        
        return None
    
    def _is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available in deployments.
        
        Args:
            model_name: Model name to check
            
        Returns:
            True if model is available
        """
        model_name_lower = model_name.lower()
        
        for deployment in self.available_deployments:
            deployment_model = deployment.get("model_name", "").lower()
            
            # Exact match
            if deployment_model == model_name_lower:
                return True
            
            # Partial match (e.g., 'gpt-4o' matches 'gpt-4o-2024-05-13')
            if model_name_lower in deployment_model or deployment_model.startswith(model_name_lower):
                return True
        
        return False
    
    def _find_deployment_for_model(self, model_name: str) -> Optional[str]:
        """
        Find deployment name for a given model name.
        
        Args:
            model_name: Model name
            
        Returns:
            Deployment name or None
        """
        # Direct lookup
        if model_name in self._deployment_map:
            return self._deployment_map[model_name]
        
        # Partial match
        model_name_lower = model_name.lower()
        for deployment in self.available_deployments:
            deployment_model = deployment.get("model_name", "").lower()
            
            if model_name_lower in deployment_model or deployment_model.startswith(model_name_lower):
                return deployment.get("deployment_name")
        
        return None
    
    def _get_fallback_model(self) -> str:
        """
        Get fallback model when no preferred models are available.
        
        Returns:
            Fallback model name
        """
        # Try to find any GPT-4 variant
        for deployment in self.available_deployments:
            model_name = deployment.get("model_name", "").lower()
            if "gpt-4" in model_name:
                return deployment.get("model_name", "")
        
        # Try GPT-3.5
        for deployment in self.available_deployments:
            model_name = deployment.get("model_name", "").lower()
            if "gpt-3" in model_name or "gpt-35" in model_name:
                return deployment.get("model_name", "")
        
        # Last resort: use first available chat model
        for deployment in self.available_deployments:
            if deployment.get("model_type") == "chat":
                logger.warning(f"Using last-resort fallback: {deployment.get('model_name')}")
                return deployment.get("model_name", "")
        
        # If no deployments at all, return default
        logger.error("No chat deployments available! Using default 'gpt-4o'")
        return "gpt-4o"
    
    def _is_reasoning_model(self, model_name: str) -> bool:
        """
        Check if a model is a reasoning model (o1, o3 series).
        
        Args:
            model_name: Model name
            
        Returns:
            True if reasoning model
        """
        model_name_lower = model_name.lower()
        return any(prefix in model_name_lower for prefix in ["o1-", "o3-", "o1preview", "o3mini"])
    
    def get_available_models_for_depth(self, depth: str) -> List[Dict[str, Any]]:
        """
        Get list of available models suitable for a depth level.
        
        Args:
            depth: Research depth
            
        Returns:
            List of model info dictionaries
        """
        depth_config = MODEL_CONFIGS_BY_DEPTH.get(depth, MODEL_CONFIGS_BY_DEPTH["comprehensive"])
        preferred_models = depth_config["preferred_models"]
        
        available_models = []
        
        for model_name in preferred_models:
            deployment_name = self._find_deployment_for_model(model_name)
            if deployment_name:
                # Find full deployment info
                for deployment in self.available_deployments:
                    if deployment.get("deployment_name") == deployment_name:
                        available_models.append({
                            "model_name": deployment.get("model_name"),
                            "deployment_name": deployment_name,
                            "model_version": deployment.get("model_version"),
                            "is_reasoning_model": self._is_reasoning_model(deployment.get("model_name", "")),
                            "recommended_for_depth": depth
                        })
                        break
        
        return available_models
    
    def get_all_depth_configs(self) -> Dict[str, Any]:
        """
        Get model configurations for all depth levels.
        
        Returns:
            Dictionary with configs for each depth
        """
        return {
            depth: {
                "config": config,
                "available_models": self.get_available_models_for_depth(depth)
            }
            for depth, config in MODEL_CONFIGS_BY_DEPTH.items()
        }

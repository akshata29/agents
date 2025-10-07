import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api';
import { Cpu, Zap, AlertCircle, CheckCircle2, Info } from 'lucide-react';

interface DeploymentInfo {
  deployment_name: string;
  model_name: string;
  model_version: string;
  capacity: number;
  sku_name: string;
}

interface ModelConfig {
  deployment_name: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  use_reasoning_model: boolean;
  preferred_models: string[];
}

interface ModelSelectorProps {
  depth: 'quick' | 'standard' | 'comprehensive' | 'exhaustive';
  selectedModel?: string;
  onModelSelect: (deploymentName: string) => void;
}

export function ModelSelector({ depth, selectedModel, onModelSelect }: ModelSelectorProps) {
  const [autoSelect, setAutoSelect] = useState(true);

  // Fetch available deployments
  const { data: deployments, isLoading: deploymentsLoading, error: deploymentsError } = useQuery<DeploymentInfo[]>({
    queryKey: ['deployments'],
    queryFn: async () => {
      try {
        const response = await apiClient.getDeployments();
        console.log('Deployments response:', response);
        // Response contains { chat_models: [], embedding_models: [], ... }
        // We only care about chat models for research
        return response.chat_models || [];
      } catch (error) {
        console.error('Error fetching deployments:', error);
        throw error;
      }
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 1,
  });

  // Fetch recommended config for current depth
  const { data: modelConfig, isLoading: configLoading, error: configError } = useQuery<ModelConfig>({
    queryKey: ['model-config', depth],
    queryFn: async () => {
      try {
        const response = await apiClient.getModelForDepth(depth);
        console.log('Model config response:', response);
        return response;
      } catch (error) {
        console.error('Error fetching model config:', error);
        throw error;
      }
    },
    enabled: !!depth,
    retry: 1,
  });

  // Auto-select recommended model when config loads
  useEffect(() => {
    if (autoSelect && modelConfig && !selectedModel) {
      onModelSelect(modelConfig.deployment_name);
    }
  }, [autoSelect, modelConfig, selectedModel, onModelSelect]);

  if (deploymentsLoading || configLoading) {
    return (
      <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
        <div className="flex items-center gap-2 text-slate-400">
          <Cpu className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading available models...</span>
        </div>
      </div>
    );
  }

  if (deploymentsError || configError) {
    return (
      <div className="p-4 bg-red-500/10 rounded-lg border border-red-500/30">
        <div className="flex items-start gap-2 text-red-400">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <div className="font-semibold mb-1">Error loading model information</div>
            <div className="text-xs text-red-300">
              {deploymentsError ? 'Failed to fetch deployments. ' : ''}
              {configError ? 'Failed to fetch model config. ' : ''}
              Using default settings.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const recommendedDeployment = modelConfig?.deployment_name;
  const currentModel = selectedModel || recommendedDeployment;

  return (
    <div className="space-y-3">
      {/* Header with Auto-Select Toggle */}
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-slate-300">
          AI Model Selection
        </label>
        <button
          type="button"
          onClick={() => setAutoSelect(!autoSelect)}
          className={`px-3 py-1 text-xs rounded-lg transition-colors ${
            autoSelect
              ? 'bg-primary-500/20 text-primary-300 border border-primary-500/30'
              : 'bg-slate-700 text-slate-400 border border-slate-600'
          }`}
        >
          {autoSelect ? (
            <>
              <Zap className="w-3 h-3 inline mr-1" />
              Auto
            </>
          ) : (
            'Manual'
          )}
        </button>
      </div>

      {/* Recommended Model Info */}
      {modelConfig && (
        <div className="p-3 bg-gradient-to-r from-primary-500/10 to-purple-500/10 rounded-lg border border-primary-500/30">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-primary-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-white">
                  Recommended: {modelConfig.model_name || 'Loading...'}
                </span>
                {modelConfig.use_reasoning_model && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    🧠 Reasoning Model
                  </span>
                )}
              </div>
              <div className="flex gap-3 mt-1 text-xs text-slate-400">
                <span>Temp: {modelConfig.temperature ?? 0.7}</span>
                <span>Max Tokens: {(modelConfig.max_tokens ?? 4000).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Model Selector Dropdown */}
      {!autoSelect && deployments && (
        <div>
          <select
            value={currentModel}
            onChange={(e) => onModelSelect(e.target.value)}
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {deployments.map((deployment) => {
              const isRecommended = deployment.deployment_name === recommendedDeployment;
              return (
                <option
                  key={deployment.deployment_name}
                  value={deployment.deployment_name}
                >
                  {deployment.model_name} ({deployment.deployment_name})
                  {isRecommended ? ' ⭐ Recommended' : ''}
                  {` - Capacity: ${deployment.capacity}`}
                </option>
              );
            })}
          </select>

          {/* Model Details */}
          {currentModel && (
            <div className="mt-2 p-2 bg-slate-700/50 rounded text-xs text-slate-400">
              {deployments.find((d) => d.deployment_name === currentModel) && (
                <div className="flex items-center gap-2">
                  <Info className="w-3 h-3" />
                  <span>
                    {deployments.find((d) => d.deployment_name === currentModel)?.model_name} •{' '}
                    {deployments.find((d) => d.deployment_name === currentModel)?.model_version} •{' '}
                    SKU: {deployments.find((d) => d.deployment_name === currentModel)?.sku_name}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Depth-Specific Model Info */}
      <div className="text-xs text-slate-500 flex items-start gap-2 p-2 bg-slate-800/50 rounded">
        <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <div>
          {depth === 'exhaustive' && (
            <span>
              Exhaustive mode uses advanced models with higher temperature ({modelConfig?.temperature ?? '0.7'}) for creative,
              comprehensive analysis. Reasoning models (o1/o3) may be used for complex synthesis.
            </span>
          )}
          {depth === 'comprehensive' && (
            <span>
              Comprehensive mode balances capability and speed. Temperature set to {modelConfig?.temperature ?? '0.6'} for
              detailed analysis.
            </span>
          )}
          {depth === 'standard' && (
            <span>
              Standard mode uses efficient models with moderate temperature ({modelConfig?.temperature ?? '0.5'}) for balanced
              results.
            </span>
          )}
          {depth === 'quick' && (
            <span>
              Quick mode prioritizes speed with focused models (temperature {modelConfig?.temperature ?? '0.3'}) for fast
              overviews.
            </span>
          )}
        </div>
      </div>

      {/* Available Models Count */}
      {deployments && (
        <div className="text-xs text-slate-500 text-center">
          {deployments.length} model{deployments.length !== 1 ? 's' : ''} available in your Azure OpenAI deployment
        </div>
      )}
    </div>
  );
}

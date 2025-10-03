import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Play, Loader2 } from 'lucide-react';
import { api, SequentialResearchRequest, ConcurrentResearchRequest } from '../lib/api';

interface ResearchFormProps {
  onResearchStart: (runId: string) => void;
}

export default function ResearchForm({ onResearchStart }: ResearchFormProps) {
  const [ticker, setTicker] = useState('');
  const [pattern, setPattern] = useState<'sequential' | 'concurrent'>('sequential');
  const [scope, setScope] = useState<string[]>(['company', 'sec', 'earnings', 'fundamentals', 'technicals']);
  const [depth, setDepth] = useState<'standard' | 'deep' | 'comprehensive'>('standard');
  const [includePdf, setIncludePdf] = useState(true);

  const sequentialMutation = useMutation({
    mutationFn: (request: SequentialResearchRequest) => api.runSequential(request),
    onSuccess: (data) => {
      // Immediately switch to monitor tab when research starts
      onResearchStart(data.run_id);
    },
  });

  const concurrentMutation = useMutation({
    mutationFn: (request: ConcurrentResearchRequest) => api.runConcurrent(request),
    onSuccess: (data) => {
      // Immediately switch to monitor tab when research starts
      onResearchStart(data.run_id);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (pattern === 'sequential') {
      sequentialMutation.mutate({
        ticker: ticker.toUpperCase(),
        scope,
        depth,
        includePdf,
      });
    } else {
      concurrentMutation.mutate({
        ticker: ticker.toUpperCase(),
        modules: scope,
        aggregationStrategy: 'merge',
        includePdf,
      });
    }
  };

  const toggleScope = (module: string) => {
    setScope(prev =>
      prev.includes(module)
        ? prev.filter(m => m !== module)
        : [...prev, module]
    );
  };

  const isLoading = sequentialMutation.isPending || concurrentMutation.isPending;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h2 className="text-2xl font-bold mb-6">Configure Research</h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Ticker Input */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Stock Ticker
            </label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="e.g., MSFT, AAPL, GOOGL"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              required
            />
          </div>

          {/* Pattern Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Execution Pattern
            </label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setPattern('sequential')}
                className={`p-4 rounded-lg border-2 transition-colors ${
                  pattern === 'sequential'
                    ? 'border-primary-500 bg-primary-500/10'
                    : 'border-slate-600 hover:border-slate-500'
                }`}
              >
                <div className="font-semibold mb-1">Sequential</div>
                <div className="text-xs text-slate-400">
                  Agents run in order, building context
                </div>
              </button>
              <button
                type="button"
                onClick={() => setPattern('concurrent')}
                className={`p-4 rounded-lg border-2 transition-colors ${
                  pattern === 'concurrent'
                    ? 'border-primary-500 bg-primary-500/10'
                    : 'border-slate-600 hover:border-slate-500'
                }`}
              >
                <div className="font-semibold mb-1">Concurrent</div>
                <div className="text-xs text-slate-400">
                  Agents run in parallel, results merged
                </div>
              </button>
            </div>
          </div>

          {/* Research Scope */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Research Scope
            </label>
            <div className="grid grid-cols-3 gap-3">
              {['company', 'sec', 'earnings', 'fundamentals', 'technicals'].map((module) => (
                <button
                  key={module}
                  type="button"
                  onClick={() => toggleScope(module)}
                  className={`px-4 py-2 rounded-lg border transition-colors ${
                    scope.includes(module)
                      ? 'border-primary-500 bg-primary-500/20 text-primary-300'
                      : 'border-slate-600 hover:border-slate-500'
                  }`}
                >
                  {module.charAt(0).toUpperCase() + module.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Depth Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Analysis Depth
            </label>
            <div className="flex space-x-4">
              {['standard', 'deep', 'comprehensive'].map((d) => (
                <label key={d} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    value={d}
                    checked={depth === d}
                    onChange={(e) => setDepth(e.target.value as any)}
                    className="text-primary-500"
                  />
                  <span className="capitalize">{d}</span>
                </label>
              ))}
            </div>
          </div>

          {/* PDF Option */}
          <div>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includePdf}
                onChange={(e) => setIncludePdf(e.target.checked)}
                className="rounded text-primary-500"
              />
              <span>Generate PDF Equity Brief</span>
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !ticker || scope.length === 0}
            className="w-full px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-semibold flex items-center justify-center space-x-2 transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Starting Research...</span>
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                <span>Start Research</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

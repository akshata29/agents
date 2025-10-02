import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../api';
import { ResearchRequest } from '../types';
import { Search, Loader2 } from 'lucide-react';

interface ResearchFormProps {
  onResearchStart: (executionId: string) => void;
}

export default function ResearchForm({ onResearchStart }: ResearchFormProps) {
  const [formData, setFormData] = useState<ResearchRequest>({
    topic: '',
    depth: 'comprehensive',
    max_sources: 10,
    include_citations: true,
    execution_mode: 'workflow',
  });

  const startResearchMutation = useMutation({
    mutationFn: apiClient.startResearch,
    onSuccess: (data) => {
      onResearchStart(data.execution_id);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.topic.trim()) {
      startResearchMutation.mutate(formData);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-xl font-bold text-white flex items-center space-x-2">
          <Search className="w-5 h-5" />
          <span>Start New Research</span>
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Enter a research topic to begin multi-agent deep research workflow
        </p>
      </div>
      <div className="card-body">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Research Topic */}
          <div>
            <label htmlFor="topic" className="block text-sm font-medium text-slate-300 mb-2">
              Research Topic <span className="text-error-500">*</span>
            </label>
            <input
              id="topic"
              type="text"
              value={formData.topic}
              onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
              placeholder="e.g., Artificial Intelligence in Healthcare"
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              required
            />
          </div>

          {/* Research Depth */}
          <div>
            <label htmlFor="depth" className="block text-sm font-medium text-slate-300 mb-2">
              Research Depth
            </label>
            <select
              id="depth"
              value={formData.depth}
              onChange={(e) =>
                setFormData({ ...formData, depth: e.target.value as ResearchRequest['depth'] })
              }
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="quick">Quick - Fast overview (5-10 min)</option>
              <option value="standard">Standard - Balanced analysis (15-20 min)</option>
              <option value="comprehensive">Comprehensive - Deep analysis (30-40 min)</option>
              <option value="exhaustive">Exhaustive - Complete analysis (1+ hour)</option>
            </select>
          </div>

          {/* Execution Mode */}
          <div>
            <label htmlFor="execution_mode" className="block text-sm font-medium text-slate-300 mb-2">
              Execution Mode
            </label>
            <select
              id="execution_mode"
              value={formData.execution_mode}
              onChange={(e) =>
                setFormData({ ...formData, execution_mode: e.target.value as ResearchRequest['execution_mode'] })
              }
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="workflow">Workflow Engine (Declarative YAML)</option>
              <option value="code">Code-Based (Programmatic Patterns)</option>
              <option value="maf-workflow">MAF Workflows (Graph-Based)</option>
            </select>
            <p className="text-xs text-slate-500 mt-1">
              Choose between declarative YAML, code-based patterns, or MAF graph-based workflows
            </p>
          </div>

          {/* Options Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Max Sources */}
            <div>
              <label htmlFor="max_sources" className="block text-sm font-medium text-slate-300 mb-2">
                Maximum Sources
              </label>
              <input
                id="max_sources"
                type="number"
                min="3"
                max="50"
                value={formData.max_sources}
                onChange={(e) =>
                  setFormData({ ...formData, max_sources: parseInt(e.target.value) })
                }
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <p className="text-xs text-slate-500 mt-1">Number of sources to analyze (3-50)</p>
            </div>

            {/* Include Citations */}
            <div className="flex items-center">
              <input
                id="include_citations"
                type="checkbox"
                checked={formData.include_citations}
                onChange={(e) =>
                  setFormData({ ...formData, include_citations: e.target.checked })
                }
                className="w-4 h-4 text-primary-600 bg-slate-700 border-slate-600 rounded focus:ring-primary-500"
              />
              <label htmlFor="include_citations" className="ml-2 text-sm text-slate-300">
                Include citations in the final report
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end space-x-4">
            <button
              type="button"
              onClick={() =>
                setFormData({
                  topic: '',
                  depth: 'comprehensive',
                  max_sources: 10,
                  include_citations: true,
                  execution_mode: 'workflow',
                })
              }
              className="btn btn-secondary"
              disabled={startResearchMutation.isPending}
            >
              Clear
            </button>
            <button
              type="submit"
              disabled={!formData.topic.trim() || startResearchMutation.isPending}
              className="btn btn-primary flex items-center space-x-2"
            >
              {startResearchMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Starting...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>Start Research</span>
                </>
              )}
            </button>
          </div>

          {/* Error Display */}
          {startResearchMutation.isError && (
            <div className="p-4 bg-error-500/10 border border-error-500 rounded-lg text-error-400 text-sm">
              Failed to start research: {(startResearchMutation.error as Error).message}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

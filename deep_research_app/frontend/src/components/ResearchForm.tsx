import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../api';
import { ResearchRequest } from '../types';
import { Search, Loader2, Lightbulb, Brain, TrendingUp, Shield, Rocket, BookOpen, Globe, Info, FileText } from 'lucide-react';
import { ModelSelector } from './ModelSelector';
import FileUploader from './FileUploader';
import DocumentSelector from './DocumentSelector';

interface QuickTask {
  title: string;
  description: string;
  template: string;
  icon: React.ReactNode;
  executionMode: 'workflow' | 'code' | 'maf-workflow';
  depth: 'quick' | 'standard' | 'comprehensive' | 'exhaustive';
}

// Depth configuration mapping (matches backend DEPTH_CONFIGS)
const DEPTH_INFO = {
  quick: {
    sources: 5,
    duration: '5-10 min',
    words: '500-1,500',
    description: 'Fast overview with essential information'
  },
  standard: {
    sources: 10,
    duration: '15-20 min',
    words: '1,500-3,000',
    description: 'Balanced analysis with moderate depth'
  },
  comprehensive: {
    sources: 20,
    duration: '30-40 min',
    words: '3,000-6,000',
    description: 'Deep analysis with extensive coverage'
  },
  exhaustive: {
    sources: 50,
    duration: '1-2 hours',
    words: '6,000-15,000',
    description: 'Comprehensive scholarly research'
  }
};

interface ResearchFormProps {
  onResearchStart: (executionId: string) => void;
  sessionId: string | null;
}

const quickTasks: QuickTask[] = [
  {
    title: 'AI in Healthcare',
    description: 'Emerging AI applications in medical diagnosis',
    template: 'Artificial Intelligence in Healthcare: Current applications, emerging trends, ethical considerations, and future impact on medical diagnosis and patient care',
    icon: <Brain className="w-5 h-5" />,
    executionMode: 'workflow',
    depth: 'comprehensive',
  },
  {
    title: 'Quantum Computing',
    description: 'Quantum computing breakthroughs and applications',
    template: 'Quantum Computing: Recent breakthroughs, practical applications, challenges in scalability, and potential impact on cryptography and drug discovery',
    icon: <Rocket className="w-5 h-5" />,
    executionMode: 'code',
    depth: 'standard',
  },
  {
    title: 'Climate Technology',
    description: 'Innovative climate solutions and carbon capture',
    template: 'Climate Technology Solutions: Analysis of carbon capture technologies, renewable energy innovations, sustainable agriculture practices, and their effectiveness in combating climate change',
    icon: <Globe className="w-5 h-5" />,
    executionMode: 'maf-workflow',
    depth: 'comprehensive',
  },
  {
    title: 'Cybersecurity Trends',
    description: 'Emerging cyber threats and defense strategies',
    template: 'Cybersecurity in 2025: Emerging threats including AI-powered attacks, zero-trust architecture adoption, quantum-resistant cryptography, and best practices for enterprise security',
    icon: <Shield className="w-5 h-5" />,
    executionMode: 'workflow',
    depth: 'standard',
  },
  {
    title: 'Space Exploration',
    description: 'Commercial space industry and Mars missions',
    template: 'Future of Space Exploration: Commercial space industry growth, Mars colonization efforts, satellite technology advancements, and international space collaboration',
    icon: <Rocket className="w-5 h-5" />,
    executionMode: 'code',
    depth: 'comprehensive',
  },
  {
    title: 'EdTech Innovation',
    description: 'Technology transforming education',
    template: 'Educational Technology: Impact of AI tutors, personalized learning platforms, virtual reality in education, and the future of remote learning post-pandemic',
    icon: <BookOpen className="w-5 h-5" />,
    executionMode: 'workflow',
    depth: 'quick',
  },
  {
    title: 'Biotech Advances',
    description: 'Gene editing and personalized medicine',
    template: 'Biotechnology Breakthroughs: CRISPR gene editing applications, personalized medicine advancements, synthetic biology innovations, and ethical implications',
    icon: <Lightbulb className="w-5 h-5" />,
    executionMode: 'maf-workflow',
    depth: 'standard',
  },
  {
    title: 'Sustainable Energy',
    description: 'Clean energy transition and storage',
    template: 'Sustainable Energy Transition: Analysis of solar and wind efficiency improvements, battery storage innovations, green hydrogen potential, and challenges in grid modernization',
    icon: <TrendingUp className="w-5 h-5" />,
    executionMode: 'code',
    depth: 'exhaustive',
  },
  // NEW: Financial & Business Analysis Tasks
  {
    title: 'SEC 10-K Analysis',
    description: 'Deep dive into company financials and risks',
    template: 'SEC 10-K Analysis for Microsoft: Comprehensive review of financial performance, revenue streams, business segments, risk factors, management discussion & analysis (MD&A), competitive positioning, and strategic initiatives.',
    icon: <FileText className="w-5 h-5" />,
    executionMode: 'code',
    depth: 'exhaustive',
  },
  {
    title: 'Competitor Analysis',
    description: 'Market positioning and competitive landscape',
    template: 'Competitor Analysis: Detailed comparison of market leaders, competitive advantages, product portfolios, pricing strategies, market share trends, SWOT analysis, and strategic differentiation.',
    icon: <TrendingUp className="w-5 h-5" />,
    executionMode: 'maf-workflow',
    depth: 'comprehensive',
  },
  {
    title: 'M&A Due Diligence',
    description: 'Acquisition target evaluation',
    template: 'M&A Due Diligence Report: Financial health assessment, synergy opportunities, integration risks, valuation analysis, regulatory considerations, cultural fit evaluation, and deal structure recommendations.',
    icon: <FileText className="w-5 h-5" />,
    executionMode: 'code',
    depth: 'exhaustive',
  },
  {
    title: 'Market Research',
    description: 'Industry trends and market opportunities',
    template: 'Market Research Analysis: Industry size and growth projections, emerging trends, customer segmentation, competitive dynamics, regulatory landscape, technology disruptions, and market entry strategies.',
    icon: <TrendingUp className="w-5 h-5" />,
    executionMode: 'workflow',
    depth: 'comprehensive',
  },
  {
    title: 'ESG Performance',
    description: 'Environmental, social, and governance analysis',
    template: 'ESG Performance Analysis: Environmental impact assessment, social responsibility initiatives, governance structure evaluation, sustainability metrics, regulatory compliance, stakeholder engagement, and ESG risk factors.',
    icon: <Globe className="w-5 h-5" />,
    executionMode: 'maf-workflow',
    depth: 'comprehensive',
  },
  {
    title: 'Product Launch Strategy',
    description: 'Go-to-market planning and analysis',
    template: 'Product Launch Strategy: Market readiness assessment, target audience analysis, competitive positioning, pricing strategy, distribution channels, marketing campaigns, success metrics, and risk mitigation.',
    icon: <Rocket className="w-5 h-5" />,
    executionMode: 'code',
    depth: 'standard',
  },
  {
    title: 'Patent Analysis',
    description: 'IP portfolio and innovation trends',
    template: 'Patent & IP Analysis: Technology landscape mapping, patent portfolio strength, innovation trends, competitive IP positioning, freedom to operate assessment, litigation risks, and licensing opportunities.',
    icon: <Lightbulb className="w-5 h-5" />,
    executionMode: 'workflow',
    depth: 'comprehensive',
  },
  {
    title: 'Regulatory Compliance',
    description: 'Industry regulations and compliance requirements',
    template: 'Regulatory Compliance Analysis: Current regulatory framework, compliance requirements, upcoming regulatory changes, industry best practices, enforcement trends, risk assessment, and compliance strategy recommendations.',
    icon: <Shield className="w-5 h-5" />,
    executionMode: 'maf-workflow',
    depth: 'standard',
  },
];

export default function ResearchForm({ onResearchStart, sessionId }: ResearchFormProps) {
  const [formData, setFormData] = useState<ResearchRequest>({
    topic: '',
    depth: 'comprehensive',
    max_sources: 10,
    include_citations: true,
    execution_mode: 'workflow',
    document_ids: [],
  });
  
  const [selectedModel, setSelectedModel] = useState<string | undefined>(undefined);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);

  // Get current depth info for display
  const currentDepthInfo = DEPTH_INFO[formData.depth];

  const startResearchMutation = useMutation({
    mutationFn: apiClient.startResearch,
    onSuccess: (data) => {
      onResearchStart(data.execution_id);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.topic.trim() && sessionId) {
      // Include session_id, optional model override, and selected documents in the request
      startResearchMutation.mutate({ 
        ...formData, 
        session_id: sessionId,
        model_deployment: selectedModel,
        document_ids: selectedDocumentIds,
      });
    }
  };

  const handleQuickTask = (task: QuickTask) => {
    setFormData({ 
      ...formData, 
      topic: task.template,
      execution_mode: task.executionMode,
      depth: task.depth,
    });
    // Scroll to the topic field
    const topicField = document.getElementById('topic') as HTMLTextAreaElement;
    topicField?.focus();
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Quick Tasks Section */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-white">Quick Tasks</h3>
          <p className="text-sm text-slate-400 mt-1">
            Choose a pre-configured research topic to get started quickly
          </p>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {quickTasks.map((task, index) => (
              <button
                key={index}
                onClick={() => handleQuickTask(task)}
                disabled={startResearchMutation.isPending}
                className="flex items-start gap-3 p-4 bg-slate-700 hover:bg-slate-600 rounded-lg border border-slate-600 hover:border-primary-500 text-left transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="flex-shrink-0 w-10 h-10 bg-primary-500/20 rounded-lg flex items-center justify-center text-primary-400">
                  {task.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-white mb-1">
                    {task.title}
                  </h4>
                  <p className="text-xs text-slate-400 mb-2">
                    {task.description}
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-500/20 text-primary-300">
                      {task.executionMode === 'workflow' && '📋 YAML'}
                      {task.executionMode === 'code' && '💻 Code'}
                      {task.executionMode === 'maf-workflow' && '🔗 MAF'}
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-600 text-slate-300">
                      {task.depth === 'quick' && '⚡ Quick'}
                      {task.depth === 'standard' && '📊 Standard'}
                      {task.depth === 'comprehensive' && '🔬 Deep'}
                      {task.depth === 'exhaustive' && '🚀 Exhaustive'}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Research Form */}
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
            <textarea
              id="topic"
              value={formData.topic}
              onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
              placeholder="e.g., Artificial Intelligence in Healthcare: Current applications, emerging trends, and future impact..."
              rows={4}
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-y"
              required
            />
            <p className="text-xs text-slate-500 mt-1">
              Describe your research topic in detail. You can use Quick Tasks above for inspiration.
            </p>
          </div>

          {/* Document Upload and Selection */}
          <div className="space-y-4 p-4 bg-slate-800 rounded-lg border border-slate-600">
            <div className="flex items-center space-x-2 mb-3">
              <FileText className="w-5 h-5 text-primary-400" />
              <h3 className="text-sm font-semibold text-slate-200">
                Research Documents (Optional)
              </h3>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Upload new documents or select from previously uploaded files to include in your research context.
              Documents will be processed and combined with web search results.
            </p>

            {/* File Uploader */}
            {sessionId && (
              <FileUploader
                sessionId={sessionId}
                onFilesProcessed={(fileIds) => {
                  // Auto-select newly uploaded files
                  setSelectedDocumentIds(prev => [...new Set([...prev, ...fileIds])]);
                }}
              />
            )}

            {/* Document Selector */}
            <DocumentSelector
              selectedDocumentIds={selectedDocumentIds}
              onSelectionChange={setSelectedDocumentIds}
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
              <option value="quick">⚡ Quick - Fast overview (5-10 min)</option>
              <option value="standard">📊 Standard - Balanced analysis (15-20 min)</option>
              <option value="comprehensive">🔬 Comprehensive - Deep analysis (30-40 min)</option>
              <option value="exhaustive">🚀 Exhaustive - Complete analysis (1-2 hours)</option>
            </select>
            
            {/* Depth Info Display */}
            <div className="mt-3 p-3 bg-slate-600/50 rounded-lg border border-slate-500">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <span className="text-slate-400">Sources:</span>
                  <span className="ml-1 text-white font-semibold">{currentDepthInfo.sources}</span>
                </div>
                <div>
                  <span className="text-slate-400">Duration:</span>
                  <span className="ml-1 text-white font-semibold">{currentDepthInfo.duration}</span>
                </div>
                <div>
                  <span className="text-slate-400">Words:</span>
                  <span className="ml-1 text-white font-semibold">{currentDepthInfo.words}</span>
                </div>
              </div>
              <p className="text-xs text-slate-300 mt-2">{currentDepthInfo.description}</p>
            </div>
          </div>

          {/* AI Model Selection */}
          <ModelSelector
            depth={formData.depth}
            selectedModel={selectedModel}
            onModelSelect={setSelectedModel}
          />

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
            {/* Max Sources - Now readonly, controlled by depth */}
            <div>
              <label htmlFor="max_sources" className="block text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
                Maximum Sources
                <span className="text-xs text-slate-400 font-normal">(Auto-configured)</span>
              </label>
              <div className="relative">
                <input
                  id="max_sources"
                  type="number"
                  value={currentDepthInfo.sources}
                  readOnly
                  className="w-full px-4 py-3 bg-slate-600 border border-slate-500 rounded-lg text-slate-300 cursor-not-allowed"
                  title="This value is automatically set based on your selected research depth"
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  <Info className="w-4 h-4 text-slate-400" />
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Automatically set by research depth selection
              </p>
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
    </div>
  );
}

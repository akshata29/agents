import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Circle, XCircle, Loader2, Clock, ChevronRight } from 'lucide-react';
import { api, ExecutionStep } from '../lib/api';
import { formatDistanceToNow } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

const markdownClassName = 'prose prose-invert prose-sm text-slate-300 max-w-none';

const markdownComponents: Components = {
  a: (props: any) => (
    <a
      {...props}
      className="text-primary-300 underline"
      target="_blank"
      rel="noopener noreferrer"
    />
  ),
  code: ({ inline, className, children, ...props }: any) => {
    if (inline) {
      return (
        <code className="px-1 py-0.5 bg-slate-700 rounded text-primary-200" {...props}>
          {children}
        </code>
      );
    }

    return (
      <pre className="bg-slate-900 text-xs p-3 rounded overflow-auto">
        <code className={className} {...props}>
          {children}
        </code>
      </pre>
    );
  },
  table: ({ className, ...props }: any) => (
    <div className="overflow-auto">
      <table className={`min-w-full border-collapse ${className ?? ''}`} {...props} />
    </div>
  ),
  th: ({ className, ...props }: any) => (
    <th className={`border border-slate-600 px-3 py-2 bg-slate-700 ${className ?? ''}`} {...props} />
  ),
  td: ({ className, ...props }: any) => (
    <td className={`border border-slate-700 px-3 py-2 ${className ?? ''}`} {...props} />
  ),
};

interface ExecutionMonitorProps {
  runId: string;
  selectedAgentProp?: string | null;
  onAgentSelect?: (agentName: string) => void;
}

export default function ExecutionMonitor({ runId, selectedAgentProp, onAgentSelect }: ExecutionMonitorProps) {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(selectedAgentProp || null);
  
  // Update local state when prop changes
  if (selectedAgentProp !== selectedAgent && selectedAgentProp !== undefined) {
    setSelectedAgent(selectedAgentProp);
  }
  
  const handleAgentSelect = (agentName: string) => {
    setSelectedAgent(agentName);
    onAgentSelect?.(agentName);
  };
  const { data: execution, isLoading, error } = useQuery({
    queryKey: ['execution', runId],
    queryFn: () => api.getRunStatus(runId),
    refetchInterval: 2000, // Poll every 2 seconds
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error || !execution) {
    return (
      <div className="bg-error-500/10 border border-error-500 rounded-lg p-4">
        <p className="text-error-400">Failed to load execution details</p>
      </div>
    );
  }

  // If an agent is selected, show detailed view
  if (selectedAgent) {
    return <AgentDetailView 
      execution={execution} 
      agentName={selectedAgent} 
      onBack={() => handleAgentSelect(null as any)} 
    />;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left: Execution Steps */}
      <div className="lg:col-span-2 space-y-4">
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold">Execution Timeline</h2>
            <StatusBadge status={execution.status} />
          </div>

          <div className="space-y-4">
            {execution.steps.map((step) => (
              <StepCard 
                key={step.step_number} 
                step={step} 
                onClick={() => handleAgentSelect(step.agent)}
              />
            ))}
          </div>

          {execution.summary && (
            <div className="mt-6 p-4 bg-primary-500/10 border border-primary-500/30 rounded-lg">
              <h3 className="font-semibold mb-2">Summary</h3>
              <p className="text-sm text-slate-300">{execution.summary}</p>
            </div>
          )}

          {execution.error && (
            <div className="mt-6 p-4 bg-error-500/10 border border-error-500 rounded-lg">
              <h3 className="font-semibold text-error-400 mb-2">Error</h3>
              <p className="text-sm text-slate-300">{execution.error}</p>
            </div>
          )}
        </div>

        {/* Agent Messages */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-xl font-bold mb-4">Agent Messages</h2>
          <div className="space-y-3">
            {execution.messages.map((msg, idx) => (
              <div key={idx} className="border-l-2 border-primary-500 pl-4 py-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-primary-400">
                    {msg.agent_name}
                  </span>
                  <span className="text-xs text-slate-400">
                    {formatDistanceToNow(new Date(msg.timestamp), { addSuffix: true })}
                  </span>
                </div>
                <ReactMarkdown
                  className={`${markdownClassName} [&>*]:mb-2 last:[&>*]:mb-0`}
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: Artifacts & Info */}
      <div className="space-y-4">
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="font-bold mb-4">Execution Info</h3>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-slate-400">Run ID</dt>
              <dd className="font-mono text-xs">{execution.run_id}</dd>
            </div>
            <div>
              <dt className="text-slate-400">Ticker</dt>
              <dd className="font-semibold text-lg">{execution.ticker}</dd>
            </div>
            <div>
              <dt className="text-slate-400">Pattern</dt>
              <dd className="capitalize">{execution.pattern}</dd>
            </div>
            <div>
              <dt className="text-slate-400">Started</dt>
              <dd>{new Date(execution.started_at).toLocaleString()}</dd>
            </div>
            {execution.duration_seconds && (
              <div>
                <dt className="text-slate-400">Duration</dt>
                <dd>{execution.duration_seconds.toFixed(1)}s</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Artifacts */}
        {execution.artifacts && execution.artifacts.length > 0 && (
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h3 className="font-bold mb-4">Generated Artifacts</h3>
            <div className="space-y-2">
              {execution.artifacts.map((artifact) => (
                <div
                  key={artifact.id}
                  className="p-3 bg-slate-700 rounded border border-slate-600"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{artifact.title}</span>
                    <span className="text-xs text-slate-400 uppercase">
                      {artifact.type}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles = {
    pending: 'bg-slate-500/20 text-slate-400',
    running: 'bg-primary-500/20 text-primary-400',
    completed: 'bg-success-500/20 text-success-400',
    failed: 'bg-error-500/20 text-error-400',
    cancelled: 'bg-warning-500/20 text-warning-400',
  };

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${styles[status as keyof typeof styles]}`}>
      {status.toUpperCase()}
    </span>
  );
}

function StepCard({ step, onClick }: { step: ExecutionStep; onClick?: () => void }) {
  const getIcon = () => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-success-400" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-error-400" />;
      default:
        return <Circle className="w-5 h-5 text-slate-500" />;
    }
  };

  return (
    <div 
      className={`flex items-start space-x-3 p-4 bg-slate-700 rounded border border-slate-600 ${
        onClick && step.status === 'completed' ? 'cursor-pointer hover:border-primary-500 transition-colors' : ''
      }`}
      onClick={step.status === 'completed' ? onClick : undefined}
    >
      <div className="mt-0.5">{getIcon()}</div>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className="font-semibold">
            {step.step_number}. {step.agent.charAt(0).toUpperCase() + step.agent.slice(1)} Agent
          </span>
          <div className="flex items-center space-x-2">
            {step.duration_seconds && (
              <span className="text-xs text-slate-400 flex items-center space-x-1">
                <Clock className="w-3 h-3" />
                <span>{step.duration_seconds.toFixed(1)}s</span>
              </span>
            )}
            {step.status === 'completed' && onClick && (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>
        {step.error && (
          <p className="text-sm text-error-400 mt-1">{step.error}</p>
        )}
      </div>
    </div>
  );
}

// Agent Detail View Component
interface AgentDetailViewProps {
  execution: any;
  agentName: string;
  onBack: () => void;
}

function AgentDetailView({ execution, agentName, onBack }: AgentDetailViewProps) {
  // Find the agent's message
  const agentMessage = execution.messages.find((msg: any) => 
    msg.agent === agentName || msg.agent_name === agentName
  );
  
  // Find the agent's step
  const agentStep = execution.steps.find((step: any) => step.agent === agentName);
  
  // Find artifacts from this agent
  const agentArtifacts = execution.artifacts?.filter((artifact: any) => 
    artifact.metadata?.agent === agentName ||
    artifact.title?.toLowerCase().includes(agentName.toLowerCase())
  ) || [];

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="flex items-center space-x-2 text-primary-400 hover:text-primary-300 transition-colors"
      >
        <ChevronRight className="w-4 h-4 rotate-180" />
        <span>Back to Timeline</span>
      </button>

      {/* Agent Header */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold mb-2">
              {agentName.charAt(0).toUpperCase() + agentName.slice(1)} Agent
            </h2>
            <p className="text-slate-400">
              Detailed analysis and output
            </p>
          </div>
          {agentStep && (
            <div className="text-right">
              <StatusBadge status={agentStep.status} />
              {agentStep.duration_seconds && (
                <div className="text-sm text-slate-400 mt-2">
                  Duration: {agentStep.duration_seconds.toFixed(1)}s
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Agent Output */}
      {agentMessage && (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-xl font-bold mb-4">Analysis Output</h3>
          <div className="bg-slate-900 p-4 rounded overflow-auto max-h-[600px]">
            <ReactMarkdown
              className={`${markdownClassName} leading-relaxed`}
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {agentMessage.content}
            </ReactMarkdown>
          </div>
          <div className="mt-4 text-xs text-slate-400">
            Generated {formatDistanceToNow(new Date(agentMessage.timestamp), { addSuffix: true })}
          </div>
        </div>
      )}

      {/* Artifacts */}
      {agentArtifacts.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-xl font-bold mb-4">Generated Artifacts</h3>
          <div className="space-y-4">
            {agentArtifacts.map((artifact: any) => (
              <div
                key={artifact.id}
                className="p-4 bg-slate-700 rounded border border-slate-600"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold">{artifact.title}</span>
                  <span className="text-xs text-slate-400 uppercase px-2 py-1 bg-slate-600 rounded">
                    {artifact.type}
                  </span>
                </div>
                {artifact.content && typeof artifact.content === 'string' && (
                  <div className="text-sm text-slate-300 mt-2 whitespace-pre-wrap bg-slate-900 p-3 rounded max-h-60 overflow-auto">
                    {artifact.content}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Display */}
      {agentStep?.error && (
        <div className="bg-error-500/10 border border-error-500 rounded-lg p-6">
          <h3 className="text-xl font-bold text-error-400 mb-2">Error</h3>
          <p className="text-sm text-slate-300">{agentStep.error}</p>
        </div>
      )}
    </div>
  );
}

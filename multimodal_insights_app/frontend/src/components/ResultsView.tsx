import React from 'react';
import { useSession } from '../contexts/SessionContext';
import { FileText, Check, Activity, CheckCircle, Loader2 } from 'lucide-react';
import { FormattedAgentResult } from './FormattedResults';

const ResultsView: React.FC = () => {
  const { session } = useSession();

  if (!session?.currentPlan) return null;

  const { currentPlan } = session;

  // Helper to parse and render step results
  const renderStepResults = (step: any) => {
    if (!step.agent_reply) return null;

    try {
      const parsed = JSON.parse(step.agent_reply);
      return <FormattedAgentResult agentName={step.agent} data={parsed} />;
    } catch {
      // Fallback for non-JSON responses
      return (
        <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
          <pre className="text-xs text-slate-200 whitespace-pre-wrap overflow-x-auto font-mono">
            {step.agent_reply}
          </pre>
        </div>
      );
    }
  };

  // Get agent display info
  const getAgentInfo = (agentName: string) => {
    const agentMap: Record<string, { icon: any; color: string; title: string }> = {
      'MultimodalProcessor_Agent': { 
        icon: Activity, 
        color: 'text-blue-400', 
        title: 'Content Extraction' 
      },
      'Sentiment_Agent': { 
        icon: Activity, 
        color: 'text-pink-400', 
        title: 'Sentiment Analysis' 
      },
      'Summarizer_Agent': { 
        icon: FileText, 
        color: 'text-emerald-400', 
        title: 'Executive Summary' 
      },
      'Analytics_Agent': { 
        icon: Activity, 
        color: 'text-indigo-400', 
        title: 'Analytics & Insights' 
      },
    };

    return agentMap[agentName] || { icon: FileText, color: 'text-primary-400', title: agentName };
  };

  return (
    <div className="space-y-4">
      {/* Plan Summary */}
      {currentPlan.overall_status === 'completed' && (
        <div className="bg-success/10 border border-success/30 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <Check className="h-5 w-5 text-success" />
            <h4 className="font-semibold text-slate-100">Analysis Complete</h4>
          </div>
          <p className="text-sm text-slate-300">
            {currentPlan.initial_goal}
          </p>
        </div>
      )}

      {/* Steps Results - Show all steps including in-progress */}
      <div className="space-y-4">
        {currentPlan.steps.map((step, idx) => {
          const agentInfo = getAgentInfo(step.agent);
          const Icon = agentInfo.icon;
          const isCompleted = step.status === 'completed';
          const isFailed = step.status === 'failed';
          const isExecuting = step.status === 'executing';

          return (
            <div key={step.id} className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
              {/* Step Header */}
              <div className="p-4 border-b border-slate-700">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <Icon className={`h-5 w-5 ${agentInfo.color}`} />
                    <div>
                      <div className="flex items-center space-x-2">
                        <h5 className="font-semibold text-slate-100">{agentInfo.title}</h5>
                        <span className="text-xs px-2 py-0.5 bg-slate-700 text-slate-400 rounded-full">
                          Step {idx + 1} of {currentPlan.total_steps}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">{step.action}</p>
                    </div>
                  </div>
                  
                  {/* Status Badge */}
                  <div className="flex-shrink-0">
                    {isCompleted && (
                      <div className="flex items-center space-x-1 text-green-400">
                        <CheckCircle className="h-4 w-4" />
                        <span className="text-xs font-medium">Completed</span>
                      </div>
                    )}
                    {isFailed && (
                      <div className="flex items-center space-x-1 text-red-400">
                        <span className="text-xs font-medium">Failed</span>
                      </div>
                    )}
                    {isExecuting && (
                      <div className="flex items-center space-x-1 text-blue-400">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-xs font-medium">Processing...</span>
                      </div>
                    )}
                    {!isCompleted && !isFailed && !isExecuting && (
                      <span className="text-xs text-slate-500">Pending</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Step Results */}
              {isCompleted && step.agent_reply && (
                <div className="p-4">
                  {renderStepResults(step)}
                </div>
              )}

              {/* Error Message */}
              {isFailed && step.error_message && (
                <div className="p-4">
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                    <p className="text-xs text-red-400">{step.error_message}</p>
                  </div>
                </div>
              )}

              {/* No Results Message */}
              {isCompleted && !step.agent_reply && !step.error_message && (
                <div className="p-4">
                  <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-3 text-center">
                    <p className="text-xs text-slate-500 italic">No output generated</p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ResultsView;

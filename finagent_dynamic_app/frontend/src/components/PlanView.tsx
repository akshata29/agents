/**
 * PlanView Component
 * 
 * Displays the generated plan with steps and execution output
 * Clean layout with left steps panel and right output panel
 */

import React, { useState, useMemo, useEffect } from 'react';
import { marked } from 'marked';
import { Play, CheckCircle, XCircle, Clock, TrendingUp, Users, Zap, Activity } from 'lucide-react';
import { Plan, Step, AgentMessage, apiClient } from '../lib/api';

// Configure marked for better output
marked.setOptions({
  breaks: true,
  gfm: true,
});

interface PlanViewProps {
  plan: Plan;
  onApprove: (stepId: string) => void;
  onReject: (stepId: string, reason?: string) => void;
  isExecuting?: boolean;
}

export const PlanView: React.FC<PlanViewProps> = ({
  plan,
  onApprove,
  onReject,
  isExecuting = false
}) => {
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [processingSteps, setProcessingSteps] = useState<Set<string>>(new Set());
  const [stepMessages, setStepMessages] = useState<AgentMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  // Fetch messages when selected step changes
  useEffect(() => {
    if (!selectedStep || !plan.session_id) return;

    const fetchMessages = async () => {
      setLoadingMessages(true);
      try {
        const allMessages = await apiClient.getMessagesByPlan(plan.session_id, plan.id);
        // Filter messages for the selected step
        const filtered = allMessages.filter(msg => msg.step_id === selectedStep);
        console.log('Fetched messages for step:', selectedStep, 'Count:', filtered.length, 'Messages:', filtered);
        setStepMessages(filtered);
      } catch (error) {
        console.error('Failed to fetch messages:', error);
        setStepMessages([]);
      } finally {
        setLoadingMessages(false);
      }
    };

    fetchMessages();
    
    // Poll for updates if step is not in a terminal state
    const selectedStepData = plan.steps?.find(s => s.id === selectedStep);
    const isTerminalState = selectedStepData?.status === 'completed' || 
                           selectedStepData?.status === 'failed' || 
                           selectedStepData?.status === 'rejected';
    
    console.log('Selected step status:', selectedStepData?.status, 'Will poll:', !isTerminalState);
    
    // Poll for any non-terminal state (planned, approved, executing, etc.)
    if (!isTerminalState) {
      console.log('Starting polling for step:', selectedStep);
      const interval = setInterval(() => {
        console.log('Polling for messages...');
        fetchMessages();
      }, 2000);
      return () => {
        console.log('Stopping polling for step:', selectedStep);
        clearInterval(interval);
      };
    }
  }, [selectedStep, plan.session_id, plan.id, plan.steps]);

  const getStatusBadge = (status: string) => {
    const badges = {
      'planned': { text: 'PLANNED', class: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
      'awaiting_feedback': { text: 'AWAITING', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
      'approved': { text: 'APPROVED', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
      'executing': { text: 'EXECUTING', class: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
      'completed': { text: 'COMPLETED', class: 'bg-success-500/20 text-success-400 border-success-500/30' },
      'failed': { text: 'FAILED', class: 'bg-error-500/20 text-error-400 border-error-500/30' },
      'rejected': { text: 'REJECTED', class: 'bg-error-500/20 text-error-400 border-error-500/30' },
    };
    const badge = badges[status as keyof typeof badges] || badges.planned;
    return <span className={`px-2 py-0.5 rounded text-xs font-medium border ${badge.class}`}>{badge.text}</span>;
  };

  // Helper to check if dependencies are met for a step
  const checkDependenciesMet = (step: Step): { met: boolean; unmetDeps: Step[] } => {
    if (!step.dependencies || step.dependencies.length === 0) {
      return { met: true, unmetDeps: [] };
    }

    const unmetDeps: Step[] = [];
    for (const depId of step.dependencies) {
      const depStep = plan.steps?.find(s => s.id === depId);
      if (depStep && depStep.status !== 'completed') {
        unmetDeps.push(depStep);
      }
    }

    return {
      met: unmetDeps.length === 0,
      unmetDeps
    };
  };

  const canApprove = (step: Step) => {
    const isPending = ['planned', 'awaiting_feedback'].includes(step.status);
    const { met: dependenciesMet } = checkDependenciesMet(step);
    return isPending && dependenciesMet;
  };

  const handleApprove = async (stepId: string) => {
    setProcessingSteps(prev => new Set(prev).add(stepId));
    try {
      await onApprove(stepId);
    } finally {
      // Keep it in processing state - it will update when the plan refreshes
    }
  };

  const handleReject = async (stepId: string, reason?: string) => {
    setProcessingSteps(prev => new Set(prev).add(stepId));
    try {
      await onReject(stepId, reason);
    } finally {
      // Keep it in processing state - it will update when the plan refreshes
    }
  };

  const isStepProcessing = (stepId: string) => {
    return processingSteps.has(stepId);
  };

  // Helper function to extract the actual result from agent_reply
  const extractResult = (agentReply: string | undefined): string => {
    if (!agentReply) return '';
    
    // First, trim the string
    const trimmed = agentReply.trim();
    
    // Check if it looks like a Python dict (starts with { and has 'result':)
    if (trimmed.startsWith('{') && trimmed.includes("'result':")) {
      try {
        // Find the start of the result field value
        const resultStart = trimmed.indexOf("'result':");
        if (resultStart !== -1) {
          // Find where the result value starts (after the colon and optional whitespace/quote)
          let valueStart = resultStart + "'result':".length;
          
          // Skip whitespace
          while (valueStart < trimmed.length && /\s/.test(trimmed[valueStart])) {
            valueStart++;
          }
          
          // Check if it's a string (starts with ' or ")
          if (trimmed[valueStart] === '"' || trimmed[valueStart] === "'") {
            const quoteChar = trimmed[valueStart];
            valueStart++; // Skip opening quote
            
            // Find the closing quote (handling escaped quotes)
            let valueEnd = valueStart;
            while (valueEnd < trimmed.length) {
              if (trimmed[valueEnd] === '\\') {
                valueEnd += 2; // Skip escaped character
                continue;
              }
              if (trimmed[valueEnd] === quoteChar) {
                break; // Found closing quote
              }
              valueEnd++;
            }
            
            // Extract the value
            let result = trimmed.substring(valueStart, valueEnd);
            
            // Unescape common escape sequences
            result = result.replace(/\\n/g, '\n');
            result = result.replace(/\\t/g, '\t');
            result = result.replace(/\\r/g, '\r');
            result = result.replace(/\\"/g, '"');
            result = result.replace(/\\'/g, "'");
            result = result.replace(/\\\\/g, '\\');
            
            console.log('Extracted result field:', result.substring(0, 200) + '...');
            return result;
          }
        }
      } catch (error) {
        console.log('String extraction failed:', error);
      }
    }
    
    // Try standard JSON parsing as fallback
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        const parsed = JSON.parse(trimmed);
        
        if (parsed.result !== undefined && parsed.result !== null) {
          return String(parsed.result);
        }
        
        // Look for other common fields
        const resultFields = ['content', 'output', 'response', 'data', 'text', 'message'];
        for (const field of resultFields) {
          if (parsed[field] !== undefined && parsed[field] !== null) {
            return String(parsed[field]);
          }
        }
      } catch (error) {
        console.log('JSON parse failed, using original');
      }
    }
    
    // If all parsing fails, return as-is
    return agentReply;
  };

  const selectedStepData = selectedStep ? plan.steps?.find(s => s.id === selectedStep) : null;

  // Calculate stats
  const stats = useMemo(() => {
    const steps = plan.steps || [];
    const completed = steps.filter(s => s.status === 'completed').length;
    const failed = steps.filter(s => s.status === 'failed').length;
    const inProgress = steps.filter(s => ['approved', 'awaiting_feedback'].includes(s.status)).length;
    const uniqueAgents = new Set(steps.map(s => s.agent)).size;
    const progress = steps.length > 0 ? (completed / steps.length) * 100 : 0;
    
    return {
      total: steps.length,
      completed,
      failed,
      inProgress,
      pending: steps.length - completed - failed - inProgress,
      uniqueAgents,
      progress: Math.round(progress)
    };
  }, [plan.steps]);

  return (
    <div className="flex gap-6 h-full">
      {/* Left Panel - Plan and Steps List (Reduced to 40% width) */}
      <div className="w-2/5 space-y-4 overflow-y-auto pr-2">
        {/* Plan Header with Stats */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg shadow-lg border border-slate-700 p-5">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Play className="w-5 h-5 text-primary-400" />
                <h2 className="text-lg font-semibold text-white">Research Plan</h2>
              </div>
              <p className="text-sm text-slate-300 line-clamp-2">{plan.initial_goal}</p>
              {plan.ticker && (
                <div className="mt-2 inline-flex items-center gap-1 px-2 py-1 bg-primary-500/20 border border-primary-500/30 rounded text-xs font-semibold text-primary-400">
                  <TrendingUp className="w-3 h-3" />
                  {plan.ticker}
                </div>
              )}
            </div>
            <div className="ml-4">
              {plan.overall_status === 'in_progress' && (
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  IN PROGRESS
                </span>
              )}
              {plan.overall_status === 'completed' && (
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-success-500/20 text-success-400 border border-success-500/30">
                  COMPLETED
                </span>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span>Overall Progress</span>
              <span className="font-semibold text-white">{stats.progress}%</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-500 ease-out relative"
                style={{ width: `${stats.progress}%` }}
              >
                <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
              </div>
            </div>
            <div className="flex items-center justify-between mt-2 text-xs">
              <span className="text-slate-400">{stats.completed} of {stats.total} completed</span>
              {stats.failed > 0 && (
                <span className="text-error-400">{stats.failed} failed</span>
              )}
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-600/50">
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-slate-400">Active</span>
              </div>
              <div className="text-lg font-bold text-white">{stats.inProgress}</div>
            </div>
            
            <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-600/50">
              <div className="flex items-center gap-2 mb-1">
                <Users className="w-4 h-4 text-purple-400" />
                <span className="text-xs text-slate-400">Agents</span>
              </div>
              <div className="text-lg font-bold text-white">{stats.uniqueAgents}</div>
            </div>
            
            <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-600/50">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="w-4 h-4 text-yellow-400" />
                <span className="text-xs text-slate-400">Pending</span>
              </div>
              <div className="text-lg font-bold text-white">{stats.pending}</div>
            </div>
          </div>
        </div>

        {/* Steps List - Clean and Compact */}
        <div className="space-y-2">
          {plan.steps?.map((step, index) => (
            <div 
              key={step.id} 
              onClick={() => setSelectedStep(step.id)}
              className={`bg-slate-800 rounded-lg border border-slate-700 p-4 cursor-pointer hover:border-primary-500/50 transition-all ${
                selectedStep === step.id ? 'border-primary-500 shadow-lg' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                {/* Step Number with dynamic status color */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm border-2 transition-all ${
                  step.status === 'completed' ? 'bg-success-500/20 border-success-500 text-success-400' :
                  step.status === 'failed' ? 'bg-error-500/20 border-error-500 text-error-400' :
                  step.status === 'approved' ? 'bg-blue-500/20 border-blue-500 text-blue-400 animate-pulse' :
                  step.status === 'awaiting_feedback' ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400' :
                  'bg-slate-700 border-slate-600 text-slate-300'
                }`}>
                  {index + 1}
                </div>

                {/* Step Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {getStatusBadge(step.status)}
                    {step.tools && step.tools.length > 0 && (
                      <span className="px-2 py-0.5 bg-blue-500/20 border border-blue-500/30 rounded text-xs font-mono text-blue-300">
                        {step.tools[0]}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-100 text-sm font-medium mb-1 line-clamp-1">{step.action}</p>
                  <div className="text-xs text-slate-400">
                    <span>Agent: {step.agent}</span>
                    {step.dependencies && step.dependencies.length > 0 && (
                      <>
                        {' • '}
                        <span className="text-yellow-400">
                          Depends on {step.dependencies.length} step{step.dependencies.length > 1 ? 's' : ''}
                        </span>
                        {(() => {
                          const { met, unmetDeps } = checkDependenciesMet(step);
                          return !met ? (
                            <span className="ml-1 text-yellow-300">(⚠️ {unmetDeps.length} pending)</span>
                          ) : (
                            <span className="ml-1 text-green-400">(✓ ready)</span>
                          );
                        })()}
                      </>
                    )}
                  </div>
                </div>

                {/* Compact Action Buttons */}
                {canApprove(step) && (
                  <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleApprove(step.id)}
                      disabled={isExecuting || isStepProcessing(step.id)}
                      title="Approve & Execute"
                      className="p-2 bg-success-600 hover:bg-success-700 text-white rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <CheckCircle className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        const reason = prompt('Reason for rejection (optional):');
                        if (reason !== null) { // User didn't cancel
                          handleReject(step.id, reason || undefined);
                        }
                      }}
                      disabled={isExecuting || isStepProcessing(step.id)}
                      title="Reject"
                      className="p-2 bg-error-600 hover:bg-error-700 text-white rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {/* Status Indicator for Completed/Running */}
                {step.status === 'completed' && (
                  <CheckCircle className="w-5 h-5 text-success-400" />
                )}
                {step.status === 'approved' && (
                  <Clock className="w-5 h-5 text-blue-400 animate-spin" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Panel - Execution Output (Expanded to 60% width) */}
      <div className="w-3/5 flex-shrink-0">
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg shadow-lg border border-slate-700 p-5 h-full flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-primary-400" />
            <h3 className="text-lg font-semibold text-white">Execution Output</h3>
          </div>
          
          {selectedStepData ? (
            <div className="flex-1 overflow-y-auto space-y-4">
              {/* Step Details Header */}
              <div className="bg-slate-900/50 rounded-lg border border-slate-600/50 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border-2 ${
                    selectedStepData.status === 'completed' ? 'bg-success-500/20 border-success-500 text-success-400' :
                    selectedStepData.status === 'failed' ? 'bg-error-500/20 border-error-500 text-error-400' :
                    selectedStepData.status === 'approved' ? 'bg-blue-500/20 border-blue-500 text-blue-400' :
                    'bg-slate-700 border-slate-600 text-slate-300'
                  }`}>
                    {plan.steps?.findIndex(s => s.id === selectedStep)! + 1}
                  </div>
                  <div className="text-sm font-medium text-slate-200">{selectedStepData.action}</div>
                </div>
                <div className="flex items-center gap-3 mt-2">
                  {getStatusBadge(selectedStepData.status)}
                  <div className="flex items-center gap-1 text-xs text-slate-400">
                    <Users className="w-3 h-3" />
                    <span>{selectedStepData.agent}</span>
                  </div>
                </div>
              </div>

              {/* Agent Messages - show progress and final result */}
              <div className="flex-1 flex flex-col min-h-0 space-y-3">
                {stepMessages.length > 0 ? (
                  (() => {
                    // Check if we have a result message
                    const hasResult = stepMessages.some(m => m.message_type === 'action_response');
                    const hasError = stepMessages.some(m => m.message_type === 'error');
                    
                    return stepMessages.map((msg) => (
                      <div key={msg.id} className="animate-fadeIn">
                        {/* Progress Message - only show if no result/error yet */}
                        {msg.message_type === 'progress' && !hasResult && !hasError && (
                          <div className="flex items-start gap-2 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                            <Activity className="w-4 h-4 text-blue-400 mt-0.5 animate-pulse" />
                            <div className="flex-1">
                              <span className="text-xs font-semibold text-blue-300 block mb-1">IN PROGRESS</span>
                              <p className="text-sm text-blue-100">{msg.content}</p>
                            </div>
                          </div>
                        )}
                        
                        {/* Result Message */}
                        {msg.message_type === 'action_response' && (
                          <div className="flex-1 flex flex-col min-h-0">
                            <div className="flex items-center gap-2 mb-3">
                              <Zap className="w-4 h-4 text-yellow-400" />
                              <span className="text-xs font-semibold text-slate-400">RESULT</span>
                            </div>
                            <div 
                              className="flex-1 p-5 bg-slate-900 rounded-lg border border-slate-600 overflow-y-auto shadow-inner custom-scrollbar prose prose-invert prose-sm max-w-none"
                              dangerouslySetInnerHTML={{ 
                                __html: marked(extractResult(msg.content)) as string
                              }}
                              style={{
                                fontSize: '0.875rem',
                                lineHeight: '1.6',
                              }}
                            />
                          </div>
                        )}
                        
                        {/* Error Message */}
                        {msg.message_type === 'error' && (
                          <div className="p-4 bg-error-500/10 border border-error-500/30 rounded-lg text-sm text-error-400 flex items-start gap-2">
                            <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <div>
                              <strong className="block mb-1">Error Occurred</strong>
                              <span>{msg.content}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ));
                  })()
                ) : (
                  <>
                    {/* Fallback to agent_reply if no messages */}
                    {selectedStepData.agent_reply ? (
                      <div className="flex-1 flex flex-col min-h-0">
                        <div className="flex items-center gap-2 mb-3">
                          <Zap className="w-4 h-4 text-yellow-400" />
                          <span className="text-xs font-semibold text-slate-400">RESULT</span>
                        </div>
                        <div 
                          className="flex-1 p-5 bg-slate-900 rounded-lg border border-slate-600 overflow-y-auto shadow-inner custom-scrollbar prose prose-invert prose-sm max-w-none"
                          dangerouslySetInnerHTML={{ 
                            __html: marked(extractResult(selectedStepData.agent_reply)) as string
                          }}
                          style={{
                            fontSize: '0.875rem',
                            lineHeight: '1.6',
                          }}
                        />
                      </div>
                    ) : loadingMessages ? (
                      <div className="text-center text-slate-500 text-sm py-8">
                        <Activity className="w-8 h-8 mx-auto mb-2 opacity-50 animate-pulse" />
                        <p>Loading...</p>
                      </div>
                    ) : (
                      <div className="text-center text-slate-500 text-sm py-8">
                        {selectedStepData.status === 'planned' || selectedStepData.status === 'awaiting_feedback' ? (
                          <div>
                            <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p>Awaiting approval</p>
                          </div>
                        ) : selectedStepData.status === 'executing' || selectedStepData.status === 'approved' ? (
                          <div>
                            <Activity className="w-8 h-8 mx-auto mb-2 opacity-50 animate-pulse" />
                            <p>Agent is working...</p>
                          </div>
                        ) : (
                          <div>
                            <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p>No output yet</p>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Legacy error message display */}
              {selectedStepData.error_message && !stepMessages.some(m => m.message_type === 'error') && (
                <div className="p-4 bg-error-500/10 border border-error-500/30 rounded-lg text-sm text-error-400 flex items-start gap-2">
                  <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="block mb-1">Error Occurred</strong>
                    <span>{selectedStepData.error_message}</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
              <div className="text-center">
                <Play className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Select a step to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

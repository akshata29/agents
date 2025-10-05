import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSession } from '../contexts/SessionContext';
import ExecutionProgress from '../components/ExecutionProgress';
import ResultsView from '../components/ResultsView';
import ExportPanel from '../components/ExportPanel';
import { FileText, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import * as api from '../services/api';
import type { PlanWithSteps } from '../types';

const TaskDetailsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { session, messages, setCurrentPlan, initializeSession } = useSession();
  const [isPolling, setIsPolling] = useState(false);
  const [isLoadingFromUrl, setIsLoadingFromUrl] = useState(false);
  const [historicalPlan, setHistoricalPlan] = useState<PlanWithSteps | null>(null);
  const [hasLoadedFromUrl, setHasLoadedFromUrl] = useState(false);

  // Load plan from URL parameters if provided (only once)
  useEffect(() => {
    const planId = searchParams.get('plan_id');
    const sessionId = searchParams.get('session_id');

    if (planId && sessionId && !hasLoadedFromUrl) {
      setHasLoadedFromUrl(true);
      setIsLoadingFromUrl(true);
      
      api.getPlan(planId, sessionId)
        .then((plan) => {
          // If we don't have an active session, initialize one
          if (!session) {
            initializeSession();
          }
          
          // Set the plan both in context and local state
          setCurrentPlan(plan);
          setHistoricalPlan(plan);
          setIsLoadingFromUrl(false);
        })
        .catch((error) => {
          console.error('Failed to load plan from URL:', error);
          setIsLoadingFromUrl(false);
        });
    }
  }, [searchParams, setCurrentPlan, initializeSession, session, hasLoadedFromUrl]);

  // Poll for plan status updates
  useEffect(() => {
    if (!session?.currentPlan || session.currentPlan.overall_status === 'completed' || session.currentPlan.overall_status === 'failed') {
      return;
    }

    setIsPolling(true);
    const pollInterval = setInterval(async () => {
      try {
        const plan = await api.getPlan(session.currentPlan!.id, session.currentPlan!.session_id);
        setCurrentPlan(plan);

        // Stop polling if completed or failed
        if (plan.overall_status === 'completed' || plan.overall_status === 'failed') {
          setIsPolling(false);
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Failed to fetch plan status:', error);
      }
    }, 2000); // Poll every 2 seconds

    return () => {
      clearInterval(pollInterval);
      setIsPolling(false);
    };
  }, [session?.currentPlan, setCurrentPlan]);

  // Show loading state when loading plan from URL
  if (isLoadingFromUrl) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-12 text-center">
          <Loader2 className="h-16 w-16 text-primary-400 mx-auto mb-4 animate-spin" />
          <h2 className="text-xl font-semibold text-white mb-2">Loading Session...</h2>
          <p className="text-slate-400">
            Retrieving analysis results from history.
          </p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-12 text-center">
          <FileText className="h-16 w-16 text-slate-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">No Active Task</h2>
          <p className="text-slate-400">
            Start a new analysis from the "New Analysis" tab to see task details here.
          </p>
        </div>
      </div>
    );
  }

  const currentPlan = session?.currentPlan || historicalPlan;
  const hasResults = currentPlan?.overall_status === 'completed';

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Polling Indicator */}
      {isPolling && (
        <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3 flex items-center space-x-3">
          <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
          <span className="text-sm text-blue-400">Monitoring task execution...</span>
        </div>
      )}

      {/* Session Info */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Session Information</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-slate-400">Session ID</p>
            <p className="text-sm font-mono text-slate-200">{session.id}</p>
          </div>
          <div>
            <p className="text-sm text-slate-400">Files Uploaded</p>
            <p className="text-sm text-slate-200">{session.files.length} file(s)</p>
          </div>
        </div>
      </div>

      {/* Messages/Activity Log */}
      {messages.length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Activity Log</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex items-start space-x-3 px-4 py-2 rounded-lg text-sm ${
                  message.type === 'error'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                    : message.type === 'system'
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    : 'bg-slate-700 text-slate-300 border border-slate-600'
                }`}
              >
                <div className="flex-shrink-0 mt-0.5">
                  {message.type === 'error' && <XCircle className="h-4 w-4" />}
                  {message.type === 'system' && <Clock className="h-4 w-4" />}
                  {(message.type === 'user' || message.type === 'agent') && <CheckCircle className="h-4 w-4" />}
                </div>
                <div className="flex-1">
                  <p>{message.content}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Current Plan Info */}
      {currentPlan && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Current Task Plan</h3>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-slate-400">Objective</p>
              <p className="text-sm text-slate-200">{currentPlan.initial_goal}</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-slate-400">Total Steps</p>
                <p className="text-lg font-semibold text-slate-200">{currentPlan.total_steps}</p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Completed</p>
                <p className="text-lg font-semibold text-green-400">{currentPlan.completed_steps}</p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Status</p>
                <div className="flex items-center space-x-2 mt-1">
                  {currentPlan.overall_status === 'in_progress' && (
                    <>
                      <Loader2 className="h-4 w-4 text-primary-400 animate-spin" />
                      <span className="text-sm font-semibold text-primary-400">Executing</span>
                    </>
                  )}
                  {currentPlan.overall_status === 'completed' && (
                    <>
                      <CheckCircle className="h-4 w-4 text-green-400" />
                      <span className="text-sm font-semibold text-green-400">Completed</span>
                    </>
                  )}
                  {currentPlan.overall_status === 'failed' && (
                    <>
                      <XCircle className="h-4 w-4 text-red-400" />
                      <span className="text-sm font-semibold text-red-400">Failed</span>
                    </>
                  )}
                  {currentPlan.overall_status === 'pending' && (
                    <>
                      <Clock className="h-4 w-4 text-slate-400" />
                      <span className="text-sm font-semibold text-slate-400">Pending</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Execution Progress */}
      {session.executing && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Execution Progress</h3>
          <ExecutionProgress />
        </div>
      )}

      {/* Results Section - Show if plan has steps */}
      {currentPlan && currentPlan.steps && currentPlan.steps.length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Analysis Results</h3>
          <ResultsView />
        </div>
      )}

      {/* Export Results - Only when completed */}
      {hasResults && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Export Results</h3>
          <ExportPanel />
        </div>
      )}

      {/* No active execution message */}
      {!session.executing && !hasResults && currentPlan && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-12 text-center">
          <Clock className="h-16 w-16 text-slate-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">Plan Created</h3>
          <p className="text-slate-400">
            The task plan has been created. Execution will begin shortly.
          </p>
        </div>
      )}
    </div>
  );
};

export default TaskDetailsPage;

import React, { useEffect, useState } from 'react';
import { useSession } from '../contexts/SessionContext';
import { CheckCircle, Circle, Loader2, AlertCircle } from 'lucide-react';
import * as api from '../services/api';

const ExecutionProgress: React.FC = () => {
  const { session, updateStatus, setCurrentPlan } = useSession();
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    if (!session?.currentPlan) return;

    const planId = session.currentPlan.id;
    const sessionId = session.id;

    const poll = async () => {
      try {
        const status = await api.getPlanStatus(planId, sessionId);
        updateStatus(status);

        if (status.overall_status === 'in_progress' && !polling) {
          setPolling(true);
        } else if (['completed', 'failed'].includes(status.overall_status)) {
          setPolling(false);
          // Fetch complete plan with results
          const completePlan = await api.getPlan(planId, sessionId);
          setCurrentPlan(completePlan);
        }
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    };

    // Initial poll
    poll();

    // Continue polling if in progress
    let interval: number | null = null;
    if (session.status?.overall_status === 'in_progress') {
      interval = setInterval(poll, 2000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [session?.currentPlan?.id, session?.status?.overall_status]);

  if (!session?.currentPlan || !session.status) {
    return null;
  }

  const { status, currentPlan } = session;

  const getStepIcon = (stepStatus: string) => {
    switch (stepStatus) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'executing':
        return <Loader2 className="h-5 w-5 text-primary-600 animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Circle className="h-5 w-5 text-gray-300" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">
            Overall Progress
          </span>
          <span className="text-sm font-semibold text-primary-600">
            {Math.round(status.progress_percentage)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full transition-all duration-500"
            style={{ width: `${status.progress_percentage}%` }}
          />
        </div>
        <div className="mt-2 text-sm text-gray-600">
          {status.completed_steps} of {status.total_steps} steps completed
        </div>
      </div>

      {/* Current Step */}
      {status.current_step && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
            <div>
              <p className="font-medium text-blue-900">Currently Executing</p>
              <p className="text-sm text-blue-700">{status.current_step}</p>
              {status.current_agent && (
                <p className="text-xs text-blue-600 mt-1">
                  Agent: {status.current_agent}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Steps List */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-700">Execution Steps</h4>
        {currentPlan.steps.map((step, idx) => (
          <div
            key={step.id}
            className={`flex items-start space-x-3 p-3 rounded-lg border ${
              step.status === 'executing'
                ? 'bg-blue-50 border-blue-200'
                : step.status === 'completed'
                ? 'bg-green-50 border-green-200'
                : step.status === 'failed'
                ? 'bg-red-50 border-red-200'
                : 'bg-gray-50 border-gray-200'
            }`}
          >
            <div className="flex-shrink-0 mt-0.5">
              {getStepIcon(step.status)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-semibold text-gray-500">
                  Step {idx + 1}
                </span>
                <span className="text-xs px-2 py-0.5 bg-white rounded-full border border-gray-200">
                  {step.agent}
                </span>
              </div>
              <p className="text-sm text-gray-900 mt-1">{step.action}</p>
              {step.error_message && (
                <p className="text-xs text-red-600 mt-1">{step.error_message}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Recent Messages */}
      {status.recent_messages && status.recent_messages.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Recent Activity
          </h4>
          <div className="space-y-1 text-sm text-gray-600">
            {status.recent_messages.slice(-3).map((msg, idx) => (
              <div key={idx} className="flex items-start space-x-2">
                <span className="text-gray-400">•</span>
                <span>{msg}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExecutionProgress;

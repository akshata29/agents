/**
 * StepCard Component
 * 
 * Individual step card with approval/rejection controls
 */

import React, { useState } from 'react';
import { CheckCircle, XCircle, Clock, AlertCircle, User } from 'lucide-react';
import { Step } from '../lib/api';

interface StepCardProps {
  step: Step;
  stepNumber: number;
  onApprove: () => void;
  onReject: (reason?: string) => void;
  isExecuting?: boolean;
}

export const StepCard: React.FC<StepCardProps> = ({
  step,
  stepNumber,
  onApprove,
  onReject,
  isExecuting = false
}) => {
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'border-green-500 bg-green-50';
      case 'action_requested':
      case 'approved':
        return 'border-blue-500 bg-blue-50';
      case 'failed':
      case 'rejected':
        return 'border-red-500 bg-red-50';
      default:
        return 'border-gray-300 bg-white';
    }
  };

  const getStatusIcon = () => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'action_requested':
      case 'approved':
        return <Clock className="w-5 h-5 text-blue-600 animate-pulse" />;
      case 'failed':
      case 'rejected':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
    }
  };

  const handleReject = () => {
    onReject(rejectReason || undefined);
    setShowRejectDialog(false);
    setRejectReason('');
  };

  const isPending = step.status === 'planned' || step.status === 'awaiting_feedback';
  const isCompleted = step.status === 'completed';
  const isFailed = step.status === 'failed' || step.status === 'rejected';

  return (
    <div className={`border-2 rounded-lg p-6 transition-all ${getStatusColor(step.status)}`}>
      {/* Step Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-3 flex-1">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white font-semibold flex-shrink-0">
            {stepNumber}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              {getStatusIcon()}
              <span className="text-xs font-medium uppercase text-gray-500">
                {step.status.replace('_', ' ')}
              </span>
            </div>
            <p className="text-gray-900 font-medium">{step.action}</p>
          </div>
        </div>
      </div>

      {/* Agent Info */}
      <div className="flex flex-wrap gap-4 mb-4 text-sm">
        <div className="flex items-center gap-2 text-gray-600">
          <User className="w-4 h-4" />
          <span className="px-2 py-0.5 bg-gray-200 rounded text-xs">{step.agent}</span>
        </div>
      </div>

      {/* Result (if completed) */}
      {isCompleted && step.agent_reply && (
        <div className="mt-4 p-4 bg-white rounded-lg border border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Result:</h4>
          <div className="text-sm text-gray-600 whitespace-pre-wrap">
            {step.agent_reply}
          </div>
        </div>
      )}

      {/* Error (if failed) */}
      {isFailed && step.agent_reply && (
        <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
          <h4 className="text-sm font-medium text-red-700 mb-2">Error:</h4>
          <div className="text-sm text-red-600">
            {step.agent_reply}
          </div>
        </div>
      )}

      {/* Approval Actions */}
      {isPending && !isExecuting && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex gap-3">
            <button
              onClick={onApprove}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              <CheckCircle className="w-4 h-4" />
              Approve & Execute
            </button>
            <button
              onClick={() => setShowRejectDialog(true)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
            >
              <XCircle className="w-4 h-4" />
              Reject
            </button>
          </div>
        </div>
      )}

      {/* Reject Dialog */}
      {showRejectDialog && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Rejection Reason (Optional)</h4>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Why are you rejecting this step?"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
          />
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleReject}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
            >
              Confirm Rejection
            </button>
            <button
              onClick={() => {
                setShowRejectDialog(false);
                setRejectReason('');
              }}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default StepCard;

import React, { useEffect, useState } from 'react';
import { useSession } from '../contexts/SessionContext';
import { useNavigate } from 'react-router-dom';
import FileUploader from '../components/FileUploader';
import PromptInput from '../components/PromptInput';
import QuickTasks from '../components/QuickTasks';
import { Play, Loader2 } from 'lucide-react';
import * as api from '../services/api';
import type { PlanWithSteps } from '../types';

const HomePage: React.FC = () => {
  const { session, initializeSession, messages, addMessage, setCurrentPlan } = useSession();
  const [isExecuting, setIsExecuting] = useState(false);
  const [objective, setObjective] = useState('');
  const [summaryType, setSummaryType] = useState('detailed');
  const [persona, setPersona] = useState('executive');
  const navigate = useNavigate();

  useEffect(() => {
    if (!session) {
      initializeSession();
    }
  }, [session, initializeSession]);

  const handleQuickTaskSelect = (taskObjective: string) => {
    setObjective(taskObjective);
  };

  const handleExecute = async () => {
    if (!session || !objective.trim() || session.files.length === 0) {
      addMessage({
        type: 'error',
        content: 'Please upload files and provide an objective before executing.',
      });
      return;
    }

    const fileIds = session.files
      .filter((f) => f.metadata)
      .map((f) => f.metadata!.id);

    if (fileIds.length === 0) {
      addMessage({
        type: 'error',
        content: 'Please wait for files to finish uploading.',
      });
      return;
    }

    setIsExecuting(true);

    try {
      // Note: user_id is now automatically extracted from Azure EasyAuth headers on the backend
      const response = await api.createAndExecutePlan(
        session.id,
        objective,
        fileIds,
        summaryType,
        persona
      );

      // Store the plan information in session context
      const planData = response.data;
      const plan: PlanWithSteps = {
        id: planData.plan_id,
        session_id: planData.session_id,
        user_id: '', // Will be populated when we fetch the full plan
        initial_goal: objective,
        summary: undefined,
        overall_status: 'in_progress',
        file_ids: fileIds,
        total_steps: planData.total_steps,
        completed_steps: 0,
        failed_steps: 0,
        steps: planData.steps || [],
        timestamp: new Date().toISOString(),
      };

      setCurrentPlan(plan);

      // Navigate to task details to see progress
      navigate('/task-details');
    } catch (error: any) {
      addMessage({
        type: 'error',
        content: `Failed to execute: ${error.response?.data?.detail || error.message}`,
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const canExecute =
    session &&
    session.files.length > 0 &&
    session.files.every((f) => f.status === 'uploaded') &&
    objective.trim().length > 0 &&
    !isExecuting;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* File Upload Section */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">
          Step 1: Upload Files
        </h3>
        <FileUploader />
      </div>

      {/* Objective Input Section */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-6">
          Step 2: Enter Your Objective
        </h3>
        
        {/* Quick Tasks */}
        <div className="mb-6">
          <QuickTasks 
            onSelectTask={handleQuickTaskSelect}
            disabled={isExecuting}
          />
        </div>

        {/* Summary Preferences */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Summary Type
            </label>
            <select
              value={summaryType}
              onChange={(e) => setSummaryType(e.target.value)}
              disabled={isExecuting}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="brief">Brief - Quick overview</option>
              <option value="detailed">Detailed - Comprehensive insights</option>
              <option value="comprehensive">Comprehensive - Full analysis</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Target Audience
            </label>
            <select
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              disabled={isExecuting}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="executive">Executive - High-level insights</option>
              <option value="technical">Technical - Detailed analysis</option>
              <option value="general">General - Balanced overview</option>
            </select>
          </div>
        </div>

        {/* Custom Objective Input */}
        <div className="space-y-4">
          <PromptInput
            value={objective}
            onChange={setObjective}
            onSubmit={handleExecute}
            disabled={isExecuting}
            placeholder="Or write your custom objective here..."
          />
          <button
            onClick={handleExecute}
            disabled={!canExecute}
            className={`w-full flex items-center justify-center space-x-2 px-6 py-3 rounded-lg font-medium transition-colors ${
              canExecute
                ? 'bg-primary-600 text-white hover:bg-primary-700'
                : 'bg-slate-700 text-slate-500 cursor-not-allowed'
            }`}
          >
            {isExecuting ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Starting Execution...</span>
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                <span>Execute Analysis</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Messages Section */}
      {messages.length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Messages</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
            {messages.map((message, idx) => (
              <div
                key={idx}
                className={`px-4 py-2 rounded-lg text-sm ${
                  message.type === 'error'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                    : message.type === 'system'
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    : 'bg-slate-700 text-slate-300 border border-slate-600'
                }`}
              >
                {message.content}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default HomePage;

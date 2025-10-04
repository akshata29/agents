import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendingUp } from 'lucide-react';
import { TaskList } from './components/TaskList';
import { TaskInput } from './components/TaskInput';
import { PlanView } from './components/PlanView';
import { UserHistory } from './components/UserHistory';
import { apiClient, Plan } from './lib/api';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

function AppContent() {
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [isCreatingPlan, setIsCreatingPlan] = useState(false);
  const [view, setView] = useState<'new' | 'detail' | 'history'>('new');

  const handleTaskSelect = async (sessionId: string, planId: string) => {
    setSelectedSession(sessionId);
    setSelectedPlanId(planId);
    setView('detail');
    
    // Fetch plan details
    try {
      const planData = await apiClient.getPlan(sessionId, planId);
      setPlan(planData);
    } catch (err) {
      console.error('Failed to fetch plan:', err);
    }
  };

  const handleCreatePlan = async (objective: string, ticker?: string) => {
    setIsCreatingPlan(true);
    
    try {
      const inputTask = {
        description: objective,
        ticker: ticker
        // No session_id - backend will create new one
      };
      
      const newPlan = await apiClient.createPlan(inputTask);
      setPlan(newPlan);
      setSelectedSession(newPlan.session_id);
      setSelectedPlanId(newPlan.id);
      setView('detail');
      
      // Refresh task list (will happen automatically via react-query)
    } catch (err) {
      console.error('Failed to create plan:', err);
    } finally {
      setIsCreatingPlan(false);
    }
  };

  const handleNewTask = () => {
    setPlan(null);
    setSelectedSession(null);
    setSelectedPlanId(null);
    setView('new');
  };

  const refreshPlan = async () => {
    if (!selectedSession || !selectedPlanId) return;
    
    try {
      const updatedPlan = await apiClient.getPlan(selectedSession, selectedPlanId);
      setPlan(updatedPlan);
    } catch (err) {
      console.error('Failed to refresh plan:', err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <TrendingUp className="w-8 h-8 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-white">
                  Financial Research Platform
                </h1>
                <p className="text-sm text-slate-400">
                  Multi-Agent Equity Analysis System
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm">
              <div className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full">
                System Operational
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <div className="bg-slate-800 border-b border-slate-700">
        <div className="px-6">
          <div className="flex space-x-1">
            <button
              onClick={handleNewTask}
              className={`px-6 py-3 font-medium transition-colors ${
                view === 'new'
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              New Research
            </button>
            <button
              onClick={() => plan && setView('detail')}
              className={`px-6 py-3 font-medium transition-colors ${
                view === 'detail'
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              disabled={!plan}
            >
              Task Details
            </button>
            <button
              onClick={() => setView('history')}
              className={`px-6 py-3 font-medium transition-colors ${
                view === 'history'
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              History
            </button>
          </div>
        </div>
      </div>

      {/* Main Content - 3 Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Compact Task List */}
        <div className="w-56 flex-shrink-0">
          <TaskList
            onTaskSelect={handleTaskSelect}
            selectedPlanId={selectedPlanId}
          />
        </div>

        {/* Center/Right Panel - Main Content Area with Right Output Panel */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 overflow-y-auto bg-slate-900 p-6">
            {view === 'new' && (
              <TaskInput
                onSubmit={handleCreatePlan}
                isLoading={isCreatingPlan}
              />
            )}
            
            {view === 'history' && (
              <div className="max-w-4xl mx-auto">
                <UserHistory onSelectTask={handleTaskSelect} />
              </div>
            )}
            
            {view === 'detail' && plan && (
              <div className="h-full">
                <PlanView
                  plan={plan}
                  onApprove={async (stepId) => {
                    await apiClient.approveStep({
                      session_id: plan.session_id,
                      plan_id: plan.id,
                      step_id: stepId,
                      approved: true
                    });
                    await refreshPlan();
                  }}
                  onReject={async (stepId, reason) => {
                    await apiClient.approveStep({
                      session_id: plan.session_id,
                      plan_id: plan.id,
                      step_id: stepId,
                      approved: false,
                      human_feedback: reason
                    });
                    await refreshPlan();
                  }}
                  onRefreshPlan={refreshPlan}
                  isExecuting={false}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-slate-800 border-t border-slate-700">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <div>
              Powered by Microsoft Agent Framework & Magentic Foundation
            </div>
            <div>
              v2.0.0 | Dynamic Planning
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;

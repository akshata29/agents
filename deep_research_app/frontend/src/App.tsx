import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from './api';
import Dashboard from './components/Dashboard.tsx';
import ResearchForm from './components/ResearchForm.tsx';
import WorkflowVisualization from './components/WorkflowVisualization.tsx';
import ExecutionMonitor from './components/ExecutionMonitor.tsx';
import { Brain, Workflow, FileSearch } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'new' | 'workflow' | 'monitor'>('new');
  const [currentExecutionId, setCurrentExecutionId] = useState<string | null>(null);

  // Fetch workflow info
  const { data: workflowInfo } = useQuery({
    queryKey: ['workflowInfo'],
    queryFn: apiClient.getWorkflowInfo,
  });

  const handleResearchStart = (executionId: string) => {
    setCurrentExecutionId(executionId);
    setActiveTab('monitor');
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Brain className="w-8 h-8 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-white">Deep Research</h1>
                <p className="text-sm text-slate-400">Powered by Magentic Foundation Framework</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm">
              <div className="px-3 py-1 bg-success-500/20 text-success-400 rounded-full">
                Framework v1.0.0
              </div>
              {workflowInfo && (
                <div className="px-3 py-1 bg-primary-500/20 text-primary-400 rounded-full">
                  {workflowInfo.total_tasks} Tasks
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-slate-800 border-b border-slate-700">
        <div className="container mx-auto px-6">
          <div className="flex space-x-1">
            <button
              onClick={() => setActiveTab('new')}
              className={`px-6 py-3 font-medium transition-colors flex items-center space-x-2 ${
                activeTab === 'new'
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              <FileSearch className="w-4 h-4" />
              <span>New Research</span>
            </button>
            <button
              onClick={() => setActiveTab('workflow')}
              className={`px-6 py-3 font-medium transition-colors flex items-center space-x-2 ${
                activeTab === 'workflow'
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              <Workflow className="w-4 h-4" />
              <span>Execution Modes</span>
            </button>
            <button
              onClick={() => setActiveTab('monitor')}
              className={`px-6 py-3 font-medium transition-colors flex items-center space-x-2 ${
                activeTab === 'monitor'
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              disabled={!currentExecutionId}
            >
              <Brain className="w-4 h-4" />
              <span>Execution Monitor</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {activeTab === 'new' && (
          <div className="space-y-6">
            <Dashboard />
            <ResearchForm onResearchStart={handleResearchStart} />
          </div>
        )}
        {activeTab === 'workflow' && workflowInfo && (
          <WorkflowVisualization workflow={workflowInfo} />
        )}
        {activeTab === 'monitor' && currentExecutionId && (
          <ExecutionMonitor executionId={currentExecutionId} />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-slate-800 border-t border-slate-700 mt-12">
        <div className="container mx-auto px-6 py-4">
          <div className="text-center text-sm text-slate-400">
            <p>
              Built with{' '}
              <a
                href="https://github.com/microsoft/agent-framework"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-400 hover:text-primary-300"
              >
                Microsoft Agent Framework
              </a>{' '}
              and Magentic Foundation
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;

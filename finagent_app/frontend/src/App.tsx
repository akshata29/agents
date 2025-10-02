import { useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { TrendingUp } from 'lucide-react';
import ResearchForm from './components/ResearchForm';
import ExecutionMonitor from './components/ExecutionMonitor';
import AgentBanner from './components/AgentBanner';
import { api } from './lib/api';
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
  const [activeTab, setActiveTab] = useState<'new' | 'monitor'>('new');
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  // Fetch execution data if we have a runId - now inside QueryClientProvider
  const { data: execution } = useQuery({
    queryKey: ['execution', currentRunId],
    queryFn: () => currentRunId ? api.getRunStatus(currentRunId) : null,
    enabled: !!currentRunId,
    refetchInterval: 2000, // Poll every 2 seconds
  });

  const handleResearchStart = (runId: string) => {
    setCurrentRunId(runId);
    setActiveTab('monitor');
    setSelectedAgent(null);
  };

  const handleAgentSelect = (agentName: string) => {
    setSelectedAgent(agentName);
    setActiveTab('monitor');
  };

  return (
      <div className="min-h-screen bg-slate-900 text-slate-100">
        {/* Header */}
        <header className="bg-slate-800 border-b border-slate-700">
          <div className="container mx-auto px-6 py-4">
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
                <div className="px-3 py-1 bg-success-500/20 text-success-400 rounded-full">
                  System Operational
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Agent Overview Banner - Now Interactive */}
        <AgentBanner 
          steps={execution?.steps} 
          onAgentClick={handleAgentSelect}
        />

        {/* Navigation */}
        <div className="bg-slate-800 border-b border-slate-700">
          <div className="container mx-auto px-6">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab('new')}
                className={`px-6 py-3 font-medium transition-colors ${
                  activeTab === 'new'
                    ? 'text-primary-400 border-b-2 border-primary-400'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                New Research
              </button>
              <button
                onClick={() => setActiveTab('monitor')}
                className={`px-6 py-3 font-medium transition-colors ${
                  activeTab === 'monitor'
                    ? 'text-primary-400 border-b-2 border-primary-400'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
                disabled={!currentRunId}
              >
                Execution Monitor
              </button>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="container mx-auto px-6 py-8">
          {activeTab === 'new' && (
            <ResearchForm onResearchStart={handleResearchStart} />
          )}
          {activeTab === 'monitor' && currentRunId && (
            <ExecutionMonitor 
              runId={currentRunId} 
              selectedAgentProp={selectedAgent}
              onAgentSelect={handleAgentSelect}
            />
          )}
        </main>

        {/* Footer */}
        <footer className="bg-slate-800 border-t border-slate-700 mt-12">
          <div className="container mx-auto px-6 py-4">
            <div className="flex items-center justify-between text-sm text-slate-400">
              <div>
                Powered by Microsoft Agent Framework & finagentsk
              </div>
              <div>
                v1.0.0 | <a href="/docs" className="hover:text-primary-400">Documentation</a>
              </div>
            </div>
          </div>
        </footer>
      </div>
  );
}

export default App;

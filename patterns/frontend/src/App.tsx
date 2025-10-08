import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from './api';
import Dashboard from './components/Dashboard';
import PatternSelector from './components/PatternSelector';
import ExecutionMonitor from './components/ExecutionMonitor';
import ExecutionHistory from './components/ExecutionHistory';
import { Brain, Layers, Activity, History, Settings } from 'lucide-react';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'patterns' | 'execution' | 'history' | 'settings'>('patterns');
  const [currentExecutionId, setCurrentExecutionId] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string>(`session-${Date.now()}`);

  // Fetch system status
  const { data: systemStatus } = useQuery({
    queryKey: ['systemStatus'],
    queryFn: apiClient.getSystemStatus,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch available patterns
  const { data: patterns, isLoading: patternsLoading } = useQuery({
    queryKey: ['patterns'],
    queryFn: apiClient.getPatterns,
  });

  const handleExecutionStart = (executionId: string) => {
    setCurrentExecutionId(executionId);
    setActiveTab('execution');
  };

  const handleNavigateToExecution = (executionId: string) => {
    setCurrentExecutionId(executionId);
    setActiveTab('execution');
  };

  // Handle tab changes
  const handleTabChange = (tab: 'patterns' | 'execution' | 'history' | 'settings') => {
    if (tab === 'patterns') {
      setCurrentSessionId(`session-${Date.now()}`);
    }
    setActiveTab(tab);
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
                <h1 className="text-2xl font-bold text-white">Agent Patterns</h1>
                <p className="text-slate-400 text-sm">
                  Microsoft Agent Framework Orchestration Patterns
                </p>
              </div>
            </div>
            
            {/* System Status */}
            <div className="flex items-center space-x-4">
              {systemStatus && (
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    systemStatus.azure_openai_configured && systemStatus.agent_framework_available
                      ? 'bg-green-500' 
                      : 'bg-red-500'
                  }`} />
                  <span className="text-sm text-slate-400">
                    {systemStatus.azure_openai_configured && systemStatus.agent_framework_available
                      ? 'System Ready'
                      : 'Configuration Required'
                    }
                  </span>
                </div>
              )}
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="flex space-x-6 mt-4">
            <button
              onClick={() => handleTabChange('patterns')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'patterns'
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Patterns</span>
            </button>
            
            <button
              onClick={() => handleTabChange('execution')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'execution'
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
              disabled={!currentExecutionId}
            >
              <Activity className="w-4 h-4" />
              <span>Execution</span>
            </button>
            
            <button
              onClick={() => handleTabChange('history')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'history'
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              <History className="w-4 h-4" />
              <span>History</span>
            </button>
            
            <button
              onClick={() => handleTabChange('settings')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'settings'
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {activeTab === 'patterns' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1">
              <PatternSelector
                patterns={patterns || []}
                isLoading={patternsLoading}
                onExecutionStart={handleExecutionStart}
                sessionId={currentSessionId}
              />
            </div>
            <div className="lg:col-span-2">
              <Dashboard patterns={patterns || []} systemStatus={systemStatus} />
            </div>
          </div>
        )}

        {activeTab === 'execution' && currentExecutionId && (
          <ExecutionMonitor executionId={currentExecutionId} />
        )}

        {activeTab === 'history' && (
          <ExecutionHistory onNavigateToExecution={handleNavigateToExecution} />
        )}

        {activeTab === 'settings' && (
          <div className="bg-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">System Configuration</h2>
            {systemStatus ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <span>Azure OpenAI</span>
                  <span className={`px-3 py-1 rounded-full text-sm ${
                    systemStatus.azure_openai_configured
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {systemStatus.azure_openai_configured ? 'Configured' : 'Not Configured'}
                  </span>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <span>Agent Framework</span>
                  <span className={`px-3 py-1 rounded-full text-sm ${
                    systemStatus.agent_framework_available
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {systemStatus.agent_framework_available ? 'Available' : 'Not Available'}
                  </span>
                </div>
                
                {systemStatus.endpoint && (
                  <div className="p-4 bg-slate-700 rounded-lg">
                    <div className="text-sm text-slate-400">Endpoint</div>
                    <div className="text-white">{systemStatus.endpoint}</div>
                  </div>
                )}
                
                {systemStatus.model && (
                  <div className="p-4 bg-slate-700 rounded-lg">
                    <div className="text-sm text-slate-400">Model</div>
                    <div className="text-white">{systemStatus.model}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-slate-400">Loading system status...</div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
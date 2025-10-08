import React from 'react';
import type { PatternInfo, SystemStatus } from '../types';
import { 
  Layers, 
  Users, 
  Clock, 
  CheckCircle2, 
  XCircle,
  AlertTriangle,
  Activity,
  Zap
} from 'lucide-react';

interface DashboardProps {
  patterns: PatternInfo[];
  systemStatus?: SystemStatus;
}

const Dashboard: React.FC<DashboardProps> = ({ patterns, systemStatus }) => {
  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="bg-gradient-to-br from-primary-600 to-primary-800 rounded-lg p-6 text-white">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-3 bg-white/20 rounded-lg">
            <Layers className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-2xl font-bold">AI Business Intelligence Platform</h2>
            <p className="text-primary-100">
              Enterprise Multi-Agent Orchestration • Strategic Solutions • Real-time Analytics
            </p>
          </div>
        </div>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Layers className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="text-sm text-slate-400">Available Patterns</div>
              <div className="text-xl font-semibold text-white">{patterns.length}</div>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-500/10 rounded-lg">
              <Users className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <div className="text-sm text-slate-400">Total Agents</div>
              <div className="text-xl font-semibold text-white">
                {patterns.reduce((sum, pattern) => sum + (pattern.agents?.length || 0), 0)}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${
              systemStatus?.azure_openai_configured 
                ? 'bg-green-500/10' 
                : 'bg-red-500/10'
            }`}>
              {systemStatus?.azure_openai_configured ? (
                <CheckCircle2 className="w-5 h-5 text-green-400" />
              ) : (
                <XCircle className="w-5 h-5 text-red-400" />
              )}
            </div>
            <div>
              <div className="text-sm text-slate-400">Azure OpenAI</div>
              <div className="text-sm font-medium text-white">
                {systemStatus?.azure_openai_configured ? 'Connected' : 'Not Connected'}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${
              systemStatus?.agent_framework_available 
                ? 'bg-green-500/10' 
                : 'bg-red-500/10'
            }`}>
              {systemStatus?.agent_framework_available ? (
                <Zap className="w-5 h-5 text-green-400" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-red-400" />
              )}
            </div>
            <div>
              <div className="text-sm text-slate-400">Agent Framework</div>
              <div className="text-sm font-medium text-white">
                {systemStatus?.agent_framework_available ? 'Available' : 'Unavailable'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Pattern Overview */}
      <div className="bg-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Pattern Overview</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {patterns.map((pattern) => (
            <div
              key={pattern.name}
              className="bg-slate-700/50 rounded-lg p-4 border border-slate-600"
            >
              <div className="flex items-center space-x-3 mb-3">
                <div className="text-2xl">{pattern.icon}</div>
                <div>
                  <h4 className="font-medium text-white">{pattern.name}</h4>
                  <p className="text-sm text-slate-400">{pattern.agents?.length || 0} agents</p>
                </div>
              </div>
              
              <p className="text-sm text-slate-300 mb-3 leading-relaxed">
                {pattern.description}
              </p>
              
              {pattern.use_cases && pattern.use_cases.length > 0 && (
                <div>
                  <h5 className="text-xs font-medium text-slate-400 mb-2">Use Cases</h5>
                  <div className="space-y-1">
                    {pattern.use_cases.slice(0, 2).map((useCase, index) => (
                      <div key={index} className="text-xs text-slate-400">
                        • {useCase}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Getting Started Guide */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">How It Works</h3>
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                1
              </div>
              <div>
                <div className="font-medium text-white">Select Pattern</div>
                <div className="text-sm text-slate-400">Choose the orchestration pattern that fits your use case</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                2
              </div>
              <div>
                <div className="font-medium text-white">Configure Task</div>
                <div className="text-sm text-slate-400">Define your objectives or use pre-configured scenarios</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                3
              </div>
              <div>
                <div className="font-medium text-white">Execute Workflow</div>
                <div className="text-sm text-slate-400">Launch AI agents and monitor real-time progress</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                4
              </div>
              <div>
                <div className="font-medium text-white">Review Results</div>
                <div className="text-sm text-slate-400">Analyze outcomes and export findings</div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Key Features</h3>
          <div className="space-y-3">
            <div className="flex items-center space-x-3">
              <Activity className="w-5 h-5 text-primary-400" />
              <span className="text-slate-300">Real-time execution monitoring</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <Users className="w-5 h-5 text-primary-400" />
              <span className="text-slate-300">Multi-agent collaboration</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <Layers className="w-5 h-5 text-primary-400" />
              <span className="text-slate-300">Multiple orchestration patterns</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <Clock className="w-5 h-5 text-primary-400" />
              <span className="text-slate-300">Execution history tracking</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <CheckCircle2 className="w-5 h-5 text-primary-400" />
              <span className="text-slate-300">Microsoft Agent Framework integration</span>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration Warning */}
      {systemStatus && (!systemStatus.azure_openai_configured || !systemStatus.agent_framework_available) && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-yellow-400">Configuration Required</h4>
              <p className="text-yellow-300 text-sm mt-1">
                Please ensure your Azure OpenAI credentials are configured and the Agent Framework is properly installed.
                Check the Settings tab for more details.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
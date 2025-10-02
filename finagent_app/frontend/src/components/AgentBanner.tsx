import { Building2, FileCheck, FileText, BarChart3, Activity, Brain, CheckCircle2, Loader2, XCircle, Circle } from 'lucide-react';

interface AgentBannerProps {
  steps?: any[];
  onAgentClick?: (agentName: string) => void;
}

const AGENTS = [
  { name: 'company', label: 'Company', icon: Building2 },
  { name: 'sec', label: 'SEC', icon: FileCheck },
  { name: 'earnings', label: 'Earnings', icon: FileText },
  { name: 'fundamentals', label: 'Fundamentals', icon: BarChart3 },
  { name: 'technicals', label: 'Technicals', icon: Activity },
  { name: 'report', label: 'Report', icon: Brain },
];

export default function AgentBanner({ steps, onAgentClick }: AgentBannerProps) {
  const getAgentStatus = (agentName: string) => {
    if (!steps) return null;
    const step = steps.find((s: any) => s.agent === agentName);
    return step?.status;
  };

  const getStatusIcon = (status: string | null) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-3 h-3 text-success-400" />;
      case 'running':
        return <Loader2 className="w-3 h-3 text-primary-400 animate-spin" />;
      case 'failed':
        return <XCircle className="w-3 h-3 text-error-400" />;
      case 'pending':
        return <Circle className="w-3 h-3 text-slate-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="bg-slate-800 border-b border-slate-700">
      <div className="container mx-auto px-6 py-3">
        <div className="flex items-center justify-around text-xs">
          {AGENTS.map((agent) => {
            const status = getAgentStatus(agent.name);
            const Icon = agent.icon;
            const isClickable = status === 'completed' && onAgentClick;

            return (
              <div
                key={agent.name}
                className={`flex items-center space-x-2 ${
                  isClickable ? 'cursor-pointer hover:text-primary-300 transition-colors' : ''
                }`}
                onClick={isClickable ? () => onAgentClick(agent.name) : undefined}
              >
                <div className="relative">
                  <Icon className={`w-4 h-4 ${
                    status === 'completed' ? 'text-success-400' :
                    status === 'running' ? 'text-primary-400' :
                    status === 'failed' ? 'text-error-400' :
                    'text-primary-400'
                  }`} />
                  {status && (
                    <div className="absolute -bottom-1 -right-1">
                      {getStatusIcon(status)}
                    </div>
                  )}
                </div>
                <span className={`${
                  status === 'completed' ? 'text-success-300' :
                  status === 'running' ? 'text-primary-300' :
                  status === 'failed' ? 'text-error-300' :
                  'text-slate-300'
                }`}>
                  {agent.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// @ts-nocheck
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../api';
import type { PatternInfo, PatternType } from '../types';
import { 
  Play, 
  ArrowRight, 
  Users, 
  Workflow,
  MessageSquare,
  RefreshCcw,
  Zap,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Microscope
} from 'lucide-react';

interface PatternSelectorProps {
  patterns: PatternInfo[];
  isLoading: boolean;
  onExecutionStart: (executionId: string) => void;
  sessionId: string;
}

// Pattern metadata with icons and scenarios
const PATTERN_METADATA = {
  sequential: {
    icon: Workflow,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20',
    description: 'Structured workflow execution: Strategic Planning → Research → Development → Quality Review',
    scenario: 'Digital Transformation Strategy',
    defaultTask: 'Develop a comprehensive digital transformation strategy for a mid-size manufacturing company looking to modernize operations, implement IoT systems, and improve customer experience across all touchpoints.',
    agents: ['Planner', 'Researcher', 'Writer', 'Reviewer'],
    quickTasks: [
      {
        title: 'Corporate Training Program',
        description: 'Design leadership development curriculum',
        task: 'Create a comprehensive leadership development program for mid-level managers in a Fortune 500 technology company, including curriculum design, delivery methods, assessment criteria, and success metrics.'
      },
      {
        title: 'Software Development Lifecycle',
        description: 'Plan new product development process',
        task: 'Design a complete software development lifecycle for launching a new mobile banking app, including requirements gathering, technical architecture, development phases, testing protocols, and deployment strategy.'
      },
      {
        title: 'Supply Chain Optimization',
        description: 'Redesign logistics and distribution',
        task: 'Optimize the supply chain for a global e-commerce company to reduce costs by 20% while improving delivery times, including vendor selection, warehouse optimization, and last-mile delivery improvements.'
      },
      {
        title: 'Merger & Acquisition Plan',
        description: 'Strategic M&A integration roadmap',
        task: 'Develop a detailed integration plan for acquiring a competitor company worth $500M, including due diligence processes, cultural integration, technology consolidation, and synergy realization timelines.'
      }
    ]
  },
  concurrent: {
    icon: RefreshCcw,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/20',
    description: 'Parallel task processing: Multi-dimensional analysis with simultaneous evaluation streams',
    scenario: 'Market Analysis',
    defaultTask: 'Conduct a comprehensive market analysis for launching a sustainable packaging startup that focuses on biodegradable food containers for the restaurant industry, including competitor analysis, target market sizing, and growth projections.',
    agents: ['Summarizer', 'ProsCons Analyst', 'Risk Assessor'],
    quickTasks: [
      {
        title: 'Investment Decision',
        description: 'Multi-criteria financial analysis',
        task: 'Evaluate a $10M investment opportunity in renewable energy infrastructure, analyzing financial returns, environmental impact, regulatory risks, and market competition simultaneously across different expert perspectives.'
      },
      {
        title: 'Product Launch Assessment',
        description: 'Parallel market evaluation',
        task: 'Assess the viability of launching a new AI-powered fitness app in three different markets (US, Europe, Asia) by analyzing user demographics, competitive landscape, and regulatory requirements concurrently.'
      },
      {
        title: 'Crisis Response Analysis',
        description: 'Multi-angle impact assessment',
        task: 'Analyze the impact of a major data breach on a financial services company, evaluating legal implications, customer trust effects, financial costs, and operational recovery requirements in parallel.'
      },
      {
        title: 'Technology Adoption Study',
        description: 'Simultaneous feasibility review',
        task: 'Evaluate adopting blockchain technology for supply chain transparency by analyzing technical feasibility, cost implications, security benefits, and implementation challenges across multiple business units simultaneously.'
      }
    ]
  },
  group_chat: {
    icon: MessageSquare,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/20',
    description: 'Collaborative decision-making: Interactive stakeholder consultation and iterative refinement',
    scenario: 'Product Launch',
    defaultTask: 'Create a complete go-to-market plan for launching an innovative AI-powered personal finance app that helps millennials and Gen Z users automate savings, track expenses, and make smart investment decisions.',
    agents: ['Writer', 'Reviewer', 'Moderator'],
    quickTasks: [
      {
        title: 'Policy Development',
        description: 'Collaborative policy creation',
        task: 'Develop a comprehensive remote work policy for a 5000-employee corporation that balances productivity, employee satisfaction, and operational efficiency, requiring input from HR, legal, and management stakeholders.'
      },
      {
        title: 'Content Strategy',
        description: 'Multi-stakeholder content planning',
        task: 'Create a content marketing strategy for a B2B SaaS company targeting enterprise customers, involving marketing, sales, and product teams in collaborative discussions to align messaging and tactics.'
      },
      {
        title: 'Budget Negotiation',
        description: 'Cross-department budget planning',
        task: 'Negotiate and finalize the annual technology budget for a healthcare organization, requiring collaboration between IT, finance, clinical departments, and executive leadership to prioritize investments.'
      },
      {
        title: 'Crisis Communication Plan',
        description: 'Stakeholder communication strategy',
        task: 'Develop a crisis communication plan for a potential product recall, requiring coordination between legal, PR, customer service, and executive teams to ensure consistent and effective messaging.'
      }
    ]
  },
  handoff: {
    icon: ArrowRight,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/20',
    description: 'Intelligent task routing: Automated delegation to specialized business units',
    scenario: 'Customer Service',
    defaultTask: 'I ordered a premium laptop for my home office three days ago, but when it arrived today, the screen was cracked and there were missing accessories. I need help with returning this defective product and getting a replacement as quickly as possible.',
    agents: ['Router', 'Status Agent', 'Returns Agent', 'Support Agent'],
    quickTasks: [
      {
        title: 'IT Help Desk Ticket',
        description: 'Technical support routing',
        task: 'My corporate email stopped working this morning and I can\'t access important client communications. The error message says "server timeout" and I\'ve already restarted my computer twice. I need urgent help as I have a client presentation in 2 hours.'
      },
      {
        title: 'Insurance Claim Processing',
        description: 'Multi-department claim handling',
        task: 'I was in a car accident last week and need to file an insurance claim. My vehicle has significant front-end damage, I have medical bills from the emergency room visit, and I need a rental car while mine is being repaired.'
      },
      {
        title: 'Banking Issue Resolution',
        description: 'Financial services routing',
        task: 'There are three unauthorized transactions on my credit card totaling $1,200 that I didn\'t make. I need to dispute these charges, get my card cancelled, and understand how this happened. I also need temporary access to my funds.'
      },
      {
        title: 'Legal Document Review',
        description: 'Specialized legal routing',
        task: 'I received a contract for a business partnership worth $2M and need legal review for intellectual property clauses, liability terms, and termination conditions. The deadline for signing is in 48 hours.'
      }
    ]
  },
  magentic: {
    icon: Zap,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/20',
    description: 'Strategic project management: Goal-oriented coordination with comprehensive task tracking',
    scenario: 'Technical Support',
    defaultTask: 'My newly installed smart home security system isn\'t connecting to my WiFi network properly. I\'ve tried restarting the router, checking the password, and following the basic setup guide, but the cameras still show as offline in the app.',
    agents: ['Planner', 'Researcher', 'Writer', 'Validator'],
    quickTasks: [
      {
        title: 'Event Planning Coordination',
        description: 'Multi-phase event management',
        task: 'Plan and execute a 3-day international technology conference for 2,000 attendees, coordinating venue logistics, speaker management, catering, technology setup, marketing, and attendee registration with multiple vendor relationships.'
      },
      {
        title: 'Product Development Project',
        description: 'Cross-functional product delivery',
        task: 'Launch a new mobile app feature that integrates AI-powered recommendations, requiring coordination between data science, mobile development, UX design, QA testing, marketing, and customer success teams with tight deadlines.'
      },
      {
        title: 'Infrastructure Migration',
        description: 'Complex technical project management',
        task: 'Migrate our entire cloud infrastructure from AWS to Azure within 6 months while maintaining 99.9% uptime, coordinating between DevOps, security, database, application teams, and external consultants.'
      },
      {
        title: 'Market Expansion Initiative',
        description: 'Strategic growth project',
        task: 'Launch our e-commerce platform in three new international markets, requiring legal compliance, payment integration, logistics setup, marketing localization, and customer support infrastructure coordination.'
      }
    ]
  },
  deep_research: {
    icon: Microscope,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10',
    borderColor: 'border-cyan-500/20',
    description: 'Comprehensive research orchestration: ReAct planning, concurrent search, code analysis, and cited reporting',
    scenario: 'AI Impact Analysis',
    defaultTask: 'Conduct comprehensive research on the adoption and impact of Large Language Models in enterprise software development, including productivity gains, security concerns, best practices for integration, and future trends.',
    agents: ['Planner', 'Researcher', 'ConcurrentSearch', 'Writer', 'Analyst', 'Reviewer'],
    quickTasks: [
      {
        title: 'Market Research Study',
        description: 'Multi-source competitive analysis',
        task: 'Research the cloud infrastructure market including AWS, Azure, and Google Cloud, analyzing market share, pricing strategies, unique features, enterprise adoption rates, and future technology roadmaps with proper citations.',
        recommendedMode: 'baseline'
      },
      {
        title: 'Technology Deep Dive',
        description: 'Technical documentation research',
        task: 'Conduct deep technical research on implementing microservices architecture for enterprise applications, including best practices, common pitfalls, monitoring strategies, security considerations, and real-world case studies.',
        recommendedMode: 'baseline'
      },
      {
        title: 'Academic Literature Review',
        description: 'Scholarly research synthesis',
        task: 'Comprehensive literature review on AI safety and alignment research, covering current approaches, key challenges, prominent researchers, recent breakthroughs, and future research directions with academic citations.',
        recommendedMode: 'reviewer'
      },
      {
        title: 'Industry Trend Analysis',
        description: 'Multi-perspective trend research',
        task: 'Analyze emerging trends in sustainable technology and green computing, including renewable energy data centers, carbon-neutral cloud services, energy-efficient AI models, and corporate sustainability initiatives.',
        recommendedMode: 'analyst'
      },
      {
        title: 'Regulatory Compliance Research',
        description: 'Legal and compliance deep-dive',
        task: 'Research GDPR, CCPA, and emerging data privacy regulations globally, analyzing compliance requirements, implementation strategies, penalties for non-compliance, and best practices for multi-jurisdictional operations.',
        recommendedMode: 'reviewer'
      },
      {
        title: 'Competitive Intelligence',
        description: 'Strategic competitor analysis',
        task: 'Deep competitive analysis of the electric vehicle market, examining Tesla, Rivian, and traditional automakers, covering technology innovations, market positioning, supply chain strategies, and investment in R&D.',
        recommendedMode: 'analyst'
      }
    ]
  }
};

const PatternSelector = ({ 
  patterns, 
  isLoading, 
  onExecutionStart, 
  sessionId 
}: PatternSelectorProps) => {
  const [selectedPattern, setSelectedPattern] = useState<PatternType>('sequential');
  const [customTask, setCustomTask] = useState('');
  const [useCustomTask, setUseCustomTask] = useState(false);
  const [researchMode, setResearchMode] = useState<string>('baseline');

  const executePatternMutation = useMutation({
    mutationFn: apiClient.executePattern,
    onSuccess: (response: any) => {
      onExecutionStart(response.execution_id);
    },
  });

  const handleExecute = () => {
    const metadata = PATTERN_METADATA[selectedPattern as keyof typeof PATTERN_METADATA];
    const task = useCustomTask && customTask.trim() 
      ? customTask.trim() 
      : metadata.defaultTask;

    const requestPayload: any = {
      pattern: selectedPattern,
      task,
      session_id: sessionId
    };

    // Add mode for deep_research pattern
    if (selectedPattern === 'deep_research') {
      requestPayload.mode = researchMode;
    }

    executePatternMutation.mutate(requestPayload);
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
          <span className="ml-2 text-slate-400">Loading patterns...</span>
        </div>
      </div>
    );
  }

  const selectedMetadata = PATTERN_METADATA[selectedPattern as keyof typeof PATTERN_METADATA];
  const IconComponent = selectedMetadata?.icon;

  const renderTaskConfiguration = (): JSX.Element => {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Task Configuration</h3>
        
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="use-custom"
              checked={useCustomTask}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUseCustomTask(e.target.checked)}
              className="w-4 h-4 text-primary-600 bg-slate-700 border-slate-600 rounded focus:ring-primary-500"
            />
            <label htmlFor="use-custom" className="text-sm text-slate-300">
              Use custom task instead of default scenario
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              {useCustomTask ? 'Custom Task' : 'Default Scenario Task'}
            </label>
            {useCustomTask ? (
              <textarea
                value={customTask}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCustomTask(e.target.value)}
                placeholder="Describe your custom task..."
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={4}
              />
            ) : (
              <div className="p-3 bg-slate-700/50 border border-slate-600 rounded-lg">
                <p className="text-sm text-slate-300 leading-relaxed">
                  {selectedMetadata?.defaultTask || 'No default task available'}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Pattern Selection */}
      <div className="bg-slate-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Select Pattern</h2>
        
        <div className="space-y-3">
          {Object.entries(PATTERN_METADATA).map(([pattern, metadata]) => {
            const Icon = metadata.icon;
            const isSelected = selectedPattern === pattern;
            
            return (
              <button
                key={pattern}
                onClick={() => setSelectedPattern(pattern as PatternType)}
                className={`w-full text-left p-4 rounded-lg border-2 transition-all duration-200 pattern-card ${
                  isSelected
                    ? `${metadata.bgColor} ${metadata.borderColor} border-solid`
                    : 'bg-slate-700/50 border-slate-600 hover:border-slate-500'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${metadata.bgColor}`}>
                    <Icon className={`w-5 h-5 ${metadata.color}`} />
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-white capitalize">
                      {pattern.replace('_', ' ')}
                    </div>
                    <div className="text-sm text-slate-400 mt-1">
                      {metadata.scenario}
                    </div>
                  </div>
                  {isSelected && (
                    <CheckCircle2 className="w-5 h-5 text-green-400" />
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected Pattern Details */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className={`p-3 rounded-lg ${selectedMetadata.bgColor}`}>
            <IconComponent className={`w-6 h-6 ${selectedMetadata.color}`} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white capitalize">
              {selectedPattern.replace('_', ' ')}
            </h3>
            <p className="text-slate-400 text-sm">{selectedMetadata.scenario}</p>
          </div>
        </div>

        <p className="text-slate-300 text-sm mb-4">
          {selectedMetadata.description}
        </p>

        {/* Agents */}
        <div className="mb-4">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Agents Involved</h4>
          <div className="flex flex-wrap gap-2">
            {selectedMetadata.agents.map((agent: string) => (
              <span
                key={agent}
                className="px-3 py-1 bg-slate-700 text-slate-300 text-xs rounded-full"
              >
                {agent}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Tasks */}
      <div className="bg-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Quick Tasks</h3>
        <p className="text-sm text-slate-400 mb-4">
          Real-world examples perfect for the {selectedPattern.replace('_', ' ')} pattern
        </p>
        
        <div className="space-y-3">
          {selectedMetadata?.quickTasks?.map((quickTask, index) => (
            <button
              key={index}
              onClick={() => {
                setCustomTask(quickTask.task);
                setUseCustomTask(true);
                // Set recommended mode for deep_research
                if (selectedPattern === 'deep_research' && quickTask.recommendedMode) {
                  setResearchMode(quickTask.recommendedMode);
                }
              }}
              className="w-full text-left p-4 rounded-lg bg-slate-700/50 border border-slate-600 hover:border-slate-500 transition-all duration-200 group"
            >
              <div className="flex items-start space-x-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="font-medium text-white group-hover:text-primary-300 transition-colors">
                      {quickTask.title}
                    </div>
                    {selectedPattern === 'deep_research' && quickTask.recommendedMode && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                        {quickTask.recommendedMode}
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-slate-400 mt-1">
                    {quickTask.description}
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-primary-400 transition-colors" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Deep Research Mode Selector */}
      {selectedPattern === 'deep_research' && (
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Research Mode</h3>
          <p className="text-sm text-slate-400 mb-4">
            Choose the execution mode for your deep research
          </p>
          
          <div className="grid grid-cols-2 gap-3">
            {[
              { value: 'baseline', label: 'Baseline', desc: 'Standard research workflow' },
              { value: 'reviewer', label: 'Reviewer', desc: 'With quality review loop' },
              { value: 'analyst', label: 'Analyst', desc: 'Code interpreter analysis' },
              { value: 'full', label: 'Full', desc: 'All features enabled' }
            ].map((mode) => (
              <button
                key={mode.value}
                onClick={() => setResearchMode(mode.value)}
                className={`p-3 rounded-lg border-2 transition-all ${
                  researchMode === mode.value
                    ? 'border-cyan-500 bg-cyan-500/10'
                    : 'border-slate-600 bg-slate-700/50 hover:border-slate-500'
                }`}
              >
                <div className="font-medium text-white text-sm">{mode.label}</div>
                <div className="text-xs text-slate-400 mt-1">{mode.desc}</div>
              </button>
            ))}
          </div>
          
          <div className="mt-4 p-3 bg-slate-700/50 rounded-lg border border-slate-600">
            <div className="text-xs text-slate-300">
              <strong>Current Mode:</strong> <span className="text-cyan-300">{researchMode}</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {researchMode === 'baseline' && '→ Planner → Researcher → Concurrent Search → Writer'}
              {researchMode === 'reviewer' && '→ Baseline + Reviewer critique and revision'}
              {researchMode === 'analyst' && '→ Baseline + Code Interpreter data analysis'}
              {researchMode === 'full' && '→ All agents + Analyst + Reviewer + Advanced features'}
            </div>
          </div>
        </div>
      )}

      {renderTaskConfiguration() as JSX.Element}

      {/* Execute Button */}
      <button
        onClick={handleExecute}
        disabled={
          executePatternMutation.isPending || 
          (useCustomTask && !customTask.trim())
        }
        className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2"
      >
        {executePatternMutation.isPending ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Starting Execution...</span>
          </>
        ) : (
          <>
            <Play className="w-4 h-4" />
            <span>Execute Pattern</span>
          </>
        )}
      </button>

      {executePatternMutation.error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-400 font-medium">Execution Failed</span>
          </div>
          <p className="text-red-300 text-sm mt-2">
            {executePatternMutation.error instanceof Error 
              ? executePatternMutation.error.message 
              : 'An unknown error occurred'
            }
          </p>
        </div>
      )}
    </div>
  );
};

export default PatternSelector;
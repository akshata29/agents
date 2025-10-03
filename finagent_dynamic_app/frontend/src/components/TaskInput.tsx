/**
 * TaskInput Component
 * 
 * Form for submitting objectives and creating dynamic plans
 * Includes Quick Tasks for common research scenarios
 */

import React, { useState } from 'react';
import { Send, Sparkles, TrendingUp, DollarSign, BarChart3, FileText } from 'lucide-react';

interface TaskInputProps {
  onSubmit: (objective: string, ticker?: string) => void;
  isLoading?: boolean;
}

interface QuickTask {
  title: string;
  description: string;
  template: string;
  icon: React.ReactNode;
  requiresTicker: boolean;
}

const quickTasks: QuickTask[] = [
  {
    title: 'Market News',
    description: 'Comprehensive news and sentiment',
    template: 'Get Market news and generate the sentiment for all the news as summary for Microsoft',
    icon: <TrendingUp className="w-5 h-5" />,
    requiresTicker: false,
  },
  {
    title: 'Company Basic Analysis',
    description: 'Basic analysis of a company',
    template: "Retrieve Apple's company information, stock data, analyst recommendation and news, analyze them, and predict stock movement.",
    icon: <DollarSign className="w-5 h-5" />,
    requiresTicker: false,
  },
  {
    title: 'Advanced Analysis',
    description: 'Advanced analysis on a company',
    template: "Retrieve Tesla's company information, stock data, analyst recommendation and news. Analyze the positive developments and potential concerns of Tesla. with 2-4 most important factors respectively and keep them concise. Most factors should be inferred from company related news. Then make a rough prediction (e.g. up/down by 2-3%) of the company stock price movement for next week. Provide a summary analysis to support your prediction.",
    icon: <BarChart3 className="w-5 h-5" />,
    requiresTicker: false,
  },
  {
    title: 'Earning Call Analysis',
    description: 'Call Analysis',
    template: "Summarize and analyze the 2024 earning call transcript for Google and based on management positive and negative outlook, and future growth, predict the stock movement.",
    icon: <BarChart3 className="w-5 h-5" />,
    requiresTicker: false,
  },
  {
    title: 'Earning Prediction',
    description: 'Earning and Call Prediction',
    template: "Predict the next week recommendation for Nvidia based on : 1. Sentiment from the company news 2. Stock data 3. Company Information 4. Management positive outlook from Call transcript 5. Management negative outlook from Call transcript 6. Future growth opportunities from Call transcript 7. Analyst recommendations Once all data is captured analyze and make a prediction for next week's target price range of company's stock price movement. Provide a summary analysis to support your prediction.",
    icon: <BarChart3 className="w-5 h-5" />,
    requiresTicker: false,
  },
  {
    title: 'SEC Analysis',
    description: 'SEC Analysis',
    template: "Perform Risk assessment, Business highlights, income statement and cash flow analysis for Microsoft based on 2024 SEC reports",
    icon: <BarChart3 className="w-5 h-5" />,
    requiresTicker: false,
  },
  {
    title: 'Financial Health Report',
    description: 'Comprehensive financial health assessment',
    template: 'Assess {ticker}\'s financial health and growth prospects based on fundamentals, earnings, and market data',
    icon: <FileText className="w-5 h-5" />,
    requiresTicker: true,
  },
];

export const TaskInput: React.FC<TaskInputProps> = ({ onSubmit, isLoading = false }) => {
  const [objective, setObjective] = useState('');
  const [ticker, setTicker] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (objective.trim()) {
      onSubmit(objective, ticker || undefined);
      setObjective('');
      setTicker('');
    }
  };

  const handleQuickTask = (task: QuickTask) => {
    if (task.requiresTicker && !ticker) {
      // Focus ticker input if required but not provided
      const tickerInput = document.getElementById('ticker') as HTMLInputElement;
      tickerInput?.focus();
      return;
    }
    
    const taskText = task.template.replace('{ticker}', ticker || 'the company');
    setObjective(taskText);
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* Main Input Form */}
      <div className="bg-slate-800 rounded-lg shadow-lg border border-slate-700 p-6 mb-6">
        <div className="flex items-center gap-2 mb-6">
          <Sparkles className="w-5 h-5 text-primary-400" />
          <h2 className="text-lg font-semibold text-white">Create Research Plan</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="ticker" className="block text-sm font-medium text-slate-300 mb-2">
              Ticker Symbol (Optional)
            </label>
            <input
              id="ticker"
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="e.g., MSFT, AAPL, TSLA"
              className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors"
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="objective" className="block text-sm font-medium text-slate-300 mb-2">
              Research Objective
            </label>
            <textarea
              id="objective"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="Describe what you want to research... e.g., 'Analyze Microsoft's financial health and growth prospects'"
              rows={4}
              className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none transition-colors"
              disabled={isLoading}
              required
            />
            <p className="mt-2 text-sm text-slate-400">
              AI will create a structured plan with steps for specialized financial agents
            </p>
          </div>

          <button
            type="submit"
            disabled={isLoading || !objective.trim()}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Creating Plan...
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Create Research Plan
              </>
            )}
          </button>
        </form>
      </div>

      {/* Quick Tasks */}
      <div className="bg-slate-800 rounded-lg shadow-lg border border-slate-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Quick Tasks</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {quickTasks.map((task, index) => (
            <button
              key={index}
              onClick={() => handleQuickTask(task)}
              disabled={isLoading}
              className="flex items-start gap-3 p-4 bg-slate-700 hover:bg-slate-600 rounded-lg border border-slate-600 hover:border-primary-500 text-left transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex-shrink-0 w-10 h-10 bg-primary-500/20 rounded-lg flex items-center justify-center text-primary-400">
                {task.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-white mb-1">
                  {task.title}
                </h4>
                <p className="text-xs text-slate-400">
                  {task.description}
                </p>
                {task.requiresTicker && !ticker && (
                  <p className="text-xs text-amber-400 mt-1">
                    Requires ticker symbol
                  </p>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

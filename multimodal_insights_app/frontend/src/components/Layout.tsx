import React, { ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Brain } from 'lucide-react';
import { useSession } from '../contexts/SessionContext';

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { clearSession, initializeSession } = useSession();

  const isActive = (path: string) => location.pathname === path;

  const handleNewAnalysis = (e: React.MouseEvent) => {
    e.preventDefault();
    // Always create a fresh session when clicking "New Analysis"
    clearSession();
    initializeSession();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Brain className="w-8 h-8 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-white">
                  Multimodal Insights
                </h1>
                <p className="text-sm text-slate-400">
                  AI-Powered Content Analysis System
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
            <Link
              to="/"
              onClick={handleNewAnalysis}
              className={`px-6 py-3 font-medium transition-colors ${
                isActive('/')
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              New Analysis
            </Link>
            <Link
              to="/task-details"
              className={`px-6 py-3 font-medium transition-colors ${
                isActive('/task-details')
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              Task Details
            </Link>
            <Link
              to="/sessions"
              className={`px-6 py-3 font-medium transition-colors ${
                isActive('/sessions')
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              History
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto bg-slate-900 p-6">
        {children}
      </div>

      {/* Footer */}
      <footer className="bg-slate-800 border-t border-slate-700">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <div>
              Powered by Microsoft Agent Framework & Magentic Foundation
            </div>
            <div>
              Multimodal processing • Sentiment analysis • Intelligent summarization • Deep analytics
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;

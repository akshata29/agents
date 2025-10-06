import React, { useEffect, useState } from 'react';
import { Clock, Calendar, FileSearch, CheckCircle, XCircle, Loader2, ChevronRight, BarChart3, BookOpen, Zap, Trash2 } from 'lucide-react';
import { apiClient } from '../api';

interface SessionWithDetails {
  id: string;
  session_id: string;
  user_id: string;
  created_at: string;
  last_active: string;
  latest_topic: string | null;
  latest_depth: string | null;
  latest_execution_mode: string | null;
  run_count: number;
  latest_status: string | null;
  total_execution_time: number | null;
  total_sources_analyzed: number;
}

interface RunSummary {
  run_id: string;
  session_id: string;
  topic: string;
  depth: string;
  execution_mode: string;
  status: string;
  started_at: string;
  execution_time: number | null;
  progress: number;
  sources_analyzed: number;
  has_report: boolean;
  summary: string | null;
}

interface SessionHistoryPageProps {
  onNavigateToExecution?: (executionId: string) => void;
}

const SessionHistoryPage: React.FC<SessionHistoryPageProps> = ({ onNavigateToExecution }) => {
  const [sessions, setSessions] = useState<SessionWithDetails[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionWithDetails | null>(null);
  const [sessionRuns, setSessionRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const sessions = await apiClient.getSessions(50);
      setSessions(sessions);
    } catch (err: any) {
      console.error('Failed to load sessions:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const loadSessionRuns = async (sessionId: string) => {
    try {
      setLoadingRuns(true);
      const runs = await apiClient.getSessionRuns(sessionId);
      setSessionRuns(runs);
    } catch (err: any) {
      console.error('Failed to load session runs:', err);
    } finally {
      setLoadingRuns(false);
    }
  };

  const handleSessionClick = async (session: SessionWithDetails) => {
    // If session has only 1 run, navigate directly to execution monitor
    if (session.run_count === 1 && onNavigateToExecution) {
      setLoadingRuns(true);
      try {
        const runs = await apiClient.getSessionRuns(session.session_id);
        if (runs.length === 1) {
          onNavigateToExecution(runs[0].run_id);
          return;
        }
      } catch (err) {
        console.error('Failed to load run for navigation:', err);
      } finally {
        setLoadingRuns(false);
      }
    }
    
    // Otherwise, show the session detail view
    setSelectedSession(session);
    await loadSessionRuns(session.session_id);
  };

  const handleBackToSessions = () => {
    setSelectedSession(null);
    setSessionRuns([]);
  };

  const handleDeleteSession = async (sessionId: string, event: React.MouseEvent) => {
    // Prevent the session click handler from firing
    event.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this session and all its research runs? This action cannot be undone.')) {
      return;
    }
    
    try {
      setDeletingSessionId(sessionId);
      await apiClient.deleteSession(sessionId);
      
      // Remove from sessions list
      setSessions(sessions.filter(s => s.session_id !== sessionId));
      
      // If we're viewing this session, go back to sessions list
      if (selectedSession?.session_id === sessionId) {
        handleBackToSessions();
      }
    } catch (err: any) {
      console.error('Failed to delete session:', err);
      alert(err.response?.data?.detail || err.message || 'Failed to delete session');
    } finally {
      setDeletingSessionId(null);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
      case 'success':
        return 'text-success-400 bg-success-500/20 border-success-500/30';
      case 'running':
        return 'text-primary-400 bg-primary-500/20 border-primary-500/30';
      case 'failed':
        return 'text-red-400 bg-red-500/20 border-red-500/30';
      case 'pending':
        return 'text-slate-400 bg-slate-500/20 border-slate-500/30';
      default:
        return 'text-slate-400 bg-slate-500/20 border-slate-500/30';
    }
  };

  const getDepthColor = (depth: string) => {
    switch (depth) {
      case 'quick':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      case 'standard':
        return 'bg-green-500/20 text-green-300 border-green-500/30';
      case 'comprehensive':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      case 'exhaustive':
        return 'bg-red-500/20 text-red-300 border-red-500/30';
      default:
        return 'bg-slate-500/20 text-slate-300 border-slate-500/30';
    }
  };

  const getExecutionModeLabel = (mode: string) => {
    switch (mode) {
      case 'workflow':
        return 'Workflow';
      case 'code':
        return 'Code-Based';
      case 'maf-workflow':
        return 'MAF Workflow';
      default:
        return mode;
    }
  };

  const getExecutionModeColor = (mode: string) => {
    switch (mode) {
      case 'workflow':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
      case 'code':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
      case 'maf-workflow':
        return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
      default:
        return 'bg-slate-500/20 text-slate-300 border-slate-500/30';
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 text-primary-400 animate-spin" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center space-x-3 mb-6">
            <FileSearch className="h-6 w-6 text-primary-400" />
            <h2 className="text-2xl font-bold text-white">Session History</h2>
          </div>
          <div className="text-center py-12">
            <XCircle className="h-16 w-16 text-red-400 mx-auto mb-4" />
            <p className="text-red-400 mb-4">{error}</p>
            <button
              onClick={loadSessions}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show session runs view
  if (selectedSession) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <button
                onClick={handleBackToSessions}
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <ChevronRight className="h-5 w-5 text-slate-400 transform rotate-180" />
              </button>
              <FileSearch className="h-6 w-6 text-primary-400" />
              <div>
                <h2 className="text-2xl font-bold text-white">
                  Session {selectedSession.session_id.slice(0, 12)}...
                </h2>
                <p className="text-sm text-slate-400">
                  {selectedSession.run_count} research run{selectedSession.run_count !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3 text-sm">
              <div className="flex items-center space-x-2 text-slate-400">
                <Clock className="h-4 w-4" />
                <span>Created {formatDate(selectedSession.created_at)}</span>
              </div>
              {selectedSession.total_execution_time && (
                <div className="px-3 py-1 bg-primary-500/20 text-primary-400 rounded-full">
                  Total Time: {formatDuration(selectedSession.total_execution_time)}
                </div>
              )}
              {selectedSession.total_sources_analyzed > 0 && (
                <div className="px-3 py-1 bg-success-500/20 text-success-400 rounded-full">
                  {selectedSession.total_sources_analyzed} Sources
                </div>
              )}
            </div>
          </div>

          {loadingRuns ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 text-primary-400 animate-spin" />
            </div>
          ) : sessionRuns.length === 0 ? (
            <div className="text-center py-12">
              <BookOpen className="h-16 w-16 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-400">No research runs found in this session.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessionRuns.map((run) => (
                <div
                  key={run.run_id}
                  onClick={() => onNavigateToExecution?.(run.run_id)}
                  className="bg-slate-900/50 rounded-lg border border-slate-700 p-4 hover:border-primary-500 transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="text-lg font-semibold text-white truncate">
                          {run.topic}
                        </h3>
                        <span className={`px-2 py-1 text-xs rounded-md border ${getDepthColor(run.depth)}`}>
                          {run.depth}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded-md border ${getStatusColor(run.status)}`}>
                          {run.status}
                        </span>
                      </div>
                      {run.summary && (
                        <p className="text-sm text-slate-300 mb-2 line-clamp-2">
                          {run.summary}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm text-slate-400">
                      <div className="flex items-center space-x-1">
                        <Clock className="h-4 w-4" />
                        <span>{formatDate(run.started_at)}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <BarChart3 className="h-4 w-4" />
                        <span>{run.execution_mode}</span>
                      </div>
                      {run.execution_time && (
                        <div className="flex items-center space-x-1">
                          <span>{formatDuration(run.execution_time)}</span>
                        </div>
                      )}
                      {run.sources_analyzed > 0 && (
                        <div className="flex items-center space-x-1">
                          <BookOpen className="h-4 w-4" />
                          <span>{run.sources_analyzed} sources</span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      {run.progress < 100 && (
                        <div className="w-24 bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-primary-500 h-2 rounded-full transition-all"
                            style={{ width: `${run.progress}%` }}
                          />
                        </div>
                      )}
                      {run.has_report && (
                        <CheckCircle className="h-5 w-5 text-success-400" />
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Show sessions list view
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <FileSearch className="h-6 w-6 text-primary-400" />
            <h2 className="text-2xl font-bold text-white">Research History</h2>
          </div>
          <div className="text-sm text-slate-400">
            {sessions.length} session{sessions.length !== 1 ? 's' : ''} total
          </div>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-12">
            <Calendar className="h-16 w-16 text-slate-400 mx-auto mb-4" />
            <p className="text-slate-400">
              No research sessions found. Start your first research to build your history!
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSessionClick(session)}
                className="bg-slate-900/50 rounded-lg border border-slate-700 p-4 hover:border-primary-500 transition-all cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2 flex-wrap gap-y-2">
                      <h3 className="text-lg font-semibold text-white">
                        Session {session.session_id.slice(0, 12)}...
                      </h3>
                      {session.run_count > 0 && (
                        <span className="flex items-center space-x-1 px-2 py-1 bg-primary-500/20 border border-primary-500/30 rounded-md text-xs text-primary-300">
                          <BarChart3 className="h-3 w-3" />
                          <span>{session.run_count} run{session.run_count !== 1 ? 's' : ''}</span>
                        </span>
                      )}
                      {session.latest_status && (
                        <span className={`px-2 py-1 text-xs rounded-md border ${getStatusColor(session.latest_status)}`}>
                          {session.latest_status}
                        </span>
                      )}
                      {session.latest_execution_mode && (
                        <span className={`flex items-center space-x-1 px-2 py-1 text-xs rounded-md border ${getExecutionModeColor(session.latest_execution_mode)}`}>
                          <Zap className="h-3 w-3" />
                          <span>{getExecutionModeLabel(session.latest_execution_mode)}</span>
                        </span>
                      )}
                      {session.latest_depth && (
                        <span className={`px-2 py-1 text-xs rounded-md border ${getDepthColor(session.latest_depth)} uppercase font-medium`}>
                          {session.latest_depth}
                        </span>
                      )}
                    </div>

                    {session.latest_topic && (
                      <p className="text-sm text-slate-300 mb-2 truncate">
                        Latest: {session.latest_topic}
                      </p>
                    )}

                    <div className="flex items-center space-x-4 text-sm text-slate-400">
                      <div className="flex items-center space-x-1">
                        <Clock className="h-4 w-4" />
                        <span>Last active {formatDate(session.last_active)}</span>
                      </div>
                      {session.total_execution_time && session.total_execution_time > 0 && (
                        <div className="flex items-center space-x-1">
                          <span>Total: {formatDuration(session.total_execution_time)}</span>
                        </div>
                      )}
                      {session.total_sources_analyzed > 0 && (
                        <div className="flex items-center space-x-1">
                          <BookOpen className="h-4 w-4" />
                          <span>{session.total_sources_analyzed} sources</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 flex-shrink-0">
                    <button
                      onClick={(e) => handleDeleteSession(session.session_id, e)}
                      disabled={deletingSessionId === session.session_id}
                      className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete session and all its runs"
                    >
                      {deletingSessionId === session.session_id ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <Trash2 className="h-5 w-5" />
                      )}
                    </button>
                    <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-primary-400 transition-colors" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionHistoryPage;

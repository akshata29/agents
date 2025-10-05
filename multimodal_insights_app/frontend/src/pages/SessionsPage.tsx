import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Calendar, Clock, CheckCircle, XCircle, Loader2, ChevronRight, Trash2, FileAudio, FileVideo, File } from 'lucide-react';
import { listSessions, getSessionPlans, deleteSession } from '../services/api';
import type { Session } from '../types';

interface SessionWithStats extends Session {
  planCount?: number;
  lastActivity?: string;
  completedPlans?: number;
}

const getFileIcon = (fileType: string) => {
  switch (fileType.toLowerCase()) {
    case 'audio':
      return FileAudio;
    case 'video':
      return FileVideo;
    case 'pdf':
      return File;
    default:
      return FileText;
  }
};

const SessionsPage: React.FC = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const sessionsData = await listSessions(50);
      
      // Fetch plan counts for each session
      const sessionsWithStats = await Promise.all(
        sessionsData.map(async (session) => {
          try {
            const plans = await getSessionPlans(session.session_id);
            const completedPlans = plans.filter(p => p.overall_status === 'completed').length;
            
            return {
              ...session,
              planCount: plans.length,
              completedPlans,
              lastActivity: plans.length > 0 ? plans[0].timestamp : session.timestamp,
            };
          } catch (err) {
            // If we can't get plans, just return session
            return {
              ...session,
              planCount: 0,
              completedPlans: 0,
            };
          }
        })
      );
      
      setSessions(sessionsWithStats);
    } catch (err: any) {
      console.error('Failed to load sessions:', err);
      setError(err.message || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const handleSessionClick = async (sessionId: string) => {
    try {
      // Get plans for this session
      const plans = await getSessionPlans(sessionId);
      
      if (plans.length === 0) {
        // No plans for this session yet
        console.warn('No plans found for session:', sessionId);
        return;
      }
      
      // Get the most recent plan (already sorted by timestamp DESC from API)
      const latestPlan = plans[0];
      
      // Navigate to task details page with the plan ID
      navigate(`/task-details?plan_id=${latestPlan.id}&session_id=${sessionId}`);
    } catch (err: any) {
      console.error('Failed to navigate to session:', err);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation(); // Prevent triggering the session click
    
    if (!window.confirm('Are you sure you want to delete this session? This will permanently delete all associated plans, steps, and file metadata.')) {
      return;
    }

    try {
      await deleteSession(sessionId);
      // Reload sessions after successful deletion
      loadSessions();
    } catch (err: any) {
      console.error('Failed to delete session:', err);
      alert(err.response?.data?.detail || 'Failed to delete session');
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

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
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
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center space-x-3 mb-6">
            <FileText className="h-6 w-6 text-primary-400" />
            <h2 className="text-2xl font-bold text-white">Sessions</h2>
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

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <FileText className="h-6 w-6 text-primary-400" />
            <h2 className="text-2xl font-bold text-white">Session History</h2>
          </div>
          <div className="text-sm text-slate-400">
            {sessions.length} session{sessions.length !== 1 ? 's' : ''} total
          </div>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-12">
            <Calendar className="h-16 w-16 text-slate-400 mx-auto mb-4" />
            <p className="text-slate-400">
              No sessions found. Create your first analysis to get started!
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => {
              const FileIcon = session.file_types && session.file_types.length > 0 
                ? getFileIcon(session.file_types[0])
                : FileText;

              return (
                <div
                  key={session.id}
                  onClick={() => handleSessionClick(session.session_id)}
                  className="bg-slate-900/50 rounded-lg border border-slate-700 p-4 hover:border-primary-500 transition-all cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-semibold text-white truncate">
                          Session {session.session_id.slice(0, 8)}...
                        </h3>
                        {session.planCount !== undefined && session.planCount > 0 && (
                          <span className="flex items-center space-x-1 px-2 py-1 bg-primary-500/20 border border-primary-500/30 rounded-md text-xs text-primary-300">
                            <CheckCircle className="h-3 w-3" />
                            <span>{session.completedPlans}/{session.planCount} completed</span>
                          </span>
                        )}
                      </div>

                      {/* Objective preview */}
                      {session.latest_objective && (
                        <p className="text-sm text-slate-300 mb-2 line-clamp-2">
                          {session.latest_objective.length > 100 
                            ? `${session.latest_objective.slice(0, 100)}...` 
                            : session.latest_objective}
                        </p>
                      )}

                      <div className="flex items-center space-x-4 text-sm text-slate-400">
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>{formatDate(session.lastActivity || session.timestamp)}</span>
                        </div>
                        {session.planCount !== undefined && (
                          <div className="flex items-center space-x-1">
                            <FileText className="h-4 w-4" />
                            <span>{session.planCount} analysis{session.planCount !== 1 ? 'es' : ''}</span>
                          </div>
                        )}
                        {session.file_count !== undefined && session.file_count > 0 && (
                          <div className="flex items-center space-x-2">
                            <div className="flex items-center space-x-1">
                              <FileIcon className="h-4 w-4" />
                              <span>{session.file_count} file{session.file_count !== 1 ? 's' : ''}</span>
                            </div>
                            {session.file_types && session.file_types.length > 0 && (
                              <div className="flex items-center space-x-1">
                                {session.file_types.map((type, idx) => (
                                  <span 
                                    key={idx}
                                    className="px-1.5 py-0.5 bg-slate-700/50 border border-slate-600 rounded text-xs"
                                  >
                                    {type}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                        <div className="flex items-center space-x-1">
                          <span className="text-slate-500">User:</span>
                          <span>{session.user_id}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 flex-shrink-0">
                      <button
                        onClick={(e) => handleDeleteSession(e, session.session_id)}
                        className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Delete session"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                      <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-primary-400 transition-colors" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionsPage;

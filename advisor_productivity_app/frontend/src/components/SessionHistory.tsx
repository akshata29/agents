import type { FC } from 'react'
import { useState, useEffect } from 'react'
import { resolveBackendUrl } from '../utils/backendUrl'
import { History, Calendar, Clock, TrendingUp, User, ChevronRight, Loader2 } from 'lucide-react'
import type { HistoricalSession } from '../types'

const BACKEND_URL = resolveBackendUrl()

interface SessionHistoryProps {
  onLoadSession: (sessionId: string) => void
}

const SessionHistory: FC<SessionHistoryProps> = ({ onLoadSession }) => {
  const [sessions, setSessions] = useState<HistoricalSession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`${BACKEND_URL}/history/sessions?limit=50`)
      if (!response.ok) {
        throw new Error('Failed to load sessions')
      }
      
      const data = await response.json()
      setSessions(data)
    } catch (err) {
      console.error('Error loading sessions:', err)
      setError(err instanceof Error ? err.message : 'Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}m ${secs}s`
  }

  const getReadinessColor = (score: number | null) => {
    if (!score) return 'text-slate-400'
    if (score >= 0.7) return 'text-green-400'
    if (score >= 0.4) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getReadinessLabel = (score: number | null) => {
    if (!score) return 'Unknown'
    if (score >= 0.7) return 'High'
    if (score >= 0.4) return 'Medium'
    return 'Low'
  }

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-12">
        <div className="flex flex-col items-center justify-center">
          <Loader2 className="w-12 h-12 text-primary-400 animate-spin mb-4" />
          <p className="text-slate-300 text-lg">Loading session history...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-lg border border-red-500/50 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <History className="w-5 h-5 text-red-400" />
          <h3 className="text-lg font-semibold text-white">Error Loading History</h3>
        </div>
        <p className="text-red-300 mb-4">{error}</p>
        <button
          onClick={loadSessions}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-12">
        <div className="text-center">
          <History className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-slate-300 mb-2">No Sessions Yet</h3>
          <p className="text-slate-400">
            Complete your first session to see it appear here
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <History className="w-5 h-5 text-primary-400" />
            <h3 className="text-lg font-semibold text-white">Session History</h3>
          </div>
          <span className="text-sm text-slate-400">{sessions.length} sessions</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {sessions.map((session) => (
          <div
            key={session.session_id}
            className="bg-slate-800 rounded-lg border border-slate-700 p-5 hover:border-primary-500/50 transition-colors cursor-pointer"
            onClick={() => onLoadSession(session.session_id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 space-y-3">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <User className="w-5 h-5 text-slate-400" />
                    <div>
                      <h4 className="text-white font-medium">
                        {session.client_name || 'Client Session'}
                      </h4>
                      {session.advisor_name && (
                        <p className="text-xs text-slate-400">
                          with {session.advisor_name}
                        </p>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="flex items-center space-x-2">
                    <Calendar className="w-4 h-4 text-slate-400" />
                    <div>
                      <p className="text-xs text-slate-400">Date</p>
                      <p className="text-sm text-slate-200">
                        {formatDate(session.created_at)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Clock className="w-4 h-4 text-slate-400" />
                    <div>
                      <p className="text-xs text-slate-400">Duration</p>
                      <p className="text-sm text-slate-200">
                        {formatDuration(session.duration_seconds)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <TrendingUp className="w-4 h-4 text-slate-400" />
                    <div>
                      <p className="text-xs text-slate-400">Readiness</p>
                      <p className={`text-sm font-semibold ${getReadinessColor(session.investment_readiness_score)}`}>
                        {getReadinessLabel(session.investment_readiness_score)}
                        {session.investment_readiness_score && 
                          ` (${Math.round(session.investment_readiness_score * 100)}%)`
                        }
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-slate-400 mb-1">Exchanges</p>
                    <p className="text-sm text-slate-200">{session.exchange_count}</p>
                  </div>
                </div>

                {/* Key Topics */}
                {session.key_topics && session.key_topics.length > 0 && (
                  <div>
                    <p className="text-xs text-slate-400 mb-2">Key Topics</p>
                    <div className="flex flex-wrap gap-2">
                      {session.key_topics.slice(0, 5).map((topic, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-slate-700/50 text-slate-300 rounded text-xs"
                        >
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default SessionHistory

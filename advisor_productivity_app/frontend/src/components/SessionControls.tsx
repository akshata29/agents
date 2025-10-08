import type { FC } from 'react'
import { Play, Square, LayoutGrid, MessageSquare, BarChart3, CheckCircle2 } from 'lucide-react'
import type { ViewMode } from '../types'

interface SessionControlsProps {
  sessionActive: boolean
  viewMode: ViewMode
  onStartSession: () => void
  onEndSession: () => void
  onViewModeChange: (mode: ViewMode) => void
}

const SessionControls: FC<SessionControlsProps> = ({
  sessionActive,
  viewMode,
  onStartSession,
  onEndSession,
  onViewModeChange
}) => {
  return (
    <div className="flex items-center justify-between w-full">
      {/* Tab Navigation */}
      <div className="flex space-x-1">
        <button
          onClick={() => onViewModeChange('unified')}
          className={`px-6 py-3 font-medium transition-colors flex items-center space-x-2 ${
            viewMode === 'unified'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          <LayoutGrid className="w-4 h-4" />
          <span>Unified View</span>
        </button>
        <button
          onClick={() => onViewModeChange('chat')}
          className={`px-6 py-3 font-medium transition-colors flex items-center space-x-2 ${
            viewMode === 'chat'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Conversation</span>
        </button>
        <button
          onClick={() => onViewModeChange('analytics')}
          className={`px-6 py-3 font-medium transition-colors flex items-center space-x-2 ${
            viewMode === 'analytics'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Analytics</span>
        </button>
        <button
          onClick={() => onViewModeChange('progress')}
          className={`px-6 py-3 font-medium transition-colors flex items-center space-x-2 ${
            viewMode === 'progress'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>Summary</span>
        </button>
      </div>

      {/* Session Controls */}
      <div>
        {!sessionActive ? (
          <button
            onClick={onStartSession}
            className="px-4 py-2 bg-success-500 text-white rounded-lg hover:bg-success-600 font-medium transition-colors flex items-center space-x-2"
          >
            <Play className="w-4 h-4" />
            <span>Start Session</span>
          </button>
        ) : (
          <button
            onClick={onEndSession}
            className="px-4 py-2 bg-error-500 text-white rounded-lg hover:bg-error-600 font-medium transition-colors flex items-center space-x-2"
          >
            <Square className="w-4 h-4" />
            <span>End Session</span>
          </button>
        )}
      </div>
    </div>
  )
}

export default SessionControls

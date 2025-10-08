import type { FC } from 'react'
import { useState } from 'react'
import { FileText, CheckCircle2, Clock, User, AlertCircle, Loader2 } from 'lucide-react'
import type { Summary, ActionItem, Decision } from '../types'

interface SummaryPanelProps {
  summary: Summary[] | null
  sessionId: string
  isLoading?: boolean
}

const SummaryPanel: FC<SummaryPanelProps> = ({ summary, sessionId, isLoading = false }) => {
  const [selectedPersona, setSelectedPersona] = useState<string>('advisor')

  // Show loading state
  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <FileText className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-white">Session Summary</h3>
        </div>
        <div className="text-center py-12">
          <Loader2 className="w-12 h-12 mx-auto mb-4 text-primary-400 animate-spin" />
          <p className="text-slate-300 text-lg font-medium mb-2">Generating Summary...</p>
          <p className="text-slate-400 text-sm">
            Analyzing conversation, sentiment, and recommendations to create comprehensive summaries for all personas
          </p>
          <div className="mt-6 flex justify-center gap-2">
            <div className="w-2 h-2 bg-primary-400 rounded-full animate-pulse" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-primary-400 rounded-full animate-pulse" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-primary-400 rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></div>
          </div>
        </div>
      </div>
    )
  }

  if (!summary || summary.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <FileText className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-white">Session Summary</h3>
        </div>
        <div className="text-center py-8 text-slate-400">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Summary will be generated when session ends</p>
        </div>
      </div>
    )
  }

  const currentSummary = summary.find(s => s.persona === selectedPersona) || summary[0]
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <FileText className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-white">Session Summary</h3>
        </div>
        <div className="flex space-x-2">
          {summary.map(s => (
            <button
              key={s.persona}
              onClick={() => setSelectedPersona(s.persona)}
              className={`px-3 py-1 text-sm rounded-lg capitalize transition-colors ${
                selectedPersona === s.persona
                  ? 'bg-primary-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {s.persona}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {/* Summary Text */}
        <div className="p-4 bg-slate-750 rounded-lg border border-slate-700">
          <p className="text-slate-200 leading-relaxed">{currentSummary.summary}</p>
        </div>

        {/* Key Points */}
        {currentSummary.key_points && currentSummary.key_points.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-slate-300 mb-2">Key Points</h4>
            <ul className="space-y-1">
              {currentSummary.key_points.map((point, index) => (
                <li key={index} className="flex items-start space-x-2 text-sm">
                  <span className="text-primary-400 mt-1">•</span>
                  <span className="text-slate-300">{point}</span>
                </li>
              ))}
            </ul>
          </div>
        )}


        {/* Action Items */}
        {currentSummary.action_items && currentSummary.action_items.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-slate-300 mb-2">Action Items</h4>
            <div className="space-y-2">
              {currentSummary.action_items.map((action, index) => {
                // Handle both string and object formats
                const isObject = typeof action === 'object'
                const actionText = isObject ? (action as ActionItem).action : action
                const responsible = isObject ? (action as ActionItem).responsible : null
                const deadline = isObject ? (action as ActionItem).deadline : null
                const priority = isObject ? (action as ActionItem).priority : null
                const details = isObject ? (action as ActionItem).details || (action as ActionItem).context : null
                
                const priorityColors = {
                  high: 'border-red-500/50 bg-red-500/10',
                  medium: 'border-yellow-500/50 bg-yellow-500/10',
                  low: 'border-blue-500/50 bg-blue-500/10'
                }
                
                const borderColor = priority 
                  ? priorityColors[priority as keyof typeof priorityColors] 
                  : 'border-slate-600 bg-slate-800/50'
                
                return (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border ${borderColor}`}
                  >
                    <div className="flex items-start space-x-3">
                      <input
                        type="checkbox"
                        className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-700 text-primary-500"
                        id={`action-${index}`}
                      />
                      <div className="flex-1 space-y-1">
                        <label
                          htmlFor={`action-${index}`}
                          className="text-sm text-slate-200 font-medium cursor-pointer"
                        >
                          {actionText}
                        </label>
                        
                        {details && (
                          <p className="text-xs text-slate-400">{details}</p>
                        )}
                        
                        <div className="flex items-center gap-3 text-xs text-slate-400">
                          {responsible && (
                            <span className="flex items-center gap-1">
                              <User className="w-3 h-3" />
                              <span className="capitalize">{responsible}</span>
                            </span>
                          )}
                          {deadline && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {deadline}
                            </span>
                          )}
                          {priority && (
                            <span className={`flex items-center gap-1 ${
                              priority === 'high' ? 'text-red-400' : 
                              priority === 'medium' ? 'text-yellow-400' : 
                              'text-blue-400'
                            }`}>
                              <AlertCircle className="w-3 h-3" />
                              <span className="capitalize">{priority}</span>
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}


        {/* Decisions Made */}
        {currentSummary.decisions_made && currentSummary.decisions_made.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-slate-300 mb-2">Decisions Made</h4>
            <div className="space-y-2">
              {currentSummary.decisions_made.map((decision, index) => {
                // Handle both string and object formats
                const isObject = typeof decision === 'object'
                const decisionText = isObject ? (decision as Decision).decision : decision
                const rationale = isObject ? (decision as Decision).rationale : null
                const impact = isObject ? (decision as Decision).impact : null
                
                return (
                  <div
                    key={index}
                    className="p-3 bg-green-500/10 rounded-lg border border-green-500/50"
                  >
                    <div className="flex items-start space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 space-y-1">
                        <p className="text-sm text-slate-200 font-medium">{decisionText}</p>
                        {rationale && (
                          <p className="text-xs text-slate-400">
                            <span className="font-semibold">Rationale:</span> {rationale}
                          </p>
                        )}
                        {impact && (
                          <p className="text-xs text-slate-400">
                            <span className="font-semibold">Impact:</span> {impact}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-slate-700">
        <p className="text-xs text-slate-500">Session ID: {sessionId}</p>
      </div>
    </div>
  )
}

export default SummaryPanel

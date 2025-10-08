import type { FC } from 'react'
import { useState } from 'react'
import { FileText, CheckCircle2 } from 'lucide-react'
import type { Summary } from '../types'

interface SummaryPanelProps {
  summary: Summary[] | null
  sessionId: string
}

const SummaryPanel: FC<SummaryPanelProps> = ({ summary, sessionId }) => {
  const [selectedPersona, setSelectedPersona] = useState<string>('advisor')

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
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Action Items</h4>
            <div className="space-y-2">
              {currentSummary.action_items.map((action, index) => (
                <div
                  key={index}
                  className="flex items-start space-x-2 p-2 bg-yellow-50 rounded border border-yellow-200"
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    id={`action-${index}`}
                  />
                  <label
                    htmlFor={`action-${index}`}
                    className="text-sm text-gray-700 flex-1"
                  >
                    {action}
                  </label>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Decisions Made */}
        {currentSummary.decisions_made && currentSummary.decisions_made.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Decisions Made</h4>
            <div className="space-y-1">
              {currentSummary.decisions_made.map((decision, index) => (
                <div
                  key={index}
                  className="flex items-start space-x-2 p-2 bg-green-50 rounded border border-green-200 text-sm"
                >
                  <svg className="w-4 h-4 text-green-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-gray-700">{decision}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">Session ID: {sessionId}</p>
      </div>
    </div>
  )
}

export default SummaryPanel

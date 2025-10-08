import type { FC } from 'react'
import { MessageSquare } from 'lucide-react'
import type { TranscriptSegment, SentimentData } from '../types'

interface TranscriptViewProps {
  transcript: TranscriptSegment[]
  sentiment: SentimentData | null
}

const TranscriptView: FC<TranscriptViewProps> = ({ transcript, sentiment }) => {
  const getSentimentColor = (score: number) => {
    if (score >= 70) return 'bg-success-500/20 border-success-500 text-success-400'
    if (score >= 40) return 'bg-warning-500/20 border-warning-500 text-warning-400'
    return 'bg-error-500/20 border-error-500 text-error-400'
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-white">Conversation Transcript</h3>
        </div>
        {sentiment && (
          <div className={`px-3 py-1 rounded border ${getSentimentColor(sentiment.investment_readiness_score)}`}>
            <span className="text-sm font-medium">
              Readiness: {sentiment.investment_readiness_score}%
            </span>
          </div>
        )}
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
        {transcript.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No transcript yet. Start recording to begin.</p>
          </div>
        ) : (
          transcript.map((segment, index) => (
            <div
              key={index}
              className={`p-3 rounded-lg ${
                segment.speaker === 'Advisor'
                  ? 'bg-primary-500/10 border-l-4 border-primary-500'
                  : 'bg-slate-700 border-l-4 border-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-sm text-slate-300">
                  {segment.speaker}
                </span>
                <span className="text-xs text-slate-400">
                  {new Date(segment.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-slate-100">{segment.text}</p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default TranscriptView

import type { FC } from 'react'
import { BarChart3 } from 'lucide-react'
import type { TranscriptSegment, SentimentData } from '../types'

interface AnalyticsDashboardProps {
  transcript: TranscriptSegment[]
  sentiment: SentimentData | null
}

const AnalyticsDashboard: FC<AnalyticsDashboardProps> = ({ transcript, sentiment }) => {
  // Calculate talk time distribution
  const talkTime = transcript.reduce((acc, segment) => {
    const speaker = segment.speaker
    if (!acc[speaker]) acc[speaker] = 0
    acc[speaker]++
    return acc
  }, {} as Record<string, number>)

  const totalSegments = transcript.length
  const talkTimePercentages = Object.entries(talkTime).map(([speaker, count]) => ({
    speaker,
    percentage: totalSegments > 0 ? (count / totalSegments) * 100 : 0
  }))

  // Calculate conversation duration
  const duration = transcript.length > 0
    ? (new Date(transcript[transcript.length - 1].timestamp).getTime() -
       new Date(transcript[0].timestamp).getTime()) / 1000 / 60
    : 0

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center space-x-2 mb-4">
        <BarChart3 className="w-5 h-5 text-primary-400" />
        <h3 className="text-lg font-semibold text-white">Analytics Dashboard</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Duration */}
        <div className="p-4 bg-primary-500/10 rounded-lg border border-primary-500/30">
          <p className="text-sm text-slate-400 mb-1">Duration</p>
          <p className="text-2xl font-bold text-primary-400">
            {duration.toFixed(1)} min
          </p>
        </div>

        {/* Total Segments */}
        <div className="p-4 bg-success-500/10 rounded-lg border border-success-500/30">
          <p className="text-sm text-slate-400 mb-1">Exchanges</p>
          <p className="text-2xl font-bold text-success-400">
            {totalSegments}
          </p>
        </div>

        {/* Investment Readiness */}
        <div className="p-4 bg-warning-500/10 rounded-lg border border-warning-500/30">
          <p className="text-sm text-slate-400 mb-1">Readiness</p>
          <p className="text-2xl font-bold text-warning-400">
            {sentiment?.investment_readiness_score || 0}%
          </p>
        </div>
      </div>

      {/* Talk Time Distribution */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-slate-300 mb-3">Talk Time Distribution</h4>
        <div className="space-y-3">
          {talkTimePercentages.length === 0 ? (
            <p className="text-sm text-slate-400">No data yet</p>
          ) : (
            talkTimePercentages.map(({ speaker, percentage }) => (
              <div key={speaker}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="font-medium text-slate-300">{speaker}</span>
                  <span className="text-slate-400">{percentage.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${
                      speaker === 'Advisor' ? 'bg-primary-500' : 'bg-slate-500'
                    }`}
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Key Phrases */}
      {sentiment && sentiment.key_phrases && sentiment.key_phrases.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Key Phrases</h4>
          <div className="flex flex-wrap gap-2">
            {sentiment.key_phrases.map((phrase, index) => (
              <span
                key={index}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm border border-gray-300"
              >
                {phrase}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default AnalyticsDashboard

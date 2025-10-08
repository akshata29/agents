import type { FC } from 'react'
import { Activity, TrendingUp } from 'lucide-react'
import type { SentimentData } from '../types'

interface SentimentGaugeProps {
  sentiment: SentimentData | null
}

const SentimentGauge: FC<SentimentGaugeProps> = ({ sentiment }) => {
  if (!sentiment) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Activity className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-white">Sentiment Analysis</h3>
        </div>
        <div className="text-center py-8 text-slate-400">
          <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No sentiment data yet</p>
        </div>
      </div>
    )
  }

  const getGaugeColor = (score: number) => {
    if (score >= 70) return '#22c55e' // success-500
    if (score >= 40) return '#eab308' // warning-500
    return '#ef4444' // error-500
  }

  const topEmotions = Object.entries(sentiment.emotions)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center space-x-2 mb-4">
        <Activity className="w-5 h-5 text-primary-400" />
        <h3 className="text-lg font-semibold text-white">Sentiment Analysis</h3>
      </div>

      {/* Investment Readiness Gauge */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-300">Investment Readiness</span>
          <span className="text-2xl font-bold" style={{ color: getGaugeColor(sentiment.investment_readiness_score) }}>
            {sentiment.investment_readiness_score}%
          </span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-3">
          <div
            className="h-3 rounded-full transition-all duration-500"
            style={{
              width: `${sentiment.investment_readiness_score}%`,
              backgroundColor: getGaugeColor(sentiment.investment_readiness_score)
            }}
          ></div>
        </div>
      </div>

      {/* Overall Sentiment */}
      <div className="mb-6">
        <div className="flex items-center justify-between p-3 bg-slate-700 rounded-lg">
          <span className="text-sm font-medium text-slate-300">Overall Sentiment</span>
          <span className="text-sm font-semibold capitalize text-white">{sentiment.overall_sentiment}</span>
        </div>
      </div>

      {/* Top Emotions */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-slate-300 mb-3">Top Emotions</h4>
        <div className="space-y-2">
          {topEmotions.map(([emotion, score]) => (
            <div key={emotion}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="capitalize text-slate-300">{emotion}</span>
                <span className="font-medium text-slate-300">{Math.round(score * 100)}%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div
                  className="bg-primary-500 h-2 rounded-full"
                  style={{ width: `${score * 100}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Compliance Risk */}
      <div className="mb-4">
        <div className="flex items-center justify-between p-3 bg-error-500/10 rounded-lg border border-error-500/30">
          <span className="text-sm font-medium text-slate-300">Compliance Risk</span>
          <span className="text-sm font-semibold text-error-400">
            {sentiment.compliance_risk_score}%
          </span>
        </div>
      </div>

      {/* Sentiment Trend */}
      <div>
        <div className="flex items-center space-x-2 p-3 bg-primary-500/10 rounded-lg border border-primary-500/30">
          <span className="text-sm font-medium text-slate-300">Trend:</span>
          <span className="text-sm font-semibold capitalize text-primary-400">
            {sentiment.sentiment_trend}
          </span>
        </div>
      </div>
    </div>
  )
}

export default SentimentGauge

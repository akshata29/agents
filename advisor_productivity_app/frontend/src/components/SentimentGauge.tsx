import type { FC } from 'react'
import { Activity } from 'lucide-react'
import type { SentimentData } from '../types'

interface SentimentGaugeProps {
  sentiment: SentimentData | null
}

const SentimentGauge: FC<SentimentGaugeProps> = ({ sentiment }) => {
  // Debug: log what we receive
  console.log('SentimentGauge received:', sentiment)
  
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

  // Extract investment readiness score from the nested structure
  const investmentReadiness = (sentiment as any).investment_readiness?.score 
    ? Math.round((sentiment as any).investment_readiness.score * 100)
    : sentiment.investment_readiness_score || 0

  // Extract risk tolerance info
  const riskTolerance = (sentiment as any).risk_tolerance?.level || 'unknown'
  const riskScore = (sentiment as any).risk_tolerance?.score 
    ? Math.round((sentiment as any).risk_tolerance.score * 100)
    : 0

  // Extract investment emotions array
  const investmentEmotions = (sentiment as any).investment_emotions || []

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center space-x-2 mb-6">
        <Activity className="w-5 h-5 text-primary-400" />
        <h3 className="text-lg font-semibold text-white">Sentiment Analysis</h3>
      </div>

      {/* Investment Readiness Gauge */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-slate-300">Investment Readiness</span>
          <span className="text-3xl font-bold tabular-nums" style={{ color: getGaugeColor(investmentReadiness) }}>
            {Math.round(investmentReadiness)}%
          </span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-4 shadow-inner">
          <div
            className="h-4 rounded-full transition-all duration-500 shadow-lg"
            style={{
              width: `${investmentReadiness}%`,
              backgroundColor: getGaugeColor(investmentReadiness)
            }}
          ></div>
        </div>
      </div>

      {/* Overall Sentiment */}
      <div className="mb-6">
        <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg border border-slate-600">
          <span className="text-sm font-medium text-slate-300">Overall Sentiment</span>
          <span className="text-base font-bold capitalize text-white">{sentiment.overall_sentiment}</span>
        </div>
      </div>

      {/* Top Emotions - show investment emotions */}
      {investmentEmotions.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-slate-300 mb-4">Investment Emotions</h4>
          <div className="space-y-3">
            {investmentEmotions.slice(0, 5).map((emotionObj: any, idx: number) => (
              <div key={idx}>
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="capitalize text-slate-200 font-medium">{emotionObj.emotion}</span>
                  <span className="font-semibold text-primary-400 tabular-nums">
                    {Math.round((emotionObj.intensity || 0) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2.5 shadow-inner">
                  <div
                    className="bg-gradient-to-r from-primary-500 to-primary-400 h-2.5 rounded-full transition-all duration-500 shadow-sm"
                    style={{ width: `${(emotionObj.intensity || 0) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Tolerance */}
          {riskTolerance !== 'unknown' && (
            <div className="mb-4 space-y-3">
              <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                <span className="text-sm font-medium text-slate-300">Risk Tolerance</span>
                <span className="text-base font-bold capitalize text-white">{riskTolerance}</span>
              </div>
              {riskScore > 0 && (
                <div className="w-full bg-slate-700 rounded-full h-2.5 shadow-inner">
                  <div
                    className="bg-gradient-to-r from-primary-500 to-primary-400 h-2.5 rounded-full transition-all duration-500 shadow-sm"
                    style={{ width: `${riskScore}%` }}
                  ></div>
                </div>
              )}
            </div>
          )}

      {/* Compliance Risk - only show if available */}
      {sentiment.compliance_risk_score !== undefined && (
        <div className="mb-4">
          <div className="flex items-center justify-between p-3 bg-error-500/10 rounded-lg border border-error-500/30">
            <span className="text-sm font-medium text-slate-300">Compliance Risk</span>
            <span className="text-sm font-semibold text-error-400">
              {sentiment.compliance_risk_score}%
            </span>
          </div>
        </div>
      )}

      {/* Sentiment Trend - only show if available */}
      {sentiment.sentiment_trend && (
        <div>
          <div className="flex items-center space-x-2 p-3 bg-primary-500/10 rounded-lg border border-primary-500/30">
            <span className="text-sm font-medium text-slate-300">Trend:</span>
            <span className="text-sm font-semibold capitalize text-primary-400">
              {sentiment.sentiment_trend}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default SentimentGauge

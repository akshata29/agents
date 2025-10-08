import type { FC } from 'react'
import { Sparkles, TrendingUp } from 'lucide-react'
import type { Recommendation } from '../types'

interface RecommendationCardsProps {
  recommendations: Recommendation[]
  onGenerate: () => void
}

const RecommendationCards: FC<RecommendationCardsProps> = ({ recommendations, onGenerate }) => {
  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low':
        return 'bg-success-500/20 text-success-400 border-success-500'
      case 'medium':
        return 'bg-warning-500/20 text-warning-400 border-warning-500'
      case 'high':
        return 'bg-error-500/20 text-error-400 border-error-500'
      default:
        return 'bg-slate-700 text-slate-300 border-slate-500'
    }
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <TrendingUp className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-white">Recommendations</h3>
        </div>
        <button
          onClick={onGenerate}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium transition-colors"
        >
          Generate
        </button>
      </div>

      <div className="space-y-4 max-h-96 overflow-y-auto custom-scrollbar">
        {recommendations.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No recommendations yet. Click "Generate" to create.</p>
          </div>
        ) : (
          recommendations
            .sort((a, b) => a.priority - b.priority)
            .map((rec, index) => (
              <div
                key={index}
                className="border border-slate-700 rounded-lg p-4 bg-slate-750 hover:border-slate-600 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-semibold text-white">{rec.product_name}</h4>
                    <p className="text-sm text-slate-400 capitalize">{rec.product_type}</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(rec.risk_level)}`}>
                    {rec.risk_level} Risk
                  </span>
                </div>

                <p className="text-sm text-slate-300 mb-3">{rec.rationale}</p>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="flex items-center space-x-2">
                    <span className="text-slate-400">Alignment:</span>
                    <div className="flex-1 bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-primary-500 h-2 rounded-full"
                        style={{ width: `${rec.alignment_score}%` }}
                      ></div>
                    </div>
                    <span className="font-medium text-slate-300">{rec.alignment_score}%</span>
                  </div>

                  {rec.time_horizon && (
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-400">Horizon:</span>
                      <span className="font-medium text-slate-300">{rec.time_horizon}</span>
                    </div>
                  )}

                  {rec.expected_return_range && (
                    <div className="flex items-center space-x-2">
                      <span className="text-gray-600">Return:</span>
                      <span className="font-medium">{rec.expected_return_range}</span>
                    </div>
                  )}

                  {rec.min_investment && (
                    <div className="flex items-center space-x-2">
                      <span className="text-gray-600">Min:</span>
                      <span className="font-medium">${rec.min_investment.toLocaleString()}</span>
                    </div>
                  )}
                </div>

                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs text-gray-500">Priority: {rec.priority}</span>
                </div>
              </div>
            ))
        )}
      </div>
    </div>
  )
}

export default RecommendationCards

import type { FC } from 'react'
import { Sparkles, TrendingUp } from 'lucide-react'
import type { Recommendation } from '../types'

interface RecommendationCardsProps {
  recommendations: Recommendation[]
  onGenerate: () => void
}

const RecommendationCards: FC<RecommendationCardsProps> = ({ recommendations, onGenerate }) => {
  // Debug: log what we receive
  console.log('RecommendationCards received:', recommendations)
  
  // Extract the actual recommendations array from the response object
  const recommendationsList = Array.isArray(recommendations) 
    ? recommendations 
    : (recommendations as any)?.investment_recommendations || []
  
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
        {recommendationsList.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No recommendations yet. Click "Generate" to create.</p>
          </div>
        ) : (
          recommendationsList
            .sort((a: any, b: any) => (a.priority || 0) - (b.priority || 0))
            .map((rec: any, index: number) => (
              <div
                key={index}
                className="border border-slate-600 rounded-lg p-5 bg-slate-800/50 hover:border-primary-500/50 transition-all hover:shadow-lg"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h4 className="font-semibold text-white text-base mb-1">
                      {rec.recommendation || rec.product_name || 'Investment Recommendation'}
                    </h4>
                    <p className="text-sm text-slate-400 capitalize">
                      {rec.type || rec.product_type || rec.category || 'investment'}
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-md text-xs font-semibold border whitespace-nowrap ml-3 ${getRiskColor(rec.risk_level)}`}>
                    {rec.risk_level || 'moderate'} Risk
                  </span>
                </div>

                <p className="text-sm text-slate-300 mb-4 leading-relaxed">{rec.rationale}</p>

                <div className="space-y-2 text-xs">
                  {/* Alignment/Confidence Score */}
                  {(rec.confidence !== undefined || rec.alignment_score !== undefined) && (
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-400 w-20">
                        {rec.confidence !== undefined ? 'Confidence:' : 'Alignment:'}
                      </span>
                      <div className="flex-1 bg-slate-700 rounded-full h-2.5">
                        <div
                          className="bg-primary-500 h-2.5 rounded-full transition-all"
                          style={{ width: `${(rec.confidence || rec.alignment_score || 0) * 100}%` }}
                        ></div>
                      </div>
                      <span className="font-medium text-slate-300 w-12 text-right">
                        {Math.round((rec.confidence || rec.alignment_score || 0) * 100)}%
                      </span>
                    </div>
                  )}

                  {/* Priority */}
                  {rec.priority && (
                    <div className="flex items-center justify-between pt-2 border-t border-slate-700">
                      <span className="text-slate-400">Priority:</span>
                      <span className={`font-semibold px-2 py-0.5 rounded ${
                        rec.priority === 'high' ? 'text-error-400 bg-error-500/10' :
                        rec.priority === 'medium' ? 'text-warning-400 bg-warning-500/10' :
                        'text-success-400 bg-success-500/10'
                      }`}>
                        {rec.priority}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))
        )}
      </div>
    </div>
  )
}

export default RecommendationCards

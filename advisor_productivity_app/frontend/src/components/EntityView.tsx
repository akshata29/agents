import type { FC } from 'react'
import { Shield, AlertTriangle } from 'lucide-react'
import type { EntityData } from '../types'

interface EntityViewProps {
  entities: EntityData | null
}

const EntityView: FC<EntityViewProps> = ({ entities }) => {
  if (!entities) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Shield className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-white">Entities & Compliance</h3>
        </div>
        <div className="text-center py-8 text-slate-400">
          <Shield className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No entity data yet</p>
        </div>
      </div>
    )
  }

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'high':
        return 'bg-error-500/20 text-error-400 border-error-500'
      case 'medium':
        return 'bg-warning-500/20 text-warning-400 border-warning-500'
      case 'low':
        return 'bg-success-500/20 text-success-400 border-success-500'
      default:
        return 'bg-slate-700 text-slate-300 border-slate-500'
    }
  }

  const entityCategories = Object.entries(entities.entities).filter(([, items]) => items.length > 0)

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Shield className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-white">Entities & Compliance</h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-slate-400">
            {entities.metadata.entity_count} entities
          </span>
          {entities.pii.detected.length > 0 && (
            <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(entities.pii.risk_level)}`}>
              {entities.pii.detected.length} PII
            </span>
          )}
        </div>
      </div>

      {/* PII Warning */}
      {entities.pii.detected.length > 0 && (
        <div className={`p-3 rounded-lg border mb-4 ${getRiskColor(entities.pii.risk_level)}`}>
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">
              {entities.pii.detected.length} PII item(s) detected - {entities.pii.risk_level} risk
            </span>
          </div>
        </div>
      )}

      {/* Entity Categories */}
      <div className="space-y-4 max-h-64 overflow-y-auto custom-scrollbar">
        {entityCategories.length === 0 ? (
          <div className="text-center py-4 text-slate-400">
            <p>No entities extracted yet</p>
          </div>
        ) : (
          entityCategories.map(([category, items]) => (
            <div key={category} className="border-b border-slate-700 pb-3">
              <h4 className="text-sm font-semibold text-slate-300 mb-2 capitalize">
                {category.replace(/_/g, ' ')} ({items.length})
              </h4>
              <div className="flex flex-wrap gap-2">
                {items.map((item, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs border border-blue-200"
                    title={item.context || ''}
                  >
                    {item.value}
                  </span>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* PII Details */}
      {entities.pii.detected.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">PII Detected</h4>
          <div className="space-y-1">
            {entities.pii.detected.map((pii, index) => (
              <div
                key={index}
                className="flex items-center justify-between text-xs p-2 bg-red-50 rounded"
              >
                <span className="font-medium capitalize">{pii.type}</span>
                <span className="text-gray-600">***REDACTED***</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default EntityView

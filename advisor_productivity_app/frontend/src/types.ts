// Type definitions for Advisor Productivity App

export type ViewMode = 'unified' | 'chat' | 'analytics' | 'progress' | 'history'

export interface TranscriptSegment {
  text: string
  timestamp: string
  speaker: string
  isFinal: boolean
}

export interface SentimentData {
  overall_sentiment: string
  investment_readiness_score: number
  emotions: Record<string, number>
  compliance_risk_score: number
  sentiment_trend: string
  key_phrases: string[]
}

export interface Recommendation {
  product_type: string
  product_name: string
  rationale: string
  alignment_score: number
  risk_level: string
  priority: number
  time_horizon?: string
  expected_return_range?: string
  min_investment?: number
}

export interface EntityData {
  entities: Record<string, Array<{ value: string; context?: string }>>
  pii: {
    detected: Array<{ type: string; value: string; position: number }>
    risk_level: string
  }
  redacted_text?: string
  metadata: {
    entity_count: number
    pii_count: number
  }
}

export interface ActionItem {
  action: string
  responsible?: string
  deadline?: string
  priority?: string
  details?: string
  context?: string
  dependencies?: string[]
  success_criteria?: string
}

export interface Decision {
  decision: string
  rationale?: string
  impact?: string
  stakeholders?: string[]
  timeline?: string
}

export interface Summary {
  persona: string
  summary_type: string
  summary: string
  action_items?: (string | ActionItem)[]
  key_points?: string[]
  decisions_made?: (string | Decision)[]
  client_commitments?: string[]
}

export interface SessionData {
  transcript: TranscriptSegment[]
  sentiment: SentimentData | null
  recommendations: Recommendation[]
  entities: EntityData | null
  summary: Summary[] | null
  isRecording: boolean
  sessionActive: boolean
  isSummaryLoading: boolean
}

export interface HistoricalSession {
  session_id: string
  created_at: string
  ended_at: string | null
  duration_seconds: number | null
  status: string
  client_name: string | null
  advisor_name: string | null
  exchange_count: number
  investment_readiness_score: number | null
  key_topics: string[]
}

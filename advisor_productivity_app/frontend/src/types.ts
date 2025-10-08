// Type definitions for Advisor Productivity App

export type ViewMode = 'unified' | 'chat' | 'analytics' | 'progress'

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

export interface Summary {
  persona: string
  summary_type: string
  summary: string
  action_items?: string[]
  key_points?: string[]
  decisions_made?: string[]
}

export interface SessionData {
  transcript: TranscriptSegment[]
  sentiment: SentimentData | null
  recommendations: Recommendation[]
  entities: EntityData | null
  summary: Summary[] | null
  isRecording: boolean
  sessionActive: boolean
}

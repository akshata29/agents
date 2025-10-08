import { useState, useEffect } from 'react'
import './App.css'
import { Headphones, Activity } from 'lucide-react'
import AudioRecorder from './components/AudioRecorder'
import TranscriptView from './components/TranscriptView'
import SentimentGauge from './components/SentimentGauge'
import RecommendationCards from './components/RecommendationCards'
import EntityView from './components/EntityView'
import SummaryPanel from './components/SummaryPanel'
import AnalyticsDashboard from './components/AnalyticsDashboard'
import SessionControls from './components/SessionControls'
import SessionHistory from './components/SessionHistory'
import type { SessionData, ViewMode, TranscriptSegment } from './types'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

function App() {
  const [sessionId] = useState<string>(() => `session_${Date.now()}`)
  const [viewMode, setViewMode] = useState<ViewMode>('unified')
  const [sessionData, setSessionData] = useState<SessionData>({
    transcript: [],
    sentiment: null,
    recommendations: [],
    entities: null,
    summary: null,
    isRecording: false,
    sessionActive: false,
    isSummaryLoading: false
  })

  // WebSocket connections
  const [transcriptionWs, setTranscriptionWs] = useState<WebSocket | null>(null)
  const [sentimentWs, setSentimentWs] = useState<WebSocket | null>(null)
  const [entityWs, setEntityWs] = useState<WebSocket | null>(null)
  const [recommendationsWs, setRecommendationsWs] = useState<WebSocket | null>(null)

  useEffect(() => {
    // Initialize WebSocket connections when session starts
    if (sessionData.sessionActive) {
      // Transcription WebSocket
      const transWs = new WebSocket(`${BACKEND_URL.replace('http', 'ws')}/transcription/ws/${sessionId}`)
      transWs.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'transcript_chunk') {
          setSessionData(prev => ({
            ...prev,
            transcript: [...prev.transcript, {
              text: data.text,
              timestamp: data.timestamp,
              speaker: data.speaker || 'Unknown',
              isFinal: data.is_final
            }]
          }))
        }
      }
      setTranscriptionWs(transWs)

      // Sentiment WebSocket
      const sentWs = new WebSocket(`${BACKEND_URL.replace('http', 'ws')}/sentiment/ws/${sessionId}`)
      sentWs.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'sentiment_update') {
          setSessionData(prev => ({
            ...prev,
            sentiment: data.data  // Backend sends sentiment in 'data' field
          }))
        }
      }
      setSentimentWs(sentWs)

      // Entity/PII WebSocket
      const entWs = new WebSocket(`${BACKEND_URL.replace('http', 'ws')}/entity-pii/ws/${sessionId}`)
      entWs.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'extraction_completed') {
          setSessionData(prev => ({
            ...prev,
            entities: data.result
          }))
        }
      }
      setEntityWs(entWs)

      // Recommendations WebSocket
      const recWs = new WebSocket(`${BACKEND_URL.replace('http', 'ws')}/recommendations/ws/${sessionId}`)
      recWs.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'recommendations_update') {
          // Backend sends the full recommendations object in 'data' field
          setSessionData(prev => ({
            ...prev,
            recommendations: data.data
          }))
        }
      }
      setRecommendationsWs(recWs)

      return () => {
        transWs.close()
        sentWs.close()
        entWs.close()
        recWs.close()
      }
    }
  }, [sessionData.sessionActive, sessionId])

  const handleStartSession = () => {
    setSessionData(prev => ({ ...prev, sessionActive: true }))
  }

  const handleEndSession = async () => {
    // First, stop recording immediately to release microphone
    setSessionData(prev => ({ ...prev, isRecording: false }))
    
    // Give a moment for the AudioRecorder useEffect to clean up
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Now update the rest of the session state
    setSessionData(prev => ({ ...prev, sessionActive: false, isSummaryLoading: true }))
    
    // Close WebSocket connections
    transcriptionWs?.close()
    sentimentWs?.close()
    entityWs?.close()
    recommendationsWs?.close()

    // Automatically switch to Summary tab
    setViewMode('progress')

    // Request comprehensive summary with transcript, sentiment, and recommendations
    try {
      const response = await fetch(`${BACKEND_URL}/summary/generate-all-personas/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript_segments: sessionData.transcript,
          sentiment_data: sessionData.sentiment,
          recommendations: sessionData.recommendations
        })
      })
      const summaries = await response.json()
      console.log('📝 Summary response received:', summaries)
      
      // Convert dictionary to array format expected by SummaryPanel
      const summaryArray = Object.entries(summaries).map(([persona, data]: [string, any]) => ({
        persona,
        ...data
      }))
      
      console.log('📝 Summary array:', summaryArray)
      setSessionData(prev => ({ ...prev, summary: summaryArray, isSummaryLoading: false }))
    } catch (error) {
      console.error('Error generating summary:', error)
      setSessionData(prev => ({ ...prev, isSummaryLoading: false }))
    }
  }

  const handleLoadHistoricalSession = async (historicalSessionId: string) => {
    try {
      console.log('Loading historical session:', historicalSessionId)
      
      const response = await fetch(`${BACKEND_URL}/history/sessions/${historicalSessionId}`)
      if (!response.ok) {
        throw new Error('Failed to load session')
      }
      
      const session = await response.json()
      console.log('Historical session loaded:', session)
      
      // Convert summaries dictionary to array format
      const summaryArray = session.summaries 
        ? Object.entries(session.summaries).map(([persona, data]: [string, any]) => ({
            persona,
            ...data
          }))
        : null
      
      // Load the historical data into current session
      setSessionData({
        transcript: session.transcript || [],
        sentiment: session.sentiment_data || null,
        recommendations: session.recommendations || [],
        entities: session.entities || null,
        summary: summaryArray,
        isRecording: false,
        sessionActive: false,
        isSummaryLoading: false
      })
      
      // Switch to unified view to see the data
      setViewMode('unified')
      
    } catch (error) {
      console.error('Error loading historical session:', error)
      alert('Failed to load session. Please try again.')
    }
  }

  const handleGenerateRecommendations = async () => {
    const fullTranscript = sessionData.transcript.map(t => t.text).join(' ')
    try {
      const response = await fetch(`${BACKEND_URL}/recommendations/generate/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: fullTranscript,
          sentiment_data: sessionData.sentiment
        })
      })
      const recommendations = await response.json()
      setSessionData(prev => ({ ...prev, recommendations: recommendations.recommendations || [] }))
    } catch (error) {
      console.error('Error generating recommendations:', error)
    }
  }

  const renderView = () => {
    switch (viewMode) {
      case 'chat':
        return (
          <div className="grid grid-cols-1 gap-6">
            <TranscriptView 
              transcript={sessionData.transcript}
              sentiment={sessionData.sentiment}
            />
            <AudioRecorder
              sessionId={sessionId}
              isRecording={sessionData.isRecording}
              onRecordingChange={(recording) => 
                setSessionData(prev => ({ ...prev, isRecording: recording }))
              }
            />
          </div>
        )

      case 'analytics':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SentimentGauge sentiment={sessionData.sentiment} />
            <RecommendationCards 
              recommendations={sessionData.recommendations}
              onGenerate={handleGenerateRecommendations}
            />
            <AnalyticsDashboard 
              transcript={sessionData.transcript}
              sentiment={sessionData.sentiment}
            />
          </div>
        )

      case 'progress':
        return (
          <div className="grid grid-cols-1 gap-6">
            <SummaryPanel 
              summary={sessionData.summary}
              sessionId={sessionId}
              isLoading={sessionData.isSummaryLoading}
            />
            <EntityView entities={sessionData.entities} />
          </div>
        )

      case 'history':
        return (
          <SessionHistory onLoadSession={handleLoadHistoricalSession} />
        )

      case 'unified':
      default:
        return (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column - Transcript, Audio, and Analytics Dashboard */}
            <div className="lg:col-span-2 space-y-6">
              <TranscriptView 
                transcript={sessionData.transcript}
                sentiment={sessionData.sentiment}
              />
              <AudioRecorder
                sessionId={sessionId}
                isRecording={sessionData.isRecording}
                onRecordingChange={(recording) => 
                  setSessionData(prev => ({ ...prev, isRecording: recording }))
                }
              />
              <AnalyticsDashboard 
                transcript={sessionData.transcript}
                sentiment={sessionData.sentiment}
              />
            </div>

            {/* Right column - Sentiment, Recommendations, and Entities */}
            <div className="space-y-6">
              <SentimentGauge sentiment={sessionData.sentiment} />
              <RecommendationCards 
                recommendations={sessionData.recommendations}
                onGenerate={handleGenerateRecommendations}
              />
              <EntityView entities={sessionData.entities} />
            </div>

            {/* Full width - Summary only */}
            {sessionData.summary && (
              <div className="lg:col-span-3">
                <SummaryPanel 
                  summary={sessionData.summary}
                  sessionId={sessionId}
                  isLoading={sessionData.isSummaryLoading}
                />
              </div>
            )}
          </div>
        )
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Headphones className="w-8 h-8 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-white">
                  Advisor Productivity Platform
                </h1>
                <p className="text-sm text-slate-400">
                  AI-Powered Client Conversation Intelligence
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm">
              <div className={`px-3 py-1 rounded-full ${
                sessionData.sessionActive 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-slate-700 text-slate-400'
              }`}>
                {sessionData.sessionActive ? (
                  <div className="flex items-center space-x-2">
                    <Activity className="w-4 h-4 animate-pulse" />
                    <span>Session Active</span>
                  </div>
                ) : (
                  'Ready'
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <div className="bg-slate-800 border-b border-slate-700">
        <div className="px-6">
          <SessionControls
            sessionActive={sessionData.sessionActive}
            viewMode={viewMode}
            onStartSession={handleStartSession}
            onEndSession={handleEndSession}
            onViewModeChange={setViewMode}
          />
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto custom-scrollbar bg-slate-900 p-6">
        <div className="max-w-[1600px] mx-auto">
          {renderView()}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-800 border-t border-slate-700">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <div>
              Powered by Microsoft Agent Framework & Azure AI Services
            </div>
            <div>
              Session: {sessionId.slice(-8)}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App

import type { FC } from 'react'
import { useState, useRef, useEffect } from 'react'
import { Mic, MicOff } from 'lucide-react'

interface AudioRecorderProps {
  sessionId: string
  isRecording: boolean
  onRecordingChange: (recording: boolean) => void
}

const AudioRecorder: FC<AudioRecorderProps> = ({
  sessionId,
  isRecording,
  onRecordingChange
}) => {
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null)
  const [audioWorkletNode, setAudioWorkletNode] = useState<AudioWorkletNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  // Effect to stop recording when parent sets isRecording to false
  useEffect(() => {
    if (!isRecording && (audioContext || streamRef.current)) {
      stopRecording()
    }
  }, [isRecording])

  const startRecording = async () => {
    try {
      // Request microphone access with specific constraints for Azure Speech SDK
      // Must be 16kHz, mono, 16-bit PCM
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      })
      
      streamRef.current = stream
      
      // Create AudioContext at 16kHz sample rate (required by Azure Speech SDK)
      const context = new AudioContext({ sampleRate: 16000 })
      setAudioContext(context)
      
      // Create MediaStreamSource from microphone
      const source = context.createMediaStreamSource(stream)
      
      // Create ScriptProcessorNode to capture raw PCM audio
      // Buffer size 4096 provides good balance between latency and efficiency
      const processor = context.createScriptProcessor(4096, 1, 1)
      
      processor.onaudioprocess = async (event) => {
        // Get raw PCM samples (Float32Array)
        const inputBuffer = event.inputBuffer
        const rawSamples = inputBuffer.getChannelData(0)
        
        // Convert Float32 samples (-1.0 to 1.0) to Int16 PCM (required by Azure)
        const pcmData = new Int16Array(rawSamples.length)
        for (let i = 0; i < rawSamples.length; i++) {
          // Clamp to -1.0 to 1.0 and convert to 16-bit integer
          const s = Math.max(-1, Math.min(1, rawSamples[i]))
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }
        
        // Send raw PCM bytes to backend
        const blob = new Blob([pcmData.buffer], { type: 'audio/pcm' })
        const formData = new FormData()
        formData.append('audio', blob)
        formData.append('session_id', sessionId)

        try {
          await fetch('http://localhost:8000/transcription/upload', {
            method: 'POST',
            body: formData
          })
        } catch (error) {
          console.error('Error uploading audio:', error)
        }
      }
      
      // Connect: microphone -> processor -> destination
      source.connect(processor)
      processor.connect(context.destination)
      
      console.log('Started recording with raw PCM capture at 16kHz, mono, 16-bit')
      onRecordingChange(true)
    } catch (error) {
      console.error('Error starting recording:', error)
    }
  }

  const stopRecording = () => {
    console.log('Stopping recording and releasing microphone...')
    
    // Stop audio processing
    if (audioContext) {
      audioContext.close()
      setAudioContext(null)
    }
    
    // Stop microphone stream - this releases the microphone
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop()
        console.log('Stopped audio track:', track.label)
      })
      streamRef.current = null
    }
    
    setAudioWorkletNode(null)
    
    // Only update parent if currently recording
    if (isRecording) {
      onRecordingChange(false)
    }
    
    console.log('Microphone released')
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center space-x-2 mb-4">
        <Mic className="w-5 h-5 text-primary-400" />
        <h3 className="text-lg font-semibold text-white">Audio Recording</h3>
      </div>
      
      <div className="flex items-center justify-center space-x-4">
        {!isRecording ? (
          <button
            onClick={startRecording}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium flex items-center space-x-2 transition-colors"
          >
            <Mic className="w-5 h-5" />
            <span>Start Recording</span>
          </button>
        ) : (
          <div className="flex items-center space-x-4">
            <button
              onClick={stopRecording}
              className="px-6 py-3 bg-error-600 text-white rounded-lg hover:bg-error-700 font-medium flex items-center space-x-2 transition-colors"
            >
              <MicOff className="w-5 h-5" />
              <span>Stop Recording</span>
            </button>
            
            <div className="flex items-center space-x-2 text-error-400">
              <div className="w-3 h-3 bg-error-500 rounded-full animate-pulse"></div>
              <span className="font-medium">Recording...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AudioRecorder

import React from 'react';
import { FileAudio, FileText, Video, MessageSquare, BarChart3, TrendingUp, AlertTriangle } from 'lucide-react';

interface QuickTasksProps {
  onSelectTask: (objective: string) => void;
  disabled?: boolean;
}

interface QuickTask {
  id: string;
  title: string;
  description: string;
  objective: string;
  icon: React.ReactNode;
  category: 'audio' | 'video' | 'document' | 'general';
}

const quickTasks: QuickTask[] = [
  {
    id: 'audio-sentiment',
    title: 'Audio Sentiment Analysis',
    description: 'Extract sentiment and emotional tone from audio transcripts',
    objective: 'Analyze the sentiment and emotional tone from all uploaded audio files. Extract key themes, speaker insights, and provide a comprehensive sentiment summary report with positive, negative, and neutral classifications.',
    icon: <MessageSquare className="w-5 h-5" />,
    category: 'audio',
  },
  {
    id: 'meeting-summary',
    title: 'Meeting Summarization',
    description: 'Generate action items and key discussion points',
    objective: 'Transcribe and summarize the uploaded meeting recording. Identify key discussion points, action items, decisions made, and participant contributions. Create a structured meeting summary with timestamps for important moments.',
    icon: <FileAudio className="w-5 h-5" />,
    category: 'audio',
  },
  {
    id: 'document-insights',
    title: 'Research Document Analysis',
    description: 'Extract insights and summarize research papers',
    objective: 'Analyze the uploaded research document or PDF. Extract the main thesis, key findings, methodology, conclusions, and recommendations. Provide a comprehensive summary with important quotes and references.',
    icon: <FileText className="w-5 h-5" />,
    category: 'document',
  },
  {
    id: 'video-transcript',
    title: 'Video Content Analysis',
    description: 'Transcribe and analyze video content',
    objective: 'Process the uploaded video file to extract audio transcription, identify key visual elements, and provide a detailed content summary. Highlight important moments, topics discussed, and create a searchable transcript with timestamps.',
    icon: <Video className="w-5 h-5" />,
    category: 'video',
  },
  {
    id: 'product-feedback',
    title: 'Product Feedback Analysis',
    description: 'Analyze customer feedback and reviews',
    objective: 'Analyze all uploaded customer feedback, reviews, or interview recordings. Extract common themes, pain points, feature requests, and overall satisfaction levels. Provide actionable insights and categorized feedback summary.',
    icon: <BarChart3 className="w-5 h-5" />,
    category: 'general',
  },
  {
    id: 'competitive-analysis',
    title: 'Competitive Intelligence',
    description: 'Extract competitive insights from documents',
    objective: 'Analyze uploaded competitive intelligence materials, presentations, or market research documents. Extract key competitor strategies, market positioning, strengths, weaknesses, and opportunities. Create a structured competitive analysis report.',
    icon: <TrendingUp className="w-5 h-5" />,
    category: 'document',
  },
  {
    id: 'sec-filing-analysis',
    title: 'SEC Filing Risk Analysis',
    description: 'Detailed SEC document analysis with risk extraction',
    objective: `Perform comprehensive SEC document analysis with detailed focus on:

1. RISK FACTORS ANALYSIS:
   - Extract all risk factors from the Risk Factors section
   - Categorize by type (Market, Operational, Financial, Regulatory, Cybersecurity, Legal)
   - Rate severity (Critical/High/Medium/Low) based on language intensity
   - Identify new risks compared to typical disclosures

2. KEY SECTIONS EXTRACTION:
   - Business Overview and Operations
   - Management Discussion & Analysis (MD&A) key points
   - Financial Highlights and Metrics
   - Forward-Looking Statements
   - Legal Proceedings summary

3. FINANCIAL METRICS:
   - Revenue trends and segment breakdown
   - Profitability metrics (gross margin, operating margin, net margin)
   - Cash flow and liquidity position
   - Debt levels and key ratios

4. STRATEGIC INSIGHTS:
   - Business strategy and initiatives
   - Capital allocation plans
   - M&A activity and partnerships
   - R&D focus areas and market expansion

5. ACTIONABLE OUTPUTS:
   - Top 10 investor insights
   - Critical risks requiring attention (🔴 Critical, 🟡 High, 🟢 Medium, ⚪ Low)
   - Growth opportunities identified
   - Red flags or concerns

Structure output with clear headers, bullet points, risk ratings, and quantified metrics.`,
    icon: <AlertTriangle className="w-5 h-5" />,
    category: 'document',
  },
];

const QuickTasks: React.FC<QuickTasksProps> = ({ onSelectTask, disabled = false }) => {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Quick Tasks</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {quickTasks.map((task) => (
          <button
            key={task.id}
            onClick={() => onSelectTask(task.objective)}
            disabled={disabled}
            className={`
              flex items-start p-4 rounded-lg border text-left transition-all
              ${
                disabled
                  ? 'bg-slate-800 border-slate-700 cursor-not-allowed opacity-50'
                  : 'bg-slate-800 border-slate-700 hover:border-primary-500 hover:bg-slate-750 cursor-pointer'
              }
            `}
          >
            <div className="flex-shrink-0 p-2 bg-primary-500/10 rounded-lg mr-3">
              <div className="text-primary-400">{task.icon}</div>
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-white mb-1">{task.title}</h4>
              <p className="text-xs text-slate-400 line-clamp-2">{task.description}</p>
            </div>
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500 text-center">
        Click a quick task to auto-fill the objective, or write your own custom objective below
      </p>
    </div>
  );
};

export default QuickTasks;

import React, { useState } from 'react';
import { 
  Mic, Heart, BookOpen, BarChart3, FileText,
  MessageSquare, TrendingUp, Users, Lightbulb, AlertTriangle,
  CheckCircle2, Target, Zap, Code, ChevronDown, ChevronUp
} from 'lucide-react';

// Raw JSON Viewer Component
const RawOutputViewer: React.FC<{ data: any }> = ({ data }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="mt-3 border-t border-slate-700 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center space-x-2 text-xs text-slate-400 hover:text-slate-300 transition-colors"
      >
        <Code className="h-3 w-3" />
        <span>View Raw Output</span>
        {isExpanded ? (
          <ChevronUp className="h-3 w-3" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>
      
      {isExpanded && (
        <div className="mt-2 bg-slate-950 rounded-lg p-3 border border-slate-700 max-h-96 overflow-y-auto">
          <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

// Transcription/Content Extraction Card - Handles audio, video, PDF
const ContentExtractionCard: React.FC<{ data: any }> = ({ data }) => {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const PREVIEW_LENGTH = 1000;
  
  // Data might be wrapped in file_id key, so unwrap it
  let content = data;
  if (data && typeof data === 'object' && !data.file_id && !data.transcription && !data.text_content) {
    // Data is wrapped - get the first key's value
    const firstKey = Object.keys(data)[0];
    if (firstKey && typeof data[firstKey] === 'object') {
      content = data[firstKey];
    }
  }

  const fileType = content.file_type || 'audio';
  const textContent = content.transcription || content.text_content || '';
  const metadata = content.audio_metadata || content.video_metadata || content.document_structure || {};
  
  // Determine if content needs truncation
  const needsTruncation = textContent.length > PREVIEW_LENGTH;
  const displayContent = isExpanded ? textContent : textContent.slice(0, PREVIEW_LENGTH);
  
  // Determine card styling and labels based on file type
  const isAudioVideo = fileType === 'audio' || fileType === 'video';
  
  const cardTitle = isAudioVideo ? 'Transcription' : 'Content Extraction';
  const CardIcon = isAudioVideo ? Mic : FileText;
  const iconColor = isAudioVideo ? 'text-blue-400' : 'text-purple-400';
  const titleColor = isAudioVideo ? 'text-blue-300' : 'text-purple-300';
  const borderColor = isAudioVideo ? 'border-blue-500/30' : 'border-purple-500/30';
  const gradientFrom = isAudioVideo ? 'from-blue-500/10' : 'from-purple-500/10';
  const gradientTo = isAudioVideo ? 'to-purple-500/10' : 'to-pink-500/10';
  const badgeBorderColor = isAudioVideo ? 'border-blue-500/20' : 'border-purple-500/20';
  
  return (
    <div className={`bg-gradient-to-br ${gradientFrom} ${gradientTo} border ${borderColor} rounded-lg p-4 space-y-3`}>
      <div className="flex items-center space-x-2">
        <CardIcon className={`h-5 w-5 ${iconColor}`} />
        <h4 className={`font-semibold ${titleColor}`}>{cardTitle}</h4>
        <span className="text-xs px-2 py-0.5 bg-slate-700 text-slate-300 rounded-full">
          {fileType.toUpperCase()}
        </span>
      </div>
      
      {textContent ? (
        <div className="space-y-2">
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
              {displayContent}
              {needsTruncation && !isExpanded && (
                <span className="text-slate-500">...</span>
              )}
            </p>
          </div>
          {needsTruncation && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs text-blue-400 hover:text-blue-300 transition-colors flex items-center space-x-1"
            >
              <span>{isExpanded ? '▼ Show Less' : '▶ Show More'}</span>
              <span className="text-slate-500">
                ({isExpanded ? 'Collapse' : `${(textContent.length - PREVIEW_LENGTH).toLocaleString()} more characters`})
              </span>
            </button>
          )}
        </div>
      ) : (
        <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-400 italic">
            No content extracted
          </p>
        </div>
      )}
      
      <div className={`flex flex-wrap gap-2 pt-2 border-t ${badgeBorderColor}`}>
        {/* Audio/Video metadata */}
        {metadata.language && (
          <span className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded-full">
            🌐 {metadata.language}
          </span>
        )}
        {metadata.format && (
          <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-300 rounded-full">
            📁 {metadata.format}
          </span>
        )}
        {metadata.duration && (
          <span className="text-xs px-2 py-1 bg-green-500/20 text-green-300 rounded-full">
            ⏱️ {metadata.duration}
          </span>
        )}
        
        {/* PDF metadata */}
        {metadata.page_count !== undefined && (
          <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-300 rounded-full">
            📄 {metadata.page_count} page{metadata.page_count !== 1 ? 's' : ''}
          </span>
        )}
        {metadata.languages && metadata.languages.length > 0 && (
          <span className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded-full">
            🌐 {metadata.languages.join(', ')}
          </span>
        )}
        
        {/* Character count */}
        {textContent && (
          <span className="text-xs px-2 py-1 bg-slate-500/20 text-slate-300 rounded-full">
            📝 {textContent.length.toLocaleString()} characters
          </span>
        )}
      </div>
      
      <RawOutputViewer data={data} />
    </div>
  );
};

// Sentiment Analysis Card
const SentimentCard: React.FC<{ data: any }> = ({ data }) => {
  const getSentimentColor = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return 'text-green-400 bg-green-500/20 border-green-500/30';
      case 'negative': return 'text-red-400 bg-red-500/20 border-red-500/30';
      case 'neutral': return 'text-slate-400 bg-slate-500/20 border-slate-500/30';
      case 'mixed': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
      default: return 'text-slate-400 bg-slate-500/20 border-slate-500/30';
    }
  };

  const overall = data.overall_sentiment || 'neutral';
  const score = data.sentiment_score || 0;
  const emotions = data.emotions || [];
  const tone = data.tone;
  const sentimentBySections = data.sentiment_by_section || [];

  return (
    <div className="bg-gradient-to-br from-pink-500/10 to-rose-500/10 border border-pink-500/30 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Heart className="h-5 w-5 text-pink-400" />
          <h4 className="font-semibold text-pink-300">Sentiment Analysis</h4>
        </div>
        <div className={`px-3 py-1 rounded-full border ${getSentimentColor(overall)}`}>
          <span className="text-sm font-semibold capitalize">{overall}</span>
        </div>
      </div>

      {/* Sentiment Score */}
      {score !== undefined && (
        <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400">Confidence Score</span>
            <span className="text-sm font-semibold text-slate-200">{score.toFixed(2)}</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-pink-500 to-rose-500 h-2 rounded-full transition-all"
              style={{ width: `${score * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Emotions */}
      {emotions.length > 0 && (
        <div className="space-y-2">
          <h5 className="text-xs font-medium text-slate-300 flex items-center space-x-1">
            <MessageSquare className="h-3 w-3" />
            <span>Detected Emotions</span>
          </h5>
          <div className="flex flex-wrap gap-2">
            {emotions.map((emotion: any, idx: number) => (
              <div key={idx} className="bg-pink-500/20 border border-pink-500/30 rounded-lg px-3 py-1.5">
                <div className="text-xs font-medium text-pink-300 capitalize">{emotion.emotion}</div>
                <div className="text-xs text-slate-400">
                  {(emotion.intensity * 100).toFixed(0)}% intensity
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tone */}
      {tone && (
        <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700">
          <h5 className="text-xs font-medium text-slate-300 mb-2">Overall Tone</h5>
          <div className="flex flex-wrap gap-2">
            {tone.key_phrases?.map((phrase: string, idx: number) => (
              <span key={idx} className="text-xs px-2 py-1 bg-rose-500/20 text-rose-300 rounded-full">
                "{phrase}"
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sentiment by Section */}
      {sentimentBySections.length > 0 && (
        <div className="space-y-2">
          <h5 className="text-xs font-medium text-slate-300">Sentiment Timeline</h5>
          {sentimentBySections.map((section: any, idx: number) => (
            <div key={idx} className="bg-slate-900/50 rounded-lg p-2 border border-slate-700">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">{section.section}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${getSentimentColor(section.sentiment)}`}>
                  {section.sentiment}
                </span>
              </div>
              {section.score !== undefined && (
                <div className="text-xs text-slate-500 mt-1">Score: {section.score.toFixed(2)}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Insights */}
      {data.insights && (
        <div className="bg-pink-500/10 rounded-lg p-3 border border-pink-500/20">
          <div className="flex items-start space-x-2">
            <Lightbulb className="h-4 w-4 text-pink-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-slate-300 leading-relaxed">{data.insights}</p>
          </div>
        </div>
      )}
      
      <RawOutputViewer data={data} />
    </div>
  );
};

// Summary Card
const SummaryCard: React.FC<{ data: any }> = ({ data }) => {
  const summary = data.summary || data.executive_summary || '';
  const keyInsights = data.key_insights || [];
  const segments = data.segments || [];
  const persona = data.persona;
  const summaryLength = data.summary_length;
  const metrics = data.metrics;

  return (
    <div className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-emerald-500/30 rounded-lg p-4 space-y-4">
      <div className="flex items-center space-x-2">
        <BookOpen className="h-5 w-5 text-emerald-400" />
        <h4 className="font-semibold text-emerald-300">Executive Summary</h4>
      </div>

      {/* Main Summary */}
      {summary && (
        <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
            {summary}
          </p>
        </div>
      )}

      {/* Metrics */}
      {metrics && (
        <div className="grid grid-cols-2 gap-2">
          {metrics.quantitative_findings && metrics.quantitative_findings.length > 0 && (
            <div className="bg-emerald-500/10 rounded-lg p-3 border border-emerald-500/20">
              <div className="text-xs text-emerald-400 font-medium mb-1">Key Metrics</div>
              {metrics.quantitative_findings.map((finding: any, idx: number) => (
                <div key={idx} className="text-xs text-slate-300">
                  {finding.metric}: <span className="font-semibold">{finding.value}</span>
                </div>
              ))}
            </div>
          )}
          {summaryLength && (
            <div className="bg-teal-500/10 rounded-lg p-3 border border-teal-500/20">
              <div className="text-xs text-teal-400 font-medium mb-1">Summary Stats</div>
              <div className="text-xs text-slate-300">
                Length: <span className="font-semibold">{summaryLength}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Key Insights */}
      {keyInsights.length > 0 && (
        <div className="space-y-2">
          <h5 className="text-xs font-medium text-slate-300 flex items-center space-x-1">
            <Target className="h-3 w-3" />
            <span>Key Insights</span>
          </h5>
          <div className="space-y-2">
            {keyInsights.map((insight: any, idx: number) => (
              <div key={idx} className="flex items-start space-x-2 bg-emerald-500/10 rounded-lg p-2 border border-emerald-500/20">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  {typeof insight === 'string' ? (
                    <p className="text-xs text-slate-300">{insight}</p>
                  ) : (
                    <>
                      <p className="text-xs font-medium text-emerald-300">{insight.insight}</p>
                      {insight.supporting_evidence && (
                        <p className="text-xs text-slate-400 mt-1">{insight.supporting_evidence}</p>
                      )}
                      {insight.importance && (
                        <span className="text-xs text-emerald-400 mt-1 inline-block">
                          Priority: {insight.importance}
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Segments */}
      {segments.length > 0 && (
        <div className="space-y-2">
          <h5 className="text-xs font-medium text-slate-300">Content Segments</h5>
          {segments.map((segment: any, idx: number) => (
            <div key={idx} className="bg-slate-900/50 rounded-lg p-3 border border-slate-700">
              <div className="text-xs font-medium text-emerald-300 mb-1">{segment.segment}</div>
              <p className="text-xs text-slate-300">{segment.content}</p>
            </div>
          ))}
        </div>
      )}

      {/* Persona */}
      {persona && (
        <div className="bg-teal-500/10 rounded-lg p-3 border border-teal-500/20">
          <div className="flex items-start space-x-2">
            <Users className="h-4 w-4 text-teal-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-xs font-medium text-teal-300 mb-1">Target Audience</div>
              <p className="text-xs text-slate-300">{persona.name}</p>
              {persona.description && (
                <p className="text-xs text-slate-400 mt-1">{persona.description}</p>
              )}
            </div>
          </div>
        </div>
      )}
      
      <RawOutputViewer data={data} />
    </div>
  );
};

// Smart Analytics Card - Dynamically renders whatever fields are present
const AnalyticsCard: React.FC<{ data: any }> = ({ data }) => {
  // Helper to format field names for display
  const formatFieldName = (key: string): string => {
    return key
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Helper to determine if a value is a "summary" type field (string, not array/object)
  const isSummaryField = (key: string, value: any): boolean => {
    return typeof value === 'string' && 
           (key.includes('summary') || key.includes('overview') || key.includes('description'));
  };

  // Helper to determine if a value is a list field
  const isListField = (value: any): boolean => {
    return Array.isArray(value) && value.length > 0;
  };

  // Helper to render a list item based on its structure
  const renderListItem = (item: any, idx: number, fieldKey: string) => {
    const isString = typeof item === 'string';
    
    // Determine styling based on field type
    const isRecommendation = fieldKey.includes('recommend');
    const isRisk = fieldKey.includes('risk') || fieldKey.includes('concern') || fieldKey.includes('challenge');
    const isFinding = fieldKey.includes('finding') || fieldKey.includes('insight') || fieldKey.includes('key_point');
    const isPattern = fieldKey.includes('pattern') || fieldKey.includes('trend');
    
    let bgColor = 'bg-indigo-500/10';
    let borderColor = 'border-indigo-500/20';
    let iconColor = 'text-indigo-400';
    let Icon = Lightbulb;
    
    if (isRecommendation) {
      bgColor = 'bg-green-500/10';
      borderColor = 'border-green-500/20';
      iconColor = 'text-green-400';
      Icon = CheckCircle2;
    } else if (isRisk) {
      bgColor = 'bg-yellow-500/10';
      borderColor = 'border-yellow-500/20';
      iconColor = 'text-yellow-400';
      Icon = AlertTriangle;
    } else if (isPattern) {
      bgColor = 'bg-violet-500/10';
      borderColor = 'border-violet-500/20';
      iconColor = 'text-violet-400';
      Icon = TrendingUp;
    } else if (isFinding) {
      bgColor = 'bg-indigo-500/10';
      borderColor = 'border-indigo-500/20';
      iconColor = 'text-indigo-400';
      Icon = Zap;
    }
    
    return (
      <div key={idx} className={`${bgColor} rounded-lg p-3 border ${borderColor}`}>
        <div className="flex items-start space-x-2">
          <Icon className={`h-4 w-4 ${iconColor} mt-0.5 flex-shrink-0`} />
          <div className="flex-1">
            {isString ? (
              <p className="text-xs text-slate-300">{item}</p>
            ) : (
              <>
                {/* Render object properties dynamically */}
                {Object.entries(item).map(([subKey, subValue]: [string, any]) => {
                  if (typeof subValue === 'string') {
                    const isTitle = subKey === 'title' || subKey === 'name' || subKey === Object.keys(item)[0];
                    return (
                      <p key={subKey} className={`text-xs ${isTitle ? 'font-medium text-indigo-300' : 'text-slate-400 mt-1'}`}>
                        {!isTitle && <span className="font-medium">{formatFieldName(subKey)}:</span>} {subValue}
                      </p>
                    );
                  } else if (Array.isArray(subValue)) {
                    return (
                      <div key={subKey} className="mt-1">
                        <span className="text-xs font-medium text-slate-400">{formatFieldName(subKey)}:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {subValue.map((v: any, i: number) => (
                            <span key={i} className="text-xs px-2 py-0.5 bg-slate-700/50 text-slate-300 rounded-full">
                              {typeof v === 'string' ? v : JSON.stringify(v)}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  }
                  return null;
                })}
              </>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Separate fields into categories
  const summaryFields: [string, string][] = [];
  const listFields: [string, any[]][] = [];
  const otherFields: [string, any][] = [];

  Object.entries(data).forEach(([key, value]) => {
    if (isSummaryField(key, value)) {
      summaryFields.push([key, value as string]);
    } else if (isListField(value)) {
      listFields.push([key, value as any[]]);
    } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      // Handle nested objects (like metrics)
      otherFields.push([key, value]);
    }
  });

  return (
    <div className="bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/30 rounded-lg p-4 space-y-4">
      <div className="flex items-center space-x-2">
        <BarChart3 className="h-5 w-5 text-indigo-400" />
        <h4 className="font-semibold text-indigo-300">Analytics & Insights</h4>
      </div>

      {/* Render summary fields first */}
      {summaryFields.map(([key, value]) => (
        <div key={key} className="bg-indigo-500/10 rounded-lg p-3 border border-indigo-500/20">
          <h5 className="text-xs font-medium text-indigo-300 mb-2 flex items-center space-x-1">
            <Target className="h-3 w-3" />
            <span>{formatFieldName(key)}</span>
          </h5>
          <p className="text-sm text-slate-200 leading-relaxed">{value}</p>
        </div>
      ))}

      {/* Render list fields */}
      {listFields.map(([key, items]) => (
        <div key={key} className="space-y-2">
          <h5 className="text-xs font-medium text-slate-300 flex items-center space-x-1">
            <Lightbulb className="h-3 w-3" />
            <span>{formatFieldName(key)}</span>
          </h5>
          <div className="space-y-2">
            {items.map((item, idx) => renderListItem(item, idx, key))}
          </div>
        </div>
      ))}

      {/* Render other structured fields (like metrics) */}
      {otherFields.map(([key, value]) => (
        <div key={key} className="space-y-2">
          <h5 className="text-xs font-medium text-slate-300">{formatFieldName(key)}</h5>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700">
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(value).map(([subKey, subValue]: [string, any]) => (
                <div key={subKey} className="text-xs">
                  <span className="text-slate-400">{formatFieldName(subKey)}:</span>{' '}
                  <span className="text-slate-200 font-medium">
                    {typeof subValue === 'object' ? JSON.stringify(subValue) : String(subValue)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
      
      <RawOutputViewer data={data} />
    </div>
  );
};

// Main component that routes to the right formatter
export const FormattedAgentResult: React.FC<{ agentName: string; data: any }> = ({ agentName, data }) => {
  // Handle multimodal processor
  if (agentName === 'MultimodalProcessor_Agent' || agentName === 'multimodal_processor') {
    // Check if it has multiple files
    if (data.results || data.processed_files) {
      const results = data.results ? Object.values(data.results) : [];
      return (
        <div className="space-y-3">
          {results.map((fileData: any, idx: number) => (
            <ContentExtractionCard key={idx} data={fileData} />
          ))}
        </div>
      );
    }
    // Single file
    return <ContentExtractionCard data={data} />;
  }

  // Handle sentiment agent
  if (agentName === 'Sentiment_Agent' || agentName === 'sentiment') {
    return <SentimentCard data={data} />;
  }

  // Handle summarizer agent
  if (agentName === 'Summarizer_Agent' || agentName === 'summarizer') {
    return <SummaryCard data={data} />;
  }

  // Handle analytics agent
  if (agentName === 'Analytics_Agent' || agentName === 'analytics') {
    return <AnalyticsCard data={data} />;
  }

  // Fallback: pretty print JSON
  return (
    <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
      <pre className="text-xs text-slate-200 whitespace-pre-wrap overflow-x-auto font-mono">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
};

export default FormattedAgentResult;

/**
 * User History Component with Advanced Filters
 * 
 * Displays user's previous research tasks with comprehensive filtering:
 * - Status filter
 * - Date range filter
 * - Ticker/company filter
 * - Full-screen mode with modern scrollbar
 */

import { useState, useEffect } from 'react';
import { apiClient, UserHistoryItem } from '../lib/api';

interface UserHistoryProps {
  onSelectTask?: (sessionId: string, planId: string) => void;
}

export function UserHistory({ onSelectTask }: UserHistoryProps) {
  const [history, setHistory] = useState<UserHistoryItem[]>([]);
  const [filteredHistory, setFilteredHistory] = useState<UserHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filter states
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [tickerFilter, setTickerFilter] = useState<string>('');
  const [dateRangeFilter, setDateRangeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  // UI states
  const [isFullScreen, setIsFullScreen] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [history, statusFilter, tickerFilter, dateRangeFilter, searchQuery]);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const items = await apiClient.getUserHistory(100); // Get more items for better filtering
      setHistory(items);
    } catch (err: any) {
      console.error('Failed to load history:', err);
      setError(err.message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...history];
    
    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(item => item.status === statusFilter);
    }
    
    // Ticker filter
    if (tickerFilter.trim()) {
      const ticker = tickerFilter.toUpperCase().trim();
      filtered = filtered.filter(item => 
        item.ticker?.toUpperCase().includes(ticker) ||
        item.objective.toUpperCase().includes(ticker)
      );
    }
    
    // Date range filter
    if (dateRangeFilter !== 'all') {
      const now = new Date();
      const filterDate = new Date();
      
      switch (dateRangeFilter) {
        case 'today':
          filterDate.setHours(0, 0, 0, 0);
          break;
        case 'week':
          filterDate.setDate(now.getDate() - 7);
          break;
        case 'month':
          filterDate.setMonth(now.getMonth() - 1);
          break;
        case '3months':
          filterDate.setMonth(now.getMonth() - 3);
          break;
      }
      
      filtered = filtered.filter(item => new Date(item.created_at) >= filterDate);
    }
    
    // Search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(item => 
        item.objective.toLowerCase().includes(query)
      );
    }
    
    setFilteredHistory(filtered);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-400 bg-green-900/30 border-green-700';
      case 'in_progress': return 'text-blue-400 bg-blue-900/30 border-blue-700';
      case 'failed': return 'text-red-400 bg-red-900/30 border-red-700';
      case 'cancelled': return 'text-slate-400 bg-slate-800 border-slate-600';
      default: return 'text-slate-400 bg-slate-800 border-slate-600';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    // Relative time for recent items
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    // Absolute time for older items
    return date.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  const clearAllFilters = () => {
    setStatusFilter('all');
    setTickerFilter('');
    setDateRangeFilter('all');
    setSearchQuery('');
  };

  const hasActiveFilters = statusFilter !== 'all' || tickerFilter !== '' || dateRangeFilter !== 'all' || searchQuery !== '';

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
        <span className="ml-3 text-slate-300">Loading history...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
        <p className="text-red-400">Error: {error}</p>
        <button onClick={loadHistory} className="mt-2 text-sm text-red-400 hover:text-red-300 underline">
          Retry
        </button>
      </div>
    );
  }

  const content = (
    <div className={`flex flex-col h-full ${isFullScreen ? 'fixed inset-0 z-50 bg-slate-900 p-6' : 'space-y-4'}`}>
      {/* Header */}
      <div className="space-y-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-100">Your Research History</h2>
          <div className="flex items-center gap-2">
            <button 
              onClick={loadHistory} 
              className="text-sm text-primary-400 hover:text-primary-300 font-medium transition-colors"
            >
              ↻ Refresh
            </button>
            <button
              onClick={() => setIsFullScreen(!isFullScreen)}
              className="text-sm text-slate-400 hover:text-slate-300 font-medium transition-colors"
              title={isFullScreen ? "Exit full screen" : "Enter full screen"}
            >
              {isFullScreen ? '⊗ Exit' : '⊕ Expand'}
            </button>
          </div>
        </div>

        {/* Filters Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Search */}
          <input
            type="text"
            placeholder="🔍 Search objectives..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-3 py-2 border border-slate-600 bg-slate-800 text-slate-100 placeholder-slate-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
          />
          
          {/* Ticker Filter */}
          <input
            type="text"
            placeholder="📊 Filter by ticker..."
            value={tickerFilter}
            onChange={(e) => setTickerFilter(e.target.value)}
            className="px-3 py-2 border border-slate-600 bg-slate-800 text-slate-100 placeholder-slate-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm uppercase"
          />
          
          {/* Date Range Filter */}
          <select
            value={dateRangeFilter}
            onChange={(e) => setDateRangeFilter(e.target.value)}
            className="px-3 py-2 border border-slate-600 bg-slate-800 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
          >
            <option value="all">📅 All Time</option>
            <option value="today">Today</option>
            <option value="week">Last 7 Days</option>
            <option value="month">Last 30 Days</option>
            <option value="3months">Last 3 Months</option>
          </select>
          
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-slate-600 bg-slate-800 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
          >
            <option value="all">All Status</option>
            <option value="completed">✓ Completed</option>
            <option value="in_progress">⟳ In Progress</option>
            <option value="failed">✗ Failed</option>
            <option value="cancelled">— Cancelled</option>
          </select>
        </div>

        {/* Filter Status Bar */}
        <div className="flex items-center justify-between text-xs">
          <p className="text-slate-400">
            Showing <span className="font-semibold text-slate-300">{filteredHistory.length}</span> of <span className="font-semibold text-slate-300">{history.length}</span> tasks
          </p>
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="text-primary-400 hover:text-primary-300 font-medium transition-colors"
            >
              Clear all filters
            </button>
          )}
        </div>
      </div>

      {/* Results List with Modern Scrollbar */}
      <div className="flex-1 overflow-hidden">
        {filteredHistory.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center p-8 text-slate-400 border border-dashed border-slate-600 rounded-lg">
              <p className="text-lg font-medium">
                {history.length === 0 ? "No Previous Tasks" : "No Matching Tasks"}
              </p>
              <p className="text-sm mt-2">
                {history.length === 0 ? "Your research history will appear here" : "Try adjusting your filters"}
              </p>
              {hasActiveFilters && (
                <button
                  onClick={clearAllFilters}
                  className="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto pr-2 space-y-3 custom-scrollbar">
            {filteredHistory.map((item) => (
              <div
                key={item.plan_id}
                className="border border-slate-700 bg-slate-800 rounded-lg p-4 hover:shadow-lg hover:shadow-primary-900/20 transition-all cursor-pointer hover:border-primary-600 hover:bg-slate-750"
                onClick={() => onSelectTask?.(item.session_id, item.plan_id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-slate-100 mb-2 line-clamp-2">{item.objective}</h3>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                      {item.ticker && (
                        <>
                          <span className="px-2 py-0.5 bg-slate-700 rounded text-slate-300 font-mono font-semibold">{item.ticker}</span>
                          <span>•</span>
                        </>
                      )}
                      <span>📅 {formatDate(item.created_at)}</span>
                      <span>•</span>
                      <span>🔢 {item.steps_count} steps</span>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium border whitespace-nowrap ${getStatusColor(item.status)}`}>
                    {item.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  return content;
}

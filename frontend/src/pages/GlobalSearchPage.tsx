import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, ExternalLink, Loader2, X, Sparkles, Building2, SlidersHorizontal } from 'lucide-react';
import { globalSearch, getChannels, getSearchSectors } from '../services/api';
import { Message, Channel } from '../types';

const DEFAULT_SECTORS = [
  'All Sectors',
  'Banking & Financial Services',
  'FinTech & Payments',
  'Cybersecurity',
  'Technology & Software',
  'Healthcare',
  'E-commerce',
  'Telecommunications',
  'Government',
  'Education',
  'Aviation',
  'Automotive',
  'Energy',
  'Defense',
  'Retail',
  'Logistics',
  'Other / General'
];

const SECTOR_ICONS: Record<string, string> = {
  'Banking & Financial Services': '🏦',
  'FinTech & Payments': '💳',
  'Cybersecurity': '🛡️',
  'Technology & Software': '💻',
  'Healthcare': '🏥',
  'E-commerce': '🛒',
  'Telecommunications': '📡',
  'Government': '🏛️',
  'Education': '🎓',
  'Aviation': '✈️',
  'Automotive': '🚗',
  'Energy': '⚡',
  'Defense': '🪖',
  'Retail': '🛍️',
  'Logistics': '🚚',
  'Other / General': '🌐',
  'All Sectors': '🔍'
};

function ConfidenceBadge({ score, level }: { score?: number; level?: string }) {
  if (score === undefined && !level) return null;
  const numScore = score ?? 0;
  let bg = 'bg-slate-100 text-slate-700 border-slate-200';
  let dotBg = 'bg-slate-400';

  if (numScore >= 75 || level === 'HIGH') {
    bg = 'bg-emerald-50 text-emerald-800 border-emerald-300';
    dotBg = 'bg-emerald-500';
  } else if (numScore >= 50 || level === 'MEDIUM') {
    bg = 'bg-amber-50 text-amber-800 border-amber-300';
    dotBg = 'bg-amber-500';
  } else {
    bg = 'bg-slate-100 text-slate-600 border-slate-300';
    dotBg = 'bg-slate-400';
  }

  return (
    <span 
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-extrabold border ${bg} shadow-xs`}
      title={`Confidence Score: ${numScore}%`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotBg}`}></span>
      <span>{numScore}%</span>
      <span className="text-[10px] font-semibold opacity-85">({level || (numScore >= 75 ? 'HIGH' : numScore >= 50 ? 'MED' : 'LOW')})</span>
    </span>
  );
}

function highlightText(text: string, query: string): React.ReactNode {
  if (!query || !query.trim()) return text;
  
  const patternStr = query.trim().replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
  const splitRegex = new RegExp(`(${patternStr})`, 'gi');
  const matchRegex = new RegExp(`^(${patternStr})$`, 'i');
  
  const parts = text.split(splitRegex);
  return (
    <>
      {parts.map((part, index) => 
        matchRegex.test(part) 
          ? <mark key={index} className="bg-yellow-300 text-slate-900 rounded-sm px-0.5">{part}</mark> 
          : part
      )}
    </>
  );
}

function formatDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

export const GlobalSearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [selectedSector, setSelectedSector] = useState<string>('All Sectors');
  const [sectors, setSectors] = useState<string[]>(DEFAULT_SECTORS);
  const [minConfidenceFilter, setMinConfidenceFilter] = useState<number>(0);
  const [results, setResults] = useState<Message[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [sectorStats, setSectorStats] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');
  
  // Pagination & Infinite Scroll States
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const observerTarget = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getChannels().then(setChannels).catch(console.error);
    getSearchSectors().then(loaded => {
      if (loaded && loaded.length > 0) {
        setSectors(loaded);
      }
    }).catch(console.error);
  }, []);

  const getChannelName = useCallback((msg: Message) => {
    const matched = channels.find(c => c.id === msg.channel_id);
    if (matched) return matched.title;
    if (msg.channel_username && !msg.channel_username.startsWith('-') && !/^\d+$/.test(msg.channel_username)) {
      return msg.channel_username;
    }
    return msg.channel_id;
  }, [channels]);

  const doSearch = useCallback(async (
    q: string, 
    sec: string, 
    minConf?: number
  ) => {
    if (!q.trim()) {
      setResults([]);
      setSectorStats({});
      setSearched(false);
      setPage(1);
      setHasMore(false);
      return;
    }
    setLoading(true);
    setError('');
    setPage(1);
    try {
      const data = await globalSearch(
        q.trim(), 
        undefined, 
        false, 
        1, 
        50,
        sec === 'All Sectors' ? undefined : sec,
        minConf && minConf > 0 ? minConf : undefined
      );
      setResults(data.results);
      setHasMore(data.has_more);
      setSectorStats(data.sector_stats || {});
      setSearched(true);
    } catch (e) {
      setError('Search failed. Please ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  const triggerManualSearch = () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    doSearch(query, selectedSector, minConfidenceFilter);
  };

  const loadNextPage = useCallback(async () => {
    if (!query.trim() || !hasMore || loadingMore || loading) return;
    setLoadingMore(true);
    const nextPage = page + 1;
    try {
      const data = await globalSearch(
        query.trim(), 
        undefined, 
        false, 
        nextPage, 
        50,
        selectedSector === 'All Sectors' ? undefined : selectedSector,
        minConfidenceFilter > 0 ? minConfidenceFilter : undefined
      );
      setResults(prev => [...prev, ...data.results]);
      setHasMore(data.has_more);
      setPage(nextPage);
    } catch (e) {
      console.error("Failed to load more results:", e);
    } finally {
      setLoadingMore(false);
    }
  }, [query, selectedSector, minConfidenceFilter, page, hasMore, loading, loadingMore]);

  // Set up intersection observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !loading && !loadingMore) {
          loadNextPage();
        }
      },
      { threshold: 0.1 }
    );
    
    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }
    
    return () => observer.disconnect();
  }, [hasMore, loading, loadingMore, loadNextPage]);

  // Debounce search when query, selectedSector, minConfidenceFilter changes
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      doSearch(query, selectedSector, minConfidenceFilter);
    }, 400);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, selectedSector, minConfidenceFilter, doSearch]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setSectorStats({});
    setSearched(false);
    setPage(1);
    setHasMore(false);
    inputRef.current?.focus();
  };

  // Group results by channel for the stats bar
  const channelCounts = results.reduce((acc, m) => {
    const name = getChannelName(m);
    acc[name] = (acc[name] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="min-h-full bg-slate-50 p-6 space-y-6">
      {/* Page Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
          <Search className="w-6 h-6 text-blue-600" />
          Global Message Search & Sector Intelligence
        </h1>
        <p className="text-sm text-slate-500">
          Contextual sector-aware keyword search with confidence scoring across <span className="font-semibold text-slate-700">all monitored channels</span>.
        </p>
      </div>

      {/* Search Bar & Sector Filter Box */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5 space-y-4">
        {/* Main Search Controls */}
        <div className="flex flex-col md:flex-row items-stretch gap-3">
          {/* Query Input */}
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
            <input
              ref={inputRef}
              id="global-search-input"
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') triggerManualSearch(); }}
              placeholder="Search keywords (e.g. 'bank', 'credentials', 'CVE-2024')…"
              className="w-full pl-12 pr-12 py-3 rounded-xl border border-slate-300 bg-slate-50 text-slate-900 text-sm font-medium placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
            />
            {query && (
              <button
                onClick={clearSearch}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition"
                title="Clear input"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Sector Filter Dropdown */}
          <div className="md:w-80 flex flex-col justify-center">
            <div className="relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-base pointer-events-none select-none">
                {SECTOR_ICONS[selectedSector] || '🌐'}
              </div>
              <select
                id="sector-filter-select"
                value={selectedSector}
                onChange={e => setSelectedSector(e.target.value)}
                className="w-full pl-9 pr-8 py-3 rounded-xl border border-slate-300 bg-slate-50 text-slate-800 text-xs font-bold focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer hover:bg-slate-100 transition shadow-xs"
              >
                {sectors.map(sec => (
                  <option key={sec} value={sec}>
                    {sec === 'All Sectors' ? '🔍 All Sectors (General)' : `${SECTOR_ICONS[sec] || '🏷️'} ${sec}`}
                  </option>
                ))}
              </select>
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 text-xs">
                ▼
              </div>
            </div>
          </div>

          {/* Search Button */}
          <button
            id="global-search-button"
            onClick={triggerManualSearch}
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold text-xs rounded-xl shadow transition flex items-center justify-center gap-2 shrink-0 cursor-pointer"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Search</span>
          </button>
        </div>

        {/* Secondary Filter Row: Confidence threshold */}
        <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-100">
          {/* Confidence Threshold Pills */}
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="text-xs text-slate-500 font-medium">Confidence:</span>
            <div className="flex items-center gap-1">
              {[
                { label: 'All', val: 0 },
                { label: '≥ 50% (Med)', val: 50 },
                { label: '≥ 75% (High)', val: 75 }
              ].map(opt => (
                <button
                  key={opt.val}
                  onClick={() => setMinConfidenceFilter(opt.val)}
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border transition ${
                    minConfidenceFilter === opt.val
                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                      : 'bg-white text-slate-600 border-slate-200 hover:border-emerald-400 hover:text-emerald-700'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Loading Indicator */}
      {loading && (
        <div className="flex items-center justify-center gap-3 py-10 text-slate-500">
          <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
          <span className="text-sm font-medium">Running context-aware search across all channels…</span>
        </div>
      )}

      {/* Error Banner */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 font-medium">
          {error}
        </div>
      )}

      {/* Stats bar */}
      {!loading && searched && results.length > 0 && (
        <div className="space-y-3">
          {/* Quick Summary Banner */}
          <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-slate-800 text-white p-4 rounded-xl shadow-md border border-blue-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="text-xs opacity-80 font-semibold uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-yellow-300" />
                Sector-Aware Context Search Results
              </div>
              <div className="text-sm font-bold">
                Found <span className="underline underline-offset-4 decoration-2 decoration-white">{results.length} contextual matches</span> across{' '}
                <span className="underline underline-offset-4 decoration-2 decoration-white">
                  {Object.keys(channelCounts).length} channel{Object.keys(channelCounts).length !== 1 ? 's' : ''}
                </span>{' '}
                for filter: <span className="bg-white/20 px-2 py-0.5 rounded text-xs">{selectedSector}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] bg-white/15 px-2.5 py-1 rounded-md font-mono border border-white/20">
                Confidence Scoring Active
              </span>
            </div>
          </div>

          {/* Sector Breakdown Pills (Clickable to switch sector) */}
          {Object.keys(sectorStats).length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-600 bg-white p-3 rounded-xl border border-slate-200">
              <span className="text-slate-500 flex items-center gap-1">
                <Building2 className="w-3.5 h-3.5" />
                Sector Breakdown:
              </span>
              {Object.entries(sectorStats).map(([sec, count]) => (
                <button
                  key={sec}
                  onClick={() => setSelectedSector(sec)}
                  className={`border text-[11px] font-bold px-2.5 py-1 rounded-lg shadow-2xs transition flex items-center gap-1.5 ${
                    selectedSector === sec
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-slate-50 hover:bg-blue-50 border-slate-200 text-slate-700 hover:text-blue-700'
                  }`}
                  title={`Filter by ${sec}`}
                >
                  <span>{SECTOR_ICONS[sec] || '🏷️'}</span>
                  <span>{sec}</span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${selectedSector === sec ? 'bg-blue-700 text-white' : 'bg-slate-200 text-blue-700'}`}>
                    {count}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Breakdown by Channels */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-600">
            <span className="text-slate-500">Channels:</span>
            {Object.entries(channelCounts).slice(0, 8).map(([name, count]) => (
              <div key={name} className="bg-white border border-slate-200 text-slate-700 text-[11px] font-bold px-2.5 py-1 rounded-lg shadow-2xs">
                {name} <span className="ml-1 bg-slate-100 text-blue-600 px-1.5 py-0.5 rounded text-[10px]">{count}</span>
              </div>
            ))}
            {Object.keys(channelCounts).length > 8 && (
              <div className="text-[11px] text-slate-400 font-bold bg-slate-100 px-2.5 py-1 rounded-lg">
                +{Object.keys(channelCounts).length - 8} more channels
              </div>
            )}
          </div>
        </div>
      )}

      {/* Results Table */}
      {!loading && searched && results.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="bg-slate-100 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wide">
                  <th className="px-4 py-3 w-32">Date</th>
                  <th className="px-4 py-3 w-40">Channel / Sender</th>
                  <th className="px-4 py-3 w-56">Sector & Confidence</th>
                  <th className="px-4 py-3">Matched Message</th>
                  <th className="px-4 py-3 w-12 text-center">Open</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {results.map((msg, idx) => (
                  <tr
                    key={msg.id || idx}
                    onClick={() => window.open(`/channel/${msg.channel_id}?highlight=${msg.id}`, '_blank')}
                    className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                  >
                    {/* Date */}
                    <td className="px-4 py-3 align-top">
                      <div className="text-slate-500 text-xs whitespace-nowrap font-medium">
                        {formatDate(msg.date)}
                      </div>
                    </td>

                    {/* Channel & Sender */}
                    <td className="px-4 py-3 space-y-1 align-top">
                      <div className="font-bold text-slate-800 truncate max-w-[150px]" title={getChannelName(msg)}>
                        {getChannelName(msg)}
                      </div>
                      <div className="text-slate-500 text-xs truncate max-w-[130px]" title={msg.sender || 'Anonymous'}>
                        👤 {highlightText(msg.sender || 'Anonymous', query)}
                      </div>
                    </td>

                    {/* Sector & Confidence Column */}
                    <td className="px-4 py-3 space-y-1.5 align-top">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <ConfidenceBadge score={msg.confidence_score} level={msg.confidence_level} />
                        <span 
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200"
                          title={`Sector: ${msg.detected_sector || 'General'}`}
                        >
                          <span>{SECTOR_ICONS[msg.detected_sector || ''] || '🏷️'}</span>
                          <span className="truncate max-w-[120px]">{msg.detected_sector || 'General'}</span>
                        </span>
                      </div>

                      {/* Matched Context Keywords */}
                      {msg.matched_context_keywords && msg.matched_context_keywords.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1 pt-0.5">
                          {msg.matched_context_keywords.slice(0, 3).map((kw, i) => (
                            <span key={i} className="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono border border-slate-200">
                              #{kw}
                            </span>
                          ))}
                          {msg.matched_context_keywords.length > 3 && (
                            <span className="text-[9px] text-slate-400 font-mono">
                              +{msg.matched_context_keywords.length - 3}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Reason snippet */}
                      {msg.relevance_reason && (
                        <div className="text-[10px] text-slate-500 leading-tight line-clamp-1 italic" title={msg.relevance_reason}>
                          {msg.relevance_reason}
                        </div>
                      )}
                    </td>

                    {/* Message text with highlight */}
                    <td className="px-4 py-3 align-top max-w-[500px]">
                      <p className="text-slate-800 text-xs leading-relaxed line-clamp-4 break-words font-normal">
                        {highlightText(msg.text || '(no text)', query)}
                      </p>
                    </td>

                    {/* Open channel link */}
                    <td className="px-4 py-3 text-center align-top">
                      <button
                        title="Open message in channel"
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(`/channel/${msg.channel_id}?highlight=${msg.id}`, '_blank');
                        }}
                        className="opacity-60 group-hover:opacity-100 transition p-1.5 rounded-lg hover:bg-blue-50 text-slate-400 hover:text-blue-600"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Scroll Target for Infinite Scroll */}
          <div ref={observerTarget} className="py-6 flex justify-center border-t border-slate-100 bg-slate-50/30">
            {loadingMore ? (
              <div className="flex items-center gap-2 text-slate-500 text-xs font-semibold">
                <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                <span>Loading more contextual results...</span>
              </div>
            ) : hasMore ? (
              <span className="text-slate-400 text-xs font-medium animate-pulse">Scroll down to load more</span>
            ) : (
              <span className="text-slate-400 text-xs font-medium">All matching results loaded</span>
            )}
          </div>
        </div>
      )}

      {/* Empty state — no results */}
      {!loading && searched && results.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center space-y-3">
          <Search className="w-10 h-10 text-slate-300 mx-auto" />
          <p className="text-slate-700 font-semibold text-base">No contextually matching messages found</p>
          <p className="text-slate-400 text-sm max-w-lg mx-auto">
            No messages matched <span className="font-medium text-slate-600">"{query}"</span> in sector{' '}
            <span className="font-semibold text-slate-600">{selectedSector}</span>
            {minConfidenceFilter > 0 ? ` with confidence ≥ ${minConfidenceFilter}%` : ''}.
          </p>
          <div className="pt-2">
            <button
              onClick={() => { setSelectedSector('All Sectors'); setMinConfidenceFilter(0); }}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold underline"
            >
              Reset to "All Sectors" & Any Confidence
            </button>
          </div>
        </div>
      )}

      {/* Initial state — not searched yet */}
      {!loading && !searched && (
        <div className="bg-white border border-dashed border-slate-300 rounded-2xl p-12 text-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center mx-auto">
            <Search className="w-7 h-7 text-blue-500" />
          </div>
          <p className="text-slate-700 font-semibold text-base">Sector-Aware Context Search</p>
          <p className="text-slate-400 text-sm max-w-md mx-auto">
            Select a target sector or keep <span className="font-medium text-slate-600">All Sectors</span> to filter out false positives and view confidence-scored findings.
          </p>
          <div className="flex flex-wrap justify-center gap-2 pt-2">
            {[
              { q: 'bank', s: 'Banking & Financial Services' },
              { q: 'credentials', s: 'Cybersecurity' },
              { q: 'payment gateway', s: 'FinTech & Payments' },
              { q: 'patient records', s: 'Healthcare' },
              { q: 'CVE-2024', s: 'Technology & Software' }
            ].map(hint => (
              <button
                key={hint.q}
                onClick={() => {
                  setQuery(hint.q);
                  setSelectedSector(hint.s);
                }}
                className="px-3 py-1.5 bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-600 text-xs font-semibold rounded-full border border-slate-200 hover:border-blue-300 transition flex items-center gap-1.5"
              >
                <span>{SECTOR_ICONS[hint.s] || '🔍'}</span>
                <span>"{hint.q}" in {hint.s}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GlobalSearchPage;

import React, { useState, useEffect, useMemo } from 'react';
import { 
  Calendar as CalendarIcon, ChevronLeft, ChevronRight, MessageSquare, 
  Sparkles, Filter, RotateCcw, ArrowRight
} from 'lucide-react';
import { getDailyMessageStats } from '../services/api';
import { DailyStatsResponse, DailyStatItem, Channel } from '../types';

interface ScrapeCalendarProps {
  channelId?: string;
  channels?: Channel[];
  selectedDate?: string | null;
  onSelectDate?: (dateStr: string | null) => void;
  className?: string;
}

export const ScrapeCalendar: React.FC<ScrapeCalendarProps> = ({
  channelId,
  channels = [],
  selectedDate,
  onSelectDate,
  className = '',
}) => {
  const [statsData, setStatsData] = useState<DailyStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentChannelId, setCurrentChannelId] = useState<string>(channelId || '');
  
  // Current visible calendar month/year
  const [viewDate, setViewDate] = useState<Date>(() => new Date());
  const [internalSelectedDate, setInternalSelectedDate] = useState<string | null>(selectedDate || null);

  useEffect(() => {
    if (channelId !== undefined) {
      setCurrentChannelId(channelId);
    }
  }, [channelId]);

  useEffect(() => {
    if (selectedDate !== undefined) {
      setInternalSelectedDate(selectedDate);
    }
  }, [selectedDate]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await getDailyMessageStats(currentChannelId || undefined, 180);
      setStatsData(data);
    } catch (err) {
      console.error('Failed to fetch daily scrape stats:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [currentChannelId]);

  const statsMap = useMemo(() => {
    const map: Record<string, DailyStatItem> = {};
    if (statsData?.daily_stats) {
      for (const item of statsData.daily_stats) {
        map[item.date] = item;
      }
    }
    return map;
  }, [statsData]);

  // Calendar calculations
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const monthName = viewDate.toLocaleString('default', { month: 'short' });

  const calendarDays = useMemo(() => {
    const firstDayIndex = new Date(year, month, 1).getDay();
    const totalDaysInMonth = new Date(year, month + 1, 0).getDate();
    const prevMonthDays = new Date(year, month, 0).getDate();

    const days: Array<{
      dayNum: number;
      dateKey: string;
      isCurrentMonth: boolean;
      stat?: DailyStatItem;
      isToday: boolean;
      isSelected: boolean;
    }> = [];

    const todayStr = statsData?.today_date || new Date().toISOString().substring(0, 10);

    // Prev month padding
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const d = prevMonthDays - i;
      const prevM = month === 0 ? 12 : month;
      const prevY = month === 0 ? year - 1 : year;
      const dateKey = `${prevY}-${String(prevM).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({
        dayNum: d,
        dateKey,
        isCurrentMonth: false,
        stat: statsMap[dateKey],
        isToday: dateKey === todayStr,
        isSelected: dateKey === internalSelectedDate,
      });
    }

    // Current month days
    for (let d = 1; d <= totalDaysInMonth; d++) {
      const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({
        dayNum: d,
        dateKey,
        isCurrentMonth: true,
        stat: statsMap[dateKey],
        isToday: dateKey === todayStr,
        isSelected: dateKey === internalSelectedDate,
      });
    }

    // Next month padding to fill grid
    const remaining = 35 - days.length > 0 ? 35 - days.length : 42 - days.length;
    for (let d = 1; d <= remaining; d++) {
      const nextM = month === 11 ? 1 : month + 2;
      const nextY = month === 11 ? year + 1 : year;
      const dateKey = `${nextY}-${String(nextM).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({
        dayNum: d,
        dateKey,
        isCurrentMonth: false,
        stat: statsMap[dateKey],
        isToday: dateKey === todayStr,
        isSelected: dateKey === internalSelectedDate,
      });
    }

    return days;
  }, [year, month, statsMap, statsData, internalSelectedDate]);

  const handlePrevMonth = () => {
    setViewDate(new Date(year, month - 1, 1));
  };

  const handleNextMonth = () => {
    setViewDate(new Date(year, month + 1, 1));
  };

  const handleSelectDay = (dateKey: string) => {
    if (internalSelectedDate === dateKey) {
      setInternalSelectedDate(null);
      if (onSelectDate) onSelectDate(null);
    } else {
      setInternalSelectedDate(dateKey);
      if (onSelectDate) onSelectDate(dateKey);
    }
  };

  const selectedDayStat = useMemo(() => {
    if (!internalSelectedDate) return null;
    return statsMap[internalSelectedDate] || {
      date: internalSelectedDate,
      formatted_date: internalSelectedDate,
      display_day: internalSelectedDate,
      count: 0,
      channel_count: 0,
      threat_levels: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 },
      top_channels: [],
    };
  }, [internalSelectedDate, statsMap]);

  return (
    <div className={`glass-card p-4 rounded-xl border border-darkBorder bg-white shadow-sm ${className}`}>
      
      {/* 1. Header Bar: Compact & Informative */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 shadow-sm">
            <CalendarIcon className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800 leading-tight">
              Scraped Messages Calendar
            </h3>
            <span className="text-[11px] text-slate-500">
              Date-wise scraping history & daily counts
            </span>
          </div>
        </div>

        {/* Right Badges: Today's Messages Highlight + Channel Filter */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          {/* Today Count Badge */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span>Today ({statsData?.today_formatted ? statsData.today_formatted.replace(/\s*\d{4}$/, '') : 'Today'}):</span>
            <span className="font-mono text-emerald-800 text-sm font-black">
              {statsData ? statsData.today_count.toLocaleString() : 0} msgs
            </span>
          </div>

          {/* Yesterday Count Badge */}
          <div className="hidden md:flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-50 text-slate-600 border border-slate-200 text-xs font-semibold">
            <span className="text-slate-400">Yesterday:</span>
            <span className="font-mono font-bold text-slate-700">
              {statsData ? statsData.yesterday_count.toLocaleString() : 0}
            </span>
          </div>

          {/* Channel Filter (if channels provided) */}
          {channels.length > 0 && (
            <div className="flex items-center gap-1">
              <Filter className="w-3 h-3 text-slate-400" />
              <select
                value={currentChannelId}
                onChange={(e) => setCurrentChannelId(e.target.value)}
                className="text-xs py-1 px-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 font-semibold focus:outline-none cursor-pointer max-w-[140px] truncate"
              >
                <option value="">All Channels</option>
                {channels.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* 2. Main Body: Small Monthly Calendar Grid (Left) + Sorted Date-Wise List (Right) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 pt-3 items-start">
        
        {/* Left Side (5 cols): Small Month Calendar Grid */}
        <div className="md:col-span-5 bg-slate-50/60 p-3 rounded-xl border border-slate-100 flex flex-col justify-between">
          
          {/* Mini Month Nav */}
          <div className="flex items-center justify-between pb-2 mb-1 border-b border-slate-200/60 text-xs font-bold text-slate-700">
            <span className="tracking-wide text-slate-800">
              {monthName} {year}
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => {
                  const now = new Date();
                  setViewDate(now);
                  const todayStr = statsData?.today_date || now.toISOString().substring(0, 10);
                  handleSelectDay(todayStr);
                }}
                className="px-2 py-0.5 text-[10px] font-bold text-blue-700 hover:bg-blue-100/60 rounded transition-colors"
              >
                Today
              </button>
              <button
                type="button"
                onClick={handlePrevMonth}
                className="p-1 hover:bg-slate-200/60 rounded text-slate-600 transition-colors"
                title="Prev Month"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleNextMonth}
                className="p-1 hover:bg-slate-200/60 rounded text-slate-600 transition-colors"
                title="Next Month"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Weekday Labels */}
          <div className="grid grid-cols-7 gap-1 text-center py-1 text-[10px] font-bold text-slate-400">
            <span>S</span>
            <span>M</span>
            <span>T</span>
            <span>W</span>
            <span>T</span>
            <span>F</span>
            <span>S</span>
          </div>

          {/* Mini Day Cells */}
          <div className="grid grid-cols-7 gap-1 pt-1">
            {calendarDays.map((cell, idx) => {
              const count = cell.stat?.count || 0;
              const hasActivity = count > 0;
              const isSelected = cell.dateKey === internalSelectedDate;

              return (
                <button
                  key={`${cell.dateKey}-${idx}`}
                  type="button"
                  onClick={() => handleSelectDay(cell.dateKey)}
                  title={`${cell.dateKey}: ${count} messages`}
                  className={`relative flex flex-col items-center justify-center h-8 rounded-lg text-xs font-semibold transition-all ${
                    isSelected
                      ? 'bg-blue-600 text-white font-bold ring-2 ring-blue-400 shadow-sm'
                      : cell.isToday
                      ? 'border border-blue-500 text-blue-700 bg-blue-50/60 font-bold'
                      : hasActivity
                      ? 'bg-blue-50 text-blue-800 font-bold hover:bg-blue-100 border border-blue-200/60'
                      : cell.isCurrentMonth
                      ? 'text-slate-600 hover:bg-slate-200/40'
                      : 'text-slate-300 opacity-40'
                  }`}
                >
                  <span className="leading-none text-[11px]">{cell.dayNum}</span>
                  {hasActivity && !isSelected && (
                    <span className="w-1 h-1 rounded-full bg-blue-600 mt-0.5" />
                  )}
                </button>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-400 pt-2.5 mt-2 border-t border-slate-200/60">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-600 inline-block" />
              <span>Days with scraped messages</span>
            </span>
            <span>Click any day to filter</span>
          </div>
        </div>

        {/* Right Side (7 cols): Sorted Date-Wise Message Count Breakdown */}
        <div className="md:col-span-7 flex flex-col justify-between">
          
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
              <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
              <span>Sorted Date-Wise Breakdown</span>
            </div>
            <span className="text-[11px] text-slate-400 font-medium">
              Showing latest {statsData?.daily_stats?.length || 0} active days
            </span>
          </div>

          {/* Sorted Date Items List */}
          <div className="space-y-1.5 pt-2 max-h-56 overflow-y-auto pr-1">
            {statsData?.daily_stats && statsData.daily_stats.length > 0 ? (
              statsData.daily_stats.map((item) => {
                const isSelected = item.date === internalSelectedDate;
                const isToday = item.date === statsData.today_date;

                return (
                  <div
                    key={item.date}
                    onClick={() => {
                      handleSelectDay(item.date);
                      const [y, m] = item.date.split('-').map(Number);
                      setViewDate(new Date(y, m - 1, 1));
                    }}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-blue-50 border-blue-400 text-blue-900 shadow-sm'
                        : isToday
                        ? 'bg-emerald-50/50 border-emerald-200 hover:bg-emerald-50'
                        : 'bg-white hover:bg-slate-50 border-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-bold ${
                          isSelected ? 'text-blue-700' : isToday ? 'text-emerald-700' : 'text-slate-800'
                        }`}
                      >
                        {item.display_day}
                      </span>
                      {isToday && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-100 text-emerald-700">
                          Today
                        </span>
                      )}
                      <span className="text-[10px] text-slate-400 font-medium hidden sm:inline">
                        ({item.channel_count} {item.channel_count === 1 ? 'channel' : 'channels'})
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-black text-blue-600 bg-blue-50/80 px-2 py-0.5 rounded border border-blue-200/50">
                        {item.count.toLocaleString()} msgs
                      </span>
                      <ArrowRight className={`w-3 h-3 transition-transform ${isSelected ? 'text-blue-600 translate-x-0.5' : 'text-slate-300'}`} />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="py-8 text-center text-xs text-slate-400 italic">
                {loading ? 'Loading daily stats...' : 'No daily message records found.'}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* 3. Selected Date Status Bar (if any date selected) */}
      {internalSelectedDate && (
        <div className="flex items-center justify-between px-3 py-2 mt-3 bg-blue-50/70 border border-blue-200 rounded-lg text-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-blue-800">
              Selected: {selectedDayStat?.formatted_date || internalSelectedDate}
            </span>
            <span>•</span>
            <span className="font-mono font-bold text-blue-700">
              {selectedDayStat ? selectedDayStat.count.toLocaleString() : 0} messages scraped
            </span>
            {selectedDayStat?.top_channels && selectedDayStat.top_channels.length > 0 && (
              <span className="text-[11px] text-slate-500 hidden sm:inline">
                ({selectedDayStat.top_channels.map(c => `${c.title}: ${c.count}`).slice(0, 2).join(', ')})
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={() => handleSelectDay(internalSelectedDate)}
            className="text-slate-400 hover:text-slate-700 p-0.5 rounded hover:bg-slate-200 transition-colors"
            title="Clear date selection"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

    </div>
  );
};

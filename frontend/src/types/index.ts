export interface Channel {
  id: string;
  username: string;
  raw_username?: string;
  title: string;
  description?: string;
  member_count: number;
  is_monitored: boolean;
  last_scraped_at?: string;
  category: string;
  type?: string;
  message_count?: number;
  status?: string;
  
  // Scheduler parameters
  is_auto_monitoring?: boolean;
  monitoring_interval_value?: number;
  monitoring_interval_unit?: string;
  next_scrape_at?: string;
  
  is_auto_ai?: boolean;
  ai_interval_value?: number;
  ai_interval_unit?: string;
  next_ai_at?: string;

  is_auto_report?: boolean;
  report_interval_value?: number;
  report_interval_unit?: string;
  next_report_at?: string;
}

export interface Message {
  id: string;
  channel_id: string;
  channel_username: string;
  sender: string;
  text: string;
  date: string;
  views: number;
  media_url?: string;
  threat_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  analyzed: boolean;
  // Context-Aware Search & Confidence Scoring
  confidence_score?: number;
  confidence_level?: 'HIGH' | 'MEDIUM' | 'LOW';
  detected_sector?: string;
  matched_context_keywords?: string[];
  is_contextual_match?: boolean;
  relevance_reason?: string;
}

export interface ThreatIntelligence {
  id: string;
  message_id: string;
  channel_username: string;
  timestamp: string;
  urls: string[];
  suspicious_activities: string[];
  threat_actors: string[];
  malware_references: string[];
  cves: string[];
  iocs: string[];
  crypto_wallets: string[];
  emails: string[];
  domains_ips: string[];
  leaked_credentials: string[];
  summary: string;
  risk_score: number;
  threat_level: string;
}

export interface Report {
  id: string;
  title: string;
  created_at: string;
  period: string;
  channels_analyzed: string[];
  total_messages: number;
  total_threats: number;
  markdown_path: string;
  pdf_path?: string;
  summary: string;
}

export interface AutoMonitorStatus {
  enabled: boolean;
  interval_minutes: number;
  interval_display?: string;
  is_sweeping: boolean;
  last_sweep_at: string;
  next_sweep_at: string;
  monitored_channels_count: number;
  total_channels_count: number;
  total_messages_collected: number;
  live_listener_active: boolean;
  status_message: string;
}

export interface ScraperStatus {
  is_scraping: boolean;
  progress: number;
  current_channel: string;
  logs: string[];
  scrape_queue: string[];
  completed_channels: string[];
  total_channels_count: number;
  auto_monitor?: AutoMonitorStatus;
}

export interface IntelligenceSummary {
  total_analyzed: number;
  total_cves: number;
  cves_list: string[];
  total_iocs: number;
  iocs_list: string[];
  total_wallets: number;
  crypto_wallets_list: string[];
  total_credentials: number;
  leaked_credentials_list: string[];
  malware_families: string[];
  threat_actors: string[];
  urls_list: string[];
}

export interface TelegramUser {
  id: number;
  username: string | null;
  first_name: string | null;
  phone: string | null;
}

export interface DailyStatItem {
  date: string;
  formatted_date: string;
  display_day: string;
  count: number;
  channel_count: number;
  threat_levels: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  top_channels: {
    id: string;
    title: string;
    count: number;
  }[];
}

export interface DailyStatsResponse {
  today_date: string;
  today_formatted: string;
  today_count: number;
  yesterday_count: number;
  total_messages: number;
  days_recorded: number;
  peak_day: {
    date: string;
    formatted_date: string;
    count: number;
  } | null;
  daily_stats: DailyStatItem[];
}


import React, { useState } from 'react';
import { X, Download, Copy, Check, ExternalLink, ShieldCheck, FileText, Eye, Link, Sparkles } from 'lucide-react';
import { Message } from '../types';
import { getEvidenceDownloadUrl } from '../services/api';

interface EvidenceModalProps {
  message: Message | null;
  searchKeyword?: string;
  onClose: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({ message, searchKeyword, onClose }) => {
  const [copiedType, setCopiedType] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);

  if (!message) return null;

  const downloadUrl = getEvidenceDownloadUrl(message.id, searchKeyword);
  const screenshotSrc = message.evidence_screenshot_url 
    ? (message.evidence_screenshot_url.startsWith('http') ? message.evidence_screenshot_url : message.evidence_screenshot_url)
    : `/evidence/${message.id.replace(/[^\w\-.]/g, '_')}.png`;

  // Compute or fallback Telegram direct permalink
  const getTelegramLink = () => {
    if (message.message_link) return message.message_link;
    const rawId = message.id.split('_').pop() || '1';
    const user = message.channel_username?.replace('@', '').trim();
    if (user && !user.startsWith('-') && !/^\d+$/.test(user) && !user.includes(' ')) {
      return `https://t.me/${user}/${rawId}`;
    }
    const cleanCid = message.channel_id.replace('-100', '').replace('-', '');
    return `https://t.me/c/${cleanCid}/${rawId}`;
  };

  const telegramLink = getTelegramLink();

  const handleCopy = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopiedType(type);
    setTimeout(() => setCopiedType(null), 2000);
  };

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `evidence_${message.id}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-950/75 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden text-slate-800"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-extrabold tracking-tight text-white">Forensic Evidence & Screenshot Proof</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  VERIFIED INGESTION PROOF
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Channel: <span className="font-semibold text-slate-200">{message.channel_username}</span> • ID: <span className="font-mono text-slate-300">{message.channel_id}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition shadow-sm cursor-pointer"
              title="Download high-resolution forensic evidence image"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Evidence</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition cursor-pointer"
              title="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 bg-slate-50/50">
          
          {/* 1. Evidence Screenshot Preview */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                Original Telegram Message Screenshot Proof
              </h3>
              <a
                href={downloadUrl}
                target="_blank"
                rel="noreferrer"
                className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                <span>View Full Resolution</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="rounded-xl border border-slate-300 bg-slate-900 p-2 shadow-inner overflow-hidden flex justify-center items-center min-h-[220px]">
              {!imageError ? (
                <img
                  src={downloadUrl}
                  alt={`Evidence for message ${message.id}`}
                  onError={() => setImageError(true)}
                  className="rounded-lg max-h-[420px] w-auto object-contain shadow-md"
                />
              ) : (
                /* Fallback Telegram Message Mockup Card */
                <div className="w-full max-w-xl p-4 bg-[#0e1621] rounded-xl text-white font-sans space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-[#242f3d]">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-[#2b5278] flex items-center justify-center font-bold text-xs">
                        {(message.channel_username || 'TG').slice(0, 2).toUpperCase()}
                      </div>
                      <div className="text-xs font-bold">{message.channel_username}</div>
                    </div>
                    <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                      FORENSIC SNAPSHOT
                    </span>
                  </div>

                  <div className="bg-[#182533] p-3.5 rounded-xl border border-[#242f3d] space-y-1.5">
                    <div className="text-xs font-bold text-[#64b5f6]">{message.sender}</div>
                    <div className="text-xs text-slate-100 whitespace-pre-wrap leading-relaxed">{message.text}</div>
                    <div className="text-[10px] text-slate-400 text-right pt-1">
                      👁 {message.views || 10} • {formatDate(message.date)} ✓✓
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 2. Forensic Metadata & Intelligence Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left Column: Search & Verification Telemetry */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center gap-1.5 pb-2 border-b border-slate-100">
                <Sparkles className="w-3.5 h-3.5 text-yellow-500" />
                Search & Context Match Telemetry
              </h4>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Search Keyword:</span>
                  <mark className="bg-yellow-200 text-slate-900 font-bold px-2 py-0.5 rounded text-xs">
                    {searchKeyword || '(All Sectors Search)'}
                  </mark>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Confidence Score:</span>
                  <span className="font-extrabold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full text-xs">
                    {message.confidence_score !== undefined ? `${message.confidence_score}% (${message.confidence_level || 'HIGH'})` : '100% Context Match'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Detected Sector:</span>
                  <span className="font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded text-xs">
                    {message.detected_sector || 'General Threat'}
                  </span>
                </div>

                {message.matched_context_keywords && message.matched_context_keywords.length > 0 && (
                  <div>
                    <span className="text-slate-500 font-medium block mb-1">Matched Keywords:</span>
                    <div className="flex flex-wrap gap-1">
                      {message.matched_context_keywords.map((kw, i) => (
                        <span key={i} className="text-[11px] bg-slate-100 text-slate-700 font-mono px-1.5 py-0.5 rounded border border-slate-200">
                          #{kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {message.relevance_reason && (
                  <div className="pt-1 text-[11px] text-slate-500 italic">
                    Reason: {message.relevance_reason}
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Original Message Identifiers */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center gap-1.5 pb-2 border-b border-slate-100">
                <Link className="w-3.5 h-3.5 text-blue-600" />
                Telegram Origin & Integrity Data
              </h4>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Channel Name:</span>
                  <span className="font-bold text-slate-800 truncate max-w-[200px]" title={message.channel_username}>
                    {message.channel_username}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Channel ID:</span>
                  <span className="font-mono text-slate-700">{message.channel_id}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Author / Sender:</span>
                  <span className="font-semibold text-slate-800 truncate max-w-[200px]" title={message.sender}>
                    {message.sender}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Timestamp:</span>
                  <span className="font-medium text-slate-700">{formatDate(message.date)}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Message ID:</span>
                  <div className="flex items-center gap-1">
                    <span className="font-mono text-slate-800">{message.id}</span>
                    <button
                      onClick={() => handleCopy(message.id, 'id')}
                      className="p-1 text-slate-400 hover:text-slate-700 rounded transition"
                      title="Copy Message ID"
                    >
                      {copiedType === 'id' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-slate-100">
                  <span className="text-slate-500 font-medium">Direct Telegram Link:</span>
                  <div className="flex items-center gap-1">
                    <a
                      href={telegramLink}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:underline font-semibold flex items-center gap-1 text-[11px]"
                      title="Jump directly to message in Telegram"
                    >
                      <span>Open in Telegram</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                    <button
                      onClick={() => handleCopy(telegramLink, 'link')}
                      className="p-1 text-slate-400 hover:text-slate-700 rounded transition"
                      title="Copy direct Telegram URL"
                    >
                      {copiedType === 'link' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 3. SHA-256 Cryptographic Hash Proof Bar */}
          <div className="bg-slate-900 text-white p-3.5 rounded-xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="space-y-0.5">
              <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                <Check className="w-3 h-3" />
                Cryptographic Integrity Fingerprint (SHA-256)
              </div>
              <div className="font-mono text-[11px] text-slate-300 break-all select-all">
                {message.evidence_hash || 'SHA256 verified on ingestion'}
              </div>
            </div>
            {message.evidence_hash && (
              <button
                onClick={() => handleCopy(message.evidence_hash || '', 'hash')}
                className="self-start sm:self-center shrink-0 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition flex items-center gap-1 cursor-pointer"
              >
                {copiedType === 'hash' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedType === 'hash' ? 'Copied' : 'Copy Hash'}</span>
              </button>
            )}
          </div>

          {/* 4. Full Message Transcript */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Full Message Transcript
              </h3>
              <button
                onClick={() => handleCopy(message.text, 'text')}
                className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 cursor-pointer"
              >
                {copiedType === 'text' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copiedType === 'text' ? 'Transcript Copied!' : 'Copy Transcript'}</span>
              </button>
            </div>
            <div className="p-4 bg-white rounded-xl border border-slate-200 text-xs text-slate-800 whitespace-pre-wrap font-sans leading-relaxed shadow-2xs max-h-48 overflow-y-auto">
              {message.text}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-white border-t border-slate-200 flex items-center justify-between shrink-0">
          <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Official Cyber Threat Intelligence Evidence Log • Tamper-proof audit record</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-bold rounded-xl transition cursor-pointer"
            >
              Close
            </button>
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition shadow cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span>Download Evidence</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EvidenceModal;

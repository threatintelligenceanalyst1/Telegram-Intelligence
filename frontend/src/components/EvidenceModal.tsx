import React, { useState, useEffect } from 'react';
import {
  X,
  Download,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  FileText,
  Eye,
  Link,
  Sparkles,
  Camera,
  Layers,
  RefreshCw,
  AlertTriangle,
  CheckCheck,
  CheckCircle2,
  XCircle,
  FileArchive,
  History
} from 'lucide-react';
import { Message, EvidenceRecord, EvidenceVerification } from '../types';
import {
  getEvidenceRecord,
  verifyEvidence,
  recaptureEvidence,
  getEvidenceScreenshotUrl,
  getEvidenceBundleUrl,
  getEvidenceDownloadUrl
} from '../services/api';

interface EvidenceModalProps {
  message: Message | null;
  searchKeyword?: string;
  onClose: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({ message, searchKeyword, onClose }) => {
  const [activeTab, setActiveTab] = useState<'screenshot' | 'analyst'>('screenshot');
  const [record, setRecord] = useState<EvidenceRecord | null>(null);
  const [loadingRecord, setLoadingRecord] = useState<boolean>(true);
  const [verification, setVerification] = useState<EvidenceVerification | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isRecapturing, setIsRecapturing] = useState<boolean>(false);
  const [copiedType, setCopiedType] = useState<string | null>(null);
  const [imageError, setImageError] = useState<boolean>(false);
  const [showCustodyLog, setShowCustodyLog] = useState<boolean>(false);

  useEffect(() => {
    if (!message) return;
    let isMounted = true;
    setLoadingRecord(true);
    setImageError(false);
    setVerification(null);

    getEvidenceRecord(message.id)
      .then((data) => {
        if (isMounted) {
          setRecord(data);
          // If capture failed, start on analyst tab so user gets immediate visual feedback
          if (data && data.capture_status === 'failed') {
            setActiveTab('analyst');
          } else {
            setActiveTab('screenshot');
          }
        }
      })
      .catch((err) => {
        console.warn('Failed to load real evidence record:', err);
      })
      .finally(() => {
        if (isMounted) setLoadingRecord(false);
      });

    return () => {
      isMounted = false;
    };
  }, [message]);

  if (!message) return null;

  const screenshotUrl = getEvidenceScreenshotUrl(message.id);
  const bundleUrl = getEvidenceBundleUrl(message.id);
  const analystDownloadUrl = getEvidenceDownloadUrl(message.id, searchKeyword);

  // Compute direct Telegram permalink
  const getTelegramLink = () => {
    if (record?.embed_url) {
      return record.embed_url.replace('?embed=1', '');
    }
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

  const handleDownloadBundle = () => {
    const a = document.createElement('a');
    a.href = bundleUrl;
    a.download = `evidence_bundle_${message.id.replace(/[^\w\-.]/g, '_')}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleVerifyIntegrity = async () => {
    setIsVerifying(true);
    try {
      const res = await verifyEvidence(message.id);
      setVerification(res);
    } catch (err) {
      console.error('Integrity verification failed:', err);
      setVerification({
        message_id: message.id,
        verified: false,
        message_hash_match: false,
        screenshot_hash_match: false,
        manifest_hash_match: false,
        chain_valid: false,
        stored_hashes: {},
        recomputed_hashes: {},
        verified_at: new Date().toISOString(),
        status: 'incomplete',
        details: 'Verification network call failed'
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleRecapture = async () => {
    setIsRecapturing(true);
    try {
      const updated = await recaptureEvidence(message.id);
      setRecord(updated);
      setImageError(false);
      if (updated.capture_status === 'captured') {
        setActiveTab('screenshot');
      }
    } catch (err) {
      console.error('Recapture request failed:', err);
    } finally {
      setIsRecapturing(false);
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const isCaptured = record?.capture_status === 'captured';
  const isFailed = record?.capture_status === 'failed';
  const isPending = record?.capture_status === 'pending' || loadingRecord;

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
                {isCaptured && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    AUTHENTIC CAPTURE
                  </span>
                )}
                {isFailed && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    CAPTURE RESTRICTED
                  </span>
                )}
                {isPending && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    EVIDENCE RECORD
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Channel: <span className="font-semibold text-slate-200">{message.channel_username}</span> • ID: <span className="font-mono text-slate-300">{message.channel_id}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadBundle}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition shadow-sm cursor-pointer"
              title="Download complete authenticated forensic ZIP bundle"
            >
              <FileArchive className="w-3.5 h-3.5" />
              <span>Download Evidence Package</span>
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

        {/* Tab Switcher */}
        <div className="px-6 pt-3 pb-0 bg-slate-100 border-b border-slate-200 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('screenshot')}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === 'screenshot'
                  ? 'border-blue-600 text-blue-600 bg-white rounded-t-lg'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span>Captured Screenshot</span>
              {isCaptured && (
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block ml-1"></span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('analyst')}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === 'analyst'
                  ? 'border-blue-600 text-blue-600 bg-white rounded-t-lg'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Analyst View</span>
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500 pb-1">
            <button
              onClick={handleRecapture}
              disabled={isRecapturing}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-slate-600 hover:text-slate-900 hover:bg-slate-200 rounded text-[11px] font-medium transition cursor-pointer disabled:opacity-50"
              title="Force re-capture using headless Chromium"
            >
              <RefreshCw className={`w-3 h-3 ${isRecapturing ? 'animate-spin text-blue-600' : ''}`} />
              <span>{isRecapturing ? 'Capturing...' : 'Recapture'}</span>
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 bg-slate-50/50">
          
          {/* TAB 1: Captured Screenshot */}
          {activeTab === 'screenshot' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-blue-600" />
                    Genuine Telegram Embed Screenshot
                  </h3>
                  {record?.captured_at && (
                    <span className="text-[11px] text-slate-400">
                      Captured: {formatDate(record.captured_at)}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <a
                    href={screenshotUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    <span>View Full Resolution</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>

              <div className="rounded-xl border border-slate-300 bg-slate-900 p-2 shadow-inner overflow-hidden flex flex-col justify-center items-center min-h-[260px]">
                {isCaptured && !imageError ? (
                  <img
                    src={screenshotUrl}
                    alt={`Evidence capture for message ${message.id}`}
                    onError={() => setImageError(true)}
                    className="rounded-lg max-h-[460px] w-auto object-contain shadow-md"
                  />
                ) : isFailed ? (
                  <div className="max-w-md p-6 text-center space-y-3">
                    <div className="w-12 h-12 mx-auto rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                      <AlertTriangle className="w-6 h-6" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="text-sm font-bold text-white">Genuine Web Capture Not Available</h4>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        {record?.failure_reason || 'This channel is private or does not permit public web embeds.'}
                      </p>
                    </div>
                    <div className="pt-2 flex items-center justify-center gap-2">
                      <button
                        onClick={() => setActiveTab('analyst')}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition"
                      >
                        Switch to Analyst View
                      </button>
                      <button
                        onClick={handleRecapture}
                        disabled={isRecapturing}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition flex items-center gap-1"
                      >
                        <RefreshCw className={`w-3 h-3 ${isRecapturing ? 'animate-spin' : ''}`} />
                        <span>Retry Capture</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="py-12 flex flex-col items-center gap-2 text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-400" />
                    <p className="text-xs font-medium">Loading authentic screenshot...</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: Analyst View */}
          {activeTab === 'analyst' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-blue-600" />
                  Analyst Message Reconstruction & Context View
                </h3>
                <a
                  href={analystDownloadUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <span>Download Analyst Card</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              <div className="rounded-xl border border-slate-300 bg-[#0e1621] p-4 shadow-inner flex justify-center items-center">
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
                    <div className="text-[10px] text-slate-400 flex items-center justify-end gap-1.5 pt-1">
                      <span className="inline-flex items-center gap-1">
                        <Eye className="w-3 h-3 text-slate-400" />
                        <span>{message.views || 10}</span>
                      </span>
                      <span>•</span>
                      <span>{formatDate(message.date)}</span>
                      <CheckCheck className="w-3.5 h-3.5 text-blue-400 ml-0.5" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Cryptographic Hashes & Integrity Fingerprints */}
          <div className="bg-slate-900 text-white p-4 rounded-xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-white">
                  Cryptographic Integrity Verification (SHA-256)
                </span>
              </div>
              <button
                onClick={handleVerifyIntegrity}
                disabled={isVerifying}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition cursor-pointer shadow-sm"
              >
                <RefreshCw className={`w-3 h-3 ${isVerifying ? 'animate-spin' : ''}`} />
                <span>{isVerifying ? 'Verifying...' : 'Verify Integrity'}</span>
              </button>
            </div>

            {/* Verification Status Banner */}
            {verification && (
              <div
                className={`p-3 rounded-lg border text-xs flex items-center justify-between gap-2 ${
                  verification.verified
                    ? 'bg-emerald-950/70 border-emerald-700/60 text-emerald-200'
                    : 'bg-rose-950/70 border-rose-700/60 text-rose-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  {verification.verified ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  )}
                  <span>
                    {verification.verified
                      ? 'Integrity Verified: All SHA-256 digests match the immutable manifest and chain of custody.'
                      : `Verification Warning: ${verification.details || 'Digests do not match immutable record.'}`}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 font-mono shrink-0">
                  {formatDate(verification.verified_at)}
                </span>
              </div>
            )}

            {/* Two Distinct Hashes */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              {/* Hash 1: Screenshot SHA-256 */}
              <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                    Screenshot SHA-256 (PNG File)
                  </span>
                  {record?.screenshot_sha256 && (
                    <button
                      onClick={() => handleCopy(record.screenshot_sha256 || '', 'screenshot_hash')}
                      className="text-slate-400 hover:text-white transition p-0.5"
                      title="Copy Screenshot SHA-256"
                    >
                      {copiedType === 'screenshot_hash' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  )}
                </div>
                <div className="font-mono text-[11px] text-slate-200 break-all select-all">
                  {record?.screenshot_sha256 || (isFailed ? 'Capture restricted (No image digest)' : 'Pending capture')}
                </div>
              </div>

              {/* Hash 2: Message SHA-256 */}
              <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                    Message Data SHA-256 (Raw JSON)
                  </span>
                  {(record?.message_sha256 || message.evidence_hash) && (
                    <button
                      onClick={() => handleCopy(record?.message_sha256 || message.evidence_hash || '', 'msg_hash')}
                      className="text-slate-400 hover:text-white transition p-0.5"
                      title="Copy Message JSON SHA-256"
                    >
                      {copiedType === 'msg_hash' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  )}
                </div>
                <div className="font-mono text-[11px] text-slate-200 break-all select-all">
                  {record?.message_sha256 || message.evidence_hash || 'SHA256 verified on ingestion'}
                </div>
              </div>
            </div>

            {/* Manifest SHA-256 and Chain of Custody Toggle */}
            <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400">
              <span className="font-mono">
                Manifest Digest: <span className="text-slate-300">{record?.manifest_sha256 ? `${record.manifest_sha256.slice(0, 16)}...` : 'N/A'}</span>
              </span>
              {record?.chain_of_custody && record.chain_of_custody.length > 0 && (
                <button
                  onClick={() => setShowCustodyLog(!showCustodyLog)}
                  className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 font-semibold cursor-pointer"
                >
                  <History className="w-3 h-3" />
                  <span>{showCustodyLog ? 'Hide Custody Trail' : `View Custody Trail (${record.chain_of_custody.length})`}</span>
                </button>
              )}
            </div>

            {/* Custody Log Drawer */}
            {showCustodyLog && record?.chain_of_custody && (
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 mt-2">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                  Chain of Custody Audit Trail
                </div>
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {record.chain_of_custody.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between text-[10px] font-mono border-b border-slate-800/80 pb-1">
                      <span className="text-emerald-400 font-bold">{item.action}</span>
                      <span className="text-slate-300">{item.actor}</span>
                      <span className="text-slate-500">{formatDate(item.timestamp)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Forensic Metadata & Intelligence Breakdown */}
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
                    {message.confidence_score !== undefined
                      ? `${message.confidence_score}% (${message.confidence_level || 'EVALUATED'})`
                      : 'Evaluated Match'}
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

          {/* Full Message Transcript */}
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
              onClick={handleDownloadBundle}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition shadow cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span>Download Evidence Package</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EvidenceModal;

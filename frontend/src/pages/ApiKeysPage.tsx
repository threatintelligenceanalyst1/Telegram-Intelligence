import React, { useState, useEffect } from 'react';
import {
  Key,
  Plus,
  Shield,
  Copy,
  Check,
  Trash2,
  Power,
  RefreshCw,
  Terminal,
  Activity,
  Layers,
  AlertTriangle,
  Lock,
  ExternalLink,
  Code2
} from 'lucide-react';
import { getApiKeys, createApiKey, toggleApiKey, deleteApiKey } from '../services/api';
import { ApiKey } from '../types';

export const ApiKeysPage: React.FC = () => {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State for Generating Key
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [clientName, setClientName] = useState('');
  const [description, setDescription] = useState('');
  const [rateLimit, setRateLimit] = useState(120);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Modal State for Newly Generated Key (Reveal Modal)
  const [createdKeyData, setCreatedKeyData] = useState<ApiKey | null>(null);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  // Documentation tab state
  const [docTab, setDocTab] = useState<'curl' | 'python' | 'siem'>('curl');

  const fetchKeys = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getApiKeys();
      setKeys(data.keys || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load API keys.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientName.trim()) return;

    try {
      setIsSubmitting(true);
      const res = await createApiKey({
        client_name: clientName.trim(),
        description: description.trim(),
        rate_limit: rateLimit,
        scopes: ['read:all']
      });

      if (res.success && res.api_key) {
        setCreatedKeyData(res.api_key);
        setShowCreateModal(false);
        setClientName('');
        setDescription('');
        fetchKeys();
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to create API key.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggle = async (keyId: string) => {
    try {
      const res = await toggleApiKey(keyId);
      if (res.success) {
        setKeys((prev) =>
          prev.map((k) => (k.id === keyId ? { ...k, is_active: res.is_active } : k))
        );
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to update key status.');
    }
  };

  const handleDelete = async (keyId: string, client: string) => {
    if (!window.confirm(`Are you sure you want to permanently revoke and delete the API key for '${client}'? External tools using this key will immediately be blocked.`)) {
      return;
    }

    try {
      await deleteApiKey(keyId);
      setKeys((prev) => prev.filter((k) => k.id !== keyId));
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to revoke API key.');
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 2500);
  };

  const activeKeysCount = keys.filter((k) => k.is_active).length;
  const totalRequests = keys.reduce((acc, k) => acc + (k.total_requests || 0), 0);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-darkBorder pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-500 shadow-sm">
              <Key className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                Customer & SIEM API Keys
                <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  100% Free & Unlimited
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Generate cryptographically secure API keys to integrate Telegram Darknet Threat Intelligence into customer SOCs, SIEMs, and external scripts.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchKeys}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold bg-darkCard border border-darkBorder text-slate-300 hover:text-slate-100 hover:bg-slate-800 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20 transition"
          >
            <Plus className="w-4 h-4" />
            Generate Customer Key
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-darkCard border border-darkBorder flex items-center justify-between shadow-sm">
          <div>
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total API Keys</div>
            <div className="text-2xl font-black text-slate-100 mt-1">{keys.length}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Registered clients</div>
          </div>
          <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400">
            <Key className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-darkCard border border-darkBorder flex items-center justify-between shadow-sm">
          <div>
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Active Keys</div>
            <div className="text-2xl font-black text-emerald-400 mt-1">{activeKeysCount}</div>
            <div className="text-[11px] text-emerald-500/80 mt-0.5">Authorized for /api/v1</div>
          </div>
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400">
            <Shield className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-darkCard border border-darkBorder flex items-center justify-between shadow-sm">
          <div>
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Ingestions</div>
            <div className="text-2xl font-black text-purple-400 mt-1">{totalRequests.toLocaleString()}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">External API requests served</div>
          </div>
          <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-darkCard border border-darkBorder flex items-center justify-between shadow-sm">
          <div>
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Supported Protocols</div>
            <div className="text-base font-bold text-slate-200 mt-1">REST / JSON / STIX</div>
            <div className="text-[11px] text-blue-400 mt-0.5">Splunk • Sentinel • MISP</div>
          </div>
          <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400">
            <Layers className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Keys Table */}
      <div className="bg-darkCard border border-darkBorder rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-darkBorder flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-blue-400" />
            <h2 className="text-sm font-bold text-slate-200">Customer Access Tokens</h2>
          </div>
          <div className="text-xs text-slate-400 font-medium">
            Header: <code className="px-1.5 py-0.5 rounded bg-slate-800 text-blue-400 font-mono text-[11px]">X-API-Key: dnet_live_...</code>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-500/10 border-b border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-slate-400 text-xs">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-500 mb-2" />
            Loading API keys...
          </div>
        ) : keys.length === 0 ? (
          <div className="py-16 text-center text-slate-400 space-y-3">
            <div className="p-3 rounded-full bg-slate-800/60 w-fit mx-auto text-slate-500">
              <Key className="w-6 h-6" />
            </div>
            <div className="text-sm font-semibold text-slate-300">No Customer API Keys Generated Yet</div>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Create an API key to allow external SOC platforms, SIEM tools, or customer scripts to pull darknet threat alerts and IOC feeds.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-md transition"
            >
              <Plus className="w-4 h-4" />
              Generate First API Key
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-darkBorder bg-slate-800/20 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Client / Integration</th>
                  <th className="py-3 px-4">Key Token</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Usage & Requests</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder text-xs text-slate-300 font-medium">
                {keys.map((k) => (
                  <tr key={k.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-100 flex items-center gap-2">
                        {k.client_name}
                      </div>
                      {k.description && (
                        <div className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">
                          {k.description}
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-1 rounded bg-slate-800/80 border border-darkBorder text-blue-400 text-[11px]">
                          {k.key_masked}
                        </span>
                        <button
                          onClick={() => copyToClipboard(k.key_masked, k.id)}
                          title="Copy masked token identifier"
                          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                        >
                          {copiedKeyId === k.id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      {k.is_active ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-red-500/10 border border-red-500/20 text-red-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                          Revoked
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="text-slate-200 font-bold">
                        {(k.total_requests || 0).toLocaleString()} calls
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {k.last_used_at
                          ? `Last: ${new Date(k.last_used_at).toLocaleDateString()} ${new Date(k.last_used_at).toLocaleTimeString()}`
                          : 'Never used'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleToggle(k.id)}
                          title={k.is_active ? 'Disable Key' : 'Enable Key'}
                          className={`p-1.5 rounded-lg border transition ${
                            k.is_active
                              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                              : 'bg-slate-800 border-darkBorder text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          <Power className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(k.id, k.client_name)}
                          title="Revoke & Delete Key"
                          className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Developer Integration Quickstart */}
      <div className="bg-darkCard border border-darkBorder rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-darkBorder pb-3">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-slate-200">Customer Integration Guide (/api/v1)</h3>
          </div>
          <div className="flex gap-1.5 p-1 rounded-xl bg-slate-900 border border-darkBorder text-xs font-semibold">
            <button
              onClick={() => setDocTab('curl')}
              className={`px-3 py-1 rounded-lg transition ${
                docTab === 'curl' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              cURL
            </button>
            <button
              onClick={() => setDocTab('python')}
              className={`px-3 py-1 rounded-lg transition ${
                docTab === 'python' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Python
            </button>
            <button
              onClick={() => setDocTab('siem')}
              className={`px-3 py-1 rounded-lg transition ${
                docTab === 'siem' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Splunk / SIEM
            </button>
          </div>
        </div>

        {docTab === 'curl' && (
          <div className="space-y-3 text-xs font-mono">
            <div>
              <div className="text-slate-400 font-sans text-[11px] mb-1 font-semibold">
                1. Stream Critical/High Threat Feed (JSON):
              </div>
              <div className="p-3 rounded-xl bg-slate-950 border border-darkBorder text-slate-300 overflow-x-auto select-all">
                curl -H "X-API-Key: YOUR_API_KEY" "http://localhost:8000/api/v1/threats?min_level=HIGH&limit=50"
              </div>
            </div>

            <div>
              <div className="text-slate-400 font-sans text-[11px] mb-1 font-semibold">
                2. Export Malicious IOCs Blocklist (IPs, Domains, CVEs, Wallets):
              </div>
              <div className="p-3 rounded-xl bg-slate-950 border border-darkBorder text-slate-300 overflow-x-auto select-all">
                curl -H "X-API-Key: YOUR_API_KEY" "http://localhost:8000/api/v1/iocs?ioc_type=all&limit=100"
              </div>
            </div>

            <div>
              <div className="text-slate-400 font-sans text-[11px] mb-1 font-semibold">
                3. Verify Cryptographic Proof & Download Screenshot for a Message:
              </div>
              <div className="p-3 rounded-xl bg-slate-950 border border-darkBorder text-slate-300 overflow-x-auto select-all">
                curl -H "X-API-Key: YOUR_API_KEY" "http://localhost:8000/api/v1/evidence/msg_-1001323386230_258089"
              </div>
            </div>
          </div>
        )}

        {docTab === 'python' && (
          <div className="text-xs font-mono p-4 rounded-xl bg-slate-950 border border-darkBorder text-slate-300 overflow-x-auto space-y-1">
            <span className="text-slate-500"># Python Ingestion Client Example</span>
            <br />
            <span className="text-blue-400">import</span> requests
            <br />
            <br />
            API_KEY = <span className="text-emerald-400">"dnet_live_YOUR_KEY_HERE"</span>
            <br />
            HEADERS = &#123;<span className="text-emerald-400">"X-API-Key"</span>: API_KEY&#125;
            <br />
            <br />
            <span className="text-slate-500"># Fetch Latest Threat Alerts</span>
            <br />
            response = requests.get(
            <br />
            &nbsp;&nbsp;<span className="text-emerald-400">"http://localhost:8000/api/v1/threats?min_level=CRITICAL"</span>,
            <br />
            &nbsp;&nbsp;headers=HEADERS
            <br />
            )
            <br />
            threats = response.json().get(<span className="text-emerald-400">"threats"</span>, [])
            <br />
            <span className="text-purple-400">for</span> t <span className="text-purple-400">in</span> threats:
            <br />
            &nbsp;&nbsp;<span className="text-blue-400">print</span>(f<span className="text-emerald-400">"[&#123;t['threat_level']&#125;] &#123;t['channel_title']&#125; - Hash: &#123;t['evidence']['hash_sha256']&#125;"</span>)
          </div>
        )}

        {docTab === 'siem' && (
          <div className="text-xs text-slate-300 space-y-2 leading-relaxed">
            <p>
              External SIEMs (Splunk HEC, Elastic Agent, Microsoft Sentinel, or Cortex XSOAR) can ingest this feed directly using standard HTTP polling or Webhooks:
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-400 text-[11px]">
              <li><strong>Authentication:</strong> Pass the custom HTTP header <code className="text-blue-400 font-mono">X-API-Key</code> or <code className="text-blue-400 font-mono">Authorization: Bearer &lt;key&gt;</code>.</li>
              <li><strong>Format:</strong> Clean, structured JSON with extracted IOCs (IPs, hashes, CVEs) ready to map to Splunk CIM or Elastic ECS threat fields.</li>
              <li><strong>Evidence Integrity:</strong> Every threat record contains a canonical Telegram web deep link and a tamper-evident SHA-256 fingerprint for forensic court admissibility.</li>
            </ul>
          </div>
        )}
      </div>

      {/* Modal 1: Generate Key */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="bg-darkCard border border-darkBorder rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-darkBorder pb-3">
              <div className="flex items-center gap-2">
                <Key className="w-5 h-5 text-blue-500" />
                <h3 className="text-base font-bold text-slate-100">Generate Customer API Key</h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateKey} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Customer / Tool Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Bank SOC Ingestion, Client Splunk..."
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-darkBorder text-slate-200 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description / Integration Notes
                </label>
                <input
                  type="text"
                  placeholder="e.g. Automated threat feed polling every 15 minutes"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-darkBorder text-slate-200 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Rate Limit (Requests per minute)
                </label>
                <input
                  type="number"
                  min={10}
                  max={1000}
                  value={rateLimit}
                  onChange={(e) => setRateLimit(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-darkBorder text-slate-200 text-xs focus:outline-none focus:border-blue-500"
                />
                <div className="text-[10px] text-slate-500 mt-1">Default: 120 req/min</div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-darkBorder">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !clientName.trim()}
                  className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white shadow-md transition"
                >
                  {isSubmitting ? 'Generating...' : 'Generate Key'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Newly Generated Secret Key Reveal */}
      {createdKeyData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="bg-darkCard border border-emerald-500/30 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Shield className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">API Key Successfully Created</h3>
                <p className="text-xs text-slate-400">For client: <strong className="text-slate-200">{createdKeyData.client_name}</strong></p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <div>
                <strong>Important:</strong> Copy and store this secret key now. For your security, this key <u>will not be shown again</u>.
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Full Secret API Token
              </div>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-950 border border-darkBorder font-mono text-xs text-emerald-400 break-all select-all">
                <span className="flex-1">{createdKeyData.raw_key}</span>
                <button
                  onClick={() => copyToClipboard(createdKeyData.raw_key || '', 'modal')}
                  className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-sans text-xs font-bold flex items-center gap-1.5 shadow transition shrink-0"
                >
                  {copiedKeyId === 'modal' ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-300" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copy Key
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setCreatedKeyData(null)}
                className="px-6 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
              >
                I have safely stored this key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

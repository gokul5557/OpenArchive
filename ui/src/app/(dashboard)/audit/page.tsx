'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useUser } from '@/components/UserContext';

interface Message {
    id: string;
    subject: string;
    from: string;
    to: string;
    date: string;
    tenant_id?: string;
    size?: number;
    has_attachments?: boolean;
    is_on_hold?: boolean;
}

// Helper to separate Name and Email
const parseAddress = (full: string) => {
    if (!full) return { name: '', email: '' };

    // Check for "Name" <email> or Name <email>
    const match = full.match(/^"?(.*?)"?\s*<(.*)>$/);
    if (match) {
        return { name: match[1].trim(), email: match[2].trim() };
    }

    // Fallback: just email
    return { name: '', email: full };
};

export default function AuditPage() {

    const { userDomain, orgId } = useUser();
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Message[]>([]);
    const [totalHits, setTotalHits] = useState(0);
    const [loading, setLoading] = useState(false);
    const [page, setPage] = useState(1);
    const LIMIT = 20;

    // Advanced Filters State
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [filters, setFilters] = useState({
        from: '',
        to: '',
        dateStart: '',
        dateEnd: '',
        hasAttachments: false,
        isSpam: false,
        direction: '', // 'sent', 'received', 'internal'
        attachmentKeyword: ''
    });

    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [availableHolds, setAvailableHolds] = useState<any[]>([]);
    const [isHolding, setIsHolding] = useState(false);

    // Case Management State
    const [availableCases, setAvailableCases] = useState<any[]>([]);
    const [selectedCaseId, setSelectedCaseId] = useState<string>('');
    const [isAddingToCase, setIsAddingToCase] = useState(false);

    useEffect(() => {
        if (!orgId) return;

        // Fetch Holds
        fetch(`/api/v1/admin/holds?org_id=${orgId}`)
            .then(res => res.json())
            .then(setAvailableHolds)
            .catch(console.error);

        // Fetch Open Cases
        fetch(`/api/v1/cases?org_id=${orgId}`)
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data)) {
                    const openCases = data.filter((c: any) => c.status === 'OPEN');
                    setAvailableCases(openCases);
                    if (openCases.length > 0) setSelectedCaseId(openCases[0].id);
                }
            })
            .catch(console.error);
    }, [orgId]);

    const toggleSelect = (id: string) => {
        const next = new Set(selectedIds);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedIds(next);
    };

    const toggleSelectAll = () => {
        if (selectedIds.size === results.length && results.length > 0) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(results.map(r => r.id)));
        }
    };

    const logAudit = async (action: string, details: any) => {
        if (!orgId) return;
        try {
            await fetch(`/api/v1/admin/audit-logs?org_id=${orgId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: 0,
                    username: localStorage.getItem('user_id') || 'auditor',
                    action,
                    details,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (err) {
            console.error('Audit Log failed:', err);
        }
    };

    const handleExport = () => {
        const toExport = selectedIds.size > 0
            ? results.filter(r => selectedIds.has(r.id))
            : results;

        const csv = [
            ['ID', 'Subject', 'From', 'To', 'Date', 'Size'].join(','),
            ...toExport.map(r => [
                r.id,
                `"${r.subject}"`,
                r.from,
                r.to,
                r.date,
                r.size
            ].join(','))
        ].join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `archive_export_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        logAudit('EXPORT_CSV', { count: toExport.length, selected: selectedIds.size > 0 });
    };

    const handleApplyHold = async () => {
        if (selectedIds.size === 0 || !orgId) return;
        setIsHolding(true);
        try {
            let holdId;
            if (availableHolds.length > 0) {
                holdId = availableHolds[0].id;
            } else {
                const res = await fetch(`/api/v1/admin/holds?org_id=${orgId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: `Auto-Case-${new Date().toISOString().slice(0, 10)}`,
                        reason: 'Bulk hold from search results',
                        filter_criteria: {}
                    })
                });
                const data = await res.json();
                holdId = data.id;
            }

            const res = await fetch(`/api/v1/admin/holds/apply?org_id=${orgId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    hold_id: holdId,
                    message_ids: Array.from(selectedIds)
                })
            });

            if (res.ok) {
                alert(`Applied hold to ${selectedIds.size} messages.`);
                setSelectedIds(new Set());
                logAudit('APPLY_LEGAL_HOLD', { hold_id: holdId, count: selectedIds.size });
            }
        } finally {
            setIsHolding(false);
        }
    };

    const handleAddToCase = async () => {
        if (selectedIds.size === 0 || !selectedCaseId || !orgId) return;
        setIsAddingToCase(true);
        try {
            const res = await fetch(`/api/v1/cases/${selectedCaseId}/items?org_id=${orgId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    case_id: parseInt(selectedCaseId),
                    message_ids: Array.from(selectedIds)
                })
            });

            if (res.ok) {
                alert(`Added ${selectedIds.size} messages to case.`);
                setSelectedIds(new Set());
                logAudit('ADD_TO_CASE', { case_id: selectedCaseId, count: selectedIds.size });
            }
        } finally {
            setIsAddingToCase(false);
        }
    };

    const fetchMessages = async () => {
        if (!orgId) return;
        setLoading(true);
        try {
            let url = `/api/v1/messages?org_id=${orgId}&q=${encodeURIComponent(query)}`;
            if (userDomain) url += `&user_domain=${encodeURIComponent(userDomain)}`;

            // Append advanced filters
            if (filters.from) url += `&from_addr=${encodeURIComponent(filters.from)}`;
            if (filters.to) url += `&to_addr=${encodeURIComponent(filters.to)}`;
            if (filters.dateStart) url += `&date_start=${encodeURIComponent(filters.dateStart)}`;
            if (filters.dateEnd) url += `&date_end=${encodeURIComponent(filters.dateEnd)}`;
            if (filters.hasAttachments) url += `&has_attachments=true`;
            if (filters.isSpam) url += `&is_spam=true`;
            if (filters.direction) url += `&direction=${filters.direction}`;
            if (filters.attachmentKeyword) url += `&attachment_keyword=${encodeURIComponent(filters.attachmentKeyword)}`;

            // Pagination
            const offset = (page - 1) * LIMIT;
            url += `&limit=${LIMIT}&offset=${offset}`;

            const res = await fetch(url);
            const data = await res.json();
            setResults(data.hits || []);
            setTotalHits(data.estimatedTotalHits || 0);

            // Log the search
            if (query || Object.values(filters).some(v => v)) {
                logAudit('SEARCH', { query, filters, resultCount: data.hits?.length, page });
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    // Re-fetch when domain changes or page changes
    useEffect(() => {
        fetchMessages();
    }, [userDomain, page]);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1); // Reset to first page
        fetchMessages();
    };

    return (
        <div className="w-full space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-black text-zinc-900 tracking-tight">Audit Archive</h1>
                    <p className="text-zinc-500 mt-2 text-lg">Discovery and verification engine for institutional records.</p>
                </div>
                <div className="flex gap-3">
                    {selectedIds.size > 0 && (
                        <button
                            onClick={handleApplyHold}
                            disabled={isHolding}
                            className="px-5 py-2.5 bg-red-50 text-red-600 border border-red-100 rounded-xl text-sm font-bold hover:bg-red-100 transition-all flex items-center gap-2 disabled:opacity-50 shadow-sm"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"></path></svg>
                            {isHolding ? 'Holding...' : `Legal Hold (${selectedIds.size})`}
                        </button>
                    )}

                    <button
                        onClick={handleExport}
                        className="px-5 py-2.5 bg-zinc-900 text-white rounded-xl text-sm font-bold hover:bg-zinc-800 transition-all flex items-center gap-2 shadow-lg shadow-zinc-200"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        Export {selectedIds.size > 0 ? `Selected` : 'All'}
                    </button>

                    {selectedIds.size > 0 && availableCases.length > 0 && (
                        <div className="flex rounded-xl bg-indigo-600 p-0.5 shadow-lg shadow-indigo-100">
                            <select
                                className="pl-4 pr-1 py-2 bg-transparent text-xs text-white font-bold focus:outline-none appearance-none cursor-pointer"
                                value={selectedCaseId}
                                onChange={(e) => setSelectedCaseId(e.target.value)}
                            >
                                {availableCases.map(c => <option key={c.id} value={c.id} className="text-zinc-900">{c.name}</option>)}
                            </select>
                            <button
                                onClick={handleAddToCase}
                                disabled={isAddingToCase}
                                className="px-4 py-2 bg-white text-indigo-600 rounded-lg text-[10px] font-black uppercase tracking-widest hover:bg-indigo-50 transition-colors ml-1"
                            >
                                {isAddingToCase ? '...' : 'Add to Case'}
                            </button>
                        </div>
                    )}
                </div>
            </div>

            <div className="premium-card overflow-hidden">
                <div className="p-6 border-b border-zinc-100 bg-zinc-50/30">
                    <form onSubmit={handleSearch} className="space-y-6">
                        {/* Main Search Bar */}
                        <div className="flex gap-4">
                            <div className="flex-1 relative group">
                                <span className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-zinc-400 group-focus-within:text-indigo-500 transition-colors">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                                </span>
                                <input
                                    type="text"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder="Keywords, subjects, or forensic IDs..."
                                    className="w-full pl-12 bg-white border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium placeholder-zinc-400"
                                />
                            </div>
                            <button
                                type="submit"
                                className="px-8 py-3 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200"
                            >
                                Search
                            </button>
                            <button
                                type="button"
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                className={`px-5 py-3 border-2 rounded-xl text-sm font-bold transition-all ${showAdvanced ? 'bg-zinc-900 border-zinc-950 text-white' : 'bg-white border-zinc-100 text-zinc-600 hover:bg-zinc-50'}`}
                            >
                                Filters
                            </button>
                        </div>

                        {/* Advanced Filters Panel */}
                        {showAdvanced && (
                            <div className="pt-4 border-t border-zinc-200 grid grid-cols-1 md:grid-cols-3 gap-4 animate-in fade-in slide-in-from-top-2">
                                <div>
                                    <label className="block text-xs font-semibold text-zinc-600 mb-1">From (Sender)</label>
                                    <input
                                        type="text"
                                        placeholder="alice@example.com"
                                        className="w-full border border-zinc-300 rounded px-3 py-1.5 text-sm"
                                        value={filters.from}
                                        onChange={e => setFilters({ ...filters, from: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-zinc-600 mb-1">To (Recipient)</label>
                                    <input
                                        type="text"
                                        placeholder="bob@example.com"
                                        className="w-full border border-zinc-300 rounded px-3 py-1.5 text-sm"
                                        value={filters.to}
                                        onChange={e => setFilters({ ...filters, to: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-zinc-600 mb-1">Date Range</label>
                                    <div className="flex gap-2">
                                        <input
                                            type="date"
                                            className="w-full border border-zinc-300 rounded px-2 py-1.5 text-xs"
                                            value={filters.dateStart}
                                            onChange={e => setFilters({ ...filters, dateStart: e.target.value })}
                                        />
                                        <input
                                            type="date"
                                            className="w-full border border-zinc-300 rounded px-2 py-1.5 text-xs"
                                            value={filters.dateEnd}
                                            onChange={e => setFilters({ ...filters, dateEnd: e.target.value })}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-zinc-600 mb-1">Traffic Direction</label>
                                    <select
                                        className="w-full border border-zinc-300 rounded px-3 py-1.5 text-sm bg-white"
                                        value={filters.direction}
                                        onChange={e => setFilters({ ...filters, direction: e.target.value })}
                                    >
                                        <option value="">All Traffic</option>
                                        <option value="sent">Sent (Outgoing)</option>
                                        <option value="received">Received (Incoming)</option>
                                        <option value="internal">Internal Only</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-zinc-600 mb-1">Attachment Keyword</label>
                                    <input
                                        type="text"
                                        placeholder="Specific text in PDF/Images..."
                                        className="w-full border border-zinc-300 rounded px-3 py-1.5 text-sm"
                                        value={filters.attachmentKeyword}
                                        onChange={e => setFilters({ ...filters, attachmentKeyword: e.target.value })}
                                    />
                                </div>
                                <div className="md:col-span-3 flex gap-6 pt-2">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                                            checked={filters.hasAttachments}
                                            onChange={e => setFilters({ ...filters, hasAttachments: e.target.checked })}
                                        />
                                        <span className="text-sm text-zinc-700">Has Attachments 📎</span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            className="rounded border-zinc-300 text-red-600 focus:ring-red-500"
                                            checked={filters.isSpam}
                                            onChange={e => setFilters({ ...filters, isSpam: e.target.checked })}
                                        />
                                        <span className="text-sm text-zinc-700">Flagged as Spam 🚫</span>
                                    </label>
                                    <button
                                        type="button"
                                        onClick={() => setFilters({ from: '', to: '', dateStart: '', dateEnd: '', hasAttachments: false, isSpam: false, direction: '', attachmentKeyword: '' })}
                                        className="ml-auto text-xs text-zinc-500 hover:text-zinc-800 underline"
                                    >
                                        Clear Filters
                                    </button>
                                </div>
                            </div>
                        )}
                    </form>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-zinc-600">
                        <thead className="bg-zinc-50 border-b border-zinc-200 font-medium text-zinc-900">
                            <tr>
                                <th className="px-4 py-4 w-10 text-center">
                                    <input
                                        type="checkbox"
                                        className="rounded border-zinc-300"
                                        checked={results.length > 0 && selectedIds.size === results.length}
                                        onChange={toggleSelectAll}
                                    />
                                </th>
                                <th className="px-4 py-4 w-12 text-center text-zinc-400">📌</th>
                                <th className="px-4 py-4 w-24">ID</th>
                                <th className="px-4 py-4">Subject</th>
                                <th className="px-4 py-4">From</th>
                                <th className="px-4 py-4">To</th>
                                <th className="px-4 py-4">Date</th>
                                <th className="px-4 py-4">Size</th>
                                <th className="px-4 py-4 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-100">
                            {!loading && results.length === 0 && (
                                <tr>
                                    <td colSpan={9} className="px-6 py-12 text-center text-zinc-400">
                                        {query ? "No messages found." : "Enter a term to search the archive."}
                                    </td>
                                </tr>
                            )}

                            {loading && (
                                <tr>
                                    <td colSpan={9} className="px-6 py-12 text-center text-zinc-400">
                                        Searching...
                                    </td>
                                </tr>
                            )}

                            {results.map((msg) => (
                                <tr key={msg.id} className={`hover:bg-zinc-50/80 transition-colors group ${selectedIds.has(msg.id) ? 'bg-indigo-50/30' : ''}`}>
                                    <td className="px-4 py-4 text-center">
                                        <input
                                            type="checkbox"
                                            className="rounded border-zinc-300 text-indigo-600"
                                            checked={selectedIds.has(msg.id)}
                                            onChange={() => toggleSelect(msg.id)}
                                        />
                                    </td>
                                    <td className="px-4 py-4 text-center">
                                        {msg.has_attachments ? <span title="Has Attachments" className="text-indigo-600">📌</span> : null}
                                    </td>
                                    <td className="px-4 py-4 font-mono text-[10px] text-zinc-400">
                                        {msg.id.substring(0, 8)}...
                                    </td>
                                    <td className="px-4 py-4 font-medium text-zinc-900 max-w-md truncate" title={msg.subject}>
                                        <div className="flex items-center gap-2">
                                            {msg.is_on_hold && <span title="Account / Message on Legal Hold" className="text-red-500">⚖️</span>}
                                            {msg.subject || '(No Subject)'}
                                        </div>
                                    </td>
                                    <td className="px-4 py-4 max-w-[180px]">
                                        {(() => {
                                            const { name, email } = parseAddress(msg.from);
                                            return (
                                                <div className="flex flex-col">
                                                    {name && name !== email && (
                                                        <span className="text-xs font-medium text-zinc-900 truncate" title={name}>
                                                            {name}
                                                        </span>
                                                    )}
                                                    <span className="text-[11px] text-zinc-500 font-mono truncate" title={email}>
                                                        {email}
                                                    </span>
                                                </div>
                                            );
                                        })()}
                                    </td>
                                    <td className="px-4 py-4 max-w-[180px]">
                                        {(() => {
                                            const { name, email } = parseAddress(msg.to);
                                            return (
                                                <div className="flex flex-col">
                                                    {name && name !== email && (
                                                        <span className="text-xs font-medium text-zinc-900 truncate" title={name}>
                                                            {name}
                                                        </span>
                                                    )}
                                                    <span className="text-[11px] text-zinc-500 font-mono truncate" title={email}>
                                                        {email}
                                                    </span>
                                                </div>
                                            );
                                        })()}
                                    </td>
                                    <td className="px-4 py-4 whitespace-nowrap">
                                        {(() => {
                                            if (!msg.date) return 'N/A';
                                            try {
                                                const d = new Date(msg.date);
                                                return isNaN(d.getTime()) ? msg.date : d.toLocaleString();
                                            } catch (e) {
                                                return msg.date;
                                            }
                                        })()}
                                    </td>
                                    <td className="px-4 py-4 font-mono text-xs">
                                        {msg.size ? `${(msg.size / 1024).toFixed(1)} KB` : 'N/A'}
                                    </td>
                                    <td className="px-4 py-4 text-right">
                                        <Link
                                            href={`/message-view?id=${msg.id}`}
                                            className="text-indigo-600 hover:text-indigo-800 font-medium text-xs border border-indigo-200 bg-indigo-50 px-3 py-1 rounded"
                                        >
                                            View
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="p-4 border-t border-zinc-200 bg-zinc-50 text-xs text-zinc-500 flex justify-between items-center">
                    <span>Showing {(page - 1) * LIMIT + 1}-{Math.min(page * LIMIT, totalHits)} of {totalHits} results</span>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="px-2 py-1 border border-zinc-200 bg-white rounded hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Previous
                        </button>
                        <button
                            onClick={() => setPage(p => p + 1)}
                            disabled={page * LIMIT >= totalHits}
                            className="px-2 py-1 border border-zinc-200 bg-white rounded hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Next
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

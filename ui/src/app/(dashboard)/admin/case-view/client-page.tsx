'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';

interface CaseItem {
    id: number;
    message_id: string;
    added_at: string;
    added_by: string;
    tags: string[];
    assignee_id?: number;
    assignee_name?: string;
    review_status: string;
}

interface User {
    id: number;
    username: string;
}

interface CaseData {
    id: number;
    name: string;
    description: string;
    status: string;
    created_at: string;
}

export default function CaseDetailPage() {
    const searchParams = useSearchParams();
    const id = searchParams.get('id');
    const router = useRouter();

    const [caseInfo, setCaseInfo] = useState<CaseData | null>(null);
    const [items, setItems] = useState<CaseItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [exportModalOpen, setExportModalOpen] = useState(false);
    const [assignModalOpen, setAssignModalOpen] = useState(false);
    const [users, setUsers] = useState<User[]>([]);
    const [selectedItems, setSelectedItems] = useState<number[]>([]);
    const [selectedAssignee, setSelectedAssignee] = useState<number | null>(null);

    const [exportFormat, setExportFormat] = useState('native');
    const [redactPII, setRedactPII] = useState(false);
    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        if (id) {
            fetchCaseDetails();
            fetchUsers();
        }
    }, [id]);

    const fetchCaseDetails = async () => {
        try {
            const res = await fetch(`/api/v1/cases/${id}`);
            if (res.ok) {
                const data = await res.json();
                setCaseInfo(data.case);
                setItems(data.items);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const fetchUsers = async () => {
        try {
            const res = await fetch('/api/v1/admin/users');
            if (res.ok) {
                const data = await res.json();
                setUsers(data);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleBatchAssign = async () => {
        if (!selectedAssignee || selectedItems.length === 0) return;

        try {
            const res = await fetch('/api/v1/cases/items/batch-assign', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_ids: selectedItems,
                    assignee_id: selectedAssignee
                }),
            });
            if (res.ok) {
                const assigneeName = users.find(u => u.id === selectedAssignee)?.username;
                setItems(prev => prev.map(i =>
                    selectedItems.includes(i.id)
                        ? { ...i, assignee_id: selectedAssignee, assignee_name: assigneeName }
                        : i
                ));
                setAssignModalOpen(false);
                setSelectedItems([]);
                setSelectedAssignee(null);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleTagUpdate = async (itemId: number, currentTags: string[], newTag: string) => {
        if (!newTag) return;
        const updatedTags = [...currentTags, newTag];

        try {
            const res = await fetch(`/api/v1/cases/items/${itemId}/tags`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tags: updatedTags }),
            });
            if (res.ok) {
                setItems(prev => prev.map(i => i.id === itemId ? { ...i, tags: updatedTags } : i));
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleRemoveItem = async (itemId: number) => {
        if (!window.confirm("Are you sure you want to remove this item from the case?")) return;

        try {
            const res = await fetch(`/api/v1/cases/items/${itemId}`, { method: 'DELETE' });
            if (res.ok) {
                setItems(prev => prev.filter(i => i.id !== itemId));
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleDeleteCase = async () => {
        if (!window.confirm("CRITICAL: Deleting this case will remove all evidence. Are you sure?")) return;

        try {
            const res = await fetch(`/api/v1/cases/${id}`, { method: 'DELETE' });
            if (res.ok) {
                router.push("/admin/cases");
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleExport = async () => {
        setExporting(true);
        try {
            const res = await fetch(`/api/v1/cases/${id}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ format: exportFormat, redact: redactPII })
            });
            if (res.ok) {
                const data = await res.json();
                setExportModalOpen(false);
                window.location.href = data.download_url;
            }
        } catch (err) {
            console.error(err);
        } finally {
            setExporting(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-zinc-500">Loading case data...</div>;
    if (!caseInfo) return <div className="p-8 text-center text-red-500">Case not found.</div>;

    return (
        <div className="max-w-6xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-zinc-100 pb-8">
                <div>
                    <Link href="/admin/cases" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 uppercase tracking-widest mb-3 block italic transition-all">← Evidence Locker</Link>
                    <h1 className="text-4xl font-bold text-zinc-900 tracking-tight">{caseInfo.name}</h1>
                    <p className="text-zinc-500 mt-2 text-lg max-w-2xl">{caseInfo.description}</p>
                    <div className="flex gap-4 mt-6">
                        <span className="px-3 py-1 bg-zinc-100 text-zinc-600 rounded-lg text-xs font-bold border border-zinc-200">
                            Started: {new Date(caseInfo.created_at).toLocaleDateString()}
                        </span>
                        <span className={`px-3 py-1 rounded-lg text-xs font-bold border ${caseInfo.status === 'OPEN' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-zinc-100 border-zinc-200'}`}>
                            Status: {caseInfo.status}
                        </span>
                    </div>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleDeleteCase}
                        className="px-5 py-2.5 bg-white border border-red-200 text-red-600 rounded-xl text-sm font-bold hover:bg-red-50 transition-all shadow-sm"
                    >
                        Delete Case
                    </button>
                    <button
                        onClick={() => setExportModalOpen(true)}
                        className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200"
                    >
                        Export Case
                    </button>
                </div>
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-between bg-zinc-950 text-white p-4 rounded-2xl shadow-xl">
                <div className="flex items-center gap-4">
                    <div className="px-3 py-1 bg-zinc-800 rounded-lg text-xs font-bold text-zinc-400">
                        {selectedItems.length} Items Selected
                    </div>
                    {selectedItems.length > 0 && (
                        <button
                            onClick={() => setAssignModalOpen(true)}
                            className="text-sm font-bold bg-indigo-500 hover:bg-indigo-400 px-4 py-1.5 rounded-lg transition-colors"
                        >
                            Assign Selection
                        </button>
                    )}
                </div>
                <div className="text-xs text-zinc-500 font-medium italic">
                    Bulk actions apply to all items checked in the list below.
                </div>
            </div>

            {/* Assignment Modal */}
            {assignModalOpen && (
                <div className="fixed inset-0 bg-zinc-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl animate-in fade-in zoom-in duration-200">
                        <h3 className="text-xl font-bold text-zinc-900 mb-2">Assign Auditors</h3>
                        <p className="text-sm text-zinc-500 mb-6">Distribute {selectedItems.length} selected items to a reviewer for First Pass Review.</p>

                        <div className="space-y-2 mb-8">
                            {users.filter(u => u.id !== 1).map(u => (
                                <button
                                    key={u.id}
                                    onClick={() => setSelectedAssignee(u.id)}
                                    className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border-2 transition-all ${selectedAssignee === u.id
                                        ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                                        : 'border-zinc-100 hover:border-zinc-200 text-zinc-600'
                                        }`}
                                >
                                    <span className="font-bold">{u.username}</span>
                                    {selectedAssignee === u.id && <span className="text-xs font-bold uppercase tracking-widest">Selected</span>}
                                </button>
                            ))}
                        </div>

                        <div className="flex gap-3">
                            <button onClick={() => setAssignModalOpen(false)} className="flex-1 py-3 text-sm font-bold text-zinc-500 hover:bg-zinc-50 rounded-xl transition-colors">Cancel</button>
                            <button
                                onClick={handleBatchAssign}
                                disabled={!selectedAssignee}
                                className="flex-1 py-3 text-sm font-bold bg-zinc-900 text-white rounded-xl hover:bg-zinc-800 disabled:opacity-50 transition-all shadow-lg shadow-zinc-200"
                            >
                                Confirm Assignment
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Export Modal (Simplified for brevity in replace) */}
            {exportModalOpen && (
                <div className="fixed inset-0 bg-zinc-900/60 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl p-8 w-[450px] shadow-2xl">
                        <h3 className="text-xl font-bold text-zinc-900 mb-6 text-center">Export Case Data</h3>
                        <div className="space-y-3 mb-8">
                            {['native', 'pdf', 'mbox'].map(f => (
                                <button
                                    key={f}
                                    onClick={() => setExportFormat(f)}
                                    className={`w-full p-4 rounded-xl border-2 text-left transition-all ${exportFormat === f ? 'border-indigo-600 bg-indigo-50' : 'border-zinc-100 hover:border-zinc-200'}`}
                                >
                                    <span className="block text-sm font-bold text-zinc-900 uppercase tracking-tight">{f} Format</span>
                                    <span className="block text-xs text-zinc-500 mt-0.5">Professional standard for eDiscovery.</span>
                                </button>
                            ))}
                        </div>
                        <div className="flex items-center gap-2 mb-8 p-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
                            <input type="checkbox" checked={redactPII} onChange={e => setRedactPII(e.target.checked)} className="rounded text-indigo-600" />
                            <span className="text-sm font-bold text-indigo-700">Redact PII in Export 🔒</span>
                        </div>
                        <div className="flex gap-3">
                            <button onClick={() => setExportModalOpen(false)} className="flex-1 py-2.5 font-bold text-zinc-500 text-sm">Cancel</button>
                            <button onClick={handleExport} className="flex-1 py-2.5 bg-zinc-900 text-white rounded-xl font-bold text-sm shadow-lg">{exporting ? 'Starting...' : 'Export'}</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Table */}
            <div className="premium-card overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-zinc-600">
                        <thead className="bg-zinc-50/50 border-b border-zinc-100 font-bold text-zinc-900 uppercase text-[10px] tracking-widest">
                            <tr>
                                <th className="px-6 py-4 w-10">
                                    <input
                                        type="checkbox"
                                        onChange={(e) => setSelectedItems(e.target.checked ? items.map(i => i.id) : [])}
                                        checked={selectedItems.length === items.length && items.length > 0}
                                        className="rounded border-zinc-300"
                                    />
                                </th>
                                <th className="px-6 py-4">Evidence ID</th>
                                <th className="px-6 py-4">Assignee</th>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">Tags</th>
                                <th className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-100">
                            {items.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="px-6 py-16 text-center text-zinc-400 italic font-medium">
                                        No items collected.
                                    </td>
                                </tr>
                            )}
                            {items.map((item) => (
                                <tr key={item.id} className={`hover:bg-zinc-50/50 transition-colors ${selectedItems.includes(item.id) ? 'bg-indigo-50/30' : ''}`}>
                                    <td className="px-6 py-4">
                                        <input
                                            type="checkbox"
                                            checked={selectedItems.includes(item.id)}
                                            onChange={(e) => {
                                                if (e.target.checked) setSelectedItems([...selectedItems, item.id]);
                                                else setSelectedItems(selectedItems.filter(id => id !== item.id));
                                            }}
                                            className="rounded border-zinc-300"
                                        />
                                    </td>
                                    <td className="px-6 py-4 font-mono text-xs">
                                        <Link href={`/message-view?id=${item.message_id}`} className="text-indigo-600 font-bold hover:underline">
                                            {item.message_id.substring(0, 14)}...
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4">
                                        {item.assignee_name ? (
                                            <span className="flex items-center gap-2">
                                                <div className="w-6 h-6 rounded-full bg-zinc-200 flex items-center justify-center text-[10px] font-bold text-zinc-600 ring-1 ring-zinc-50 uppercase">{item.assignee_name.substring(0, 2)}</div>
                                                <span className="font-medium text-zinc-900">{item.assignee_name}</span>
                                            </span>
                                        ) : <span className="text-zinc-300 font-medium italic">Unassigned</span>}
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-tight ${item.review_status === 'COMPLETED' ? 'bg-green-50 border-green-200 text-green-700' :
                                            item.review_status === 'IN_REVIEW' ? 'bg-blue-50 border-blue-200 text-blue-700' :
                                                'bg-amber-50 border-amber-200 text-amber-700'
                                            }`}>
                                            {item.review_status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-wrap gap-1.5">
                                            {item.tags.map((tag, idx) => (
                                                <span key={idx} className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-md text-[10px] font-bold border border-yellow-200 uppercase tracking-tighter shadow-sm">
                                                    {tag}
                                                </span>
                                            ))}
                                            <button
                                                onClick={() => {
                                                    const t = prompt("Tag Label:");
                                                    if (t) handleTagUpdate(item.id, item.tags, t);
                                                }}
                                                className="w-5 h-5 flex items-center justify-center bg-zinc-100 hover:bg-zinc-200 rounded-md text-zinc-400 text-xs font-bold transition-all"
                                            >+</button>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button onClick={() => handleRemoveItem(item.id)} className="text-zinc-400 hover:text-red-500 transition-colors">
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

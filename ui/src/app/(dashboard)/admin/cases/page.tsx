'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useUser } from '@/components/UserContext';

interface Case {
    id: number;
    name: string;
    description: string;
    status: string;
    created_at: string;
    item_count: number;
}

export default function CasesPage() {
    const { orgId } = useUser();
    const [cases, setCases] = useState<Case[]>([]);
    const [loading, setLoading] = useState(true);
    const [newCase, setNewCase] = useState({ name: '', description: '' });
    const [showCreate, setShowCreate] = useState(false);

    useEffect(() => {
        if (orgId) {
            fetchCases();
        }
    }, [orgId]);

    const fetchCases = async () => {
        if (!orgId) return;
        try {
            const res = await fetch(`/api/v1/cases?org_id=${orgId}`);
            if (res.ok) {
                const data = await res.json();
                setCases(data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!orgId) return;
        try {
            const res = await fetch(`/api/v1/cases?org_id=${orgId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newCase),
            });
            if (res.ok) {
                setNewCase({ name: '', description: '' });
                setShowCreate(false);
                fetchCases();
            }
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Case Management</h1>
                    <p className="text-zinc-500 text-sm">Organize eDiscovery matters and reviews.</p>
                </div>
                <button
                    onClick={() => setShowCreate(!showCreate)}
                    className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 transition-colors"
                >
                    {showCreate ? 'Cancel' : 'Create New Case'}
                </button>
            </div>

            {showCreate && (
                <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-6 animate-in fade-in slide-in-from-top-4">
                    <h3 className="font-semibold text-indigo-900 mb-4">New Case Details</h3>
                    <form onSubmit={handleCreate} className="space-y-4">
                        <div>
                            <label className="block text-xs font-medium text-indigo-800 mb-1">Case Name</label>
                            <input
                                type="text"
                                required
                                placeholder="e.g. Litigation 2024-A"
                                className="w-full border border-indigo-200 rounded px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                value={newCase.name}
                                onChange={e => setNewCase({ ...newCase, name: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-indigo-800 mb-1">Description</label>
                            <textarea
                                placeholder="Brief summary of the matter..."
                                className="w-full border border-indigo-200 rounded px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                value={newCase.description}
                                onChange={e => setNewCase({ ...newCase, description: e.target.value })}
                                rows={3}
                            />
                        </div>
                        <div className="pt-2">
                            <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700">
                                Create Case
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
                <table className="w-full text-left text-sm text-zinc-600">
                    <thead className="bg-zinc-50 border-b border-zinc-200 font-medium text-zinc-900">
                        <tr>
                            <th className="px-6 py-4">Case Name</th>
                            <th className="px-6 py-4">Status</th>
                            <th className="px-6 py-4">Items Collected</th>
                            <th className="px-6 py-4">Created</th>
                            <th className="px-6 py-4 text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                        {loading && (
                            <tr><td colSpan={5} className="px-6 py-8 text-center text-zinc-400">Loading cases...</td></tr>
                        )}
                        {!loading && cases.length === 0 && (
                            <tr><td colSpan={5} className="px-6 py-8 text-center text-zinc-400">No active cases found.</td></tr>
                        )}
                        {cases.map((c) => (
                            <tr key={c.id} className="hover:bg-zinc-50/80 transition-colors">
                                <td className="px-6 py-4 font-medium text-indigo-600">
                                    <Link href={`/admin/case-view?id=${c.id}`} className="hover:underline">
                                        {c.name}
                                    </Link>
                                    <p className="text-xs text-zinc-400 font-normal mt-0.5">{c.description}</p>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${c.status === 'OPEN' ? 'bg-green-100 text-green-700' : 'bg-zinc-100 text-zinc-600'}`}>
                                        {c.status}
                                    </span>
                                </td>
                                <td className="px-6 py-4 font-mono">
                                    {c.item_count}
                                </td>
                                <td className="px-6 py-4">
                                    {new Date(c.created_at).toLocaleDateString()}
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <Link href={`/admin/case-view?id=${c.id}`} className="text-zinc-500 hover:text-zinc-900 text-xs font-medium border border-zinc-200 px-3 py-1 rounded hover:bg-white">
                                        Manage
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

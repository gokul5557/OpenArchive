'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface LegalHold {
    id: string;
    name: string;
    reason: string;
    filter_criteria: any;
    created_by: string;
    created_at: string;
    active: boolean;
    item_count: number;
}

import { useUser } from '@/components/UserContext';

export default function LegalHoldsPage() {
    const { orgId } = useUser();
    const [holds, setHolds] = useState<LegalHold[]>([]);
    const [newHold, setNewHold] = useState({
        name: '',
        reason: '',
        from: '',
        to: '',
        subject: ''
    });

    useEffect(() => {
        if (orgId) fetchHolds();
    }, [orgId]);

    const fetchHolds = async () => {
        try {
            const res = await fetch(`/api/v1/admin/holds?org_id=${orgId}`);
            if (res.ok) {
                const data = await res.json();
                setHolds(data);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            // Construct criteria object from fields
            const criteria: any = {};
            if (newHold.from) criteria['from'] = newHold.from;
            if (newHold.to) criteria['to'] = newHold.to;
            if (newHold.subject) criteria['subject'] = newHold.subject;

            // If no criteria, maybe warn? For now allowing it (manual hold).

            if (!orgId) return;

            const res = await fetch(`/api/v1/admin/holds?org_id=${orgId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newHold.name,
                    reason: newHold.reason,
                    filter_criteria: criteria
                }),
            });
            if (res.ok) {
                setNewHold({ name: '', reason: '', from: '', to: '', subject: '' });
                fetchHolds();
            } else {
                // Handle Error
                const err = await res.json();
                alert(`Error: ${err.detail}`);
            }
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-8">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Legal Holds</h1>
                    <p className="text-zinc-500 text-sm">Preserve data for litigation and compliance.</p>
                </div>
            </div>

            <div className="bg-white rounded-lg border border-red-200 shadow-sm p-6 mb-8 bg-red-50/10">
                <h3 className="font-semibold text-red-900 mb-4 flex items-center gap-2">
                    <span>⚖️</span> Create New Hold
                </h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-medium text-zinc-700 mb-1">Case Name / Hold ID</label>
                            <input
                                type="text"
                                required
                                className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                                value={newHold.name}
                                onChange={e => setNewHold({ ...newHold, name: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-zinc-700 mb-1">Reason</label>
                            <input
                                type="text"
                                required
                                className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                                value={newHold.reason}
                                onChange={e => setNewHold({ ...newHold, reason: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="pt-2 border-t border-red-200/50">
                        <label className="block text-xs font-semibold text-zinc-900 mb-3">Preservation Criteria (Leave empty to create empty hold)</label>
                        <div className="grid grid-cols-3 gap-4">
                            <div>
                                <label className="block text-xs font-medium text-zinc-700 mb-1">From (Sender Email)</label>
                                <input
                                    type="text"
                                    placeholder="suspect@example.com"
                                    className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                                    value={newHold.from}
                                    onChange={e => setNewHold({ ...newHold, from: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-zinc-700 mb-1">To (Recipient Email)</label>
                                <input
                                    type="text"
                                    placeholder="victim@example.com"
                                    className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                                    value={newHold.to}
                                    onChange={e => setNewHold({ ...newHold, to: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-zinc-700 mb-1">Subject (Exact Match)</label>
                                <input
                                    type="text"
                                    placeholder="Confidential Project"
                                    className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                                    value={newHold.subject}
                                    onChange={e => setNewHold({ ...newHold, subject: e.target.value })}
                                />
                            </div>
                        </div>
                    </div>
                    <button type="submit" className="bg-red-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-red-700">
                        Create Legal Hold
                    </button>
                </form>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm">
                <table className="w-full text-left text-sm text-zinc-600">
                    <thead className="bg-zinc-50 border-b border-zinc-200 font-medium text-zinc-900">
                        <tr>
                            <th className="px-6 py-3 w-16">ID</th>
                            <th className="px-6 py-3">Case Name</th>
                            <th className="px-6 py-3">Reason</th>
                            <th className="px-6 py-3 text-center">Items Held</th>
                            <th className="px-6 py-3">Created By</th>
                            <th className="px-6 py-3">Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                        {holds.map((hold) => (
                            <tr key={hold.id} className="hover:bg-zinc-50/80">
                                <td className="px-6 py-4 font-mono text-xs text-zinc-500">{hold.id}</td>
                                <td className="px-6 py-4 font-medium text-zinc-900">
                                    <Link href={`/admin/hold-view?id=${hold.id}`} className="hover:underline text-indigo-700">
                                        {hold.name}
                                    </Link>
                                </td>
                                <td className="px-6 py-4">{hold.reason}</td>
                                <td className="px-6 py-4 text-center font-mono text-indigo-600 font-bold">{hold.item_count}</td>
                                <td className="px-6 py-4">{hold.created_by}</td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${hold.active ? 'bg-red-100 text-red-700' : 'bg-zinc-100 text-zinc-500'}`}>
                                        {hold.active ? 'Active Hold' : 'Released'}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div >
    );
}

'use client';

import { useState, useEffect } from 'react';
import { useUser } from '@/components/UserContext';
import Link from 'next/link';

interface Assignment {
    id: number;
    message_id: string;
    case_name: string;
    added_at: string;
    review_status: string;
    tags: string[];
}

export default function ReviewDashboard() {
    const { user } = useUser();
    const [assignments, setAssignments] = useState<Assignment[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user?.id) fetchAssignments();
    }, [user]);

    const fetchAssignments = async () => {
        try {
            const res = await fetch(`/api/v1/cases/assignments/${user?.id}`);
            if (res.ok) {
                const data = await res.json();
                setAssignments(data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const updateStatus = async (itemId: number, status: string) => {
        try {
            const res = await fetch(`/api/v1/cases/items/${itemId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status }),
            });
            if (res.ok) {
                setAssignments(prev => prev.map(a => a.id === itemId ? { ...a, review_status: status } : a));
            }
        } catch (err) {
            console.error(err);
        }
    };

    if (loading) return <div className="p-8 text-center text-zinc-500">Loading your assignments...</div>;

    const stats = {
        total: assignments.length,
        completed: assignments.filter(a => a.review_status === 'COMPLETED').length,
        pending: assignments.filter(a => a.review_status === 'PENDING').length,
        inReview: assignments.filter(a => a.review_status === 'IN_REVIEW').length,
    };

    return (
        <div className="max-w-6xl mx-auto space-y-8">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-zinc-900 tracking-tight">My Assignments</h1>
                    <p className="text-zinc-500 mt-1">Review and tag messages assigned to you for investigations.</p>
                </div>
                <div className="text-right">
                    <div className="text-sm font-bold text-zinc-900">{stats.completed}/{stats.total} Completed</div>
                    <div className="w-48 h-2 bg-zinc-100 rounded-full mt-2 overflow-hidden border border-zinc-200">
                        <div
                            className="h-full bg-indigo-600 transition-all duration-500"
                            style={{ width: `${(stats.completed / (stats.total || 1)) * 100}%` }}
                        />
                    </div>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                    { label: 'Pending', count: stats.pending, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100' },
                    { label: 'In Review', count: stats.inReview, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-100' },
                    { label: 'Completed', count: stats.completed, color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-100' },
                ].map((s) => (
                    <div key={s.label} className={`p-4 rounded-xl border ${s.bg} ${s.border} shadow-sm`}>
                        <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-1">{s.label}</div>
                        <div className={`text-2xl font-bold ${s.color}`}>{s.count}</div>
                    </div>
                ))}
            </div>

            <div className="premium-card overflow-hidden">
                <table className="w-full text-left text-sm text-zinc-600">
                    <thead>
                        <tr className="bg-zinc-50/50 border-b border-zinc-100 text-zinc-900 font-semibold">
                            <th className="px-6 py-4">Message ID</th>
                            <th className="px-6 py-4">Case</th>
                            <th className="px-6 py-4">Assigned At</th>
                            <th className="px-6 py-4">Status</th>
                            <th className="px-6 py-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                        {assignments.length === 0 && (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-zinc-400 italic">
                                    No messages assigned to you yet.
                                </td>
                            </tr>
                        )}
                        {assignments.map((a) => (
                            <tr key={a.id} className="hover:bg-zinc-50/50 transition-colors">
                                <td className="px-6 py-4 font-mono text-xs">
                                    <Link href={`/message-view?id=${a.message_id}`} className="text-indigo-600 hover:underline">
                                        {a.message_id.substring(0, 16)}...
                                    </Link>
                                </td>
                                <td className="px-6 py-4 font-medium text-zinc-900">{a.case_name}</td>
                                <td className="px-6 py-4 text-zinc-500">{new Date(a.added_at).toLocaleString()}</td>
                                <td className="px-6 py-4">
                                    <select
                                        value={a.review_status}
                                        onChange={(e) => updateStatus(a.id, e.target.value)}
                                        className={`text-xs font-bold rounded-lg px-2 py-1 border transition-all ${a.review_status === 'COMPLETED' ? 'bg-green-50 border-green-200 text-green-700' :
                                            a.review_status === 'IN_REVIEW' ? 'bg-blue-50 border-blue-200 text-blue-700' :
                                                'bg-amber-50 border-amber-200 text-amber-700'
                                            }`}
                                    >
                                        <option value="PENDING">PENDING</option>
                                        <option value="IN_REVIEW">IN REVIEW</option>
                                        <option value="COMPLETED">COMPLETED</option>
                                    </select>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <Link
                                        href={`/message-view?id=${a.message_id}`}
                                        className="px-3 py-1.5 bg-white border border-zinc-200 text-zinc-600 rounded-lg text-xs font-bold hover:bg-zinc-50 shadow-sm"
                                    >
                                        Review
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

'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

interface HoldItem {
    message_id: string;
    added_at: string;
    subject: string;
    from: string;
    date: string;
}

interface HoldData {
    id: string;
    name: string;
    reason: string;
    created_at: string;
    active: boolean;
    created_by: string;
    filter_criteria: any;
}

import { useUser } from '@/components/UserContext';

export default function HoldDetailPage() {
    const { orgId } = useUser();
    const searchParams = useSearchParams();
    const id = searchParams.get('id');

    const [hold, setHold] = useState<HoldData | null>(null);
    const [items, setItems] = useState<HoldItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [isReleasing, setIsReleasing] = useState(false);

    useEffect(() => {
        if (id && orgId) fetchHoldDetails();
    }, [id, orgId]);

    const fetchHoldDetails = async () => {
        try {
            const res = await fetch(`/api/v1/admin/holds/${id}?org_id=${orgId}`);
            if (res.ok) {
                const data = await res.json();
                setHold(data.hold);
                setItems(data.items);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleReleaseHold = async () => {
        if (!confirm('Are you sure you want to release this legal hold? Items may be eligible for deletion.')) return;

        setIsReleasing(true);
        try {
            const res = await fetch(`/api/v1/admin/holds/${id}/release?org_id=${orgId}`, {
                method: 'POST'
            });
            if (res.ok) {
                fetchHoldDetails(); // Refresh
            } else {
                alert('Failed to release hold');
            }
        } catch (err) {
            console.error(err);
            alert('Error releasing hold');
        } finally {
            setIsReleasing(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-zinc-500">Loading hold data...</div>;
    if (!hold) return <div className="p-8 text-center text-red-500">Legal Hold not found.</div>;

    const criteriaStr = JSON.stringify(JSON.parse(hold.filter_criteria), null, 2);

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-zinc-200 pb-6">
                <div>
                    <Link href="/admin/holds" className="text-xs text-zinc-500 hover:text-zinc-800 mb-2 block">← Back to Legal Holds</Link>
                    <h1 className="text-3xl font-bold text-zinc-900 tracking-tight flex items-center gap-3">
                        {hold.name}
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${hold.active ? 'bg-red-100 text-red-700' : 'bg-zinc-100 text-zinc-500'}`}>
                            {hold.active ? 'Active' : 'Released'}
                        </span>
                    </h1>
                    <p className="text-zinc-500 mt-1">{hold.reason}</p>
                    <div className="flex gap-4 mt-4 text-sm text-zinc-600">
                        <span>ID: {hold.id}</span>
                        <span>Created By: {hold.created_by}</span>
                        <span>Date: {new Date(hold.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Hold Metadata */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="bg-white rounded-lg border border-zinc-200 shadow-sm p-4">
                        <h3 className="font-semibold text-zinc-800 mb-2">Preservation Criteria</h3>
                        <pre className="bg-zinc-50 p-2 rounded text-xs text-zinc-600 overflow-x-auto whitespace-pre-wrap">
                            {criteriaStr}
                        </pre>
                    </div>
                    {hold.active && (
                        <div className="bg-red-50 rounded-lg border border-red-100 p-4">
                            <h3 className="font-semibold text-red-800 mb-2">Actions</h3>
                            <button
                                onClick={handleReleaseHold}
                                disabled={isReleasing}
                                className="w-full py-2 bg-white border border-red-200 text-red-600 rounded text-sm font-medium hover:bg-red-50 disabled:opacity-50"
                            >
                                {isReleasing ? 'Releasing...' : 'Release Hold'}
                            </button>
                            <p className="text-xs text-red-600/70 mt-2 text-center">
                                Warning: Released items may be deleted if retention policy allows.
                            </p>
                        </div>
                    )}
                </div>

                {/* Held Items Table */}
                <div className="lg:col-span-2 bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
                    <div className="p-4 border-b border-zinc-200 bg-zinc-50 flex justify-between items-center">
                        <h3 className="font-semibold text-zinc-800">Held Content ({items.length})</h3>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-zinc-600">
                            <thead className="bg-white border-b border-zinc-100 font-medium text-zinc-900">
                                <tr>
                                    <th className="px-4 py-3">Subject</th>
                                    <th className="px-4 py-3">From</th>
                                    <th className="px-4 py-3">Date</th>
                                    <th className="px-4 py-3 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-zinc-50">
                                {items.length === 0 && (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center text-zinc-400 italic">
                                            No items currently held.
                                        </td>
                                    </tr>
                                )}
                                {items.map((item) => (
                                    <tr key={item.message_id} className="hover:bg-zinc-50">
                                        <td className="px-4 py-3 max-w-xs truncate font-medium text-zinc-900">
                                            {item.subject}
                                        </td>
                                        <td className="px-4 py-3 max-w-[150px] truncate">{item.from}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            {item.date ? new Date(item.date).toLocaleDateString() : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <Link href={`/message-view?id=${item.message_id}`} className="text-indigo-600 hover:underline text-xs">
                                                View
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

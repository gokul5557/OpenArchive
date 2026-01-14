'use client';

import { useState, useEffect } from 'react';
import { useUser } from '@/components/UserContext';

interface Policy {
    id: number;
    name: string;
    domains: string[];
    retention_days: number;
    action: string;
    active: boolean;
}

export default function RetentionPage() {
    const { user, orgId } = useUser();
    const [policies, setPolicies] = useState<Policy[]>([]);
    const [loading, setLoading] = useState(true);
    const [newPolicy, setNewPolicy] = useState({
        name: '',
        domains: '',
        retention_days: 365,
        action: 'PERMANENT_DELETE'
    });

    useEffect(() => {
        fetchPolicies();
    }, [user, orgId]);

    const fetchPolicies = async () => {
        try {
            let url = '/api/v1/admin/retention';
            if (user?.role !== 'super_admin' && orgId) {
                url += `?org_id=${orgId}`;
            }
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                setPolicies(data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const domainsList = newPolicy.domains.split(',').map(d => d.trim()).filter(d => d);
            let url = '/api/v1/admin/retention';
            if (user?.role !== 'super_admin' && orgId) {
                url += `?org_id=${orgId}`;
            }

            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...newPolicy,
                    domains: domainsList
                })
            });

            if (res.ok) {
                setNewPolicy({ name: '', domains: '', retention_days: 365, action: 'PERMANENT_DELETE' });
                fetchPolicies();
            } else {
                alert("Failed to create policy");
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this policy?')) return;
        let url = `/api/v1/admin/retention/${id}`;
        if (user?.role !== 'super_admin' && orgId) {
            url += `?org_id=${orgId}`;
        }
        await fetch(url, { method: 'DELETE' });
        fetchPolicies();
    };

    if (loading) return <div className="p-8">Loading...</div>;

    return (
        <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">
                        {user?.role === 'super_admin' ? 'Global Retention Rules' : 'Organization Retention Policies'}
                    </h1>
                    <p className="text-zinc-500 text-sm">
                        {user?.role === 'super_admin'
                            ? 'Manage system-wide data retention and expiry.'
                            : 'Manage data lifecycle for your domains.'}
                    </p>
                </div>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm p-6 mb-8">
                <h3 className="font-semibold text-zinc-900 mb-4">Add Retention Rule</h3>
                <form onSubmit={handleCreate} className="flex gap-4 items-end flex-wrap">
                    <div className="w-64">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Policy Name</label>
                        <input
                            type="text"
                            required
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="e.g. 7 Year Retention"
                            value={newPolicy.name}
                            onChange={e => setNewPolicy({ ...newPolicy, name: e.target.value })}
                        />
                    </div>
                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Applied Domains (Empty for All)</label>
                        <input
                            type="text"
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="*.corp.com, sales.net"
                            value={newPolicy.domains}
                            onChange={e => setNewPolicy({ ...newPolicy, domains: e.target.value })}
                        />
                    </div>
                    <div className="w-32">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Retention (Days)</label>
                        <input
                            type="number"
                            required
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            value={newPolicy.retention_days}
                            onChange={e => setNewPolicy({ ...newPolicy, retention_days: parseInt(e.target.value) })}
                        />
                    </div>
                    <div className="w-40">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Action</label>
                        <select
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            value={newPolicy.action}
                            onChange={e => setNewPolicy({ ...newPolicy, action: e.target.value })}
                        >
                            <option value="PERMANENT_DELETE">Permanent Delete</option>
                            <option value="ARCHIVE_TIER_2">Move to Cold Storage</option>
                        </select>
                    </div>
                    <button type="submit" className="bg-zinc-900 text-white px-4 py-2 rounded text-sm font-medium hover:bg-zinc-800 transition-colors shadow-sm">
                        Create Rule
                    </button>
                </form>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
                <table className="w-full text-left text-sm text-zinc-600">
                    <thead className="bg-zinc-50 border-b border-zinc-200 font-medium text-zinc-900">
                        <tr>
                            <th className="px-6 py-3">Policy Name</th>
                            <th className="px-6 py-3">Scope (Domains)</th>
                            <th className="px-6 py-3">Retention Period</th>
                            <th className="px-6 py-3">Action</th>
                            <th className="px-6 py-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                        {policies.map((p) => (
                            <tr key={p.id} className="hover:bg-zinc-50/80 transition-colors">
                                <td className="px-6 py-4 font-medium text-zinc-900">{p.name}</td>
                                <td className="px-6 py-4 font-mono text-xs text-zinc-500">
                                    {p.domains && p.domains.length > 0 ? p.domains.join(', ') : <span className="text-zinc-400 italic">Global / All</span>}
                                </td>
                                <td className="px-6 py-4">
                                    <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 px-2 py-1 rounded-full text-xs font-medium">
                                        {p.retention_days} Days
                                    </span>
                                </td>
                                <td className="px-6 py-4 font-mono text-xs">{p.action}</td>
                                <td className="px-6 py-4 text-right">
                                    <button onClick={() => handleDelete(p.id)} className="text-red-500 hover:text-red-700 text-xs font-medium transition-colors">
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {policies.length === 0 && (
                            <tr>
                                <td colSpan={5} className="px-6 py-8 text-center text-zinc-400 italic">
                                    No active retention rules found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

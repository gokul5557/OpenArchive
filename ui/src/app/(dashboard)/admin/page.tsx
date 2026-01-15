'use client';

import { useUser } from '@/components/UserContext';
import { useEffect, useState } from 'react';

export default function AdminPage() {
    const { user, orgId } = useUser();
    const [agents, setAgents] = useState<any[]>([]);
    const [organizations, setOrganizations] = useState<any[]>([]);
    const [stats, setStats] = useState<any>(null);
    const [newOrg, setNewOrg] = useState({ name: '', slug: '', domains: '' });

    useEffect(() => {
        if (user?.role === 'super_admin') {
            fetchAg();
            fetchOrgs();
        } else if (user?.role === 'client_admin' && orgId) {
            fetchStats(orgId);
        }
    }, [user, orgId]);

    const getHeaders = () => {
        const headers: Record<string, string> = {};
        const token = localStorage.getItem('access_token');
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    };

    const fetchAg = () => fetch('/api/v1/admin/agents', { headers: getHeaders() })
        .then(res => {
            if (!res.ok) throw new Error("Failed");
            return res.json();
        })
        .then(data => {
            if (Array.isArray(data)) setAgents(data);
        })
        .catch(console.error);

    const fetchOrgs = () => fetch('/api/v1/admin/organizations', { headers: getHeaders() })
        .then(res => {
            if (!res.ok) throw new Error("Failed");
            return res.json();
        })
        .then(data => {
            if (Array.isArray(data)) setOrganizations(data);
        })
        .catch(console.error);

    const fetchStats = (oid: number) => fetch(`/api/v1/admin/analytics?org_id=${oid}`, { headers: getHeaders() }).then(res => res.json()).then(setStats).catch(console.error);

    const formatBytes = (bytes: number) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${['B', 'KB', 'MB', 'GB', 'TB'][i]}`;
    };

    const handleDeleteOrg = async (id: number) => {
        if (!confirm('Are you sure? This deletes the Organization and all its users/data.')) return;
        try {
            const res = await fetch(`/api/v1/admin/organizations/${id}`, { method: 'DELETE', headers: getHeaders() });
            if (res.ok) fetchOrgs();
            else alert("Delete failed. (Ensure backend supports DELETE /organizations/{id})");
        } catch (e) { console.error(e); }
    };


    const handleCreateOrg = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const res = await fetch('/api/v1/admin/organizations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...getHeaders() },
                body: JSON.stringify({
                    ...newOrg,
                    domains: newOrg.domains.split(',').map(d => d.trim()).filter(d => d)
                }),
            });
            if (res.ok) {
                setNewOrg({ name: '', slug: '', domains: '' });
                fetchOrgs();
            } else {
                alert('Failed to create organization');
            }
        } catch (err) {
            console.error(err);
        }
    };

    if (!user) return null;

    if (user.role === 'client_admin') {
        return (
            <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Enterprise Dashboard</h1>
                        <p className="text-zinc-500 text-sm">Real-time overview of your archive and legal holds.</p>
                    </div>
                    <div className="flex gap-2">
                        <span className="px-3 py-1 bg-green-50 text-green-700 rounded-full text-xs font-semibold border border-green-200 flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                            System Healthy
                        </span>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 relative overflow-hidden group">
                        <h3 className="font-semibold text-zinc-900 mb-2">Total Messages</h3>
                        <p className="text-3xl font-bold text-indigo-600">
                            {stats?.total_messages?.toLocaleString() || '0'}
                        </p>
                        <p className="text-xs text-zinc-500 mt-2">Indexed documents.</p>
                    </div>
                    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 relative overflow-hidden group">
                        <h3 className="font-semibold text-zinc-900 mb-2">My Auditors</h3>
                        <p className="text-3xl font-bold text-indigo-600">
                            --
                        </p>
                        <p className="text-xs text-zinc-500 mt-2">Active users.</p>
                        <a href="/admin/users" className="absolute inset-0"></a>
                    </div>
                    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 relative overflow-hidden group">
                        <h3 className="font-semibold text-zinc-900 mb-2">Active Holds</h3>
                        <p className="text-3xl font-bold text-amber-600">
                            {stats?.active_holds || '0'}
                        </p>
                        <p className="text-xs text-zinc-500 mt-2">
                            {stats?.held_items?.toLocaleString() || '0'} items preserved.
                        </p>
                        <a href="/admin/holds" className="absolute inset-0"></a>
                    </div>
                    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 relative overflow-hidden group">
                        <h3 className="font-semibold text-zinc-900 mb-2">Storage Volume</h3>
                        <p className="text-3xl font-bold text-blue-600">
                            {formatBytes(stats?.storage_volume_bytes || 0)}
                        </p>
                        <p className="text-xs text-zinc-500 mt-2">Estimated consumption.</p>
                    </div>
                </div>

                <div className="mt-8">
                    <h3 className="text-lg font-semibold text-zinc-900 mb-4">Enterprise Actions</h3>
                    <div className="flex gap-4">
                        <a href="/admin/logs" className="px-4 py-3 bg-white border border-zinc-200 rounded-lg shadow-sm hover:border-indigo-300 hover:shadow-md transition-all text-sm font-medium text-zinc-700 flex items-center gap-2">
                            Verify Audit Chain &rarr;
                        </a>
                        <a href="/admin/retention" className="px-4 py-3 bg-white border border-zinc-200 rounded-lg shadow-sm hover:border-indigo-300 hover:shadow-md transition-all text-sm font-medium text-zinc-700 flex items-center gap-2">
                            Manage Retention &rarr;
                        </a>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">System Administration</h1>
                    <p className="text-zinc-500 text-sm">Manage sidecar agents and storage nodes.</p>
                </div>
                <button className="px-4 py-2 bg-indigo-600 text-white rounded text-sm font-medium hover:bg-indigo-700 transition-colors shadow-sm">
                    Generate Global API Key
                </button>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm p-6 mb-8 group">
                <h3 className="font-semibold text-zinc-900 mb-4">Create Organization (Client)</h3>
                <form onSubmit={handleCreateOrg} className="flex gap-4 items-end">
                    <div className="flex-1">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Organization Name</label>
                        <input
                            type="text"
                            required
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            value={newOrg.name}
                            onChange={e => setNewOrg({ ...newOrg, name: e.target.value })}
                        />
                    </div>
                    <div className="w-40">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Slug</label>
                        <input
                            type="text"
                            required
                            placeholder="acme-corp"
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            value={newOrg.slug}
                            onChange={e => setNewOrg({ ...newOrg, slug: e.target.value })}
                        />
                    </div>
                    <div className="flex-1">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Primary Domains</label>
                        <input
                            type="text"
                            placeholder="acme.com, corp.net"
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            value={newOrg.domains}
                            onChange={e => setNewOrg({ ...newOrg, domains: e.target.value })}
                        />
                    </div>
                    <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 transition-colors shadow-sm">
                        Create Org
                    </button>
                </form>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm">
                <div className="px-6 py-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50/50">
                    <h3 className="font-semibold text-zinc-900">Active Organizations (Clients)</h3>
                    <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full border border-indigo-200 font-medium">
                        {organizations.length} Clients
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-zinc-600">
                        <thead className="bg-zinc-50 border-b border-zinc-200 font-medium text-zinc-900">
                            <tr>
                                <th className="px-6 py-3">ID</th>
                                <th className="px-6 py-3">Organization Name</th>
                                <th className="px-6 py-3">Slug</th>
                                <th className="px-6 py-3">Domains</th>
                                <th className="px-6 py-3">Created At</th>
                                <th className="px-6 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-100">
                            {organizations.map((org) => (
                                <tr key={org.id} className="hover:bg-zinc-50/80 transition-colors">
                                    <td className="px-6 py-4 font-mono text-xs text-zinc-500">#{org.id}</td>
                                    <td className="px-6 py-4 font-medium text-zinc-900">{org.name}</td>
                                    <td className="px-6 py-4 font-mono text-xs">{org.slug}</td>
                                    <td className="px-6 py-4 font-mono text-xs text-zinc-500">
                                        {(org.domains || []).join(', ')}
                                    </td>
                                    <td className="px-6 py-4">{new Date(org.created_at).toLocaleDateString()}</td>
                                    <td className="px-6 py-4 text-right">
                                        <button onClick={() => handleDeleteOrg(org.id)} className="text-red-500 hover:text-red-700 text-xs font-medium bg-red-50 px-2 py-1 rounded border border-red-100">
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {organizations.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="px-6 py-8 text-center text-zinc-400 italic">
                                        No organizations found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm">
                <div className="px-6 py-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50/50">
                    <h3 className="font-semibold text-zinc-900">Active Sidecar Agents</h3>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full border border-green-200 font-medium">
                        {agents.filter(a => a.status === 'ONLINE').length}/{agents.length} Online
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-zinc-600">
                        <thead className="bg-zinc-50 border-b border-zinc-200 font-medium text-zinc-900">
                            <tr>
                                <th className="px-6 py-3">Name</th>
                                <th className="px-6 py-3">Hostname</th>
                                <th className="px-6 py-3">Org ID</th>
                                <th className="px-6 py-3">Last Seen</th>
                                <th className="px-6 py-3">Status</th>
                                <th className="px-6 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-100">
                            {agents.map((agent) => (
                                <tr key={agent.id} className="hover:bg-zinc-50/80 transition-colors">
                                    <td className="px-6 py-4 font-medium text-zinc-900">{agent.name}</td>
                                    <td className="px-6 py-4 font-mono text-xs">{agent.hostname}</td>
                                    <td className="px-6 py-4 text-xs font-mono">{agent.org_id || 'System'}</td>
                                    <td className="px-6 py-4">{agent.last_seen || 'Never'}</td>
                                    <td className="px-6 py-4">
                                        {agent.status === 'ONLINE' ? (
                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                <span className="w-1.5 h-1.5 rounded-full bg-green-600"></span>
                                                Online
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-800">
                                                <span className="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
                                                {agent.status}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button className="text-zinc-400 hover:text-zinc-600">•••</button>
                                    </td>
                                </tr>
                            ))}
                            {agents.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-zinc-400 italic">
                                        No agents connected.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg border border-zinc-200 shadow-sm p-6">
                    <h3 className="font-semibold text-zinc-900 mb-4">Storage Configuration</h3>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center py-2 border-b border-zinc-100">
                            <span className="text-zinc-600">Backend Type</span>
                            <span className="font-mono text-zinc-900 bg-zinc-100 px-2 py-1 rounded text-xs">S3 / MinIO</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-zinc-100">
                            <span className="text-zinc-600">Bucket Name</span>
                            <span className="font-mono text-zinc-900 bg-zinc-100 px-2 py-1 rounded text-xs">archive-blobs</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

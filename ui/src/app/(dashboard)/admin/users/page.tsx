'use client';

import { useState, useEffect } from 'react';
import { useUser } from '@/components/UserContext';

interface User {
    id: number;
    username: string;
    role: string;
    domains: string[];
}

export default function UsersPage() {
    const { user, orgId } = useUser();
    const [users, setUsers] = useState<User[]>([]);
    const [organizations, setOrganizations] = useState<any[]>([]);
    const [selectedOrgId, setSelectedOrgId] = useState<any>(orgId);

    // Form state
    const [newUser, setNewUser] = useState({ username: '', password: '', role: 'auditor', domains: '', targetOrgId: '' });
    const [loading, setLoading] = useState(true);

    const getHeaders = () => {
        const headers: Record<string, string> = {};
        const token = localStorage.getItem('access_token');
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    };

    useEffect(() => {
        if (user?.role === 'super_admin') {
            // Fetch All Orgs
            fetch('/api/v1/admin/organizations', { headers: getHeaders() })
                .then(res => res.ok ? res.json() : [])
                .then(data => Array.isArray(data) ? setOrganizations(data) : setOrganizations([]))
                .catch(console.error);

            // Fetch All Client Admins (no org filter = client admins only)
            fetchUsers(null);
        } else if (orgId) {
            // Client Admin: Fetch Org Users
            setSelectedOrgId(orgId);
            fetchUsers(orgId);
        }
    }, [user, orgId]);

    const fetchUsers = async (oid: any) => {
        try {
            let url = '/api/v1/admin/users';
            if (oid) url += `?org_id=${oid}`;
            const res = await fetch(url, { headers: getHeaders() });
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data)) setUsers(data);
                else setUsers([]); // Safety fallback
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        let targetOrg = orgId;
        let role = newUser.role;
        let domains = newUser.domains.split(',').map(d => d.trim()).filter(d => d);

        if (user?.role === 'super_admin') {
            targetOrg = Number(newUser.targetOrgId);
            role = 'client_admin';
            // Validation: For client admin, we might auto-assign all domains or let them type.
            // But if they type, it must match Org domains.
        } else {
            role = 'auditor'; // Client admin can only create auditors
        }

        if (!targetOrg) {
            alert("Organization is required");
            return;
        }

        try {
            const res = await fetch('/api/v1/admin/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...getHeaders() },
                body: JSON.stringify({
                    username: newUser.username,
                    password: newUser.password,
                    role: role,
                    domains: domains,
                    org_id: targetOrg
                }),
            });
            if (res.ok) {
                setNewUser({ username: '', password: '', role: 'auditor', domains: '', targetOrgId: '' });
                // Re-fetch correct list
                fetchUsers(user?.role === 'super_admin' ? null : orgId);
            } else {
                const err = await res.json();
                alert("Failed to create user: " + err.detail);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure?')) return;
        await fetch(`/api/v1/admin/users/${id}`, { method: 'DELETE', headers: getHeaders() });
        fetchUsers(user?.role === 'super_admin' ? null : orgId);
    };

    return (
        <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">User Management</h1>
                    <p className="text-zinc-500 text-sm">Manage auditors and admin access.</p>
                </div>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm p-6 mb-8">
                <h3 className="font-semibold text-zinc-900 mb-4">
                    {user?.role === 'super_admin' ? 'Add Client Admin' : 'Add New Auditor'}
                </h3>
                <form onSubmit={handleSubmit} className="flex gap-4 items-end flex-wrap">
                    <div className="w-48">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Username</label>
                        <input
                            type="text"
                            required
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                            value={newUser.username}
                            onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                        />
                    </div>

                    <div className="w-48">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Password</label>
                        <input
                            type="password"
                            required
                            className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                            value={newUser.password}
                            onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                        />
                    </div>

                    {user?.role === 'super_admin' && (
                        <div className="w-48">
                            <label className="block text-xs font-medium text-zinc-700 mb-1">Organization</label>
                            <select
                                className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                                value={newUser.targetOrgId}
                                required
                                onChange={e => {
                                    const selectedOrg = organizations.find(o => o.id === Number(e.target.value));
                                    setNewUser({
                                        ...newUser,
                                        targetOrgId: e.target.value,
                                        domains: selectedOrg ? (selectedOrg.domains || []).join(', ') : ''
                                    });
                                }}
                            >
                                <option value="">Select Org</option>
                                {organizations.map(o => (
                                    <option key={o.id} value={o.id}>{o.name}</option>
                                ))}
                            </select>
                        </div>
                    )}

                    <div className="w-32">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">Role</label>
                        <input
                            type="text"
                            disabled
                            value={user?.role === 'super_admin' ? 'Client Admin' : 'Auditor'}
                            className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-sm text-zinc-500"
                        />
                    </div>

                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-xs font-medium text-zinc-700 mb-1">
                            Assigned Domains {user?.role === 'super_admin' ? '(Client Admin owns all)' : '(Select Subset)'}
                        </label>
                        {user?.role === 'client_admin' || (user?.role === 'super_admin' && newUser.targetOrgId) ? (
                            <div className="border border-zinc-300 rounded px-3 py-2 text-sm bg-white max-h-32 overflow-y-auto">
                                {(user?.role === 'super_admin'
                                    ? (organizations.find(o => o.id === Number(newUser.targetOrgId))?.domains || [])
                                    : (user?.domains || [])
                                ).map((domain: string) => (
                                    <div key={domain} className="flex items-center gap-2 mb-1 last:mb-0">
                                        <input
                                            type="checkbox"
                                            id={`d-${domain}`}
                                            checked={newUser.domains.includes(domain)}
                                            onChange={(e) => {
                                                const current = newUser.domains ? newUser.domains.split(',').filter(d => d).map(d => d.trim()) : [];
                                                let updated;
                                                if (e.target.checked) updated = [...current, domain];
                                                else updated = current.filter(d => d !== domain);

                                                setNewUser({ ...newUser, domains: updated.join(', ') });
                                            }}
                                            className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                                        />
                                        <label htmlFor={`d-${domain}`} className="text-zinc-700 select-none cursor-pointer">{domain}</label>
                                    </div>
                                ))}
                                {(!newUser.targetOrgId && user?.role === 'super_admin') && <span className="text-zinc-400 text-xs">Select Org first</span>}
                            </div>
                        ) : (
                            <input
                                type="text"
                                placeholder="example.com, corp.net"
                                className="w-full border border-zinc-300 rounded px-3 py-2 text-sm"
                                value={newUser.domains}
                                onChange={e => setNewUser({ ...newUser, domains: e.target.value })}
                            />
                        )}
                    </div>
                    <button type="submit" className="bg-zinc-900 text-white px-4 py-2 rounded text-sm font-medium hover:bg-zinc-800">
                        Create User
                    </button>
                </form>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
                <table className="w-full text-left text-sm text-zinc-600">
                    <thead className="bg-zinc-50 border-b border-zinc-200 font-medium text-zinc-900">
                        <tr>
                            <th className="px-6 py-3">Username</th>
                            <th className="px-6 py-3">Role</th>
                            <th className="px-6 py-3">Domains</th>
                            <th className="px-6 py-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                        {users.map((user) => (
                            <tr key={user.id} className="hover:bg-zinc-50/80 transition-colors">
                                <td className="px-6 py-4 font-medium text-zinc-900">{user.username}</td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium 
                                        ${user.role === 'super_admin' ? 'bg-purple-100 text-purple-700' :
                                            user.role === 'client_admin' ? 'bg-indigo-100 text-indigo-700' :
                                                'bg-blue-100 text-blue-700'}`}>
                                        {user.role.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                    </span>
                                </td>
                                <td className="px-6 py-4 font-mono text-xs text-zinc-500">
                                    {user.domains.length > 0 ? user.domains.join(', ') : <span className="text-zinc-400">All Domains</span>}
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <button onClick={() => handleDelete(user.id)} className="text-red-500 hover:text-red-700 text-xs font-medium transition-colors">
                                        Remove
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

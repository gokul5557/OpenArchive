'use client';

import { useUser } from '@/components/UserContext';
import { useState, useEffect } from 'react';

interface AuditLog {
    id: number;
    username: string;
    action: string;
    details: any;
    timestamp: string;
}

export default function AuditLogsPage() {
    const { orgId } = useUser();
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [chainStatus, setChainStatus] = useState<{ valid: boolean, error?: string } | null>(null);

    useEffect(() => {
        if (orgId) {
            fetchLogs();
            verifyChain();
        }
    }, [orgId]);

    const verifyChain = async () => {
        if (!orgId) return;
        try {
            const res = await fetch(`/api/v1/admin/audit-logs/verify?org_id=${orgId}`);
            if (res.ok) {
                const data = await res.json();
                setChainStatus(data);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const fetchLogs = async () => {
        if (!orgId) return;
        try {
            const res = await fetch(`/api/v1/admin/audit-logs?org_id=${orgId}`);
            if (res.ok) {
                const data = await res.json();
                setLogs(data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">System Audit Logs</h1>
                    <p className="text-zinc-500 text-sm">Track all user actions search history, and exports.</p>
                </div>
                <div className="flex flex-col gap-2 items-end">
                    <div className="flex gap-2">
                        <button onClick={verifyChain} className="px-3 py-1 bg-white border border-zinc-200 text-zinc-700 text-xs font-medium rounded hover:bg-zinc-50 transition-colors shadow-sm">
                            Verify Integrity
                        </button>
                        <button onClick={fetchLogs} className="text-sm text-indigo-600 hover:text-indigo-800">
                            Refresh
                        </button>
                    </div>
                    {chainStatus && (
                        <div className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-bold uppercase tracking-wider ${chainStatus.valid
                            ? 'bg-green-50 border-green-200 text-green-700'
                            : 'bg-red-50 border-red-200 text-red-700 animate-pulse'
                            }`}>
                            <span>{chainStatus.valid ? '🔒 Chain of Custody: Verified' : '⚠️ Integrity Failure Detected'}</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
                <table className="w-full text-left text-sm text-zinc-600">
                    <thead className="bg-zinc-50 border-b border-zinc-200 font-medium text-zinc-900">
                        <tr>
                            <th className="px-6 py-3">Timestamp</th>
                            <th className="px-6 py-3">User</th>
                            <th className="px-6 py-3">Action</th>
                            <th className="px-6 py-3">Details</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                        {logs.map((log) => (
                            <tr key={log.id} className="hover:bg-zinc-50/80">
                                <td className="px-6 py-4 font-mono text-xs text-zinc-500">
                                    {new Date(log.timestamp).toLocaleString()}
                                </td>
                                <td className="px-6 py-4 font-medium text-zinc-900">{log.username}</td>
                                <td className="px-6 py-4">
                                    <span className="px-2 py-1 bg-zinc-100 text-zinc-700 rounded text-xs font-mono font-medium border border-zinc-200">
                                        {log.action}
                                    </span>
                                </td>
                                <td className="px-6 py-4 font-mono text-xs text-zinc-500 truncate max-w-md">
                                    {JSON.stringify(log.details)}
                                </td>
                            </tr>
                        ))}
                        {logs.length === 0 && !loading && (
                            <tr>
                                <td colSpan={4} className="px-6 py-8 text-center text-zinc-400">
                                    No audit logs found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

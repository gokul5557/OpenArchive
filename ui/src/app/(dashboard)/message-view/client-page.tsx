'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useUser } from '@/components/UserContext';

interface MessageContent {
    id: string;
    content?: string;
    content_html?: string;
    content_b64?: string;
    raw_eml?: string;
    error?: string;
}

export default function MessageDetail() {
    const searchParams = useSearchParams();
    const id = searchParams.get('id');
    const { orgId } = useUser();

    const [data, setData] = useState<MessageContent | null>(null);
    const [thread, setThread] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [showRedacted, setShowRedacted] = useState(false);
    const [redactedContent, setRedactedContent] = useState<string | null>(null);
    const [integrityStatus, setIntegrityStatus] = useState<'LOADING' | 'VALID' | 'TAMPERED' | 'UNAVAILABLE'>('LOADING');
    const [activeTab, setActiveTab] = useState<'message' | 'headers' | 'source'>('message');

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

    useEffect(() => {
        if (!id || !orgId) return;
        setLoading(true);

        // Fetch Message
        fetch(`/api/v1/messages/${id}?org_id=${orgId}`)
            .then((res) => {
                if (!res.ok) throw new Error(res.statusText);
                return res.json();
            })
            .then((data) => {
                setData(data);
                if (!data.error) {
                    logAudit('VIEW_MESSAGE', { message_id: id });
                }
            })
            .catch((err) => setData({ id, error: "Failed to load message." }))
            .finally(() => setLoading(false));

        // Fetch Thread
        fetch(`/api/v1/messages/${id}/thread?org_id=${orgId}`)
            .then((res) => res.json())
            .then((data) => setThread(Array.isArray(data) ? data : []))
            .catch((err) => console.error("Thread fetch error:", err));

        // Fetch Redacted Preview
        fetch(`/api/v1/messages/${id}/preview-redacted?org_id=${orgId}`)
            .then(res => res.json())
            .then(data => setRedactedContent(data.redacted))
            .catch(console.error);

        // Fetch Integrity Status
        fetch(`/api/v1/messages/${id}/verify?org_id=${orgId}`)
            .then(res => res.json())
            .then(data => setIntegrityStatus(data.status))
            .catch(() => setIntegrityStatus('UNAVAILABLE'));
    }, [id, orgId]);

    if (loading) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center text-zinc-400 text-sm">
                Loading...
            </div>
        );
    }

    if (!data || data.error) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center text-red-500 text-sm">
                Error: {data?.error || "Message not found"}
            </div>
        );
    }

    const content = data.content || (data.content_b64 ? atob(data.content_b64) : "No content.");

    return (
        <div className="min-h-screen bg-white text-zinc-900 font-sans pb-20">
            <div className="max-w-4xl mx-auto px-6 py-12">
                <Link href="/" className="inline-flex items-center text-zinc-500 hover:text-zinc-900 mb-8 text-sm transition-colors no-underline">
                    ← Back
                </Link>

                <div className="mb-8">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h1 className="text-2xl font-semibold text-zinc-900 mb-2 tracking-tight">Message Details</h1>
                            <div className="flex flex-col gap-1 text-sm text-zinc-500 font-mono">
                                <span>ID: {id}</span>
                                <div className="flex items-center gap-2 mt-1">
                                    {integrityStatus === 'VALID' && (
                                        <span className="flex items-center gap-1 text-[10px] font-bold text-green-600 bg-green-50 px-1.5 py-0.5 rounded border border-green-200">
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                                            Integrity Verified
                                        </span>
                                    )}
                                    {integrityStatus === 'TAMPERED' && (
                                        <span className="flex items-center gap-1 text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded border border-red-200 animate-pulse">
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                                            WARNING: Tampering Detected
                                        </span>
                                    )}
                                    {integrityStatus === 'LOADING' && (
                                        <span className="text-[10px] text-zinc-400">Verifying signature...</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Tabs */}
                    <div className="flex gap-1 border-b border-zinc-200 mb-0">
                        <button
                            onClick={() => setActiveTab('message')}
                            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'message' ? 'border-zinc-900 text-zinc-900' : 'border-transparent text-zinc-500 hover:text-zinc-700'}`}
                        >
                            Message Body
                        </button>
                        <button
                            onClick={() => setActiveTab('headers')}
                            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'headers' ? 'border-zinc-900 text-zinc-900' : 'border-transparent text-zinc-500 hover:text-zinc-700'}`}
                        >
                            Headers
                        </button>
                        <button
                            onClick={() => setActiveTab('source')}
                            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'source' ? 'border-zinc-900 text-zinc-900' : 'border-transparent text-zinc-500 hover:text-zinc-700'}`}
                        >
                            Original Source
                        </button>
                    </div>
                </div>

                {/* Tab Content */}
                <div className="min-h-[400px]">
                    {activeTab === 'message' && (
                        <>
                            <div className="flex justify-end mb-4">
                                <button
                                    onClick={() => setShowRedacted(!showRedacted)}
                                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors border ${showRedacted
                                        ? 'bg-red-50 border-red-200 text-red-600'
                                        : 'bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50'
                                        }`}
                                >
                                    {showRedacted ? '🔒 Redaction Active' : '🔓 Redaction Preview'}
                                </button>
                            </div>
                            <div className={`font-mono text-sm leading-relaxed whitespace-pre-wrap p-6 rounded-md border transition-all ${showRedacted
                                ? 'bg-zinc-900 text-zinc-100 border-zinc-800'
                                : 'bg-zinc-50 text-zinc-800 border-zinc-200'
                                }`}>
                                {showRedacted ? (redactedContent || "Processing...") : content}
                            </div>
                        </>
                    )}

                    {activeTab === 'headers' && (
                        <div className="font-mono text-xs leading-relaxed whitespace-pre-wrap p-6 rounded-md border bg-zinc-900 text-zinc-300 border-zinc-800 overflow-x-auto">
                            {data.raw_eml ? data.raw_eml.split('\n\n')[0] : "No headers available"}
                        </div>
                    )}

                    {activeTab === 'source' && (
                        <div className="font-mono text-xs leading-relaxed whitespace-pre-wrap p-6 rounded-md border bg-zinc-900 text-zinc-300 border-zinc-800 overflow-x-auto">
                            {data.raw_eml || "No source available"}
                        </div>
                    )}
                </div>

                {/* Thread Overview */}
                {thread.length > 1 && (
                    <div className="mt-12 border-t border-zinc-100 pt-8">
                        <h3 className="text-sm font-semibold text-zinc-900 mb-4 uppercase tracking-wider">Conversation History</h3>
                        <div className="space-y-3">
                            {thread.map((msg) => (
                                <Link
                                    key={msg.id}
                                    href={`/message-view?id=${msg.id}`}
                                    className={`block p-4 rounded-md border transition-all no-underline ${msg.id === id
                                        ? 'bg-indigo-50 border-indigo-200 ring-1 ring-indigo-200'
                                        : 'bg-white border-zinc-200 hover:border-zinc-300'
                                        }`}
                                >
                                    <div className="flex justify-between items-start gap-4">
                                        <div className="min-w-0">
                                            <div className="text-xs font-semibold text-zinc-900 truncate">{msg.subject || "(No Subject)"}</div>
                                            <div className="text-[10px] text-zinc-500 mt-0.5 truncate">From: {msg.from}</div>
                                        </div>
                                        <div className="text-[10px] text-zinc-400 whitespace-nowrap">
                                            {msg.date ? new Date(msg.date).toLocaleDateString() : 'No date'}
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </div>
                )}

                <div className="mt-8 text-center text-zinc-300 text-xs">
                    End-to-End Encrypted Storage
                </div>
            </div>
        </div>
    );
}

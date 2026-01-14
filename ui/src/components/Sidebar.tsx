'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUser } from './UserContext';

const Icons = {
    Dashboard: () => (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>
    ),
    Audit: () => (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
    ),
    Cases: () => (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7a2 2 0 00-2-2h-5l-2-2H5a2 2 0 00-2 2z"></path></svg>
    ),
    Holds: () => (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
    ),
    Retention: () => (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
    ),
    Users: () => (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
    ),
    Logs: () => (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
    ),
    System: () => (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
    )
};

export default function Sidebar() {
    const pathname = usePathname();
    const { user, isSidebarCollapsed, toggleSidebar } = useUser();

    let links = [
        { href: '/', label: 'Overview', icon: <Icons.Dashboard /> },
    ];

    if (user?.role === 'super_admin') {
        links = [
            ...links,
            { href: '/admin', label: 'System Health & Orgs', icon: <Icons.Dashboard /> },
            { href: '/admin/users', label: 'Client Admins', icon: <Icons.Users /> },
            { href: '/admin/system/agents', label: 'Sidecar Agents', icon: <Icons.System /> }, // Assuming agents are separate or part of dashboard, but user asked for "Agents" visibility.
            // "Agents" is currently displayed in AdminPage. Do we need a separate link? 
            // The dashboard /admin already shows agents. So maybe just keep Overview.
            // But let's be explicit if they want navigation.
            // Actually, currently /admin IS the dashboard with agents. 
            // Let's stick to Dashboard.
            // "Global Retention Rule"
            { href: '/admin/retention', label: 'Global Retention Rule', icon: <Icons.Retention /> },
            // NO Cases, NO Holds, NO Global Users (only client admins)
        ];
    } else if (user?.role === 'client_admin') {
        links = [
            { href: '/admin', label: 'Dashboard', icon: <Icons.Dashboard /> }, // Org Overview
            { href: '/admin/users', label: 'Members', icon: <Icons.Users /> }, // Manage Auditors
            { href: '/audit', label: 'Archive Search', icon: <Icons.Audit /> },
            { href: '/admin/cases', label: 'Cases', icon: <Icons.Cases /> },
            { href: '/admin/holds', label: 'Legal Holds', icon: <Icons.Holds /> },
            { href: '/admin/retention', label: 'Retention', icon: <Icons.Retention /> },
            // Client Admins may want to see audit logs for their org? Assuming /admin/logs handles org-scoping
            { href: '/admin/logs', label: 'Audit Logs', icon: <Icons.Logs /> },
        ];
    } else if (user?.role === 'auditor') {
        links = [
            { href: '/audit', label: 'Search', icon: <Icons.Audit /> }, // Auditors start at search mainly?
            { href: '/admin/review', label: 'My Assignments', icon: <Icons.Logs /> },
            { href: '/admin/cases', label: 'Cases', icon: <Icons.Cases /> },
            { href: '/admin/holds', label: 'Legal Holds', icon: <Icons.Holds /> },
        ];
    }

    return (
        <aside className={`${isSidebarCollapsed ? 'w-20' : 'w-64'} bg-white border-r border-zinc-200 h-screen flex flex-col fixed left-0 top-0 transition-all duration-300 z-50`}>
            {/* Header */}
            <div className="p-6 h-20 flex items-center justify-between border-b border-zinc-100">
                {!isSidebarCollapsed && (
                    <div className="flex items-center gap-2.5 group">
                        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-200 group-hover:scale-110 transition-transform duration-200">
                            <span className="text-white text-lg font-bold">A</span>
                        </div>
                        <span className="font-bold text-zinc-900 tracking-tight text-lg">OpenArchive</span>
                    </div>
                )}
                {isSidebarCollapsed && (
                    <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-200 mx-auto">
                        <span className="text-white text-lg font-bold">A</span>
                    </div>
                )}
                {!isSidebarCollapsed && (
                    <button onClick={toggleSidebar} className="p-1.5 rounded-md hover:bg-zinc-100 text-zinc-400 hover:text-zinc-600 transition-colors">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7"></path></svg>
                    </button>
                )}
            </div>

            {/* Nav */}
            <nav className="flex-1 px-3 py-4 space-y-1">
                {links.map((link) => {
                    const isActive = pathname === link.href;
                    return (
                        <Link
                            key={link.href}
                            href={link.href}
                            className={`flex items-center gap-3.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${isActive
                                ? 'bg-indigo-50 text-indigo-700 shadow-sm shadow-indigo-100/50'
                                : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900'
                                } ${isSidebarCollapsed ? 'justify-center' : ''}`}
                        >
                            <span className={`${isActive ? 'text-indigo-600' : 'text-zinc-400 group-hover:text-zinc-900'}`}>
                                {link.icon}
                            </span>
                            {!isSidebarCollapsed && <span>{link.label}</span>}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="p-4 bg-zinc-50/50 border-t border-zinc-100">
                <div className={`flex items-center ${isSidebarCollapsed ? 'justify-center' : 'gap-3 px-1'}`}>
                    <div className="w-9 h-9 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-xs font-bold text-zinc-600 shadow-sm ring-1 ring-zinc-100">
                        {user ? user.username.substring(0, 2).toUpperCase() : '??'}
                    </div>
                    {!isSidebarCollapsed && (
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-bold text-zinc-900 truncate">{user?.username || 'Guest'}</p>
                            <p className="text-[10px] font-medium text-zinc-400 uppercase tracking-widest">{user?.role || 'Guest'}</p>
                        </div>
                    )}
                </div>
                {isSidebarCollapsed && (
                    <button onClick={toggleSidebar} className="mt-4 mx-auto block p-2 rounded-full bg-indigo-600 text-white shadow-lg hover:scale-110 transition-transform">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 5l7 7-7 7M5 5l7 7-7 7"></path></svg>
                    </button>
                )}
            </div>
        </aside>
    );
}

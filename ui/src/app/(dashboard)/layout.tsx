'use client';

import Sidebar from '@/components/Sidebar';
import Navbar from '@/components/Navbar';
import { useUser } from '@/components/UserContext';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { isSidebarCollapsed } = useUser();

    return (
        <div className="min-h-screen bg-zinc-50 flex">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                <Navbar />
                <main className={`flex-1 ${isSidebarCollapsed ? 'ml-16' : 'ml-64'} p-4 overflow-y-auto transition-all duration-300`}>
                    {children}
                </main>
            </div>
        </div>
    );
}

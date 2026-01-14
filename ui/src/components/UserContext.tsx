'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface User {
    id: number;
    username: string;
    role: string; // 'super_admin', 'client_admin', 'auditor'
    org_id: number;
    domains: string[];
}

interface UserContextType {
    user: User | null;
    userDomain: string | null;
    login: (user: User) => void;
    logout: () => void;
    orgId: number | null;
    isSidebarCollapsed: boolean;
    toggleSidebar: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const router = useRouter();

    // Persist Login (Mock)
    useEffect(() => {
        const stored = localStorage.getItem('oa_user');
        if (stored) {
            setUser(JSON.parse(stored));
        }
    }, []);

    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

    const login = (userData: User) => {
        setUser(userData);
        localStorage.setItem('oa_user', JSON.stringify(userData));
    };

    const logout = () => {
        setUser(null);
        localStorage.removeItem('oa_user');
        router.push('/login');
    };

    const toggleSidebar = () => setIsSidebarCollapsed(!isSidebarCollapsed);

    // Derived State
    const orgId = user?.org_id || null;

    const userDomain = (user?.role === 'auditor' || user?.role === 'client_admin') && user.domains?.length > 0
        ? user.domains.join(',')
        : null;

    return (
        <UserContext.Provider value={{ user, userDomain, login, logout, orgId, isSidebarCollapsed, toggleSidebar }}>
            {children}
        </UserContext.Provider>
    );
}

export function useUser() {
    const context = useContext(UserContext);
    if (context === undefined) {
        throw new Error('useUser must be used within a UserProvider');
    }
    return context;
}

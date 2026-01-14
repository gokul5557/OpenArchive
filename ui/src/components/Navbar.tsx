import { useState } from 'react';
import { useUser } from './UserContext';

export default function Navbar() {
    const { user, userDomain, logout, isSidebarCollapsed } = useUser();
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

    // Placeholder image based on username initial
    const avatarChar = user?.username ? user.username.charAt(0).toUpperCase() : '?';

    return (
        <header className={`h-20 bg-white/80 backdrop-blur-md border-b border-zinc-100 flex items-center justify-between px-8 sticky top-0 z-40 transition-all duration-300 ${isSidebarCollapsed ? 'ml-20' : 'ml-64'}`}>
            <div className="flex items-center gap-4">
                <div className="text-zinc-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
                </div>
                <div className="text-sm font-medium text-zinc-400 flex items-center gap-2">
                    <span className="text-zinc-900">App</span>
                    <span className="text-zinc-300">/</span>
                    <span className="text-zinc-500">Dashboard</span>
                    {userDomain && (
                        <span className="ml-2 bg-indigo-50 text-indigo-600 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border border-indigo-100 italic">
                            {userDomain}
                        </span>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-6">
                <button className="relative p-2 text-zinc-400 hover:text-zinc-900 transition-colors group">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg>
                    <span className="absolute top-2 right-2 w-2 h-2 bg-indigo-500 rounded-full border-2 border-white group-hover:scale-110 transition-transform"></span>
                </button>

                <div className="h-8 w-px bg-zinc-100"></div>

                <div className="relative">
                    <button
                        onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                        className="flex items-center gap-3 hover:bg-zinc-50 p-1.5 rounded-xl transition-all"
                    >
                        <div className="text-right hidden sm:block">
                            <p className="text-sm font-bold text-zinc-900 leading-tight">{user?.username || 'Guest'}</p>
                            <p className="text-[10px] font-medium text-zinc-400 uppercase tracking-widest">{user?.role || 'Guest'}</p>
                        </div>
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-lg shadow-lg shadow-indigo-100 ring-2 ring-white">
                            {avatarChar}
                        </div>
                    </button>

                    {isUserMenuOpen && (
                        <>
                            <div
                                className="fixed inset-0 z-10"
                                onClick={() => setIsUserMenuOpen(false)}
                            ></div>
                            <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-2xl border border-zinc-100 py-2 z-20 animate-in fade-in slide-in-from-top-2 duration-200">
                                <div className="px-4 py-3 border-b border-zinc-50 mb-1">
                                    <p className="text-xs font-medium text-zinc-400 uppercase tracking-widest mb-1">Signed in as</p>
                                    <p className="text-sm font-bold text-zinc-900">{user?.username}</p>
                                </div>
                                <button className="w-full text-left px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 transition-colors flex items-center gap-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
                                    Profile Settings
                                </button>
                                <button
                                    onClick={logout}
                                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
                                    Log out
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </header>
    );
}

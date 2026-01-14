'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/components/UserContext';

export default function LoginPage() {
    const router = useRouter();
    const { login } = useUser();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        try {
            const res = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (res.ok) {
                const data = await res.json();

                // data = { access_token, user, token_type } OR { id, ... } for hardcoded admin
                // Hardcoded admin returns flat user object. 
                // DB user returns { access_token, user }

                let userObj = data.user || data;
                let token = data.access_token || 'mock_token_for_admin';

                localStorage.setItem('user_id', userObj.id.toString());
                localStorage.setItem('access_token', token);

                login(userObj);

                if (userObj.role === 'auditor') router.push('/audit');
                else router.push('/admin');
            } else {
                setError('Invalid credentials');
            }
        } catch (err) {
            console.error(err);
            setError('System error');
        }
    };

    return (
        <div className="min-h-screen bg-zinc-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-md">
                <div className="flex justify-center text-4xl">⚡</div>
                <h2 className="mt-6 text-center text-3xl font-extrabold text-zinc-900">
                    Sign in to OpenArchive
                </h2>
            </div>

            <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
                <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-zinc-200">
                    <form className="space-y-6" onSubmit={handleLogin}>
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-zinc-700">
                                Username
                            </label>
                            <div className="mt-1">
                                <input
                                    id="username"
                                    name="username"
                                    type="text"
                                    required
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="appearance-none block w-full px-3 py-2 border border-zinc-300 rounded-md shadow-sm placeholder-zinc-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-zinc-900"
                                />
                            </div>
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-zinc-700">
                                Password
                            </label>
                            <div className="mt-1">
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="appearance-none block w-full px-3 py-2 border border-zinc-300 rounded-md shadow-sm placeholder-zinc-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-zinc-900"
                                />
                            </div>
                        </div>

                        {error && (
                            <div className="text-red-600 text-sm font-medium text-center">
                                {error}
                            </div>
                        )}

                        <div>
                            <button
                                type="submit"
                                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-zinc-900 hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-zinc-500"
                            >
                                Sign in
                            </button>
                        </div>
                    </form>

                    <div className="mt-6">
                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-zinc-300" />
                            </div>
                            <div className="relative flex justify-center text-sm">
                                <span className="px-2 bg-white text-zinc-500">
                                    Demo Credentials
                                </span>
                            </div>
                        </div>

                        <div className="mt-6 grid grid-cols-2 gap-3 text-xs text-center text-zinc-500">
                            <div>
                                <p className="font-bold">Super Admin</p>
                                <p>admin / admin</p>
                            </div>
                            <div>
                                <p className="font-bold">Client Admin</p>
                                <p>client / client</p>
                            </div>
                            <div className="col-span-2">
                                <p className="font-bold">Auditor</p>
                                <p>auditor / any</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

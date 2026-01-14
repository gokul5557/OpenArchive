'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useUser } from '@/components/UserContext';

function StatCard({ title, value, sub, icon, trend }: any) {
  return (
    <div className="bg-white p-6 rounded-lg border border-zinc-200 shadow-sm flex items-start justify-between">
      <div>
        <p className="text-zinc-500 text-sm font-medium mb-1">{title}</p>
        <h3 className="text-3xl font-bold text-zinc-900 mb-2">{value}</h3>
        <p className={`text-xs ${trend === 'up' ? 'text-green-600' : 'text-zinc-400'}`}>
          {sub}
        </p>
      </div>
      <div className="p-3 bg-zinc-50 rounded-md text-xl">
        {icon}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { userDomain } = useUser();

  // Mock Data - Dynamic based on domain
  const getStats = (domain: string | null) => {
    if (domain) {
      return [
        { title: 'Domain Emails', value: '4.5K', sub: `For ${domain}`, icon: '📨', trend: 'up' },
        { title: 'Storage Used', value: '12 GB', sub: 'Allocated Quota: 50GB', icon: '💾', trend: 'neutral' },
        { title: 'Active Agents', value: '2', sub: 'Domain-specific relays', icon: '🤖', trend: 'up' },
        { title: 'Ingestion Rate', value: '2/sec', sub: 'Steady flow', icon: '⚡', trend: 'up' },
      ];
    }
    return [
      { title: 'Total Emails', value: '1.2M', sub: '+12.5% this month', icon: '📨', trend: 'up' },
      { title: 'Storage Used', value: '450 GB', sub: 'MinIO Cluster A', icon: '💾', trend: 'neutral' },
      { title: 'Active Agents', value: '8', sub: 'All systems operational', icon: '🤖', trend: 'up' },
      { title: 'Ingestion Rate', value: '45/sec', sub: 'Peak load: 120/sec', icon: '⚡', trend: 'up' },
    ];
  };

  const stats = getStats(userDomain);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-zinc-900 tracking-tight">System Overview</h2>
        <p className="text-zinc-500">
          {userDomain ? `Monitoring domain: @${userDomain}` : 'Real-time monitoring of archive performance.'}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <StatCard key={i} {...stat} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-96">
        <div className="lg:col-span-2 bg-white p-6 rounded-lg border border-zinc-200 shadow-sm flex flex-col">
          <h3 className="text-lg font-semibold text-zinc-900 mb-6">Ingestion Volume (24h)</h3>
          <div className="flex-1 flex items-end gap-2 px-4">
            {/* Mock Chart Bars */}
            {[...Array(24)].map((_, i) => (
              <div
                key={i}
                className="bg-indigo-500 rounded-t hover:bg-indigo-600 transition-colors w-full"
                style={{ height: `${Math.random() * 80 + 20}%` }}
              ></div>
            ))}
          </div>
          <div className="flex justify-between mt-4 text-xs text-zinc-400 font-mono">
            <span>00:00</span>
            <span>12:00</span>
            <span>23:59</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-zinc-200 shadow-sm">
          <h3 className="text-lg font-semibold text-zinc-900 mb-6">Recent Alerts</h3>
          <div className="space-y-4">
            <div className="flex gap-3 items-start">
              <div className="w-2 h-2 rounded-full bg-red-500 mt-2"></div>
              <div>
                <p className="text-sm font-medium text-zinc-900">Agent Connection Lost</p>
                <p className="text-xs text-zinc-500">mx-03.ny.internal failed heartbeats.</p>
                <p className="text-[10px] text-zinc-400 mt-1">10 mins ago</p>
              </div>
            </div>
            <div className="flex gap-3 items-start">
              <div className="w-2 h-2 rounded-full bg-yellow-500 mt-2"></div>
              <div>
                <p className="text-sm font-medium text-zinc-900">Storage Warning</p>
                <p className="text-xs text-zinc-500">Volume /mnt/data is 85% full.</p>
                <p className="text-[10px] text-zinc-400 mt-1">2 hours ago</p>
              </div>
            </div>
            <div className="flex gap-3 items-start">
              <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
              <div>
                <p className="text-sm font-medium text-zinc-900">Backup Completed</p>
                <p className="text-xs text-zinc-500">Daily snapshot took 4m 30s.</p>
                <p className="text-[10px] text-zinc-400 mt-1">5 hours ago</p>
              </div>
            </div>
          </div>

          <button className="w-full mt-6 py-2 border border-zinc-200 text-sm font-medium text-zinc-600 rounded hover:bg-zinc-50 transition-colors">
            View All Alerts
          </button>
        </div>
      </div>

      {/* Quick Search Section */}
      <div className="bg-white p-8 rounded-lg border border-zinc-200 shadow-sm text-center">
        <h3 className="text-lg font-medium text-zinc-900 mb-2">Need to find an email?</h3>
        <p className="text-zinc-500 mb-6">Search across 1.2M archived messages instantly.</p>
        <Link href="/audit" className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-zinc-900 hover:bg-zinc-800 transition-colors">
          Go to Search
        </Link>
      </div>
    </div>
  );
}

'use client';

import React from 'react';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import { useAuth } from '@/lib/authContext';
import { auth } from '@/lib/firebase';
import { signOut } from 'firebase/auth';
import { useRouter } from 'next/navigation';

export default function AuthorityDashboard() {
  const { profile } = useAuth();
  const router = useRouter();

  const handleSignout = async () => {
    await signOut(auth);
    router.push('/authority/signin');
  };

  return (
    <ProtectedRoute requireAuthority={true}>
      <div className="min-h-screen bg-gray-900 text-white p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8 border-b border-gray-700 pb-4">
            <div>
              <h1 className="text-3xl font-bold text-red-400">Authority Dashboard</h1>
              <p className="text-gray-400">Welcome, {profile?.name || 'Official'}</p>
            </div>
            <button
              onClick={handleSignout}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors border border-gray-700"
            >
              Sign Out
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
              <h3 className="text-lg font-medium text-gray-300 mb-2">Pending Verifications</h3>
              <p className="text-3xl font-bold text-white">0</p>
            </div>
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
              <h3 className="text-lg font-medium text-gray-300 mb-2">Active Alerts</h3>
              <p className="text-3xl font-bold text-red-400">0</p>
            </div>
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
              <h3 className="text-lg font-medium text-gray-300 mb-2">Network Status</h3>
              <p className="text-3xl font-bold text-cyan-400">Nominal</p>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

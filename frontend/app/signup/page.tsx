'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createUserWithEmailAndPassword, updateProfile } from 'firebase/auth';
import { doc, setDoc } from 'firebase/firestore';
import { auth, db } from '@/lib/firebase';
import Link from 'next/link';

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      return setError('Passwords do not match');
    }

    setLoading(true);

    try {
      // 1. Create the user in Firebase Auth
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;

      // 2. Update their display name
      await updateProfile(user, { displayName: name });

      // 3. Create the Firestore profile
      await setDoc(doc(db, 'users', user.uid), {
        uid: user.uid,
        name: name,
        email: email,
        photoURL: null,
        role: 'user', // strictly enforced
        createdAt: new Date().toISOString(),
        lastLoginAt: new Date().toISOString(),
      });

      // 4. Redirect to dashboard
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to create an account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#03111F] relative overflow-hidden py-12">
      {/* Atmospheric glow layers */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-[rgba(0,229,255,0.04)] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-[rgba(0,90,140,0.08)] rounded-full blur-[100px] pointer-events-none" />

      {/* Scanline overlay for atmosphere */}
      <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_3px,rgba(0,229,255,0.01)_3px,rgba(0,229,255,0.01)_4px)] pointer-events-none" />

      <div className="z-10 w-full max-w-md px-8 py-10 bg-[rgba(6,24,39,0.85)] backdrop-blur-xl border border-[rgba(0,213,255,0.14)] rounded-2xl shadow-2xl shadow-black/40 my-auto">
        {/* Logo / Brand */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-[rgba(0,229,255,0.08)] border border-[rgba(0,229,255,0.20)] mb-4">
            <svg viewBox="0 0 32 32" className="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="16" cy="16" r="14" stroke="#00E5FF" strokeWidth="1.5" strokeDasharray="4 2" className="animate-spin" style={{animationDuration: '20s'}} />
              <circle cx="16" cy="16" r="8" stroke="#27E0C3" strokeWidth="1.5" opacity="0.6" />
              <circle cx="16" cy="16" r="3" fill="#00E5FF" />
              <path d="M16 6V4M16 28V26M6 16H4M28 16H26" stroke="#00E5FF" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#E8F4FD] mb-1">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00E5FF] to-[#27E0C3]">Vayu</span>Net
          </h1>
          <p className="text-xs text-[#7BA4BC] uppercase tracking-widest font-medium">Platform Access Request</p>
        </div>

        {error && (
          <div className="mb-6 p-3.5 bg-[rgba(255,68,68,0.08)] border border-[rgba(255,68,68,0.25)] rounded-xl text-[#FF7070] text-xs font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-[#7BA4BC] uppercase tracking-wider mb-1.5" htmlFor="name">Operator Name</label>
            <input
              id="name"
              type="text"
              required
              className="w-full px-4 py-3 bg-[#03111F] border border-[rgba(0,213,255,0.18)] rounded-xl text-[#E8F4FD] text-sm placeholder:text-[#2E5470] focus:ring-1 focus:ring-[#00E5FF] focus:border-[#00E5FF] outline-none transition-all"
              placeholder="e.g. Jane Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[#7BA4BC] uppercase tracking-wider mb-1.5" htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              required
              className="w-full px-4 py-3 bg-[#03111F] border border-[rgba(0,213,255,0.18)] rounded-xl text-[#E8F4FD] text-sm placeholder:text-[#2E5470] focus:ring-1 focus:ring-[#00E5FF] focus:border-[#00E5FF] outline-none transition-all"
              placeholder="operator@vayunet.in"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[#7BA4BC] uppercase tracking-wider mb-1.5" htmlFor="password">Access Key (Password)</label>
            <input
              id="password"
              type="password"
              required
              className="w-full px-4 py-3 bg-[#03111F] border border-[rgba(0,213,255,0.18)] rounded-xl text-[#E8F4FD] text-sm placeholder:text-[#2E5470] focus:ring-1 focus:ring-[#00E5FF] focus:border-[#00E5FF] outline-none transition-all"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-[#7BA4BC] uppercase tracking-wider mb-1.5" htmlFor="confirmPassword">Verify Access Key</label>
            <input
              id="confirmPassword"
              type="password"
              required
              className="w-full px-4 py-3 bg-[#03111F] border border-[rgba(0,213,255,0.18)] rounded-xl text-[#E8F4FD] text-sm placeholder:text-[#2E5470] focus:ring-1 focus:ring-[#00E5FF] focus:border-[#00E5FF] outline-none transition-all"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 mt-2 bg-gradient-to-r from-[#0066CC] to-[#004A99] hover:from-[#0077EE] hover:to-[#0055BB] text-white font-semibold rounded-xl shadow-lg shadow-[rgba(0,100,204,0.25)] transition-all flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed border border-[rgba(0,150,255,0.30)]"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <span>Request Clearances</span>
            )}
          </button>
        </form>

        <div className="mt-8 text-center text-xs text-[#2E5470]">
          Already an authorized operator?{' '}
          <Link href="/signin" className="text-[#00E5FF] hover:text-[#27E0C3] transition-colors font-semibold">
            Authenticate here
          </Link>
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signInWithEmailAndPassword, signInWithPopup, GoogleAuthProvider } from 'firebase/auth';
import { doc, getDoc, setDoc } from 'firebase/firestore';
import { auth, db } from '@/lib/firebase';
import Link from 'next/link';

export default function SigninPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signInWithEmailAndPassword(auth, email, password);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to sign in');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignin = async () => {
    setError('');
    setLoading(true);

    try {
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(auth, provider);
      const user = result.user;

      // Check if profile exists, if not create it
      const docRef = doc(db, 'users', user.uid);
      const docSnap = await getDoc(docRef);

      if (!docSnap.exists()) {
        await setDoc(docRef, {
          uid: user.uid,
          name: user.displayName || 'User',
          email: user.email,
          photoURL: user.photoURL,
          role: 'user', // default strictly enforced
          createdAt: new Date().toISOString(),
          lastLoginAt: new Date().toISOString(),
        });
      } else {
        // Update last login
        await setDoc(docRef, { lastLoginAt: new Date().toISOString() }, { merge: true });
      }

      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Google sign-in failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#03111F] relative overflow-hidden">
      {/* Atmospheric glow layers */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-[rgba(0,229,255,0.04)] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-[rgba(0,90,140,0.08)] rounded-full blur-[100px] pointer-events-none" />

      {/* Scanline overlay for atmosphere */}
      <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_3px,rgba(0,229,255,0.01)_3px,rgba(0,229,255,0.01)_4px)] pointer-events-none" />

      <div className="z-10 w-full max-w-sm px-8 py-10 bg-[rgba(6,24,39,0.85)] backdrop-blur-xl border border-[rgba(0,213,255,0.14)] rounded-2xl shadow-2xl shadow-black/40">
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
          <p className="text-xs text-[#7BA4BC] uppercase tracking-widest font-medium">Environmental Intelligence</p>
        </div>

        {error && (
          <div className="mb-6 p-3.5 bg-[rgba(255,68,68,0.08)] border border-[rgba(255,68,68,0.25)] rounded-xl text-[#FF7070] text-xs font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSignin} className="space-y-4">
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
            <label className="block text-xs font-bold text-[#7BA4BC] uppercase tracking-wider mb-1.5" htmlFor="password">Access Key</label>
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

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 mt-2 bg-gradient-to-r from-[#0066CC] to-[#004A99] hover:from-[#0077EE] hover:to-[#0055BB] text-white font-semibold rounded-xl shadow-lg shadow-[rgba(0,100,204,0.25)] transition-all flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed border border-[rgba(0,150,255,0.30)]"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <span>Authenticate</span>
            )}
          </button>
        </form>

        <div className="mt-6">
          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-[rgba(0,213,255,0.10)]" />
            <span className="text-[11px] text-[#2E5470] uppercase font-semibold tracking-wider">or</span>
            <div className="flex-1 h-px bg-[rgba(0,213,255,0.10)]" />
          </div>
          <button
            onClick={handleGoogleSignin}
            disabled={loading}
            className="w-full py-3 px-4 bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.08)] text-[#E8F4FD] font-medium rounded-xl border border-[rgba(255,255,255,0.10)] transition-all flex items-center justify-center gap-2.5 disabled:opacity-50"
          >
            <svg viewBox="0 0 24 24" className="w-4.5 h-4.5" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            <span className="text-sm">Continue with Google</span>
          </button>
        </div>

        <div className="mt-8 text-center text-xs text-[#2E5470]">
          No account?{' '}
          <Link href="/signup" className="text-[#00E5FF] hover:text-[#27E0C3] transition-colors font-semibold">
            Request access
          </Link>
        </div>
      </div>
    </div>
  );
}

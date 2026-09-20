'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/authContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuthority?: boolean;
}

export default function ProtectedRoute({ children, requireAuthority = false }: ProtectedRouteProps) {
  // SECURITY NOTE:
  // Frontend role checks (like profile.role === 'authority') are for UX PROTECTION ONLY.
  // They prevent accidental rendering of privileged UI components.
  // THEY ARE NOT THE SECURITY BOUNDARY.
  // The backend (FastAPI) and Firestore Security Rules remain the authoritative
  // boundary and MUST verify the Firebase ID token and role independently.
  const { user, profile, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        // Not authenticated
        router.push(requireAuthority ? '/authority/signin' : '/signin');
      } else if (requireAuthority && profile && profile.role !== 'authority') {
        // Authenticated but not an authority trying to access authority route
        router.push('/signin'); // or some access denied page
      }
    }
  }, [user, profile, loading, router, requireAuthority]);

  // Show a loading spinner or empty state while verifying
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

  // Double check before rendering children to avoid flash of content
  if (!user) return null;
  if (requireAuthority && profile?.role !== 'authority') return null;

  return <>{children}</>;
}

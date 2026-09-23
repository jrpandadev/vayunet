'use client';

import React, { useState, useEffect } from 'react';
import { Bell, User, MapPin, ChevronRight, Radio } from 'lucide-react';
import { getApiStatus, subscribeApiStatus, ApiStatus } from '@/lib/api';
import { useAuth } from '@/lib/authContext';

interface AppTopBarProps {
  /** Page title shown in breadcrumb */
  pageTitle?: string;
  /** Optional right-side actions */
  actions?: React.ReactNode;
}

export const AppTopBar: React.FC<AppTopBarProps> = ({ pageTitle, actions }) => {
  const [apiStatus, setApiStatus] = useState<ApiStatus>(() => getApiStatus());
  const [currentTime, setCurrentTime] = useState<string>('');
  const { user } = useAuth();

  // Subscribe to real API status
  useEffect(() => {
    return subscribeApiStatus((status) => {
      setApiStatus(status);
    });
  }, []);

  // Live clock — display only, never used as "last updated"
  useEffect(() => {
    const update = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const isLive = apiStatus.isConnected;

  return (
    <header
      className="
        h-14 bg-[var(--vayu-bg-elevated)] border-b border-[var(--border-hairline)]
        px-4 flex items-center justify-between gap-4
        sticky top-0 z-30
      "
    >
      {/* Left: Breadcrumb */}
      <div className="flex items-center gap-2 text-sm min-w-0">
        <span className="text-[#7BA4BC] font-medium shrink-0">VayuNet</span>
        {pageTitle && (
          <>
            <ChevronRight className="w-3.5 h-3.5 text-[#2E5470] shrink-0" />
            <span className="text-[#E8F4FD] font-medium truncate">{pageTitle}</span>
          </>
        )}
      </div>

      {/* Right: Status + Actions + User */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Custom actions slot */}
        {actions}

        {/* Location badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[rgba(0,213,255,0.06)] border border-[rgba(0,213,255,0.12)] text-[#7BA4BC] text-xs">
          <MapPin className="w-3 h-3 text-[#2E5470]" />
          <span>Delhi, NCR</span>
        </div>

        {/* System status — real from subscribeApiStatus */}
        {isLive ? (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[rgba(39,224,195,0.08)] border border-[rgba(39,224,195,0.20)] text-[#27E0C3] text-xs font-semibold uppercase tracking-wider"
            title={`Connected to backend: ${apiStatus.backendUrl}`}
          >
            <Radio className="w-3 h-3 animate-vn-pulse" />
            <span>System Live</span>
          </div>
        ) : (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[rgba(255,181,46,0.08)] border border-[rgba(255,181,46,0.20)] text-[#FFB52E] text-xs font-semibold uppercase tracking-wider"
            title={
              apiStatus.backendConfigured
                ? 'Backend unreachable — offline simulation mode'
                : 'Running local simulation demo'
            }
          >
            <Radio className="w-3 h-3" />
            <span>{apiStatus.backendConfigured ? 'Offline' : 'Simulation'}</span>
          </div>
        )}

        {/* Live clock display (not "last updated") */}
        <div className="hidden lg:flex items-center gap-1 text-[#2E5470] text-xs font-mono tabular-telemetry">
          {currentTime}
        </div>

        {/* Notification icon */}
        <button
          type="button"
          aria-label="Notifications"
          className="p-1.5 rounded-lg text-[#7BA4BC] hover:text-[#E8F4FD] hover:bg-[rgba(255,255,255,0.05)] transition-colors duration-micro ease-vayu-entrance"
        >
          <Bell className="w-4 h-4" />
        </button>

        {/* User icon */}
        <button
          type="button"
          aria-label={user?.email ?? 'User profile'}
          title={user?.email ?? ''}
          className="p-1.5 rounded-lg text-[#7BA4BC] hover:text-[#E8F4FD] hover:bg-[rgba(255,255,255,0.05)] transition-colors duration-micro ease-vayu-entrance"
        >
          <User className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};

export default AppTopBar;

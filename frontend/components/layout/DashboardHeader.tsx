'use client';

import React, { useState, useEffect } from 'react';
import { Radio, Bell, Globe, Clock, ShieldCheck } from 'lucide-react';
import { getApiStatus, subscribeApiStatus, ApiStatus } from '@/lib/api';

interface DashboardHeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  title = 'Authority Environmental Intelligence',
  subtitle = '3-City Federated Pilot · Pollution Event Monitoring',
  actions,
}) => {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [apiStatus, setApiStatus] = useState<ApiStatus>(() => getApiStatus());

  useEffect(() => {
    const update = () => {
      const now = new Date();
      const dateStr = now.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
      const timeStr = now.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
      setCurrentTime(`${dateStr} • ${timeStr}`);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    return subscribeApiStatus((status) => {
      setApiStatus(status);
    });
  }, []);

  return (
    <header className="bg-[#061827] border-b border-[rgba(0,213,255,0.10)] px-6 py-3.5 sticky top-0 z-20 flex flex-wrap items-center justify-between gap-4">
      {/* Title & Basin Context */}
      <div>
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="text-lg font-bold text-[#E8F4FD] tracking-tight">
            {title}
          </h1>
          {apiStatus.isConnected ? (
            <span
              className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-[rgba(39,224,195,0.10)] text-[#27E0C3] border border-[rgba(39,224,195,0.25)]"
              title={`Connected to backend: ${apiStatus.backendUrl}`}
            >
              <Radio className="w-3 h-3 animate-pulse" />
              System Live
            </span>
          ) : (
            <span
              className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-[rgba(255,181,46,0.10)] text-[#FFB52E] border border-[rgba(255,181,46,0.25)]"
              title={
                apiStatus.backendConfigured
                  ? 'Backend unreachable. Running with offline simulation fallback.'
                  : 'Running in local simulation demo mode'
              }
            >
              <Radio className="w-3 h-3" />
              {apiStatus.backendConfigured ? 'Offline' : 'Simulation'}
            </span>
          )}
        </div>
        <p className="text-xs text-[#7BA4BC] mt-0.5">{subtitle}</p>
      </div>

      {/* Operational Telemetry & Quick Indicators */}
      <div className="flex items-center gap-4">
        {actions}

        {/* Temporal telemetry readout */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs text-[#7BA4BC] font-mono tabular-telemetry bg-[rgba(0,213,255,0.04)] px-3 py-1.5 rounded-lg border border-[rgba(0,213,255,0.10)]">
          <Clock className="w-3.5 h-3.5 text-[#2E5470]" />
          <span>{currentTime || 'Synchronizing...'}</span>
        </div>

        {/* Clearance indicator */}
        <div className="flex items-center gap-1.5 text-xs font-medium text-[#7BA4BC] bg-[rgba(0,213,255,0.04)] px-2.5 py-1.5 rounded-lg border border-[rgba(0,213,255,0.10)]">
          <ShieldCheck className="w-4 h-4 text-[#00E5FF]" />
          <span className="hidden sm:inline">Authority Station</span>
        </div>
      </div>
    </header>
  );
};

export default DashboardHeader;

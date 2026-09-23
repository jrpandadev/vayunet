'use client';

import React from 'react';
import { Radio, AlertTriangle, XCircle, HelpCircle, Activity } from 'lucide-react';

export type SystemStatusType = 'LIVE' | 'SIMULATION' | 'UNAVAILABLE' | 'ERROR' | 'NOT_MODELED' | 'CLEAN' | 'WARNING' | 'HIGH' | 'CRITICAL';

interface StatusBadgeProps {
  status: SystemStatusType | string;
  label?: string;
  className?: string;
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  className = '',
  pulse = true,
}) => {
  const norm = (status || '').toUpperCase();

  let text = label || norm;
  let icon = <Activity className="w-3 h-3" />;
  let style = 'bg-[var(--vayu-bg-elevated)] text-[var(--text-secondary)] border-[var(--border-hairline)]';
  let pulseColor = '';

  switch (norm) {
    case 'LIVE':
    case 'CLEAN':
      text = label || norm;
      pulseColor = 'bg-[var(--vayu-signal-clean)]';
      icon = pulse ? <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${pulseColor} animate-vn-pulse`} /> : <Radio className="w-3 h-3" />;
      style = 'bg-[rgba(39,224,195,0.08)] text-[var(--vayu-signal-clean)] border-[rgba(39,224,195,0.25)]';
      break;
    case 'SIMULATION':
    case 'WARNING':
      text = label || norm;
      pulseColor = 'bg-[var(--vayu-signal-warning)]';
      icon = pulse ? <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${pulseColor} animate-vn-pulse`} /> : <Radio className="w-3 h-3" />;
      style = 'bg-[rgba(255,181,46,0.08)] text-[var(--vayu-signal-warning)] border-[rgba(255,181,46,0.25)]';
      break;
    case 'HIGH':
      text = label || norm;
      pulseColor = 'bg-[var(--vayu-signal-high)]';
      icon = pulse ? <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${pulseColor} animate-vn-pulse`} /> : <AlertTriangle className="w-3 h-3" />;
      style = 'bg-[rgba(255,159,28,0.08)] text-[var(--vayu-signal-high)] border-[rgba(255,159,28,0.25)]';
      break;
    case 'ERROR':
    case 'CRITICAL':
      text = label || norm;
      pulseColor = 'bg-[var(--vayu-signal-critical)]';
      icon = pulse ? <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${pulseColor} animate-vn-pulse`} /> : <XCircle className="w-3 h-3" />;
      style = 'bg-[rgba(255,68,68,0.08)] text-[var(--vayu-signal-critical)] border-[rgba(255,68,68,0.25)]';
      break;
    case 'UNAVAILABLE':
      text = label || 'UNAVAILABLE';
      icon = <HelpCircle className="w-3 h-3" />;
      style = 'bg-[rgba(120,160,185,0.08)] text-[var(--text-secondary)] border-[rgba(120,160,185,0.20)]';
      break;
    case 'NOT_MODELED':
    case 'NOT MODELED':
      text = label || 'NOT MODELED';
      icon = <AlertTriangle className="w-3 h-3" />;
      style = 'bg-[rgba(0,213,255,0.06)] text-[var(--text-secondary)] border-[var(--border-hairline)]';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-widest uppercase border leading-none ${style} ${className}`}
    >
      {icon}
      <span>{text}</span>
    </span>
  );
};

export default StatusBadge;

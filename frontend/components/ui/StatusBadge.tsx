'use client';

import React from 'react';
import { Radio, AlertTriangle, XCircle, HelpCircle, Activity } from 'lucide-react';

export type SystemStatusType = 'LIVE' | 'SIMULATION' | 'UNAVAILABLE' | 'ERROR' | 'NOT_MODELED';

interface StatusBadgeProps {
  status: SystemStatusType | string;
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  className = '',
}) => {
  const norm = (status || '').toUpperCase();

  let text = label || norm;
  let icon = <Activity className="w-3 h-3" />;
  let style = 'bg-[rgba(255,255,255,0.04)] text-[#7BA4BC] border-[rgba(255,255,255,0.1)]';

  switch (norm) {
    case 'LIVE':
      text = label || 'LIVE';
      icon = <Radio className="w-3 h-3 animate-pulse" />;
      style = 'bg-[rgba(39,224,195,0.10)] text-[#27E0C3] border-[rgba(39,224,195,0.30)]';
      break;
    case 'SIMULATION':
      text = label || 'SIMULATION';
      icon = <Radio className="w-3 h-3" />;
      style = 'bg-[rgba(255,181,46,0.10)] text-[#FFB52E] border-[rgba(255,181,46,0.30)]';
      break;
    case 'UNAVAILABLE':
      text = label || 'UNAVAILABLE';
      icon = <HelpCircle className="w-3 h-3" />;
      style = 'bg-[rgba(120,160,185,0.08)] text-[#7BA4BC] border-[rgba(120,160,185,0.20)]';
      break;
    case 'ERROR':
      text = label || 'ERROR';
      icon = <XCircle className="w-3 h-3" />;
      style = 'bg-[rgba(255,68,68,0.10)] text-[#FF7070] border-[rgba(255,68,68,0.30)]';
      break;
    case 'NOT_MODELED':
    case 'NOT MODELED':
      text = label || 'NOT MODELED';
      icon = <AlertTriangle className="w-3 h-3" />;
      style = 'bg-[rgba(0,213,255,0.06)] text-[#7BA4BC] border-[rgba(0,213,255,0.15)]';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold tracking-wider uppercase border ${style} ${className}`}
    >
      {icon}
      <span>{text}</span>
    </span>
  );
};

export default StatusBadge;

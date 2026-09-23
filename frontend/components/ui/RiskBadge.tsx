'use client';

import React from 'react';
import { cn } from '@/lib/utils';

/* =============================================
 * StatusBadge — system/data status indicator
 * ============================================= */
type StatusVariant = 'live' | 'offline' | 'simulation' | 'unavailable' | 'confirmed' | 'pending' | 'reviewing';

const STATUS_CONFIG: Record<StatusVariant, { label: string; classes: string; dot?: boolean }> = {
  live:        { label: 'LIVE DATA',        classes: 'bg-[rgba(39,224,195,0.10)] border-[rgba(39,224,195,0.25)] text-[#27E0C3]', dot: true },
  offline:     { label: 'OFFLINE',          classes: 'bg-[rgba(255,68,68,0.10)] border-[rgba(255,68,68,0.25)] text-[#FF4444]', dot: true },
  simulation:  { label: 'SIMULATED DATA',   classes: 'bg-[rgba(255,181,46,0.10)] border-[rgba(255,181,46,0.25)] text-[#FFB52E]' },
  unavailable: { label: 'UNAVAILABLE',      classes: 'bg-[rgba(120,160,185,0.08)] border-[rgba(120,160,185,0.15)] text-[#7BA4BC]' },
  confirmed:   { label: 'CONFIRMED',        classes: 'bg-[rgba(39,224,195,0.10)] border-[rgba(39,224,195,0.25)] text-[#27E0C3]' },
  pending:     { label: 'PENDING',          classes: 'bg-[rgba(255,181,46,0.10)] border-[rgba(255,181,46,0.25)] text-[#FFB52E]' },
  reviewing:   { label: 'UNDER REVIEW',     classes: 'bg-[rgba(0,229,255,0.08)] border-[rgba(0,229,255,0.20)] text-[#00E5FF]' },
};

interface StatusBadgeProps {
  variant: StatusVariant;
  label?: string;
  className?: string;
}

export function StatusBadge({ variant, label, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[variant];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border',
        config.classes,
        className
      )}
    >
      {config.dot && (
        <span className="w-1.5 h-1.5 rounded-full bg-current animate-vn-pulse" />
      )}
      {label ?? config.label}
    </span>
  );
}

/* =============================================
 * SimulationBadge — prominent amber badge
 * ============================================= */
export function SimulationBadge({ className }: { className?: string }) {
  return (
    <StatusBadge variant="simulation" className={className} />
  );
}

/* =============================================
 * RiskBadge — pollution event risk level
 * ============================================= */
type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';

const RISK_CONFIG: Record<RiskLevel, string> = {
  LOW:      'bg-[rgba(39,224,195,0.10)] border-[rgba(39,224,195,0.30)] text-[#27E0C3]',
  MODERATE: 'bg-[rgba(255,181,46,0.10)] border-[rgba(255,181,46,0.30)] text-[#FFB52E]',
  HIGH:     'bg-[rgba(255,159,28,0.10)] border-[rgba(255,159,28,0.30)] text-[#FF9F1C]',
  CRITICAL: 'bg-[rgba(255,68,68,0.12)] border-[rgba(255,68,68,0.35)] text-[#FF4444] shadow-[0_0_8px_rgba(255,68,68,0.15)]',
};

interface RiskBadgeProps {
  risk: RiskLevel;
  className?: string;
}

export function RiskBadge({ risk, className }: RiskBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border',
        RISK_CONFIG[risk],
        className
      )}
    >
      {risk}
    </span>
  );
}

export default RiskBadge;

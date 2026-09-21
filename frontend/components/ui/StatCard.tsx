'use client';

import React from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | 'UNAVAILABLE';

const RISK_BORDER: Record<string, string> = {
  LOW:      'border-[rgba(39,224,195,0.30)]',
  MODERATE: 'border-[rgba(255,181,46,0.30)]',
  HIGH:     'border-[rgba(255,159,28,0.30)]',
  CRITICAL: 'border-[rgba(255,68,68,0.45)] shadow-[0_0_12px_rgba(255,68,68,0.12)]',
};

const RISK_VALUE_COLOR: Record<string, string> = {
  LOW:      'text-[#27E0C3]',
  MODERATE: 'text-[#FFB52E]',
  HIGH:     'text-[#FF9F1C]',
  CRITICAL: 'text-[#FF4444]',
};

interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  riskAccent?: RiskLevel;
  href?: string;
  className?: string;
}

export function StatCard({
  title,
  value,
  unit,
  subtitle,
  icon,
  riskAccent,
  href,
  className,
}: StatCardProps) {
  const isUnavailable =
    value === 'UNAVAILABLE' || value === null || value === undefined || value === '...';

  const borderClass = riskAccent ? RISK_BORDER[riskAccent] : 'border-[rgba(0,213,255,0.12)]';
  const valueColor = riskAccent && !isUnavailable ? RISK_VALUE_COLOR[riskAccent] : 'text-[#E8F4FD]';

  const inner = (
    <div
      className={cn(
        'bg-[#092337] border rounded-xl p-4 flex flex-col gap-2 transition-all duration-200 h-full',
        borderClass,
        href && 'hover:bg-[#0B2940] cursor-pointer',
        className
      )}
    >
      {/* Label row */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[#7BA4BC] truncate leading-snug">
          {title}
        </span>
        {icon && (
          <span className="text-[#2E5470] shrink-0 opacity-80">{icon}</span>
        )}
      </div>

      {/* Value row */}
      <div className="flex items-end gap-1.5 min-h-[2rem]">
        {isUnavailable ? (
          <span className="text-xs font-mono text-[#2E5470] uppercase tracking-wider">
            Unavailable
          </span>
        ) : (
          <>
            <span
              className={cn(
                'text-2xl font-bold font-mono tabular-telemetry leading-none',
                valueColor
              )}
            >
              {value}
            </span>
            {unit && (
              <span className="text-sm text-[#7BA4BC] pb-0.5">{unit}</span>
            )}
          </>
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-[11px] text-[#7BA4BC] leading-snug">{subtitle}</p>
      )}
    </div>
  );

  if (href) {
    return <Link href={href} className="block h-full">{inner}</Link>;
  }

  return inner;
}

export default StatCard;

import React from 'react';
import Link from 'next/link';
import { RiskLevel } from '@/lib/types';
import { ChevronRight } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  riskAccent?: RiskLevel;
  className?: string;
  unit?: string;
  badge?: React.ReactNode;
  href?: string;
}

const ACCENT_BORDER: Record<RiskLevel, string> = {
  LOW: 'border-l-4 border-l-[#22c55e]',
  MODERATE: 'border-l-4 border-l-[#eab308]',
  HIGH: 'border-l-4 border-l-[#f97316]',
  CRITICAL: 'border-l-4 border-l-[#ef4444]',
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  riskAccent,
  className = '',
  unit,
  badge,
  href,
}) => {
  const accentClass = riskAccent ? ACCENT_BORDER[riskAccent] : '';

  const cardInner = (
    <div
      className={`bg-white border border-[#e2e8f0] rounded-lg p-4 sm:p-5 shadow-xs transition-all hover:shadow-sm ${accentClass} ${
        href ? 'hover:border-slate-400 group cursor-pointer' : ''
      } ${className}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b] truncate">
          {title}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          {badge}
          {icon && (
            <div className="p-1.5 rounded bg-slate-50 text-[#0a2540] border border-slate-100">
              {icon}
            </div>
          )}
        </div>
      </div>

      <div className="mt-2.5 flex items-baseline">
        <span className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0f172a] tabular-telemetry">
          {value}
        </span>
        {unit && (
          <span className="text-xs font-semibold text-slate-500 ml-1.5 font-sans">
            {unit}
          </span>
        )}
      </div>

      {subtitle && (
        <div className="mt-1 text-xs text-[#64748b] flex items-center justify-between gap-1">
          <span className="truncate">{subtitle}</span>
          {href && (
            <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#0a2540] group-hover:translate-x-0.5 transition-all shrink-0" />
          )}
        </div>
      )}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block no-underline">
        {cardInner}
      </Link>
    );
  }

  return cardInner;
};

export default StatCard;

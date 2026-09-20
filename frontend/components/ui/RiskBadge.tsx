import React from 'react';
import { RiskLevel } from '@/lib/types';

interface RiskBadgeProps {
  level: RiskLevel | 'VERY_HIGH' | string;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
  className?: string;
}

const RISK_CONFIG: Record<
  RiskLevel | 'VERY_HIGH' | string,
  {
    label: string;
    bg: string;
    text: string;
    border: string;
    dotColor: string;
  }
> = {
  LOW: {
    label: 'LOW RISK',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    dotColor: 'bg-[#22c55e]',
  },
  MODERATE: {
    label: 'MODERATE',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    dotColor: 'bg-[#eab308]',
  },
  HIGH: {
    label: 'HIGH RISK',
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    border: 'border-orange-200',
    dotColor: 'bg-[#f97316]',
  },
  VERY_HIGH: {
    label: 'VERY HIGH',
    bg: 'bg-rose-50',
    text: 'text-rose-700',
    border: 'border-rose-200',
    dotColor: 'bg-[#ef4444]',
  },
  CRITICAL: {
    label: 'CRITICAL',
    bg: 'bg-purple-50',
    text: 'text-purple-800',
    border: 'border-purple-200',
    dotColor: 'bg-[#9333ea]',
  },
};

const SIZE_CLASSES = {
  sm: 'text-xs px-2 py-0.5 font-medium tracking-wide',
  md: 'text-xs px-2.5 py-1 font-semibold tracking-wider',
  lg: 'text-sm px-3.5 py-1.5 font-bold tracking-wider',
};

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level,
  size = 'md',
  showDot = true,
  className = '',
}) => {
  const config = RISK_CONFIG[level] || RISK_CONFIG.LOW;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border uppercase transition-colors select-none ${config.bg} ${config.text} ${config.border} ${SIZE_CLASSES[size]} ${className}`}
      role="status"
      aria-label={`Risk Level: ${config.label}`}
    >
      {showDot && (
        <span
          className={`h-1.5 w-1.5 rounded-full ${config.dotColor} shrink-0`}
          aria-hidden="true"
        />
      )}
      <span>{config.label}</span>
    </span>
  );
};

export default RiskBadge;

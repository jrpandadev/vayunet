'use client';

import React from 'react';
import { cn } from '@/lib/utils';

/* =============================================
 * VayuNet Card — dark command-center panel
 * Supports both new simple API and legacy dashboard API
 * ============================================= */

interface CardProps {
  children: React.ReactNode;
  className?: string;
  /** When true, adds cyan active glow */
  active?: boolean;
  /** When true, adds amber warning glow */
  warning?: boolean;
  /** When true, adds red critical glow */
  critical?: boolean;
  /** Click handler */
  onClick?: () => void;
}

export function Card({ children, className, active, warning, critical, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-[#092337] border border-[rgba(0,213,255,0.12)] rounded-xl transition-all duration-200',
        active && 'border-[rgba(0,229,255,0.40)] shadow-[0_0_16px_rgba(0,229,255,0.12)]',
        warning && 'border-[rgba(255,181,46,0.35)] shadow-[0_0_16px_rgba(255,181,46,0.10)]',
        critical && 'border-[rgba(255,68,68,0.35)] shadow-[0_0_16px_rgba(255,68,68,0.10)]',
        onClick && 'cursor-pointer hover:border-[rgba(0,213,255,0.25)] hover:bg-[#0B2940]',
        className
      )}
    >
      {children}
    </div>
  );
}

/* =============================================
 * CardHeader — supports both legacy and new API
 * Legacy: title, subtitle, action props
 * New: children
 * ============================================= */

interface CardHeaderProps {
  /** New API: render children directly */
  children?: React.ReactNode;
  /** Legacy API: title string */
  title?: string;
  /** Legacy API: subtitle string */
  subtitle?: string;
  /** Legacy API: right-side action node */
  action?: React.ReactNode;
  className?: string;
}

export function CardHeader({ children, title, subtitle, action, className }: CardHeaderProps) {
  // If children provided, use them directly (new API)
  if (children) {
    return (
      <div
        className={cn(
          'px-4 py-3 border-b border-[rgba(0,213,255,0.08)] flex items-center justify-between gap-3',
          className
        )}
      >
        {children}
      </div>
    );
  }

  // Legacy API with title/subtitle/action
  return (
    <div
      className={cn(
        'px-4 py-3 border-b border-[rgba(0,213,255,0.08)] flex items-start justify-between gap-3',
        className
      )}
    >
      <div className="min-w-0">
        {title && (
          <h3 className="text-sm font-bold text-[#E8F4FD] tracking-tight truncate">{title}</h3>
        )}
        {subtitle && (
          <p className="text-[11px] text-[#7BA4BC] mt-0.5 leading-snug">{subtitle}</p>
        )}
      </div>
      {action && <div className="shrink-0 mt-0.5">{action}</div>}
    </div>
  );
}

interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export function CardContent({ children, className }: CardContentProps) {
  return (
    <div className={cn('px-4 py-4', className)}>
      {children}
    </div>
  );
}

export default Card;

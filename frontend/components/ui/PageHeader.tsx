'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, Loader2, WifiOff, Database } from 'lucide-react';

/* =============================================
 * PageHeader — top of every dashboard page
 * ============================================= */
interface PageHeaderProps {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({ icon, title, subtitle, badge, actions, className }: PageHeaderProps) {
  return (
    <div className={cn('px-6 py-5 border-b border-[var(--border-hairline)]', className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          {icon && (
            <div className="mt-0.5 h-9 w-9 rounded-lg bg-[rgba(0,229,255,0.08)] border border-[rgba(0,229,255,0.15)] flex items-center justify-center shrink-0 text-[var(--vayu-signal-primary)]">
              {icon}
            </div>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">{title}</h1>
              {badge}
            </div>
            {subtitle && (
              <p className="text-sm text-[var(--text-secondary)] mt-0.5 leading-relaxed">{subtitle}</p>
            )}
          </div>
        </div>
        {actions && (
          <div className="flex items-center gap-2 shrink-0">{actions}</div>
        )}
      </div>
    </div>
  );
}

/* =============================================
 * SectionHeader — in-page section heading
 * ============================================= */
interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function SectionHeader({ title, subtitle, actions, className }: SectionHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between gap-3 mb-3', className)}>
      <div>
        <h2 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-widest">{title}</h2>
        {subtitle && <p className="text-xs text-[var(--text-secondary)] mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

/* =============================================
 * MetricCard — single measurement with null safety
 * ============================================= */
interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  icon?: React.ReactNode;
  subtext?: string;
  /** Status chip below the value */
  statusChip?: React.ReactNode;
  className?: string;
}

export function MetricCard({ label, value, unit, icon, subtext, statusChip, className }: MetricCardProps) {
  const isUnavailable = value === null || value === undefined || value === '';
  return (
    <div
      className={cn(
        'bg-[var(--vayu-surface-elevated)] border border-[var(--border-hairline)] rounded-xl p-4 flex flex-col gap-2',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest truncate">{label}</span>
        {icon && <span className="text-[var(--text-secondary)] opacity-50 shrink-0">{icon}</span>}
      </div>
      <div className="flex items-end gap-1.5">
        {isUnavailable ? (
          <span className="text-sm font-mono text-[var(--text-secondary)] opacity-70 uppercase tracking-wider">Unavailable</span>
        ) : (
          <>
            <span className="text-2xl font-bold font-mono text-[var(--text-primary)] tabular-telemetry leading-none">
              {value}
            </span>
            {unit && <span className="text-sm text-[var(--text-secondary)] pb-0.5">{unit}</span>}
          </>
        )}
      </div>
      {subtext && <p className="text-[11px] text-[var(--text-secondary)]">{subtext}</p>}
      {statusChip}
    </div>
  );
}

/* =============================================
 * AlertCard — amber warning card
 * ============================================= */
interface AlertCardProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
  critical?: boolean;
  className?: string;
}

export function AlertCard({ title, description, children, critical, className }: AlertCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-4',
        critical
          ? 'bg-[rgba(255,68,68,0.06)] border-[rgba(255,68,68,0.25)]'
          : 'bg-[rgba(255,181,46,0.06)] border-[rgba(255,181,46,0.25)]',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle
          className={cn('w-4 h-4 mt-0.5 shrink-0', critical ? 'text-[#FF4444]' : 'text-[#FFB52E]')}
        />
        <div className="min-w-0">
          <p className={cn('text-sm font-semibold', critical ? 'text-[#FF4444]' : 'text-[#FFB52E]')}>{title}</p>
          {description && <p className="text-xs text-[#7BA4BC] mt-1 leading-relaxed">{description}</p>}
          {children && <div className="mt-3">{children}</div>}
        </div>
      </div>
    </div>
  );
}

/* =============================================
 * StatCard — key metric with icon (dashboard overview)
 * ============================================= */
interface StatCardProps {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  icon: React.ReactNode;
  trend?: string;
  className?: string;
}

export function StatCard({ label, value, unit, icon, trend, className }: StatCardProps) {
  const isUnavailable = value === null || value === undefined;
  return (
    <div className={cn('bg-[var(--vayu-surface-elevated)] border border-[var(--border-hairline)] rounded-xl p-4', className)}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-secondary)]">{label}</span>
        <div className="h-7 w-7 rounded-lg bg-[rgba(0,229,255,0.06)] border border-[rgba(0,229,255,0.12)] flex items-center justify-center text-[var(--vayu-signal-primary)]">
          {icon}
        </div>
      </div>
      <div className="flex items-end gap-1.5">
        {isUnavailable ? (
          <span className="text-sm font-mono text-[var(--text-secondary)] opacity-70 uppercase tracking-wider">—</span>
        ) : (
          <>
            <span className="text-3xl font-bold font-mono text-[var(--text-primary)] tabular-telemetry leading-none">
              {value}
            </span>
            {unit && <span className="text-sm text-[var(--text-secondary)] pb-1">{unit}</span>}
          </>
        )}
      </div>
      {trend && <p className="text-xs text-[var(--text-secondary)] mt-2">{trend}</p>}
    </div>
  );
}

/* =============================================
 * EmptyState, LoadingState, ErrorState
 * ============================================= */
export function EmptyState({ message = 'No data available', className }: { message?: string; className?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 gap-3 text-center', className)}>
      <Database className="w-8 h-8 text-[#2E5470]" />
      <p className="text-sm text-[#7BA4BC]">{message}</p>
    </div>
  );
}

export function LoadingState({ message = 'Loading telemetry…', className }: { message?: string; className?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 gap-3 text-center', className)}>
      <Loader2 className="w-7 h-7 text-[#00E5FF] animate-spin" />
      <p className="text-xs font-mono text-[#7BA4BC] tracking-wider uppercase">{message}</p>
    </div>
  );
}

export function ErrorState({ message, className }: { message: string; className?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 gap-3 text-center', className)}>
      <WifiOff className="w-7 h-7 text-[#FF4444]" />
      <p className="text-sm text-[#7BA4BC] max-w-sm">{message}</p>
    </div>
  );
}

export default PageHeader;

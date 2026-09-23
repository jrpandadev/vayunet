'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Map as MapIcon,
  TrendingUp,
  AlertTriangle,
  FileText,
  Shield,
  Menu,
  X,
  Wind,
  CloudRain,
  Activity,
  Brain,
  Satellite,
  ShieldCheck,
  Info,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { getEvents } from '@/lib/api';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string | number;
  external?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

// ---------- nav structure ----------
function buildNavGroups(pendingCount: number): NavGroup[] {
  return [
    {
      label: 'COMMAND CENTER',
      items: [
        {
          label: 'Overview',
          href: '/dashboard',
          icon: <LayoutDashboard className="w-4 h-4" />,
        },
        {
          label: 'Live NCR Map',
          href: '/dashboard/map',
          icon: <MapIcon className="w-4 h-4" />,
        },
        {
          label: 'Forecast',
          href: '/dashboard/forecast',
          icon: <TrendingUp className="w-4 h-4" />,
        },
        {
          label: 'Weather × Pollution',
          href: '/dashboard/weather',
          icon: <CloudRain className="w-4 h-4" />,
        },
      ],
    },
    {
      label: 'ANALYTICS',
      items: [
        {
          label: 'Pollution Trends',
          href: '/dashboard',
          icon: <Activity className="w-4 h-4" />,
        },
        {
          label: 'Hotspot Analysis',
          href: '/dashboard/alerts',
          icon: <Satellite className="w-4 h-4" />,
          badge: pendingCount > 0 ? pendingCount : undefined,
        },
        {
          label: 'Model Insights',
          href: '/dashboard/forecast',
          icon: <Brain className="w-4 h-4" />,
        },
      ],
    },
    {
      label: 'RESPONSE',
      items: [
        {
          label: 'Early Warnings',
          href: '/dashboard/alerts',
          icon: <AlertTriangle className="w-4 h-4" />,
          badge: pendingCount > 0 ? pendingCount : undefined,
        },
        {
          label: 'Authority Response',
          href: '/authority/dashboard',
          icon: <ShieldCheck className="w-4 h-4" />,
        },
        {
          label: 'Citizen Reports',
          href: '/report',
          icon: <FileText className="w-4 h-4" />,
        },
      ],
    },
    {
      label: 'SYSTEM',
      items: [
        {
          label: 'Methodology',
          href: '/methodology',
          icon: <Info className="w-4 h-4" />,
        },
      ],
    },
  ];
}

interface DashboardSidebarProps {
  className?: string;
}

export const DashboardSidebar: React.FC<DashboardSidebarProps> = ({ className = '' }) => {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [isSimulation, setIsSimulation] = useState<boolean>(false);

  // Fetch active alerts count from API
  useEffect(() => {
    let mounted = true;
    getEvents()
      .then((events) => {
        if (mounted) {
          const pending = events.filter((e) => e.response.status === 'pending').length;
          setPendingCount(pending);
        }
      })
      .catch(() => {});
    setIsSimulation(false);
    return () => {
      mounted = false;
    };
  }, [pathname]);

  // Close mobile sidebar on route transition
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const isLinkActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname.startsWith(href);
  };

  const navGroups = buildNavGroups(pendingCount);

  const sidebarContent = (
    <aside
      className={`w-[220px] bg-[var(--vayu-bg-elevated)] text-[var(--text-primary)] flex flex-col shrink-0 border-r border-[var(--border-hairline)] min-h-screen select-none ${className}`}
      aria-label="VayuNet Navigation"
    >
      {/* Brand header */}
      <div className="px-4 py-4 border-b border-[var(--border-hairline)] flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
          {/* Logo mark */}
          <div className="h-8 w-8 rounded-lg bg-[rgba(0,229,255,0.10)] border border-[rgba(0,229,255,0.25)] flex items-center justify-center shrink-0">
            <Wind className="w-4 h-4 text-[#00E5FF]" />
          </div>
          <div>
            <span className="font-bold tracking-tight text-sm text-[#E8F4FD] block leading-tight">
              VayuNet
            </span>
            <span className="text-[9px] tracking-[0.12em] uppercase text-[#7BA4BC] font-medium block leading-tight">
              Weather-Coupled AI
            </span>
          </div>
        </Link>

        {/* Mobile close */}
        <button
          type="button"
          onClick={() => setMobileOpen(false)}
          className="md:hidden p-1 rounded text-[#7BA4BC] hover:text-[#E8F4FD] hover:bg-[rgba(255,255,255,0.05)]"
          aria-label="Close navigation"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto space-y-4">
        {navGroups.map((group) => (
          <div key={group.label}>
            {/* Group label */}
            <div className="px-3 pt-1 pb-2 text-[9px] font-semibold text-[#2E5470] tracking-[0.14em] uppercase">
              {group.label}
            </div>

            {/* Nav items */}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active = isLinkActive(item.href);
                return (
                  <Link
                    key={`${group.label}-${item.href}-${item.label}`}
                    href={item.href}
                    className={`
                      group flex items-center justify-between px-3 py-2 rounded-lg text-[13px] font-medium
                      transition-all duration-micro ease-vayu-entrance
                      ${active
                        ? 'bg-[rgba(0,229,255,0.08)] text-[#00E5FF] border-l-2 border-[#00E5FF] pl-[10px]'
                        : 'text-[#7BA4BC] hover:bg-[rgba(255,255,255,0.04)] hover:text-[#E8F4FD] border-l-2 border-transparent'}
                    `}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className={`shrink-0 transition-colors ${active ? 'text-[#00E5FF]' : 'text-[#2E5470] group-hover:text-[#7BA4BC]'}`}>
                        {item.icon}
                      </span>
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge !== undefined && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[rgba(255,181,46,0.15)] text-[#FFB52E] border border-[rgba(255,181,46,0.25)] shrink-0">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer — mode badge */}
      <div className="px-3 py-3 border-t border-[var(--border-hairline)]">
        {isSimulation ? (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[rgba(255,181,46,0.08)] border border-[rgba(255,181,46,0.20)]">
            <Zap className="w-3.5 h-3.5 text-[#FFB52E] shrink-0" />
            <div>
              <span className="text-[10px] font-bold text-[#FFB52E] uppercase tracking-wider block">Simulation Mode</span>
              <span className="text-[9px] text-[#7BA4BC]">No live telemetry</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[rgba(39,224,195,0.08)] border border-[rgba(39,224,195,0.20)]">
            <span className="w-2 h-2 rounded-full bg-[#27E0C3] animate-vn-pulse shrink-0" />
            <div>
              <span className="text-[10px] font-bold text-[#27E0C3] uppercase tracking-wider block">System Live</span>
              <span className="text-[9px] text-[#7BA4BC]">Backend connected</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );

  return (
    <>
      {/* Mobile top bar toggle */}
      <div className="md:hidden bg-[var(--vayu-bg-elevated)] text-[var(--text-primary)] px-4 py-3 flex items-center justify-between border-b border-[var(--border-hairline)] sticky top-0 z-40">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-[rgba(0,229,255,0.10)] border border-[rgba(0,229,255,0.20)] flex items-center justify-center">
            <Wind className="w-4 h-4 text-[#00E5FF]" />
          </div>
          <div>
            <span className="font-bold text-sm tracking-tight block leading-tight">VayuNet</span>
            <span className="text-[9px] text-[#7BA4BC] block leading-tight">Weather-Coupled AI</span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-1.5 rounded text-[#7BA4BC] hover:text-[#E8F4FD] hover:bg-[rgba(255,255,255,0.05)]"
          aria-label="Toggle navigation menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Desktop persistent sidebar */}
      <div className="hidden md:flex shrink-0">{sidebarContent}</div>

      {/* Mobile overlay drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="relative flex-1 max-w-[240px] w-full z-50 flex flex-col">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};

export default DashboardSidebar;

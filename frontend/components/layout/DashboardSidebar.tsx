'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Map as MapIcon,
  TrendingUp,
  AlertTriangle,
  FileSpreadsheet,
  Activity,
  ExternalLink,
  Shield,
  Menu,
  X,
  Home,
} from 'lucide-react';

import { getEvents } from '@/lib/api';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
}

const BASE_NAV_ITEMS: Omit<NavItem, 'badge'>[] = [
  {
    label: 'Overview',
    href: '/dashboard',
    icon: <LayoutDashboard className="w-4 h-4" />,
  },
  {
    label: 'Map',
    href: '/dashboard/map',
    icon: <MapIcon className="w-4 h-4" />,
  },
  {
    label: 'Forecast',
    href: '/dashboard/forecast',
    icon: <TrendingUp className="w-4 h-4" />,
  },
  {
    label: 'Alerts',
    href: '/dashboard/alerts',
    icon: <AlertTriangle className="w-4 h-4" />,
  },
  {
    label: 'Citizen Feed',
    href: '/report',
    icon: <FileSpreadsheet className="w-4 h-4" />,
  },
];

interface DashboardSidebarProps {
  className?: string;
}

export const DashboardSidebar: React.FC<DashboardSidebarProps> = ({ className = '' }) => {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);
  const [pendingCount, setPendingCount] = useState<number>(0);

  // Fetch active alerts count from API abstraction
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
    return () => {
      mounted = false;
    };
  }, [pathname]);

  // Close mobile sidebar on route transition
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const isLinkActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard';
    }
    return pathname.startsWith(href);
  };

  const navItems: NavItem[] = BASE_NAV_ITEMS.map((item) => {
    if (item.href === '/dashboard/alerts' && pendingCount > 0) {
      return { ...item, badge: `${pendingCount} Pending` };
    }
    return item;
  });

  const sidebarContent = (
    <aside
      className={`w-64 bg-[#0a2540] text-white flex flex-col shrink-0 border-r border-[#0f2a3f] min-h-screen select-none ${className}`}
      aria-label="Authority Dashboard Navigation"
    >
      {/* Brand & Command Authority Header */}
      <div className="p-5 border-b border-white/10 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 hover:opacity-95 transition-opacity">
          <div className="h-9 w-9 rounded bg-sky-600/20 border border-sky-400/40 flex items-center justify-center text-sky-400 shadow-xs">
            <Activity className="w-5 h-5 text-sky-300" />
          </div>
          <div>
            <span className="font-bold tracking-tight text-base text-white block">
              VayuNet
            </span>
            <span className="text-[10px] tracking-wider uppercase text-sky-300 font-medium block">
              3-City Federated Pilot
            </span>
          </div>
        </Link>

        {/* Mobile close button */}
        <button
          type="button"
          onClick={() => setMobileOpen(false)}
          className="md:hidden p-1.5 rounded text-slate-400 hover:text-white hover:bg-white/10"
          aria-label="Close navigation"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Authority Controls
        </div>

        {navItems.map((item) => {
          const active = isLinkActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3.5 py-2.5 rounded text-sm font-medium transition-all ${
                active
                  ? 'bg-sky-500/20 text-sky-200 border-l-2 border-sky-400 pl-3 font-semibold'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={active ? 'text-sky-300' : 'text-slate-400'}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}

        <div className="pt-4 px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          System Portals
        </div>

        <Link
          href="/"
          className="flex items-center gap-3 px-3.5 py-2 rounded text-xs text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
        >
          <Home className="w-4 h-4 text-slate-400" />
          <span>VayuNet Gateway</span>
        </Link>
      </nav>

      {/* Authority Clearance Badge & Mode Switcher */}
      <div className="p-4 border-t border-white/10 space-y-3">
        <div className="bg-[#071a2e] rounded p-3 border border-white/5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            <span>Simulation Mode</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            CPCB / Sentinel-5P / Gemini Multimodal Fusion Engine
          </p>
        </div>

        <Link
          href="/report"
          className="flex items-center justify-center gap-2 w-full py-2 px-3 text-xs rounded border border-slate-700 hover:border-slate-500 text-slate-300 hover:text-white transition-colors"
        >
          <span>Switch to Citizen Portal</span>
          <ExternalLink className="w-3 h-3" />
        </Link>
      </div>
    </aside>
  );

  return (
    <>
      {/* Mobile Top Command Header with Toggle */}
      <div className="md:hidden bg-[#0a2540] text-white px-4 py-3 flex items-center justify-between border-b border-[#0f2a3f] sticky top-0 z-40">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded bg-sky-500/20 flex items-center justify-center text-sky-300">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-sm tracking-tight block">VayuNet Authority</span>
            <span className="text-[10px] text-sky-300 block -mt-0.5">3-City Federated Pilot</span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-1.5 rounded text-slate-300 hover:text-white hover:bg-white/10"
          aria-label="Toggle navigation menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Desktop Persistent Sidebar */}
      <div className="hidden md:flex shrink-0">{sidebarContent}</div>

      {/* Mobile Overlay Drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="relative flex-1 max-w-xs w-full bg-[#0a2540] shadow-xl z-50 flex flex-col">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};

export default DashboardSidebar;

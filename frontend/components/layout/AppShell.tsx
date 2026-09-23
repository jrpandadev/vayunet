'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { DashboardSidebar } from './DashboardSidebar';
import { AppTopBar } from './AppTopBar';

interface AppShellProps {
  children: React.ReactNode;
  pageTitle?: string;
  actions?: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  pageTitle,
  actions,
}) => {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-[var(--vayu-bg)] text-[var(--text-primary)]">
      {/* Persistent Left Sidebar */}
      <DashboardSidebar />

      {/* Main Content Column */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Command Center Top Bar */}
        <AppTopBar pageTitle={pageTitle} actions={actions} />

        {/* Page Content Viewport */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: [0, 0, 0.2, 1] }}
            className="min-h-full"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
};

export default AppShell;

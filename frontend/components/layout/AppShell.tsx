'use client';

import React from 'react';
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
  return (
    <div className="flex min-h-screen bg-[#03111F] text-[#E8F4FD]">
      {/* Persistent Left Sidebar */}
      <DashboardSidebar />

      {/* Main Content Column */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Command Center Top Bar */}
        <AppTopBar pageTitle={pageTitle} actions={actions} />

        {/* Page Content Viewport */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppShell;

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { getEvents } from '@/lib/api';
import { PollutionEvent, RiskLevel } from '@/lib/types';
import DashboardHeader from '@/components/layout/DashboardHeader';
import RiskBadge from '@/components/ui/RiskBadge';
import Card, { CardHeader, CardContent } from '@/components/ui/Card';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  XCircle,
  ArrowRight,
  MapPin,
  Building2,
  Flame,
  Search,
  Filter,
  RefreshCw,
  X,
} from 'lucide-react';

type AlertTab = 'active' | 'acknowledged' | 'resolved' | 'false_alarm';

const getEventLifecycle = (
  e: PollutionEvent
): { id: AlertTab; label: string; badgeClass: string } => {
  if (e.outcome === 'resolved') {
    return {
      id: 'resolved',
      label: 'Resolved',
      badgeClass: 'bg-[rgba(39,224,195,0.10)] text-[#27E0C3] border-[rgba(39,224,195,0.30)]',
    };
  }
  if (e.outcome === 'false_alarm') {
    return {
      id: 'false_alarm',
      label: 'False Alarm',
      badgeClass: 'bg-[rgba(120,160,185,0.08)] text-[#7BA4BC] border-[rgba(120,160,185,0.20)]',
    };
  }
  if (e.response.status === 'acknowledged') {
    return {
      id: 'acknowledged',
      label: 'Acknowledged',
      badgeClass: 'bg-[rgba(0,229,255,0.08)] text-[#00E5FF] border-[rgba(0,229,255,0.25)]',
    };
  }
  return {
    id: 'active',
    label: 'Active & Pending',
    badgeClass: 'bg-[rgba(255,181,46,0.10)] text-[#FFB52E] border-[rgba(255,181,46,0.30)]',
  };
};

export default function AlertsCentrePage() {
  const [events, setEvents] = useState<PollutionEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<AlertTab>('active');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await getEvents();
      setEvents(data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Restore activeTab and searchQuery from URL if returning from event detail or direct link
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get('tab') as AlertTab | null;
      const qParam = params.get('q');
      if (
        tabParam &&
        ['active', 'acknowledged', 'resolved', 'false_alarm'].includes(tabParam)
      ) {
        setActiveTab(tabParam);
      }
      if (qParam) {
        setSearchQuery(qParam);
      }
    } catch {
      // Ignore
    }
  }, []);

  const handleTabChange = (tab: AlertTab) => {
    setActiveTab(tab);
    if (typeof window !== 'undefined') {
      try {
        const url = new URL(window.location.href);
        if (tab === 'active') {
          url.searchParams.delete('tab');
        } else {
          url.searchParams.set('tab', tab);
        }
        window.history.replaceState({}, '', url.toString());
      } catch {}
    }
  };

  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    if (typeof window !== 'undefined') {
      try {
        const url = new URL(window.location.href);
        if (!q.trim()) {
          url.searchParams.delete('q');
        } else {
          url.searchParams.set('q', q);
        }
        window.history.replaceState({}, '', url.toString());
      } catch {}
    }
  };

  // Categorize events according to response.status and outcome
  const categorizedEvents = useMemo(() => {
    const active = events.filter((e) => e.response.status === 'pending');
    const acknowledged = events.filter(
      (e) =>
        e.response.status === 'acknowledged' &&
        e.outcome !== 'resolved' &&
        e.outcome !== 'false_alarm'
    );
    const resolved = events.filter((e) => e.outcome === 'resolved');
    const falseAlarm = events.filter((e) => e.outcome === 'false_alarm');

    return {
      active,
      acknowledged,
      resolved,
      false_alarm: falseAlarm,
    };
  }, [events]);

  const isSearchActive = searchQuery.trim().length > 0;

  // Search logic:
  // - If search is empty: preserve existing active tab filtering.
  // - If search is active: perform GLOBAL search across all lifecycle categories.
  const displayedEvents = useMemo(() => {
    if (!isSearchActive) {
      return categorizedEvents[activeTab] || [];
    }

    const query = searchQuery.toLowerCase().trim();
    return events.filter(
      (e) =>
        e.location.city.toLowerCase().includes(query) ||
        e.event_id.toLowerCase().includes(query) ||
        e.source_hypothesis.category.toLowerCase().includes(query) ||
        (e.response.authority_class &&
          e.response.authority_class.toLowerCase().includes(query)) ||
        e.risk.toLowerCase().includes(query) ||
        e.response.status.toLowerCase().includes(query) ||
        e.outcome.toLowerCase().includes(query)
    );
  }, [categorizedEvents, activeTab, isSearchActive, searchQuery, events]);

  // Contextual tracking of matches outside current tab
  const matchesOutsideActiveTab = useMemo(() => {
    if (!isSearchActive) return [];
    return displayedEvents.filter((e) => getEventLifecycle(e).id !== activeTab);
  }, [isSearchActive, displayedEvents, activeTab]);

  const tabs: { id: AlertTab; label: string; count: number; icon: React.ReactNode }[] = [
    {
      id: 'active',
      label: 'Active & Pending',
      count: categorizedEvents.active.length,
      icon: <Clock className="w-3.5 h-3.5 text-[#FFB52E]" />,
    },
    {
      id: 'acknowledged',
      label: 'Acknowledged',
      count: categorizedEvents.acknowledged.length,
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-[#00E5FF]" />,
    },
    {
      id: 'resolved',
      label: 'Resolved',
      count: categorizedEvents.resolved.length,
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-[#27E0C3]" />,
    },
    {
      id: 'false_alarm',
      label: 'False Alarms',
      count: categorizedEvents.false_alarm.length,
      icon: <XCircle className="w-3.5 h-3.5 text-[#7BA4BC]" />,
    },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-[#03111F]">
      {/* Header */}
      <DashboardHeader
        title="Alert Surveillance Centre"
        subtitle="Operational Incident Lifecycle Tracking • Multi-Agency Routing & Determination"
        actions={
          <button
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-[rgba(0,213,255,0.20)] bg-[rgba(0,213,255,0.05)] text-xs font-medium text-[#7BA4BC] hover:text-[#E8F4FD] hover:border-[rgba(0,213,255,0.35)] transition-colors"
            title="Refresh alerts"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        }
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Navigation Tabs and Search Bar */}
        <div className="bg-[#092337] border border-[rgba(0,213,255,0.12)] rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Lifecycle Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => handleTabChange(tab.id)}
                  className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                    isActive
                      ? 'bg-[rgba(0,229,255,0.12)] border border-[rgba(0,229,255,0.35)] text-[#00E5FF]'
                      : 'bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-[#7BA4BC] hover:text-[#E8F4FD]'
                  }`}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      isActive
                        ? 'bg-[rgba(0,229,255,0.15)] text-[#00E5FF]'
                        : 'bg-[rgba(255,255,255,0.06)] text-[#7BA4BC]'
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Quick Search */}
          <div className="relative w-full md:w-64">
            <Search className="w-3.5 h-3.5 text-[#2E5470] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Filter by city, ID, source..."
              className="w-full bg-[#03111F] border border-[rgba(0,213,255,0.20)] rounded pl-8 pr-8 py-1.5 text-xs text-[#E8F4FD] placeholder:text-[#2E5470] focus:outline-hidden focus:border-[#00E5FF]"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => handleSearchChange('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-slate-600 cursor-pointer"
                aria-label="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Contextual Global Search Banner */}
        {isSearchActive && (
          <div className="bg-[rgba(0,229,255,0.06)] border border-[rgba(0,229,255,0.20)] rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs text-[#E8F4FD]">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-[#00E5FF] shrink-0" />
              <span>
                Showing <strong>{displayedEvents.length}</strong> {displayedEvents.length === 1 ? 'incident' : 'incidents'} across <strong>all lifecycle states</strong> for &ldquo;<strong>{searchQuery}</strong>&rdquo;
                {matchesOutsideActiveTab.length > 0 && (
                  <span className="text-[#7BA4BC] ml-1.5 font-medium">
                    ({matchesOutsideActiveTab.length} {matchesOutsideActiveTab.length === 1 ? 'match' : 'matches'} outside {tabs.find((t) => t.id === activeTab)?.label})
                  </span>
                )}
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleSearchChange('')}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#00E5FF] hover:text-[#27E0C3] underline cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear Search</span>
            </button>
          </div>
        )}

        {/* Alerts Table Card */}
        <Card className="overflow-hidden">
          <CardHeader
            title={
              isSearchActive ? (
                <div className="flex items-center gap-2">
                  <span>Global Incident Search ({displayedEvents.length})</span>
                  <span className="text-[#7BA4BC]">
                    &bull; &ldquo;{searchQuery}&rdquo;
                  </span>
                </div>
              ) : (
                <span className="capitalize">
                  {activeTab.replace('_', ' ')} Incident Registry ({displayedEvents.length})
                </span>
              )
            }
            subtitle={
              isSearchActive
                ? 'Searching complete surveillance catalog across all workflow lifecycle states'
                : 'Authoritative surveillance roster tracking verified ground & satellite triggers'
            }
          />

          <CardContent className="p-0">
            {loading ? (
              <div className="p-12 text-center text-xs text-[#7BA4BC]">
                <div className="h-6 w-6 border-2 border-[#00E5FF] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <span>Loading incident roster...</span>
              </div>
            ) : displayedEvents.length === 0 ? (
              <div className="p-12 text-center text-[#7BA4BC] space-y-2">
                <AlertTriangle className="w-8 h-8 mx-auto text-[#2E5470] mb-1" />
                <p className="text-xs font-semibold text-[#7BA4BC]">
                  {isSearchActive
                    ? `No incidents matching "${searchQuery}" found in any category.`
                    : 'No incidents found in this category.'}
                </p>
                <p className="text-[11px] text-[#7BA4BC]">
                  {isSearchActive ? (
                    <button
                      type="button"
                      onClick={() => handleSearchChange('')}
                      className="text-[#00E5FF] hover:underline font-medium cursor-pointer"
                    >
                      Clear search to return to {tabs.find((t) => t.id === activeTab)?.label}
                    </button>
                  ) : (
                    'All monitored incidents in this workflow status have been processed.'
                  )}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-[rgba(0,213,255,0.04)] border-b border-[rgba(0,213,255,0.10)] text-[10px] font-bold uppercase tracking-wider text-[#7BA4BC]">
                      <th className="py-3 px-4">Air Basin / City</th>
                      <th className="py-3 px-4">Risk Severity</th>
                      <th className="py-3 px-4">Source Hypothesis</th>
                      <th className="py-3 px-4">Telemetry Time</th>
                      <th className="py-3 px-4">Assigned Authority</th>
                      <th className="py-3 px-4">Workflow Status</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(0,213,255,0.06)]">
                    {displayedEvents.map((event) => {
                      const category =
                        event.source_hypothesis?.category || 'Unspecified';

                      const isCritical = event.risk === 'CRITICAL';
                      const lifecycle = getEventLifecycle(event);
                      const isOutsideSelectedTab =
                        isSearchActive && lifecycle.id !== activeTab;

                      return (
                        <tr
                          key={event.event_id}
                          className={`hover:bg-[rgba(0,213,255,0.03)] transition-colors ${
                            isCritical ? 'bg-[rgba(255,68,68,0.03)]' : ''
                          }`}
                        >
                          {/* City & Coordinates */}
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-[#E8F4FD] text-sm">
                              {event.location.city}
                            </div>
                            <div className="text-[10px] font-mono text-[#2E5470] flex items-center gap-1 mt-0.5">
                              <MapPin className="w-3 h-3" />
                              <span>{event.event_id}</span>
                            </div>
                          </td>

                          {/* Risk Classification */}
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <RiskBadge level={event.risk} size="sm" />
                          </td>

                          {/* Event Type / Hypothesis */}
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <div className="flex items-center gap-1.5 font-medium text-[#E8F4FD] capitalize">
                              <Flame className="w-3.5 h-3.5 text-[#FF9F1C]" />
                              <span>{category.replace('_', ' ')}</span>
                            </div>
                            <span className="text-[10px] text-[#7BA4BC] font-mono">
                              Conf: {Math.round(event.source_hypothesis.confidence * 100)}%
                            </span>
                          </td>

                          {/* Time */}
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <div className="text-[#E8F4FD] font-medium font-mono tabular-telemetry">
                              {new Date(event.timestamp).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}{' '}
                              UTC
                            </div>
                            <div className="text-[10px] text-[#7BA4BC] font-mono">
                              {new Date(event.timestamp).toLocaleDateString([], {
                                month: 'short',
                                day: 'numeric',
                              })}
                            </div>
                          </td>

                          {/* Assigned Authority */}
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-1.5 text-[#7BA4BC] font-medium text-xs">
                              <Building2 className="w-3.5 h-3.5 text-[#2E5470] shrink-0" />
                              <span>
                                {event.response.authority_class ||
                                   'State Pollution Control Board'}
                              </span>
                            </div>
                          </td>

                          {/* Workflow Status */}
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <div className="flex flex-col gap-0.5 items-start">
                              <span
                                className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${lifecycle.badgeClass}`}
                              >
                                {lifecycle.label}
                              </span>
                              {isOutsideSelectedTab && (
                                <span className="text-[9px] font-mono text-[#7BA4BC]">
                                  (In {lifecycle.label})
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Action Button */}
                          <td className="py-3.5 px-4 text-right whitespace-nowrap">
                            <Link
                              href={`/dashboard/event?id=${event.event_id}&from=alerts${
                                activeTab !== 'active' ? `&tab=${activeTab}` : ''
                              }${
                                searchQuery.trim()
                                  ? `&q=${encodeURIComponent(searchQuery.trim())}`
                                  : ''
                              }`}
                              className="inline-flex items-center gap-1 px-3 py-1.5 bg-[rgba(0,229,255,0.10)] hover:bg-[rgba(0,229,255,0.18)] border border-[rgba(0,229,255,0.25)] text-[#00E5FF] text-xs font-semibold rounded transition-colors"
                            >
                              <span>Inspect Evidence</span>
                              <ArrowRight className="w-3 h-3" />
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

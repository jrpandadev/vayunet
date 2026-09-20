'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { getEvents, updateEventAction, getIsSimulationMode } from '@/lib/api';
import { PollutionEvent, AuthorityAction } from '@/lib/types';
import DashboardHeader from '@/components/layout/DashboardHeader';
import StatCard from '@/components/ui/StatCard';
import RiskBadge from '@/components/ui/RiskBadge';
import Card, { CardHeader, CardContent } from '@/components/ui/Card';
import { MOCK_FIRE_DETECTIONS } from '@/lib/fires';
import { MOCK_EMISSION_HOTSPOTS } from '@/lib/hotspots';
import { MOCK_RISK_ZONES } from '@/lib/riskZones';
import {
  Activity,
  AlertTriangle,
  Clock,
  ArrowRight,
  MapPin,
  Flame,
  Radio,
  ExternalLink,
  Shield,
  RefreshCw,
  ShieldCheck,
  CheckCircle2,
  Camera,
  Layers,
  Wind,
  Sparkles,
  Search,
  XCircle,
  Compass,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';

// Dynamic import of Leaflet map with SSR disabled
const LeafletMap = dynamic(() => import('@/components/map/LeafletMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[380px] flex flex-col items-center justify-center bg-slate-50 text-slate-400">
      <div className="h-7 w-7 border-2 border-[#0a2540] border-t-transparent rounded-full animate-spin mb-2" />
      <span className="text-xs font-mono">Loading Spatial Surveillance Grid...</span>
    </div>
  ),
});

const LIFECYCLE_STEPS = [
  'DETECT',
  'VERIFY',
  'FORECAST',
  'EXPLAIN',
  'ROUTE',
  'HUMAN RESPONSE',
  'LEARN',
];

function getEventLifecycleStage(event: PollutionEvent): {
  activeStepIndex: number;
  stageName: string;
  stageNote: string;
} {
  if (
    event.outcome === 'confirmed' ||
    event.outcome === 'false_alarm' ||
    event.outcome === 'resolved'
  ) {
    return {
      activeStepIndex: 6,
      stageName: 'LEARN',
      stageNote: `Outcome logged as ${event.outcome.replace('_', ' ')}. Feedback stored for model calibration.`,
    };
  }
  if (event.response.status === 'acknowledged') {
    return {
      activeStepIndex: 5,
      stageName: 'HUMAN RESPONSE',
      stageNote: 'Authority response acknowledged. Containment or field unit in progress.',
    };
  }
  if (event.response.status === 'pending') {
    return {
      activeStepIndex: 4,
      stageName: 'ROUTE',
      stageNote: 'Alert routed to municipal authority. Awaiting officer confirmation.',
    };
  }
  if (event.explanation) {
    return {
      activeStepIndex: 3,
      stageName: 'EXPLAIN',
      stageNote: 'Gemini multimodal reasoning synthesized across ground and orbital passes.',
    };
  }
  if (event.forecast) {
    return {
      activeStepIndex: 2,
      stageName: 'FORECAST',
      stageNote: 'Multi-horizon PM2.5 forecast computed across 6h/24h/72h horizons.',
    };
  }
  if (event.detection?.supporting_evidence?.length) {
    return {
      activeStepIndex: 1,
      stageName: 'VERIFY',
      stageNote: 'Cross-sensor corroboration & anomaly confidence scored.',
    };
  }
  return {
    activeStepIndex: 0,
    stageName: 'DETECT',
    stageNote: 'Initial telemetry signals captured.',
  };
}

export default function DashboardOverviewPage() {
  const [events, setEvents] = useState<PollutionEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedBasin, setSelectedBasin] = useState<string>('ALL');
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<boolean>(false);
  const [actionFeedback, setActionFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const [apiError, setApiError] = useState<string | null>(null);
  const [isSimulation, setIsSimulation] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    setApiError(null);
    try {
      const mode = getIsSimulationMode();
      setIsSimulation(mode);
      const data = await getEvents();
      setEvents(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error('Failed to load dashboard events:', err);
      setApiError(msg);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filter events by jurisdiction basin
  const filteredEvents = useMemo(() => {
    let list = events;
    if (selectedBasin !== 'ALL') {
      list = events.filter(
        (e) => e.location.city.toLowerCase() === selectedBasin.toLowerCase()
      );
    }
    // Sort urgent risks first, then descending by timestamp
    const riskPriority: Record<string, number> = {
      CRITICAL: 4,
      HIGH: 3,
      MODERATE: 2,
      LOW: 1,
    };
    return [...list].sort((a, b) => {
      const diff = (riskPriority[b.risk] || 0) - (riskPriority[a.risk] || 0);
      if (diff !== 0) return diff;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
  }, [events, selectedBasin]);

  // Keep selectedEventId synced when basin changes
  useEffect(() => {
    if (filteredEvents.length > 0) {
      const exists = filteredEvents.some((e) => e.event_id === selectedEventId);
      if (!exists) {
        setSelectedEventId(filteredEvents[0].event_id);
      }
    } else {
      setSelectedEventId(null);
    }
  }, [filteredEvents, selectedEventId]);

  // The active selected event object
  const selectedEvent = useMemo(() => {
    if (!filteredEvents.length) return null;
    return (
      filteredEvents.find((e) => e.event_id === selectedEventId) ||
      filteredEvents[0]
    );
  }, [filteredEvents, selectedEventId]);

  // Event Lifecycle KPI Metrics computed dynamically from current event dataset
  const metrics = useMemo(() => {
    // 1. Total Events in Basin
    const totalEventsInBasin = filteredEvents.length;

    // 2. Open Events (unresolved incidents, excluding resolved and false alarms)
    const openEvents = filteredEvents.filter(
      (e) => e.outcome !== 'resolved' && e.outcome !== 'false_alarm'
    ).length;

    // 3. Multi-Source Events (events with >= 2 corroborated evidence sources)
    const multiSourceEvents = filteredEvents.filter(
      (e) => (e.detection?.supporting_evidence?.length ?? 0) >= 2
    ).length;

    // 4. Awaiting Human Action (events pending authority decision)
    const awaitingHumanAction = filteredEvents.filter(
      (e) => e.response?.status === 'pending' || e.outcome === 'pending'
    ).length;

    return {
      totalEventsInBasin,
      openEvents,
      multiSourceEvents,
      awaitingHumanAction,
    };
  }, [filteredEvents]);

  // Step 10: High-level situation statistics calculated deterministically from existing datasets
  const situationStats = useMemo(() => {
    // 1. Observed Ground PM2.5 Peak & Station in selected basin
    const sensorPm25Values = filteredEvents
      .map((e) => e.evidence?.sensor?.pm25)
      .filter((val): val is number => typeof val === 'number' && !isNaN(val));

    const peakPm25 = sensorPm25Values.length > 0 ? Math.max(...sensorPm25Values) : null;
    const peakEvent = peakPm25 !== null ? filteredEvents.find((e) => e.evidence?.sensor?.pm25 === peakPm25) : undefined;
    const peakStation = peakEvent?.evidence?.sensor?.station_id || peakEvent?.location.city || 'CPCB Telemetry';

    // 2. Active Pollution Events (unresolved incidents: confirmed or pending)
    const activeEventsCount = filteredEvents.filter(
      (e) => e.outcome !== 'resolved' && e.outcome !== 'false_alarm'
    ).length;

    // 3. High / Critical Risk Zones
    // In NCR: zone_ncr_001 (CRITICAL: 320), zone_ncr_002 (VERY_HIGH: 245), zone_ncr_003 (HIGH: 185), zone_ncr_004 (HIGH: 160)
    const isNCRBasin = selectedBasin === 'ALL' || selectedBasin.toLowerCase() === 'delhi';
    const riskZones = isSimulation ? MOCK_RISK_ZONES : [];
    const criticalOrVeryHighZones = isNCRBasin
      ? riskZones.filter((z) => z.level === 'CRITICAL' || z.level === 'VERY_HIGH').length
      : 0;
    const totalHighRiskZones = isNCRBasin
      ? riskZones.filter((z) => z.level === 'CRITICAL' || z.level === 'VERY_HIGH' || z.level === 'HIGH').length
      : 0;

    // 4. Active Fire Detections (status === 'ACTIVE')
    // In NCR: fire_ncr_001 (HIGH, 2.4 Ha), fire_ncr_002 (MODERATE, 1.1 Ha), fire_ncr_003 (LOW, 0.5 Ha)
    const activeFiresList = isSimulation ? MOCK_FIRE_DETECTIONS : [];
    const activeFires = isNCRBasin
      ? activeFiresList.filter((f) => f.status === 'ACTIVE')
      : [];
    const activeFiresCount = activeFires.length;
    const totalBurnAreaHa = Math.round(activeFires.reduce((sum, f) => sum + (f.sizeHectares || 0), 0) * 10) / 10;

    // 5. Significant Emission Hotspots (isActiveRecent === true)
    // In NCR: hs_ncr_001 (CRITICAL, 310), hs_ncr_002 (VERY_HIGH, 255), hs_ncr_003 (HIGH, 195)
    const activeHotspotsList = isSimulation ? MOCK_EMISSION_HOTSPOTS : [];
    const activeHotspots = isNCRBasin
      ? activeHotspotsList.filter((h) => h.isActiveRecent)
      : [];
    const activeHotspotsCount = activeHotspots.length;
    const peakPlumePm25 = activeHotspots.length > 0 ? Math.max(...activeHotspots.map((h) => h.estimatedPm25)) : 0;

    // 6. Forecast Peak Outlook
    // In NCR: zone_ncr_001 predicts 320 µg/m³ PM2.5 over Next 24 Hours (88% confidence)
    const validForecasts = filteredEvents.map((e) => e.forecast?.pm25_24h).filter((val): val is number => typeof val === 'number' && !isNaN(val));
    const peakPredictedPm25 = isSimulation && isNCRBasin
      ? Math.max(...MOCK_RISK_ZONES.map((z) => z.predicted_pm25))
      : validForecasts.length > 0
      ? Math.max(...validForecasts)
      : null;

    return {
      peakPm25,
      peakStation,
      activeEventsCount,
      criticalOrVeryHighZones,
      totalHighRiskZones,
      activeFiresCount,
      totalBurnAreaHa,
      activeHotspotsCount,
      peakPlumePm25,
      peakPredictedPm25,
      isNCRBasin,
    };
  }, [filteredEvents, selectedBasin]);

  // Basin Telemetry & Evidence Profile: 100% computed from current filteredEvents
  const basinProfile = useMemo(() => {
    const total = filteredEvents.length;
    const withSensor = filteredEvents.filter((e) => e.evidence?.sensor).length;
    const withSatellite = filteredEvents.filter((e) => e.evidence?.satellite).length;
    const withCitizen = filteredEvents.filter((e) => e.evidence?.citizen).length;
    const withWeather = filteredEvents.filter((e) => e.evidence?.weather).length;

    // Unique ground station IDs reporting in this basin
    const activeStations = Array.from(
      new Set(
        filteredEvents
          .map((e) => e.evidence?.sensor?.station_id)
          .filter((id): id is string => Boolean(id))
      )
    );

    // Authority response status breakdown in this basin
    const pendingCount = filteredEvents.filter(
      (e) => e.response?.status === 'pending' || e.outcome === 'pending'
    ).length;
    const confirmedCount = filteredEvents.filter(
      (e) => e.outcome === 'confirmed' || e.response?.status === 'acknowledged'
    ).length;
    const closedCount = filteredEvents.filter(
      (e) => e.outcome === 'resolved' || e.outcome === 'false_alarm'
    ).length;

    return {
      total,
      withSensor,
      withSatellite,
      withCitizen,
      withWeather,
      activeStations,
      pendingCount,
      confirmedCount,
      closedCount,
    };
  }, [filteredEvents]);

  // Basin options with counts
  const basinCounts = useMemo(() => {
    return {
      ALL: events.length,
      Delhi: events.filter((e) => e.location.city.toLowerCase() === 'delhi').length,
      Mumbai: events.filter((e) => e.location.city.toLowerCase() === 'mumbai').length,
      Bhubaneswar: events.filter((e) => e.location.city.toLowerCase() === 'bhubaneswar').length,
    };
  }, [events]);

  const handleAuthorityAction = async (action: AuthorityAction) => {
    if (!selectedEvent) return;
    setActionInProgress(true);
    setActionFeedback(null);
    try {
      const result = await updateEventAction(selectedEvent.event_id, action);
      if (result.success) {
        setEvents((prev) =>
          prev.map((e) => (e.event_id === result.event.event_id ? result.event : e))
        );
        setActionFeedback({
          type: 'success',
          message: `Incident ${selectedEvent.event_id} marked as "${action.toUpperCase()}". Authority decision registered${result.isSimulation ? ' (Simulation Mode)' : ''}.`,
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Action failed';
      setActionFeedback({ type: 'error', message: `Action failed: ${msg}` });
    } finally {
      setActionInProgress(false);
    }
  };

  const currentStage = selectedEvent ? getEventLifecycleStage(selectedEvent) : null;

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <DashboardHeader
        title="Environmental Intelligence Command Center"
        subtitle="3-City Federated Pilot · Pollution Event Monitoring"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={loadData}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
              title="Refresh telemetry feed"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh Feed</span>
            </button>
            <Link
              href="/dashboard/alerts"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              <span className="hidden sm:inline">Alert Center</span>
              {metrics.awaitingHumanAction > 0 && (
                <span className="text-[10px] font-mono bg-amber-100 text-amber-900 px-1.5 py-0.2 rounded-full font-bold">
                  {metrics.awaitingHumanAction}
                </span>
              )}
            </Link>
            <Link
              href="/dashboard/map"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-semibold transition-colors shadow-xs"
            >
              <Radio className="w-3.5 h-3.5 text-sky-400" />
              <span>Full Spatial Grid</span>
            </Link>
          </div>
        }
      />

      <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Jurisdiction Basin Filters Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-white border border-slate-200 rounded-lg shadow-2xs">
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-sky-600 shrink-0" />
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Surveillance Basin:
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 'ALL', label: 'All Basins', count: basinCounts.ALL },
              { id: 'Delhi', label: 'Delhi NCR', count: basinCounts.Delhi },
              { id: 'Mumbai', label: 'Mumbai MMR', count: basinCounts.Mumbai },
              { id: 'Bhubaneswar', label: 'Bhubaneswar', count: basinCounts.Bhubaneswar },
            ].map((basin) => {
              const isSelected = selectedBasin === basin.id;
              return (
                <button
                  key={basin.id}
                  type="button"
                  onClick={() => setSelectedBasin(basin.id)}
                  className={`text-xs px-3 py-1.5 rounded-md font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                    isSelected
                      ? 'bg-[#0a2540] text-white shadow-xs'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  <span>{basin.label}</span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                      isSelected
                        ? 'bg-white/20 text-white'
                        : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {basin.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Step 10: Environmental Situation Overview (6 High-Impact SIH Stat Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5 sm:gap-4">
          {/* 1. Peak Observed Ground PM2.5 */}
          <StatCard
            title="Observed PM2.5 Peak"
            value={loading ? '...' : apiError ? 'UNAVAILABLE' : situationStats.peakPm25 === null ? 'UNAVAILABLE' : situationStats.peakPm25}
            unit={apiError || situationStats.peakPm25 === null ? '' : 'µg/m³'}
            subtitle={apiError || situationStats.peakPm25 === null ? 'Telemetry disconnected' : `${situationStats.peakStation} • Sensor`}
            icon={<Radio className="w-4 h-4 text-[#0a2540]" />}
            riskAccent={
              apiError || situationStats.peakPm25 === null
                ? undefined
                : situationStats.peakPm25 >= 180
                ? 'CRITICAL'
                : situationStats.peakPm25 >= 120
                ? 'HIGH'
                : 'MODERATE'
            }
            href="/dashboard/map"
          />

          {/* 2. Active Pollution Events */}
          <StatCard
            title="Active Events"
            value={loading ? '...' : apiError ? 'UNAVAILABLE' : situationStats.activeEventsCount}
            subtitle={
              apiError
                ? 'API error'
                : selectedBasin === 'ALL'
                ? 'Unresolved incidents in all basins'
                : `Active incidents in ${selectedBasin}`
            }
            icon={<AlertTriangle className="w-4 h-4 text-orange-600" />}
            riskAccent={!apiError && situationStats.activeEventsCount > 0 ? 'HIGH' : undefined}
            href="/dashboard/map"
          />

          {/* 3. High / Critical Risk Zones */}
          <StatCard
            title="High Risk Zones"
            value={
              loading
                ? '...'
                : !isSimulation
                ? 'UNAVAILABLE'
                : situationStats.isNCRBasin
                ? situationStats.criticalOrVeryHighZones
                : '0'
            }
            subtitle={
              !isSimulation
                ? 'Synthetic feature disabled in Live Mode'
                : situationStats.isNCRBasin
                ? `${situationStats.totalHighRiskZones} High+ corridors (NCR)`
                : 'Regional NCR Focus'
            }
            icon={<Layers className="w-4 h-4 text-purple-600" />}
            riskAccent={isSimulation && situationStats.criticalOrVeryHighZones > 0 ? 'CRITICAL' : undefined}
            href="/dashboard/map"
          />

          {/* 4. Active Fire Detections */}
          <StatCard
            title="Active Fires"
            value={
              loading
                ? '...'
                : !isSimulation
                ? 'UNAVAILABLE'
                : situationStats.isNCRBasin
                ? situationStats.activeFiresCount
                : '0'
            }
            subtitle={
              !isSimulation
                ? 'Synthetic feature disabled in Live Mode'
                : situationStats.isNCRBasin
                ? `${situationStats.totalBurnAreaHa} Ha burn (Bawana buffer)`
                : 'Regional NCR Focus'
            }
            icon={<Flame className="w-4 h-4 text-amber-600" />}
            riskAccent={isSimulation && situationStats.activeFiresCount > 0 ? 'HIGH' : undefined}
            href="/dashboard/map"
          />

          {/* 5. Significant Emission Hotspots */}
          <StatCard
            title="Emission Hotspots"
            value={
              loading
                ? '...'
                : !isSimulation
                ? 'UNAVAILABLE'
                : situationStats.isNCRBasin
                ? situationStats.activeHotspotsCount
                : '0'
            }
            subtitle={
              !isSimulation
                ? 'Synthetic feature disabled in Live Mode'
                : situationStats.isNCRBasin
                ? `Up to ${situationStats.peakPlumePm25} µg/m³ plume (Okhla)`
                : 'Regional NCR Focus'
            }
            icon={<Wind className="w-4 h-4 text-sky-600" />}
            riskAccent={isSimulation && situationStats.activeHotspotsCount > 0 ? 'CRITICAL' : undefined}
            href="/dashboard/map"
          />

          {/* 6. 24h Forecast Peak */}
          <StatCard
            title="24h Forecast Peak"
            value={loading ? '...' : apiError || situationStats.peakPredictedPm25 === null ? 'UNAVAILABLE' : situationStats.peakPredictedPm25}
            unit={apiError || situationStats.peakPredictedPm25 === null ? '' : 'µg/m³'}
            subtitle={
              apiError || situationStats.peakPredictedPm25 === null
                ? 'Forecast unavailable'
                : situationStats.isNCRBasin
                ? 'Bawana Corridor (Next 24h)'
                : `${selectedBasin} 24h outlook`
            }
            icon={<TrendingUp className="w-4 h-4 text-rose-600" />}
            riskAccent={!apiError && situationStats.peakPredictedPm25 !== null && situationStats.peakPredictedPm25 >= 250 ? 'CRITICAL' : (!apiError && situationStats.peakPredictedPm25 !== null && situationStats.peakPredictedPm25 >= 120 ? 'HIGH' : undefined)}
            href="/dashboard/forecast"
          />
        </div>

        {/* Action Feedback Banner */}
        {actionFeedback && (
          <div
            className={`p-3.5 rounded-lg border text-xs flex items-center justify-between gap-3 ${
              actionFeedback.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-rose-50 text-rose-800 border-rose-200'
            }`}
            role="status"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{actionFeedback.message}</span>
            </div>
            <button
              onClick={() => setActionFeedback(null)}
              className="text-[11px] underline opacity-80 hover:opacity-100 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Main Command Center Layout: Feed (Left) & Map + Dossier (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Column A: Operational Event Triage Feed (5 cols on lg) */}
          <div className="lg:col-span-5 space-y-4">
            <Card className="overflow-hidden">
              <CardHeader
                title="Operational Incident Feed"
                subtitle={`${filteredEvents.length} pollution event${
                  filteredEvents.length === 1 ? '' : 's'
                } in selected basin`}
                action={
                  <span className="text-[11px] font-mono text-slate-500">
                    Priority Sorted
                  </span>
                }
              />

              <CardContent className="p-2 space-y-2 max-h-[520px] overflow-y-auto">
                {loading ? (
                  <div className="p-8 text-center text-xs text-slate-400">
                    <div className="h-6 w-6 border-2 border-[#0a2540] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    Ingesting active event catalog...
                  </div>
                ) : apiError ? (
                  <div className="p-8 text-center text-xs text-slate-400 border border-rose-200 bg-rose-50 rounded-lg m-2">
                    <AlertTriangle className="w-6 h-6 text-rose-500 mx-auto mb-2" />
                    <span className="text-rose-700 font-bold block mb-1">Event feed unavailable</span>
                    <span className="text-rose-600 opacity-80">{apiError}</span>
                  </div>
                ) : filteredEvents.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-400">
                    No pollution incidents registered in this basin.
                  </div>
                ) : (
                  filteredEvents.map((evt) => {
                    const isSelected = selectedEvent?.event_id === evt.event_id;
                    const eventCategory =
                      evt.source_hypothesis?.category ||
                      evt.evidence?.citizen?.gemini_output?.event_type;

                    const pm25 = evt.evidence?.sensor?.pm25;
                    const isPending = evt.response?.status === 'pending';

                    return (
                      <div
                        key={evt.event_id}
                        onClick={() => setSelectedEventId(evt.event_id)}
                        className={`p-3.5 rounded-lg border transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-sky-50/50 border-sky-500 border-l-4 border-l-sky-600 shadow-xs'
                            : 'bg-white hover:bg-slate-50 border-slate-200'
                        }`}
                      >
                        {/* Top: City, ID, Risk Badge */}
                        <div className="flex items-start justify-between gap-2 mb-1.5">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-bold text-sm text-[#0f172a]">
                              {evt.location.city}
                            </span>
                            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded">
                              {evt.event_id}
                            </span>
                          </div>
                          <RiskBadge level={evt.risk} size="sm" />
                        </div>

                        {/* Middle: Source hypothesis & PM2.5 measurement */}
                        <div className="flex items-center gap-2 text-xs text-slate-700 mb-2 flex-wrap">
                          {eventCategory && (
                            <span className="inline-flex items-center gap-1 capitalize font-medium text-slate-800">
                              <Flame className="w-3.5 h-3.5 text-orange-500" />
                              {eventCategory.replace('_', ' ')}
                            </span>
                          )}
                          {pm25 !== undefined && (
                            <>
                              <span className="text-slate-300">•</span>
                              <span className="font-mono text-[11px] text-slate-600">
                                PM2.5: <strong className="text-slate-900">{pm25} µg/m³</strong>
                              </span>
                            </>
                          )}
                        </div>

                        {/* Evidence Provenance Badges (Based solely on existing evidence fields) */}
                        <div className="flex items-center gap-1.5 mb-2.5 flex-wrap">
                          <span className="text-[10px] uppercase font-bold text-slate-400 mr-0.5">
                            Sources:
                          </span>
                          {evt.evidence?.sensor && (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 inline-flex items-center gap-1">
                              <Activity className="w-2.5 h-2.5 text-[#0a2540]" />
                              CPCB
                            </span>
                          )}
                          {evt.evidence?.satellite && (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200 inline-flex items-center gap-1">
                              <Layers className="w-2.5 h-2.5 text-sky-600" />
                              Sentinel-5P
                            </span>
                          )}
                          {evt.evidence?.citizen && (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 inline-flex items-center gap-1">
                              <Camera className="w-2.5 h-2.5 text-amber-600" />
                              Citizen
                            </span>
                          )}
                          {evt.evidence?.weather && (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-cyan-50 text-cyan-800 border border-cyan-200 inline-flex items-center gap-1">
                              <Wind className="w-2.5 h-2.5 text-cyan-600" />
                              Weather
                            </span>
                          )}
                        </div>

                        {/* Bottom Row: Timestamp, Response status, Triage indicator */}
                        <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-[#64748b]">
                          <span className="flex items-center gap-1 font-mono text-slate-400">
                            <Clock className="w-3 h-3" />
                            {new Date(evt.timestamp).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>

                          <div className="flex items-center gap-2">
                            {isPending ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                                Action Pending
                              </span>
                            ) : (
                              <span className="text-[10px] font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded capitalize">
                                {evt.outcome || evt.response?.status}
                              </span>
                            )}
                            <span className="text-xs font-semibold text-sky-700 flex items-center">
                              Inspect <ChevronRight className="w-3 h-3 ml-0.5" />
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </CardContent>
            </Card>

            {/* Basin Telemetry & Evidence Profile (Balances Left Column Vertically) */}
            <Card className="overflow-hidden border border-slate-200 shadow-2xs">
              <CardHeader
                title="Jurisdiction Telemetry Profile"
                subtitle={
                  selectedBasin === 'ALL'
                    ? 'Cross-basin sensor & evidence coverage'
                    : `${selectedBasin} basin sensor & evidence coverage`
                }
                action={
                  <span className="text-[10px] font-mono text-slate-500 uppercase bg-slate-100 px-2 py-0.5 rounded">
                    {selectedBasin} Pilot
                  </span>
                }
              />
              <CardContent className="p-4 space-y-4">
                {/* Evidence Source Coverage in this basin */}
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-2 font-mono">
                    Evidence Source Presence ({basinProfile.total} Events)
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between text-slate-700">
                        <span className="flex items-center gap-1.5 font-medium">
                          <Activity className="w-3.5 h-3.5 text-[#0a2540]" />
                          CPCB Sensors
                        </span>
                        <span className="font-bold text-slate-900 font-mono">
                          {basinProfile.withSensor}/{basinProfile.total}
                        </span>
                      </div>
                    </div>

                    <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between text-slate-700">
                        <span className="flex items-center gap-1.5 font-medium">
                          <Layers className="w-3.5 h-3.5 text-sky-600" />
                          Sentinel-5P
                        </span>
                        <span className="font-bold text-slate-900 font-mono">
                          {basinProfile.withSatellite}/{basinProfile.total}
                        </span>
                      </div>
                    </div>

                    <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between text-slate-700">
                        <span className="flex items-center gap-1.5 font-medium">
                          <Camera className="w-3.5 h-3.5 text-amber-600" />
                          Citizen Reports
                        </span>
                        <span className="font-bold text-slate-900 font-mono">
                          {basinProfile.withCitizen}/{basinProfile.total}
                        </span>
                      </div>
                    </div>

                    <div className="p-2.5 rounded bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between text-slate-700">
                        <span className="flex items-center gap-1.5 font-medium">
                          <Wind className="w-3.5 h-3.5 text-cyan-600" />
                          Weather Links
                        </span>
                        <span className="font-bold text-slate-900 font-mono">
                          {basinProfile.withWeather}/{basinProfile.total}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Ground Sensor Stations in Basin */}
                {basinProfile.activeStations.length > 0 && (
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5 font-mono">
                      Linked Ground Stations ({basinProfile.activeStations.length})
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {basinProfile.activeStations.map((station) => (
                        <span
                          key={station}
                          className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200"
                        >
                          {station}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Authority Incident Disposition */}
                <div className="pt-2 border-t border-slate-100">
                  <div className="flex items-center justify-between text-[11px] text-slate-600">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-500" />
                      Awaiting Action:{' '}
                      <strong className="text-slate-900 font-mono">
                        {basinProfile.pendingCount}
                      </strong>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-sky-500" />
                      Active/Confirmed:{' '}
                      <strong className="text-slate-900 font-mono">
                        {basinProfile.confirmedCount}
                      </strong>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-slate-400" />
                      Closed/Resolved:{' '}
                      <strong className="text-slate-900 font-mono">
                        {basinProfile.closedCount}
                      </strong>
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Column B: Map Canvas (Top) & Incident Dossier (Bottom) (7 cols on lg) */}
          <div className="lg:col-span-7 space-y-6">
            {/* 1. Spatial Hotspot Map */}
            <Card className="overflow-hidden">
              <CardHeader
                title="Spatial Hotspot Surveillance"
                subtitle="Simulated telemetry pins · Selected hotspot synchronized with dossier"
                action={
                  <Link
                    href="/dashboard/map"
                    className="inline-flex items-center gap-1 text-xs font-semibold text-[#0a2540] hover:text-sky-700 transition-colors"
                  >
                    <span>Full Screen Grid</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                }
              />
              <div className="h-[360px] sm:h-[400px] w-full relative">
                <LeafletMap
                  events={filteredEvents}
                  selectedEventId={selectedEvent?.event_id}
                  onSelectEvent={(id) => setSelectedEventId(id)}
                  defaultToNCR={false}
                  autoFitAll={true}
                  showControls={false}
                  className="w-full h-full"
                />
              </div>

              {/* Map Footer Bar */}
              <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50 flex flex-wrap items-center justify-between gap-2 text-xs text-[#64748b]">
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-sky-600" />
                  {selectedEvent ? (
                    <span>
                      Active Focus:{' '}
                      <strong className="text-slate-800">
                        {selectedEvent.location.city}
                      </strong>{' '}
                      <span className="font-mono text-[11px] text-slate-500">
                        [{selectedEvent.event_id}]
                      </span>
                    </span>
                  ) : (
                    <span>Select an incident pin to inspect forensic evidence</span>
                  )}
                </div>

                <div className="flex items-center gap-2 text-[11px]">
                  <span className="inline-flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-500" />
                    Critical
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-orange-500" />
                    High
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    Moderate
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    Low
                  </span>
                </div>
              </div>
            </Card>

            {/* 2. Incident Intelligence Dossier for Selected Event */}
            {selectedEvent ? (
              <Card className="border-2 border-slate-200 shadow-sm">
                <div className="p-5 border-b border-slate-100 bg-gradient-to-r from-slate-50 via-white to-sky-50/30">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-sky-700 font-mono">
                          Active Incident Dossier
                        </span>
                        <span className="text-slate-300">•</span>
                        <span className="font-mono text-xs text-slate-500">
                          {selectedEvent.event_id}
                        </span>
                      </div>
                      <h3 className="text-lg sm:text-xl font-bold text-[#0f172a] mt-0.5">
                        {selectedEvent.location.city} Environmental Anomaly
                      </h3>
                      <p className="text-xs text-slate-500 flex items-center gap-2 mt-1">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        <span className="font-mono">
                          {selectedEvent.location.lat.toFixed(4)}°N,{' '}
                          {selectedEvent.location.lng.toFixed(4)}°E
                        </span>
                        <span>•</span>
                        <Clock className="w-3 h-3 text-slate-400" />
                        <span>
                          {new Date(selectedEvent.timestamp).toUTCString()}
                        </span>
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <RiskBadge level={selectedEvent.risk} size="md" />
                      {selectedEvent.response.alert_sent && (
                        <span className="text-xs font-semibold px-2 py-1 rounded bg-rose-50 text-rose-700 border border-rose-200">
                          Alert Routed
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="p-5 space-y-5">
                  {/* 7-Step Lifecycle Indicator */}
                  {currentStage && (
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                          7-Step Decision Pipeline Status
                        </span>
                        <span className="text-[11px] font-semibold text-sky-800 bg-sky-100 px-2 py-0.5 rounded">
                          Stage {currentStage.activeStepIndex + 1}: {currentStage.stageName}
                        </span>
                      </div>

                      {/* Stepper Progression */}
                      <div className="overflow-x-auto pb-1">
                        <div className="grid grid-cols-7 gap-1 text-center text-[9px] font-bold uppercase tracking-wider min-w-[460px] sm:min-w-0">
                          {LIFECYCLE_STEPS.map((step, idx) => {
                            const isPast = idx < currentStage.activeStepIndex;
                            const isCurrent = idx === currentStage.activeStepIndex;
                            return (
                              <div
                                key={step}
                                className={`py-1 px-0.5 rounded transition-colors ${
                                  isCurrent
                                    ? 'bg-[#0a2540] text-white shadow-2xs'
                                    : isPast
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-slate-200/70 text-slate-400'
                                }`}
                                title={`Step ${idx + 1}: ${step}`}
                              >
                                <span className="block truncate">{step}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-2 italic">
                        {currentStage.stageNote}
                      </p>
                    </div>
                  )}

                  {/* Gemini AI Multimodal Explanation Excerpt */}
                  {selectedEvent.explanation && (
                    <div className="p-4 rounded-lg bg-sky-50/60 border border-sky-200/80">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-sky-900 mb-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-sky-600" />
                        <span>Gemini Multimodal Reasoning Synthesis</span>
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">
                        {selectedEvent.explanation
                          .replace(/satellite confirms elevated NO2/gi, 'satellite provides corroborating evidence of elevated NO₂')
                          .replace(/satellite confirms elevated NO₂/gi, 'satellite provides corroborating evidence of elevated NO₂')
                          .replace(/\bconfirms\b/gi, 'provides corroborating evidence of')}
                      </p>
                      {selectedEvent.source_hypothesis && (
                        <div className="mt-2 pt-2 border-t border-sky-200/60 flex items-center justify-between text-[11px] text-sky-900">
                          <span>
                            Source Hypothesis:{' '}
                            <strong className="capitalize">
                              {selectedEvent.source_hypothesis.category.replace(
                                '_',
                                ' '
                              )}
                            </strong>
                          </span>
                          <span className="font-mono font-bold">
                            Confidence:{' '}
                            {Math.round(
                              selectedEvent.source_hypothesis.confidence * 100
                            )}
                            %
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 4-Source Fused Evidence Telemetry Breakdown */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-2.5">
                      Fused Multi-Source Telemetry Breakdown
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {/* CPCB Sensor */}
                      <div className="p-3 bg-slate-50 rounded border border-slate-200">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 mb-1">
                          <Activity className="w-3.5 h-3.5 text-[#0a2540]" />
                          <span>CPCB Ground Sensor</span>
                        </div>
                        {selectedEvent.evidence?.sensor ? (
                          <div className="text-[11px] text-slate-600 space-y-0.5">
                            <p>
                              Station:{' '}
                              <strong className="text-slate-800 font-mono">
                                {selectedEvent.evidence.sensor.station_id}
                              </strong>
                            </p>
                            <p className="tabular-telemetry">
                              PM2.5:{' '}
                              <strong className="text-slate-900">
                                {selectedEvent.evidence.sensor.pm25} µg/m³
                              </strong>{' '}
                              · PM10: {selectedEvent.evidence.sensor.pm10} µg/m³
                            </p>
                            <p className="text-slate-500 font-mono">
                              Anomaly Score:{' '}
                              {selectedEvent.evidence.sensor.anomaly_score}
                            </p>
                          </div>
                        ) : (
                          <p className="text-[11px] text-slate-400 italic">
                            No ground sensor attached
                          </p>
                        )}
                      </div>

                      {/* Sentinel-5P Satellite */}
                      <div className="p-3 bg-slate-50 rounded border border-slate-200">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 mb-1">
                          <Layers className="w-3.5 h-3.5 text-sky-700" />
                          <span>Sentinel-5P Satellite</span>
                        </div>
                        {selectedEvent.evidence?.satellite ? (
                          <div className="text-[11px] text-slate-600 space-y-0.5">
                            <p>
                              NO₂ Column Index:{' '}
                              <strong className="text-slate-900 font-mono">
                                {selectedEvent.evidence.satellite.no2_index}
                              </strong>
                            </p>
                            <p>
                              Aerosol Index:{' '}
                              <strong className="text-slate-900 font-mono">
                                {selectedEvent.evidence.satellite.aerosol_index}
                              </strong>
                            </p>
                            <p className="text-slate-500">
                              Pass:{' '}
                              <span className="capitalize font-mono">
                                {selectedEvent.evidence.satellite.freshness}
                              </span>
                            </p>
                          </div>
                        ) : (
                          <p className="text-[11px] text-slate-400 italic">
                            No satellite overpass linked
                          </p>
                        )}
                      </div>

                      {/* Citizen Observations */}
                      <div className="p-3 bg-slate-50 rounded border border-slate-200">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 mb-1">
                          <Camera className="w-3.5 h-3.5 text-amber-600" />
                          <span>Citizen Observation</span>
                        </div>
                        {selectedEvent.evidence?.citizen ? (
                          <div className="text-[11px] text-slate-600 space-y-0.5">
                            <p>
                              Type:{' '}
                              <strong className="capitalize text-slate-800">
                                {selectedEvent.evidence.citizen.gemini_output?.event_type || 'Report filed'}
                              </strong>
                              {selectedEvent.evidence.citizen.gemini_output?.severity && (
                                <>
                                  {' '}· Severity:{' '}
                                  <span className="capitalize">
                                    {selectedEvent.evidence.citizen.gemini_output.severity}
                                  </span>
                                </>
                              )}
                            </p>
                            <p className="line-clamp-2 text-slate-500">
                              &ldquo;
                              {selectedEvent.evidence.citizen.gemini_output?.description}
                              &rdquo;
                            </p>
                          </div>
                        ) : (
                          <p className="text-[11px] text-slate-400 italic">
                            No citizen reports filed
                          </p>
                        )}
                      </div>

                      {/* Weather */}
                      <div className="p-3 bg-slate-50 rounded border border-slate-200">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 mb-1">
                          <Wind className="w-3.5 h-3.5 text-cyan-700" />
                          <span>Weather (Open-Meteo)</span>
                        </div>
                        {selectedEvent.evidence?.weather ? (
                          <div className="text-[11px] text-slate-600 space-y-0.5">
                            <p>
                              Wind Speed:{' '}
                              <strong className="text-slate-900 font-mono">
                                {selectedEvent.evidence.weather.wind_speed_kmh} km/h
                              </strong>
                            </p>
                            <p>
                              Relative Humidity:{' '}
                              <strong className="text-slate-900 font-mono">
                                {selectedEvent.evidence.weather.humidity_percent}%
                              </strong>
                            </p>
                            <p className="text-slate-500">
                              Atmospheric Stagnation Tracked
                            </p>
                          </div>
                        ) : (
                          <p className="text-[11px] text-slate-400 italic">
                            No synoptic weather stream
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Multi-Horizon PM2.5 Forecast (Existing Schema Forecast Data) */}
                  {selectedEvent.forecast && (
                    <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                          <TrendingUp className="w-3.5 h-3.5 text-sky-700" />
                          <span>PM2.5 Forecast vs NAAQS / WHO Reference Levels</span>
                        </div>
                        <span className="text-[11px] text-slate-500 font-mono">
                          Spike Risk: <strong>{selectedEvent.forecast.spike_probability}</strong>
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                        <div className="bg-white p-2 rounded border border-slate-200">
                          <span className="text-[10px] text-slate-400 block uppercase">
                            Baseline
                          </span>
                          <span className="font-bold text-slate-900 tabular-telemetry">
                            {selectedEvent.evidence?.sensor?.pm25 || '—'} µg/m³
                          </span>
                        </div>
                        <div className="bg-white p-2 rounded border border-slate-200">
                          <span className="text-[10px] text-slate-400 block uppercase">
                            +6h Horizon
                          </span>
                          <span className="font-bold text-slate-900 tabular-telemetry">
                            {selectedEvent.forecast.pm25_6h} µg/m³
                          </span>
                        </div>
                        <div className="bg-white p-2 rounded border border-slate-200">
                          <span className="text-[10px] text-slate-400 block uppercase">
                            +24h Horizon
                          </span>
                          <span className="font-bold text-slate-900 tabular-telemetry">
                            {selectedEvent.forecast.pm25_24h} µg/m³
                          </span>
                        </div>
                        <div className="bg-white p-2 rounded border border-slate-200">
                          <span className="text-[10px] text-slate-400 block uppercase">
                            +72h Horizon
                          </span>
                          <span className="font-bold text-slate-900 tabular-telemetry">
                            {selectedEvent.forecast.pm25_72h} µg/m³
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Authority Quick Action Bar (If pending) */}
                  {selectedEvent.response.status === 'pending' && (
                    <div className="pt-2 border-t border-slate-200">
                      <p className="text-xs text-slate-600 mb-2.5 font-medium">
                        Authorized Officer Decision:
                      </p>
                      <div className="flex flex-wrap gap-2.5">
                        <button
                          type="button"
                          onClick={() => handleAuthorityAction('confirm')}
                          disabled={actionInProgress}
                          className="inline-flex items-center gap-1.5 px-3 py-2 rounded bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Confirm Event & Issue Alert</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleAuthorityAction('investigate')}
                          disabled={actionInProgress}
                          className="inline-flex items-center gap-1.5 px-3 py-2 rounded bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                        >
                          <Search className="w-3.5 h-3.5 text-sky-600" />
                          <span>Dispatch Inspection Unit</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleAuthorityAction('dismiss')}
                          disabled={actionInProgress}
                          className="inline-flex items-center gap-1.5 px-3 py-2 rounded bg-white hover:bg-rose-50 text-rose-700 border border-rose-200 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                        >
                          <XCircle className="w-3.5 h-3.5 text-rose-600" />
                          <span>Dismiss as False Alarm</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Primary CTA Link to Full Forensic Screen */}
                  <div className="pt-2">
                    <Link
                      href={`/dashboard/event/${selectedEvent.event_id}`}
                      className="w-full py-2.5 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors shadow-xs"
                    >
                      <span>View Full Event Intelligence & Forensic Timeline</span>
                      <ArrowRight className="w-4 h-4 text-sky-200" />
                    </Link>
                  </div>
                </div>
              </Card>
            ) : (
              <div className="p-8 bg-white border border-slate-200 rounded-lg text-center text-xs text-slate-400">
                Select an incident from the feed or map to inspect evidence dossier.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

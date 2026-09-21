'use client';

import React, { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { getEvents, getIsSimulationMode } from '@/lib/api';
import { PollutionEvent, RiskLevel } from '@/lib/types';
import DashboardHeader from '@/components/layout/DashboardHeader';
import MapFilter, { MapFilterState } from '@/components/map/MapFilter';
import MapLegend from '@/components/map/MapLegend';
import MapLayersPanel, {
  MapLayersState,
  DEFAULT_MAP_LAYERS,
} from '@/components/map/MapLayersPanel';
import MapInfoPanel from '@/components/map/MapInfoPanel';
import MapAlertBanner from '@/components/map/MapAlertBanner';
import MapSearch, {
  SearchResultItem,
  DELHI_NCR_CENTER,
  DELHI_NCR_ZOOM,
} from '@/components/map/MapSearch';
import { getDerivedMapAlerts, MapAlertItem } from '@/lib/alerts';
import { MOCK_FIRE_DETECTIONS } from '@/lib/fires';
import { MOCK_EMISSION_HOTSPOTS } from '@/lib/hotspots';
import { MOCK_RISK_ZONES } from '@/lib/riskZones';
import { MOCK_CITIZEN_OBSERVATIONS } from '@/lib/observations';
import {
  MapPin,
  RefreshCw,
  Clock,
  Radio,
  TrendingUp,
  Compass,
  AlertCircle,
  Activity,
  Layers,
  Wind,
} from 'lucide-react';

// Dynamic import with SSR disabled to prevent Leaflet window reference errors
const LeafletMap = dynamic(() => import('@/components/map/LeafletMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center bg-slate-100 text-slate-500">
      <div className="h-8 w-8 border-3 border-[#0a2540] border-t-transparent rounded-full animate-spin mb-3" />
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
        Initializing Spatial Leaflet Engine...
      </span>
    </div>
  ),
});

export default function MapPage() {
  const [events, setEvents] = useState<PollutionEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [searchCoordinate, setSearchCoordinate] = useState<[number, number] | null>(null);
  const [cameraFocusTarget, setCameraFocusTarget] = useState<{
    lat: number;
    lng: number;
    zoom?: number;
    timestamp: number;
  } | null>(null);

  const isSimulation = getIsSimulationMode();

  const [filterState, setFilterState] = useState<MapFilterState>({
    city: 'ALL',
    risk: 'ALL',
    timeRange: 'ALL',
  });

  const [layersState, setLayersState] = useState<MapLayersState>(DEFAULT_MAP_LAYERS);

  const loadAllEvents = async () => {
    setLoading(true);
    try {
      const data = await getEvents();
      setEvents(data);
    } catch (err) {
      console.error('Failed to load map events:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllEvents();
  }, []);

  // Extract distinct monitored cities from loaded events
  const cities = useMemo(() => {
    const set = new Set<string>();
    events.forEach((e) => set.add(e.location.city));
    return Array.from(set).sort();
  }, [events]);

  // Derive latest data update timestamp from currently active event dataset (HH:MM)
  const latestDataTimestamp = useMemo(() => {
    if (!events || events.length === 0) return '--:--';
    const times = events
      .map((e) => new Date(e.timestamp).getTime())
      .filter((t) => !isNaN(t));
    if (times.length === 0) return '--:--';
    const maxTime = new Date(Math.max(...times));
    return maxTime.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }, [events]);

  // Derive dynamic representative wind speed from ingested event telemetry (defaulting to 12 km/h)
  const activeWindSpeed = useMemo(() => {
    if (!events || events.length === 0) return 12;
    const speeds = events
      .map((e) => e.evidence?.weather?.wind_speed_kmh)
      .filter((s): s is number => typeof s === 'number' && !isNaN(s));
    if (speeds.length === 0) return 12;
    const avg = speeds.reduce((a, b) => a + b, 0) / speeds.length;
    return Math.round(avg * 10) / 10;
  }, [events]);

  // Filter events based on active controls
  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      // 1. City Filter
      if (filterState.city !== 'ALL' && e.location.city !== filterState.city) {
        return false;
      }

      // 2. Risk Filter
      if (filterState.risk !== 'ALL' && e.risk !== filterState.risk) {
        return false;
      }

      // 3. Time Horizon Filter
      if (filterState.timeRange !== 'ALL') {
        const eventTime = new Date(e.timestamp).getTime();
        const now = Date.now();
        const diffHours = (now - eventTime) / (1000 * 3600);

        if (filterState.timeRange === '24H' && diffHours > 24) return false;
        if (filterState.timeRange === '48H' && diffHours > 48) return false;
        if (filterState.timeRange === '7D' && diffHours > 168) return false;
      }

      return true;
    });
  }, [events, filterState]);

  const handleFilterChange = (newState: Partial<MapFilterState>) => {
    setFilterState((prev) => ({ ...prev, ...newState }));
  };

  const handleResetFilters = () => {
    setFilterState({
      city: 'ALL',
      risk: 'ALL',
      timeRange: 'ALL',
    });
  };

  const handleToggleLayer = (layerKey: keyof MapLayersState, value: boolean) => {
    setLayersState((prev) => ({ ...prev, [layerKey]: value }));
  };

  const handleSelectAllLayers = () => {
    setLayersState({
      riskZones: true,
      hotspots: true,
      fires: true,
      observations: true,
      events: true,
      wind: true,
    });
  };

  const handleResetDefaultLayers = () => {
    setLayersState(DEFAULT_MAP_LAYERS);
  };

  const handleClearAllLayers = () => {
    setLayersState({
      riskZones: false,
      hotspots: false,
      fires: false,
      observations: false,
      events: false,
      wind: false,
    });
  };

  // Step 11: Derive prioritized surveillance alerts from actual project data
  const alerts = useMemo(() => {
    return getDerivedMapAlerts(
      events,
      isSimulation ? MOCK_FIRE_DETECTIONS : [],
      isSimulation ? MOCK_EMISSION_HOTSPOTS : [],
      isSimulation ? MOCK_RISK_ZONES : [],
      filterState.city
    );
  }, [events, filterState.city, isSimulation]);

  const handleInspectAlert = (alert: MapAlertItem) => {
    // 1. Auto-enable the corresponding layer if currently disabled
    if (!layersState[alert.targetLayer]) {
      setLayersState((prev) => ({ ...prev, [alert.targetLayer]: true }));
    }

    // 2. If target is a base station event, ensure active filters do not hide it
    if (alert.targetLayer === 'events') {
      const targetEvt = events.find((e) => e.event_id === alert.targetEntityId);
      if (targetEvt) {
        if (filterState.city !== 'ALL' && filterState.city !== targetEvt.location.city) {
          setFilterState((prev) => ({ ...prev, city: 'ALL' }));
        }
        if (filterState.risk !== 'ALL' && filterState.risk !== targetEvt.risk) {
          setFilterState((prev) => ({ ...prev, risk: 'ALL' }));
        }
      }
    }

    // 3. Set selected entity -> MapSelectionFocuser centers/zooms, and MapInfoPanel opens
    setSelectedEventId(alert.targetEntityId);
  };

  // Step 9: Handle search selection of an existing VayuNet entity
  const handleSelectSearchEntity = (item: SearchResultItem) => {
    // 1. Clear any raw coordinate highlight pin
    setSearchCoordinate(null);

    // 2. Auto-enable the target layer if currently disabled
    if (item.targetLayer && !layersState[item.targetLayer]) {
      setLayersState((prev) => ({ ...prev, [item.targetLayer!]: true }));
    }

    // 3. Auto-reset filters if active filter would hide the selected entity
    if (item.city && item.city !== 'ALL') {
      if (filterState.city !== 'ALL' && filterState.city !== item.city) {
        setFilterState((prev) => ({ ...prev, city: 'ALL' }));
      }
    }

    if (item.type === 'STATION' && item.data?.risk) {
      if (filterState.risk !== 'ALL' && filterState.risk !== item.data.risk) {
        setFilterState((prev) => ({ ...prev, risk: 'ALL' }));
      }
    }

    // 4. Set selected entity -> MapSelectionFocuser centers/zooms, and MapInfoPanel opens
    setSelectedEventId(item.entityId || item.id);
  };

  // Step 9: Handle raw coordinate search
  const handleSelectCoordinates = (lat: number, lng: number) => {
    // Deselect any active entity so MapInfoPanel does not open for nonexistent entities
    setSelectedEventId(null);
    setSearchCoordinate([lat, lng]);
    setCameraFocusTarget({
      lat,
      lng,
      zoom: 13,
      timestamp: Date.now(),
    });
  };

  // Step 9: Handle city-level selection
  const handleSelectCity = (cityName: string, coords: [number, number], zoom: number) => {
    setSelectedEventId(null);
    setSearchCoordinate(null);
    if (cities.includes(cityName)) {
      setFilterState((prev) => ({ ...prev, city: cityName }));
    } else {
      setFilterState((prev) => ({ ...prev, city: 'ALL' }));
    }
    setCameraFocusTarget({
      lat: coords[0],
      lng: coords[1],
      zoom,
      timestamp: Date.now(),
    });
  };

  // Step 9: Handle "Go to NCR" button action
  const handleGoToNCR = () => {
    setSelectedEventId(null);
    setSearchCoordinate(null);
    setFilterState((prev) => ({ ...prev, city: 'ALL' }));
    setCameraFocusTarget({
      lat: DELHI_NCR_CENTER[0],
      lng: DELHI_NCR_CENTER[1],
      zoom: DELHI_NCR_ZOOM,
      timestamp: Date.now(),
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-50px)] md:h-screen overflow-hidden bg-slate-100">
      {/* Primary Dashboard Header */}
      <DashboardHeader
        title="Geospatial Pollution Surveillance"
        subtitle="Interactive Leaflet Map • CPCB, Sentinel-5P & Citizen Evidence"
        actions={
          <button
            onClick={loadAllEvents}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer bg-white"
            title="Refresh surveillance events"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Feed</span>
          </button>
        }
      />

      {/* Operational Surveillance HUD Status Bar */}
      <div className="bg-white border-b border-slate-200 px-4 py-2 flex flex-wrap items-center justify-between gap-2.5 text-xs select-none shrink-0 z-10 shadow-2xs">
        {/* Left Status Chips */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Simulation Mode Badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-900 border border-amber-200">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span>Simulation Mode</span>
          </span>

          {/* Data Timestamp Badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-medium bg-slate-50 text-slate-700 border border-slate-200">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>Data updated: <strong>{latestDataTimestamp}</strong></span>
          </span>

          {/* PM2.5 Forecast Horizon Badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-sky-50 text-sky-800 border border-sky-200">
            <TrendingUp className="w-3.5 h-3.5 text-sky-600" />
            <span>PM2.5 forecast: next 24 hours</span>
          </span>

          {/* Wind Telemetry Badge (Step 8) */}
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-opacity ${
              layersState.wind
                ? 'bg-cyan-50 text-cyan-900 border-cyan-200'
                : 'bg-slate-50 text-slate-400 border-slate-200 opacity-50 line-through'
            }`}
            title="Prevailing Atmospheric Wind Direction & Velocity"
          >
            <Wind className={`w-3.5 h-3.5 ${layersState.wind ? 'text-cyan-600' : 'text-slate-400'}`} />
            <span>NW • <strong>{activeWindSpeed} km/h</strong></span>
          </span>
        </div>

        {/* Right Status Context */}
        <div className="hidden sm:flex items-center gap-3 text-[11px] text-slate-600">
          <span className="inline-flex items-center gap-1">
            <Compass className="w-3.5 h-3.5 text-sky-600" />
            <span>Default Focal Basin: <strong>Delhi NCR</strong></span>
          </span>
          <span className="text-slate-300">•</span>
          <span
            className={`font-mono transition-opacity ${
              layersState.events ? 'text-slate-500' : 'text-slate-400 opacity-50 line-through'
            }`}
          >
            {filteredEvents.length} Monitored Sites
          </span>
          <span className="text-slate-300">•</span>
          <span
            className={`font-mono px-1.5 py-0.5 rounded border font-semibold transition-opacity ${
              layersState.hotspots
                ? 'text-purple-700 bg-purple-50 border-purple-200'
                : 'text-slate-400 bg-slate-50 border-slate-200 opacity-50 line-through'
            }`}
          >
            7 Emission Spots (Simulation)
          </span>
          <span className="text-slate-300">•</span>
          <span
            className={`font-mono px-1.5 py-0.5 rounded border font-semibold transition-opacity ${
              layersState.fires
                ? 'text-amber-900 bg-amber-50 border-amber-200'
                : 'text-slate-400 bg-slate-50 border-slate-200 opacity-50 line-through'
            }`}
            title="Simulated Fire Detections"
          >
            3 Active · 2 Historical Fires (Simulation)
          </span>
          <span className="text-slate-300">•</span>
          <span
            className={`font-mono px-1.5 py-0.5 rounded border font-semibold transition-opacity ${
              layersState.riskZones
                ? 'text-emerald-900 bg-emerald-50 border-emerald-200'
                : 'text-slate-400 bg-slate-50 border-slate-200 opacity-50 line-through'
            }`}
            title="Simulated PM2.5 Regional Exposure Corridors"
          >
            6 Risk Zones (Simulation)
          </span>
          <span className="text-slate-300">•</span>
          <span
            className={`font-mono px-1.5 py-0.5 rounded border font-semibold transition-opacity ${
              layersState.observations
                ? 'text-sky-900 bg-sky-50 border-sky-200'
                : 'text-slate-400 bg-slate-50 border-slate-200 opacity-50 line-through'
            }`}
            title="Simulated Citizen Photographic Observations"
          >
            7 Citizen Observations (Simulation)
          </span>
          <span className="text-slate-300">•</span>
          <span
            className={`font-mono px-1.5 py-0.5 rounded border font-semibold transition-opacity ${
              layersState.wind
                ? 'text-cyan-900 bg-cyan-50 border-cyan-200'
                : 'text-slate-400 bg-slate-50 border-slate-200 opacity-50 line-through'
            }`}
            title="Prevailing Atmospheric Wind Streamlines"
          >
            Wind NW 315° (Simulation)
          </span>
        </div>
      </div>

      {/* Dominant Main Map Canvas (Takes ~75–80% of available viewport) */}
      <div className="relative flex-1 w-full h-full min-h-[500px]">
        {loading ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50 text-slate-500">
            <div className="h-8 w-8 border-3 border-sky-600 border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-700">
              Retrieving Pan-India Telemetry Hotspots...
            </p>
          </div>
        ) : (
          <>
            <LeafletMap
              events={filteredEvents}
              selectedEventId={selectedEventId}
              onSelectEvent={(id) => setSelectedEventId(id)}
              defaultToNCR={true}
              showControls={true}
              layersState={layersState}
              onMapClick={() => {
                setSelectedEventId(null);
                setSearchCoordinate(null);
              }}
              windSpeed={activeWindSpeed}
              searchCoordinate={searchCoordinate}
              onClearSearchCoordinate={() => setSearchCoordinate(null)}
              cameraFocusTarget={cameraFocusTarget}
              className="w-full h-full"
            />

            {/* Step 9: 🔍 Search & Navigation Toolbar (Top-Left) */}
            <div className="absolute top-3.5 left-14 z-[950] pointer-events-auto">
              <MapSearch
                events={events}
                hotspots={isSimulation ? MOCK_EMISSION_HOTSPOTS : []}
                fires={isSimulation ? MOCK_FIRE_DETECTIONS : []}
                riskZones={isSimulation ? MOCK_RISK_ZONES : []}
                observations={isSimulation ? MOCK_CITIZEN_OBSERVATIONS : []}
                selectedEventId={selectedEventId}
                onSelectEntity={handleSelectSearchEntity}
                onSelectCoordinates={handleSelectCoordinates}
                onSelectCity={handleSelectCity}
                onGoToNCR={handleGoToNCR}
              />
            </div>

            {/* Step 11: Prominent Map Alert System (with Click-to-Zoom) */}
            <MapAlertBanner
              alerts={alerts}
              onInspect={handleInspectAlert}
              selectedEventId={selectedEventId}
            />

            {/* Floating Map Surveillance Controls (Top-Right): Unified Layers Panel + Surveillance Filters */}
            <div className="absolute top-3.5 right-3.5 sm:top-4 sm:right-4 z-[800] flex items-start gap-2 pointer-events-auto">
              {/* Unified Map Layers Panel */}
              <MapLayersPanel
                layersState={layersState}
                onToggleLayer={handleToggleLayer}
                onSelectAll={handleSelectAllLayers}
                onResetDefault={handleResetDefaultLayers}
                onDeselectAll={handleClearAllLayers}
                counts={{
                  riskZones: 6,
                  hotspots: 7,
                  fires: 5,
                  observations: 7,
                  events: filteredEvents.length,
                  wind: `NW • ${activeWindSpeed} km/h`,
                }}
                selectedEventId={selectedEventId}
              />

              {/* Surveillance Filters */}
              <MapFilter
                cities={cities}
                filterState={filterState}
                onFilterChange={handleFilterChange}
                onReset={handleResetFilters}
                filteredCount={filteredEvents.length}
                totalCount={events.length}
                selectedEventId={selectedEventId}
              />
            </div>

            {/* Floating Risk Legend (Bottom-Left) */}
            <div className="absolute bottom-6 left-4 z-[1000] max-w-[calc(100%-2rem)] sm:max-w-xs w-auto pointer-events-auto">
              <MapLegend totalEvents={filteredEvents.length} />
            </div>

            {/* Slide-out Location & Evidence Information Panel / Drawer */}
            <MapInfoPanel
              selectedEventId={selectedEventId}
              onClose={() => setSelectedEventId(null)}
              events={events}
            />
          </>
        )}
      </div>
    </div>
  );
}

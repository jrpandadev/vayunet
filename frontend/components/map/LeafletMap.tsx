'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import Link from 'next/link';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { PollutionEvent, RiskLevel } from '@/lib/types';
import { getIsSimulationMode } from '@/lib/api';
import RiskBadge from '@/components/ui/RiskBadge';
import {
  ArrowRight,
  MapPin,
  Clock,
  Compass,
  Locate,
  Map as MapIcon,
  Satellite,
  Activity,
  TrendingUp,
  AlertTriangle,
  Layers,
  Sparkles,
  Wind,
  Flame,
  Camera,
} from 'lucide-react';
import EmissionHotspotMarker from './EmissionHotspotMarker';
import { MOCK_EMISSION_HOTSPOTS, EmissionHotspot } from '@/lib/hotspots';
import FireDetectionMarker from './FireDetectionMarker';
import { MOCK_FIRE_DETECTIONS, FireDetection } from '@/lib/fires';
import RiskZoneLayer from './RiskZoneLayer';
import { MOCK_RISK_ZONES, RiskZone } from '@/lib/riskZones';
import ObservationMarker from './ObservationMarker';
import { MOCK_CITIZEN_OBSERVATIONS, CitizenObservation } from '@/lib/observations';
import { MapLayersState } from './MapLayersPanel';
import WindFlowOverlay from './WindFlowOverlay';

export interface LeafletMapProps {
  events: PollutionEvent[];
  selectedEventId?: string | null;
  onSelectEvent?: (id: string) => void;
  className?: string;
  defaultToNCR?: boolean;
  autoFitAll?: boolean;
  showControls?: boolean;
  showHotspots?: boolean;
  onToggleHotspots?: (show: boolean) => void;
  hotspots?: EmissionHotspot[];
  showFires?: boolean;
  onToggleFires?: (show: boolean) => void;
  fires?: FireDetection[];
  showRiskZones?: boolean;
  onToggleRiskZones?: (show: boolean) => void;
  riskZones?: RiskZone[];
  showObservations?: boolean;
  onToggleObservations?: (show: boolean) => void;
  observations?: CitizenObservation[];
  showEvents?: boolean;
  onToggleEvents?: (show: boolean) => void;
  showWind?: boolean;
  onToggleWind?: (show: boolean) => void;
  layersState?: MapLayersState;
  onMapClick?: () => void;
  windSpeed?: number;
  searchCoordinate?: [number, number] | null;
  onClearSearchCoordinate?: () => void;
  cameraFocusTarget?: {
    lat: number;
    lng: number;
    zoom?: number;
    timestamp: number;
  } | null;
}

const RISK_HEX: Record<RiskLevel | 'VERY_HIGH' | string, string> = {
  LOW: '#22c55e',
  MODERATE: '#eab308',
  HIGH: '#f97316',
  VERY_HIGH: '#ef4444',
  CRITICAL: '#9333ea',
};

// Delhi NCR geographic focal coordinates (reusable across map & search navigation)
export const DELHI_NCR_CENTER: [number, number] = [28.6139, 77.2090];
export const DELHI_NCR_ZOOM = 10;

// Custom geometric markers with clear Observed (solid core) vs Predicted (dashed outer ring) visual treatment
function createRiskIcon(event: PollutionEvent, isSelected: boolean = false) {
  const risk = event.risk;
  const color = RISK_HEX[risk] || RISK_HEX.LOW;
  const isUrgent = risk === 'CRITICAL' || risk === 'HIGH';
  const hasSpike = event.forecast?.spike_probability === 'HIGH';

  const size = isSelected ? 38 : 28;
  const pinSize = isSelected ? 16 : 13;

  const html = `
    <div style="
      position: relative;
      width: ${size}px;
      height: ${size}px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    ">
      <!-- 24-Hour Forecast Horizon Ring (Dashed boundary indicates predicted projection) -->
      <div style="
        position: absolute;
        width: ${size - 2}px;
        height: ${size - 2}px;
        border-radius: 50%;
        border: 2px dashed ${hasSpike ? '#ef4444' : color};
        opacity: ${isSelected ? '0.95' : '0.65'};
        background-color: ${hasSpike ? 'rgba(239, 68, 68, 0.14)' : 'rgba(2, 132, 199, 0.08)'};
      "></div>

      <!-- Urgent / Critical Pulse Aura -->
      ${
        isSelected
          ? `<div style="
              position: absolute;
              width: ${size + 8}px;
              height: ${size + 8}px;
              border-radius: 50%;
              background-color: ${color};
              opacity: 0.28;
              border: 1.5px solid ${color};
              box-shadow: 0 0 12px ${color};
            "></div>`
          : isUrgent
          ? `<div style="
              position: absolute;
              width: ${size + 2}px;
              height: ${size + 2}px;
              border-radius: 50%;
              background-color: ${color};
              opacity: 0.22;
            "></div>`
          : ''
      }

      <!-- Solid Core: Observed Ground Sensor Reading -->
      <div style="
        position: relative;
        z-index: 2;
        width: ${pinSize}px;
        height: ${pinSize}px;
        border-radius: 50%;
        background-color: ${color};
        border: ${isSelected ? '2.5px' : '2px'} solid #ffffff;
        box-shadow: ${isSelected ? '0 0 10px rgba(10, 37, 64, 0.7)' : '0 2px 5px rgba(10, 37, 64, 0.4)'};
        ${isSelected ? 'outline: 2px solid #0a2540;' : ''}
      "></div>
    </div>
  `;

  return L.divIcon({
    className: 'custom-vayu-pin',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

// User location marker icon
function createUserLocationIcon() {
  const html = `
    <div style="
      position: relative;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        position: absolute;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background-color: #0284c7;
        opacity: 0.3;
        animation: ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;
      "></div>
      <div style="
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background-color: #0284c7;
        border: 2.5px solid #ffffff;
        box-shadow: 0 0 8px rgba(2, 132, 199, 0.8);
      "></div>
    </div>
  `;

  return L.divIcon({
    className: 'custom-user-loc-pin',
    html,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

// Custom pulsing search location coordinate pin
function createSearchCoordinateIcon() {
  const html = `
    <div style="
      position: relative;
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    ">
      <div style="
        position: absolute;
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background-color: #0284c7;
        opacity: 0.35;
        animation: ping 1.6s cubic-bezier(0, 0, 0.2, 1) infinite;
      "></div>
      <div style="
        position: absolute;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        border: 2px solid #0284c7;
        background-color: rgba(2, 132, 199, 0.15);
      "></div>
      <div style="
        position: relative;
        z-index: 2;
        width: 13px;
        height: 13px;
        border-radius: 50%;
        background-color: #0284c7;
        border: 2.5px solid #ffffff;
        box-shadow: 0 0 10px rgba(2, 132, 199, 0.9);
      "></div>
    </div>
  `;

  return L.divIcon({
    className: 'custom-search-coord-pin',
    html,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
}

// Map bounds controller ensuring Delhi NCR is default view while allowing filter navigation
const MapBoundsUpdater: React.FC<{
  events: PollutionEvent[];
  defaultToNCR?: boolean;
  autoFitAll?: boolean;
}> = ({ events, defaultToNCR = true, autoFitAll = false }) => {
  const map = useMap();
  const initialRef = useRef(true);
  const prevCitySetRef = useRef<string>('');

  useEffect(() => {
    map.invalidateSize();

    if (!events || events.length === 0) return;

    const distinctCities = Array.from(new Set(events.map((e) => e.location.city))).sort();
    const cityKey = distinctCities.join(',');

    // Initial mount behavior
    if (initialRef.current) {
      initialRef.current = false;
      prevCitySetRef.current = cityKey;

      if (defaultToNCR) {
        map.setView(DELHI_NCR_CENTER, DELHI_NCR_ZOOM);
        return;
      }

      if (autoFitAll) {
        const bounds = L.latLngBounds(events.map((e) => [e.location.lat, e.location.lng]));
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 8 });
        return;
      }
    }

    // Subsequent updates when user applies city filters
    if (cityKey !== prevCitySetRef.current) {
      prevCitySetRef.current = cityKey;

      // Single city filtered
      if (distinctCities.length === 1) {
        if (distinctCities[0].toLowerCase() === 'delhi') {
          map.flyTo(DELHI_NCR_CENTER, DELHI_NCR_ZOOM, { duration: 0.8 });
        } else {
          const bounds = L.latLngBounds(events.map((e) => [e.location.lat, e.location.lng]));
          map.fitBounds(bounds, { padding: [50, 50], maxZoom: 11 });
        }
      } else if (autoFitAll) {
        const bounds = L.latLngBounds(events.map((e) => [e.location.lat, e.location.lng]));
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 8 });
      }
    }
  }, [events, defaultToNCR, autoFitAll, map]);

  return null;
};

// Smooth pans to selected event with vertical offset to comfortably frame the marker and its top popup
const MapSelectionFocuser: React.FC<{
  events: PollutionEvent[];
  hotspots?: EmissionHotspot[];
  fires?: FireDetection[];
  riskZones?: RiskZone[];
  observations?: CitizenObservation[];
  selectedEventId?: string | null;
  cameraFocusTarget?: {
    lat: number;
    lng: number;
    zoom?: number;
    timestamp: number;
  } | null;
}> = ({
  events,
  hotspots,
  fires,
  riskZones,
  observations,
  selectedEventId,
  cameraFocusTarget,
}) => {
  const map = useMap();

  // Smooth camera navigation for coordinate search, city selection, and Go to NCR
  useEffect(() => {
    if (!cameraFocusTarget) return;
    const { lat, lng, zoom = 12 } = cameraFocusTarget;
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion) {
      map.setView([lat, lng], zoom, { animate: false });
    } else {
      map.flyTo([lat, lng], zoom, {
        animate: true,
        duration: 0.8,
      });
    }
  }, [cameraFocusTarget, map]);

  useEffect(() => {
    if (!selectedEventId) return;

    // Smoothly focus on marker while offsetting the map center vertically.
    // This leaves ample room for the popup card above the marker while keeping
    // the marker comfortably visible in the lower-middle focal zone (avoiding the bottom edge and overlays).
    const focusOnLocation = (lat: number, lng: number, verticalOffsetPixels: number = 110) => {
      try {
        const currentZoom = map.getZoom();
        const targetZoom = Math.max(currentZoom, 11);
        const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 768;
        const horizontalOffset = isDesktop ? -90 : 0;
        const projected = map.project([lat, lng], targetZoom);
        const offsetTarget = projected.subtract([horizontalOffset, verticalOffsetPixels]);
        const targetLatLng = map.unproject(offsetTarget, targetZoom);

        const prefersReducedMotion =
          typeof window !== 'undefined' &&
          window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        if (prefersReducedMotion) {
          map.setView(targetLatLng, targetZoom, { animate: false });
        } else if (targetZoom !== currentZoom) {
          map.flyTo(targetLatLng, targetZoom, {
            animate: true,
            duration: 0.8,
          });
        } else {
          map.panTo(targetLatLng, {
            animate: true,
            duration: 0.6,
          });
        }
      } catch {
        map.panTo([lat, lng], { animate: true, duration: 0.5 });
      }
    };

    // 0a. Check if a citizen observation was selected
    if (observations) {
      const selectedObs = observations.find((o) => o.id === selectedEventId);
      if (selectedObs) {
        // Observation popup with preview image is ~310px tall; 115px offset places marker comfortably
        focusOnLocation(selectedObs.latitude, selectedObs.longitude, 115);
        return;
      }
    }

    // 0b. Check if a risk zone was selected
    if (riskZones) {
      const selectedZone = riskZones.find((z) => z.id === selectedEventId);
      if (selectedZone) {
        const centerLat = selectedZone.center
          ? selectedZone.center[0]
          : selectedZone.coordinates.map((c) => c[0]).reduce((a, b) => a + b, 0) / selectedZone.coordinates.length;
        const centerLng = selectedZone.center
          ? selectedZone.center[1]
          : selectedZone.coordinates.map((c) => c[1]).reduce((a, b) => a + b, 0) / selectedZone.coordinates.length;
        // Risk zone popup is ~210px tall; 125px offset places the zone centroid comfortably
        // at ~62% viewport height, ensuring the entire popup card sits comfortably below
        // the top HUD status ribbon and map controls with ample clearance.
        focusOnLocation(centerLat, centerLng, 125);
        return;
      }
    }

    // 1. Check if an active/historical fire was selected
    if (fires) {
      const selectedFire = fires.find((f) => f.id === selectedEventId);
      if (selectedFire) {
        // Fire popup is ~310px tall; 115px offset places the fire marker comfortably at ~60% viewport height
        focusOnLocation(selectedFire.latitude, selectedFire.longitude, 115);
        return;
      }
    }

    // 2. Check if an emission hotspot was selected
    if (hotspots) {
      const selectedHotspot = hotspots.find((h) => h.id === selectedEventId);
      if (selectedHotspot) {
        focusOnLocation(selectedHotspot.latitude, selectedHotspot.longitude, 95);
        return;
      }
    }

    // 3. Check if a pollution event was selected
    const selectedEvent = events.find((e) => e.event_id === selectedEventId);
    if (selectedEvent) {
      focusOnLocation(selectedEvent.location.lat, selectedEvent.location.lng, 95);
    }
  }, [selectedEventId, events, hotspots, fires, riskZones, observations, map]);

  return null;
};

// Handle map background clicks to dismiss selection/panels
const MapBackgroundClickHandler: React.FC<{ onMapClick?: () => void }> = ({ onMapClick }) => {
  useMapEvents({
    click: (e) => {
      const target = e.originalEvent?.target as HTMLElement | null;
      if (
        target?.closest('.leaflet-marker-icon') ||
        target?.closest('.leaflet-popup') ||
        target?.closest('.leaflet-control') ||
        target?.closest('.vayu-leaflet-popup') ||
        target?.closest('.custom-vayu-pin') ||
        target?.closest('.vayu-emission-hotspot-pin') ||
        target?.closest('.vayu-fire-pin') ||
        target?.closest('.vayu-observation-pin') ||
        target?.closest('.vayu-observation-cluster-pin')
      ) {
        return;
      }
      if (onMapClick) {
        onMapClick();
      }
    },
  });
  return null;
};

// Custom Overlay Controls: Go to NCR, Geolocation, Basemap Toggle
const MapInteractiveControls: React.FC<{
  mapLayer: 'street' | 'satellite';
  onToggleLayer: (layer: 'street' | 'satellite') => void;
  userLocation: [number, number] | null;
  setUserLocation: (coords: [number, number] | null) => void;
}> = ({
  mapLayer,
  onToggleLayer,
  userLocation,
  setUserLocation,
}) => {
  const map = useMap();
  const [geoStatus, setGeoStatus] = useState<'idle' | 'locating' | 'denied' | 'unavailable' | 'located'>('idle');
  const [geoNotice, setGeoNotice] = useState<string | null>(null);

  const showTemporaryNotice = (msg: string) => {
    setGeoNotice(msg);
    setTimeout(() => setGeoNotice(null), 4500);
  };

  const handleGoToNCR = () => {
    map.flyTo(DELHI_NCR_CENTER, DELHI_NCR_ZOOM, { duration: 0.8 });
  };

  const handleLocateMe = () => {
    if (geoStatus === 'denied') {
      showTemporaryNotice('Location permission was denied in browser settings.');
      return;
    }

    if (typeof window === 'undefined' || !navigator.geolocation) {
      setGeoStatus('unavailable');
      showTemporaryNotice('Geolocation is not supported by your browser.');
      return;
    }

    setGeoStatus('locating');

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords: [number, number] = [pos.coords.latitude, pos.coords.longitude];
        setUserLocation(coords);
        setGeoStatus('located');
        map.flyTo(coords, 12, { duration: 0.8 });
      },
      (err) => {
        if (err.code === 1) {
          // PERMISSION_DENIED: record state and do not repeatedly prompt
          setGeoStatus('denied');
          showTemporaryNotice('Location access denied. Reset browser site permissions to locate.');
        } else {
          setGeoStatus('unavailable');
          showTemporaryNotice('Location signal unavailable or timed out.');
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 60000,
      }
    );
  };

  return (
    <div className="absolute top-14 left-14 sm:top-3.5 sm:left-[510px] md:left-[530px] z-[900] flex flex-wrap items-center gap-1.5 sm:gap-2 pointer-events-auto max-w-[calc(100%-80px)] sm:max-w-none">
      {/* Street / Satellite Toggle */}
      <div className="inline-flex rounded-lg border border-slate-300/90 bg-white/95 p-0.5 shadow-md backdrop-blur-md">
        <button
          type="button"
          onClick={() => onToggleLayer('street')}
          className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
            mapLayer === 'street'
              ? 'bg-[#0a2540] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
          title="Switch to Street Map (OpenStreetMap)"
        >
          <MapIcon className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Street Map</span>
          <span className="sm:hidden">Street</span>
        </button>

        <button
          type="button"
          onClick={() => onToggleLayer('satellite')}
          className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
            mapLayer === 'satellite'
              ? 'bg-[#0a2540] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
          title="Switch to Satellite Imagery (Esri World Imagery)"
        >
          <Satellite className="w-3.5 h-3.5" />
          <span>Satellite</span>
        </button>
      </div>

      {/* Navigation Quick Actions: Go to NCR & Locate Me */}
      <div className="inline-flex rounded-lg border border-slate-300/90 bg-white/95 p-0.5 shadow-md backdrop-blur-md gap-0.5">
        <button
          type="button"
          onClick={handleGoToNCR}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md text-slate-700 hover:text-[#0a2540] hover:bg-slate-100 transition-all cursor-pointer"
          title="Center and reset view to Delhi NCR"
        >
          <Compass className="w-3.5 h-3.5 text-sky-600" />
          <span className="font-semibold">Go to NCR</span>
        </button>

        <div className="w-[1px] bg-slate-200 my-1" />

        <button
          type="button"
          onClick={handleLocateMe}
          disabled={geoStatus === 'locating'}
          className={`flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
            geoStatus === 'located'
              ? 'text-sky-700 bg-sky-50'
              : geoStatus === 'denied'
              ? 'text-slate-400 hover:bg-slate-100'
              : 'text-slate-700 hover:text-[#0a2540] hover:bg-slate-100'
          }`}
          title={
            geoStatus === 'denied'
              ? 'Location permission denied in browser'
              : 'Center on your current position'
          }
        >
          <Locate className={`w-3.5 h-3.5 ${geoStatus === 'locating' ? 'animate-spin text-sky-600' : 'text-slate-600'}`} />
          <span className="hidden sm:inline">My Location</span>
        </button>
      </div>


      {/* Geolocation Notice Banner */}
      {geoNotice && (
        <div className="bg-[#0a2540] text-white text-xs px-3 py-1.5 rounded-lg shadow-lg border border-white/20 flex items-center gap-1.5 animate-in fade-in slide-in-from-top-1">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span>{geoNotice}</span>
        </div>
      )}
    </div>
  );
};

// Circular cluster badge for citizen observations when zoomed out
function createObservationClusterIcon(count: number) {
  const html = `
    <div style="
      position: relative;
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    " title="${count} Citizen Observations (Simulation) - Click to zoom in">
      <div style="
        position: absolute;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: rgba(2, 132, 199, 0.25);
        border: 1.5px dashed #38bdf8;
      "></div>
      <div style="
        position: relative;
        z-index: 2;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #0284c7 0%, #0369a1 55%, #0a2540 100%);
        border: 2px solid #ffffff;
        box-shadow: 0 3px 8px rgba(10, 37, 64, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-weight: bold;
        font-size: 11px;
        font-family: system-ui, sans-serif;
      ">
        <span style="font-size: 12px; margin-right: 2px;">📷</span>${count}
      </div>
    </div>
  `;
  return L.divIcon({
    className: 'vayu-observation-cluster-pin',
    html,
    iconSize: [44, 44],
    iconAnchor: [22, 22],
    popupAnchor: [0, -20],
  });
}

// Lightweight zoom-aware observation layer with co-location separation
const ObservationLayer: React.FC<{
  observations: CitizenObservation[];
  onSelect?: (id: string) => void;
}> = ({ observations, onSelect }) => {
  const map = useMap();
  const [currentZoom, setCurrentZoom] = useState<number>(() => map.getZoom());

  useEffect(() => {
    const onZoom = () => {
      setCurrentZoom(map.getZoom());
    };
    map.on('zoomend', onZoom);
    return () => {
      map.off('zoomend', onZoom);
    };
  }, [map]);

  // Handle identical coordinates with subtle micro-offset so co-located items remain distinguishable
  const processedObservations = useMemo(() => {
    const coordCounts = new Map<string, number>();
    return observations.map((obs) => {
      const key = `${obs.latitude.toFixed(5)},${obs.longitude.toFixed(5)}`;
      const count = coordCounts.get(key) || 0;
      coordCounts.set(key, count + 1);

      if (count === 0) return obs;
      const angle = (count * 2 * Math.PI) / 3;
      const offsetDistance = 0.0008;
      return {
        ...obs,
        latitude: obs.latitude + Math.sin(angle) * offsetDistance,
        longitude: obs.longitude + Math.cos(angle) * offsetDistance,
      };
    });
  }, [observations]);

  // When zoomed out (< 11), group nearby observations into clusters
  const clusters = useMemo(() => {
    if (currentZoom >= 11) return null;

    type ClusterGroup = {
      id: string;
      lat: number;
      lng: number;
      items: CitizenObservation[];
    };

    const groups: ClusterGroup[] = [];
    const threshold = 0.08; // ~8 km radius for clustering when zoomed out

    for (const obs of observations) {
      let placed = false;
      for (const g of groups) {
        const dLat = Math.abs(g.lat - obs.latitude);
        const dLng = Math.abs(g.lng - obs.longitude);
        if (dLat < threshold && dLng < threshold) {
          g.items.push(obs);
          g.lat = g.items.reduce((s, i) => s + i.latitude, 0) / g.items.length;
          g.lng = g.items.reduce((s, i) => s + i.longitude, 0) / g.items.length;
          placed = true;
          break;
        }
      }
      if (!placed) {
        groups.push({
          id: `cluster_${obs.id}`,
          lat: obs.latitude,
          lng: obs.longitude,
          items: [obs],
        });
      }
    }
    return groups;
  }, [observations, currentZoom]);

  // Zoomed out: render clusters or standalone markers
  if (clusters && currentZoom < 11) {
    return (
      <>
        {clusters.map((cluster) => {
          if (cluster.items.length === 1) {
            return (
              <ObservationMarker
                key={cluster.items[0].id}
                observation={cluster.items[0]}
                onSelect={onSelect}
              />
            );
          }
          const icon = createObservationClusterIcon(cluster.items.length);
          return (
            <Marker
              key={cluster.id}
              position={[cluster.lat, cluster.lng]}
              icon={icon}
              eventHandlers={{
                click: () => {
                  map.flyTo([cluster.lat, cluster.lng], 12, { duration: 0.6 });
                },
              }}
            />
          );
        })}
      </>
    );
  }

  // Zoomed in: render all individual markers with co-location separation
  return (
    <>
      {processedObservations.map((obs) => (
        <ObservationMarker
          key={obs.id}
          observation={obs}
          onSelect={onSelect}
        />
      ))}
    </>
  );
};

export const LeafletMap: React.FC<LeafletMapProps> = ({
  events,
  selectedEventId,
  onSelectEvent,
  className = '',
  defaultToNCR = true,
  autoFitAll = false,
  showControls = true,
  showHotspots: showHotspotsProp,
  onToggleHotspots: onToggleHotspotsProp,
  hotspots: hotspotsProp,
  showFires: showFiresProp,
  onToggleFires: onToggleFiresProp,
  fires: firesProp,
  showRiskZones: showRiskZonesProp,
  onToggleRiskZones: onToggleRiskZonesProp,
  riskZones: riskZonesProp,
  showObservations: showObservationsProp,
  onToggleObservations: onToggleObservationsProp,
  observations: observationsProp,
  showEvents: showEventsProp,
  onToggleEvents: onToggleEventsProp,
  showWind: showWindProp,
  onToggleWind: onToggleWindProp,
  layersState,
  onMapClick,
  windSpeed,
  searchCoordinate,
  onClearSearchCoordinate,
  cameraFocusTarget,
}) => {
  const [mapLayer, setMapLayer] = useState<'street' | 'satellite'>('street');
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);
  const [internalShowHotspots, setInternalShowHotspots] = useState<boolean>(true);
  const [internalShowFires, setInternalShowFires] = useState<boolean>(true);
  const [internalShowRiskZones, setInternalShowRiskZones] = useState<boolean>(true);
  const [internalShowObservations, setInternalShowObservations] = useState<boolean>(true);
  const [internalShowEvents, setInternalShowEvents] = useState<boolean>(true);
  const [internalShowWind, setInternalShowWind] = useState<boolean>(true);

  const isHotspotsVisible = layersState
    ? layersState.hotspots
    : showHotspotsProp !== undefined
    ? showHotspotsProp
    : internalShowHotspots;

  const handleToggleHotspots = (val: boolean) => {
    setInternalShowHotspots(val);
    if (onToggleHotspotsProp) {
      onToggleHotspotsProp(val);
    }
  };

  const isFiresVisible = layersState
    ? layersState.fires
    : showFiresProp !== undefined
    ? showFiresProp
    : internalShowFires;

  const handleToggleFires = (val: boolean) => {
    setInternalShowFires(val);
    if (onToggleFiresProp) {
      onToggleFiresProp(val);
    }
  };

  const isRiskZonesVisible = layersState
    ? layersState.riskZones
    : showRiskZonesProp !== undefined
    ? showRiskZonesProp
    : internalShowRiskZones;

  const handleToggleRiskZones = (val: boolean) => {
    setInternalShowRiskZones(val);
    if (onToggleRiskZonesProp) {
      onToggleRiskZonesProp(val);
    }
  };

  const isObservationsVisible = layersState
    ? layersState.observations
    : showObservationsProp !== undefined
    ? showObservationsProp
    : internalShowObservations;

  const handleToggleObservations = (val: boolean) => {
    setInternalShowObservations(val);
    if (onToggleObservationsProp) {
      onToggleObservationsProp(val);
    }
  };

  const isEventsVisible = layersState
    ? layersState.events
    : showEventsProp !== undefined
    ? showEventsProp
    : internalShowEvents;

  const handleToggleEvents = (val: boolean) => {
    setInternalShowEvents(val);
    if (onToggleEventsProp) {
      onToggleEventsProp(val);
    }
  };

  const isWindVisible = layersState
    ? layersState.wind
    : showWindProp !== undefined
    ? showWindProp
    : internalShowWind;

  const handleToggleWind = (val: boolean) => {
    setInternalShowWind(val);
    if (onToggleWindProp) {
      onToggleWindProp(val);
    }
  };

  const isSimulation = getIsSimulationMode();

  const activeHotspots = isSimulation ? (hotspotsProp || MOCK_EMISSION_HOTSPOTS) : [];
  const activeFires = isSimulation ? (firesProp || MOCK_FIRE_DETECTIONS) : [];
  const activeRiskZones = isSimulation ? (riskZonesProp || MOCK_RISK_ZONES) : [];
  const activeObservations = isSimulation ? (observationsProp || MOCK_CITIZEN_OBSERVATIONS) : [];

  // Satellite tile URL from environment or public Esri World Imagery service
  const satelliteTileUrl =
    process.env.NEXT_PUBLIC_SATELLITE_TILE_URL ||
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

  return (
    <div className={`relative w-full h-full min-h-[350px] overflow-hidden ${className}`}>
      <MapContainer
        center={defaultToNCR ? DELHI_NCR_CENTER : [22.9734, 78.6569]}
        zoom={defaultToNCR ? DELHI_NCR_ZOOM : 5}
        scrollWheelZoom={true}
        className="w-full h-full"
        style={{ width: '100%', height: '100%' }}
      >
        {/* Basemap Switcher: Street (OSM) vs Satellite (Esri) */}
        {mapLayer === 'street' ? (
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
        ) : (
          <TileLayer
            attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
            url={satelliteTileUrl}
            maxZoom={18}
          />
        )}

        {/* Wind Vector / Atmospheric Flow Overlay (Step 8: Translucent non-interactive vectors) */}
        {isWindVisible && (
          <WindFlowOverlay
            windSpeed={windSpeed}
            windDirectionDeg={315}
            directionLabel="NW"
          />
        )}

        <MapBoundsUpdater
          events={events}
          defaultToNCR={defaultToNCR}
          autoFitAll={autoFitAll}
        />
        <MapSelectionFocuser
          events={events}
          hotspots={activeHotspots}
          fires={activeFires}
          riskZones={activeRiskZones}
          observations={activeObservations}
          selectedEventId={selectedEventId}
          cameraFocusTarget={cameraFocusTarget}
        />
        <MapBackgroundClickHandler onMapClick={onMapClick} />

        {/* Temporary Search Coordinate Marker Pin */}
        {searchCoordinate && (
          <Marker position={searchCoordinate} icon={createSearchCoordinateIcon()}>
            <Popup className="vayu-leaflet-popup" minWidth={210}>
              <div className="p-1.5 text-xs">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <strong className="text-slate-900 flex items-center gap-1 text-[11px]">
                    <MapPin className="w-3.5 h-3.5 text-sky-600" />
                    Search Coordinates
                  </strong>
                  {onClearSearchCoordinate && (
                    <button
                      type="button"
                      onClick={onClearSearchCoordinate}
                      className="text-[10px] text-slate-400 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 px-1 py-0.5 rounded cursor-pointer transition-colors"
                      title="Dismiss search pin"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <p className="font-mono text-slate-700 text-xs font-semibold mb-1">
                  {searchCoordinate[0].toFixed(4)}°N, {searchCoordinate[1].toFixed(4)}°E
                </p>
                <span className="inline-block text-[10px] font-medium text-sky-800 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200">
                  Direct Coordinate Navigation
                </span>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Embedded Interactive Map Controls */}
        {showControls && (
          <MapInteractiveControls
            mapLayer={mapLayer}
            onToggleLayer={setMapLayer}
            userLocation={userLocation}
            setUserLocation={setUserLocation}
          />
        )}

        {/* User Location Marker (if granted) */}
        {userLocation && (
          <Marker position={userLocation} icon={createUserLocationIcon()}>
            <Popup className="vayu-leaflet-popup" minWidth={200}>
              <div className="p-1 text-xs">
                <strong className="text-slate-900 block mb-0.5">Your Current Location</strong>
                <span className="text-slate-500 font-mono text-[11px]">
                  {userLocation[0].toFixed(4)}°N, {userLocation[1].toFixed(4)}°E
                </span>
                <span className="block mt-1 text-[10px] text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200">
                  Browser Geolocation Signal
                </span>
              </div>
            </Popup>
          </Marker>
        )}

        {/* PM2.5 Risk Zones Layer (Synthetic Regional Exposure Corridors) */}
        {isRiskZonesVisible && (
          <RiskZoneLayer
            zones={activeRiskZones}
            onSelectZone={(id) => {
              if (onSelectEvent) {
                onSelectEvent(id);
              }
            }}
          />
        )}

        {/* PM2.5 Emission Hotspots Layer (Synthetic Demonstration Data) */}
        {isHotspotsVisible &&
          activeHotspots.map((hotspot) => (
            <EmissionHotspotMarker
              key={hotspot.id}
              hotspot={hotspot}
              onSelect={(id) => {
                if (onSelectEvent) {
                  onSelectEvent(id);
                }
              }}
            />
          ))}

        {/* Fire Detection Layer (Synthetic Demonstration Data) */}
        {isFiresVisible &&
          activeFires.map((fire) => (
            <FireDetectionMarker
              key={fire.id}
              fire={fire}
              onSelect={(id) => {
                if (onSelectEvent) {
                  onSelectEvent(id);
                }
              }}
            />
          ))}

        {/* Citizen Observations Layer (Synthetic Demonstration Evidence) */}
        {isObservationsVisible && (
          <ObservationLayer
            observations={activeObservations}
            onSelect={(id) => {
              if (onSelectEvent) {
                onSelectEvent(id);
              }
            }}
          />
        )}

        {/* Pollution Event Markers (Base Monitoring Stations) */}
        {isEventsVisible &&
          events.map((event) => {
          const isSelected = selectedEventId === event.event_id;
          const icon = createRiskIcon(event, isSelected);

          const observedPm25 = event.evidence?.sensor?.pm25;
          const forecast24h = event.forecast?.pm25_24h;
          const forecast6h = event.forecast?.pm25_6h;
          const stationId = event.evidence?.sensor?.station_id || 'Ground Sensor Station';
          const confidencePct = Math.round((event.detection?.confidence ?? 0.8) * 100);

          return (
            <Marker
              key={event.event_id}
              position={[event.location.lat, event.location.lng]}
              icon={icon}
              eventHandlers={{
                click: () => {
                  if (onSelectEvent) {
                    onSelectEvent(event.event_id);
                  }
                },
              }}
            >
              <Popup
                className="vayu-leaflet-popup"
                minWidth={280}
                maxWidth={340}
                autoPan={true}
                autoPanPaddingTopLeft={[50, 70]}
                autoPanPaddingBottomRight={[50, 50]}
              >
                <div className="p-1 select-none font-sans text-slate-800">
                  {/* Popup Header */}
                  <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-100 mb-2">
                    <div>
                      <div className="flex items-center gap-1.5 font-bold text-sm text-[#0f172a]">
                        <MapPin className="w-3.5 h-3.5 text-[#0a2540]" />
                        <span>{event.location.city}</span>
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded">
                          {event.event_id}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400 capitalize">
                          {event.source_hypothesis?.category?.replace('_', ' ') || 'Atmospheric Event'}
                        </span>
                      </div>
                    </div>
                    <RiskBadge level={event.risk} size="sm" />
                  </div>

                  {/* MODALITY 1: OBSERVED TELEMETRY */}
                  <div className="mb-2 p-2 rounded-md bg-slate-50 border border-slate-200/80">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-700">
                        <span className="w-2 h-2 rounded-full bg-slate-700" />
                        Observed Telemetry
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 bg-white px-1.5 py-0.2 rounded border border-slate-200">
                        Simulation Feed
                      </span>
                    </div>

                    <div className="space-y-1 text-xs">
                      {event.evidence?.sensor?.station_id && (
                        <div className="flex items-center justify-between text-slate-600">
                          <span className="text-[11px] text-slate-500">Sensor Station:</span>
                          <span className="font-mono font-medium text-slate-800 truncate max-w-[140px]" title={stationId}>
                            {stationId}
                          </span>
                        </div>
                      )}

                      {observedPm25 !== undefined && (
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-slate-500">Observed PM2.5:</span>
                          <span className="font-mono font-bold text-slate-900 tabular-telemetry">
                            {observedPm25} µg/m³
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* MODALITY 2: PM2.5 FORECAST (NEXT 24 HOURS) */}
                  {event.forecast && (
                    <div className="mb-2.5 p-2 rounded-md bg-sky-50/70 border border-dashed border-sky-300">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-sky-900">
                          <TrendingUp className="w-3 h-3 text-sky-700" />
                          PM2.5 Forecast (Next 24 Hours)
                        </span>
                        <span className="text-[10px] font-mono text-sky-800 bg-sky-100 px-1.5 py-0.2 rounded font-semibold">
                          Forecast Model
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-1.5 text-xs">
                        <div className="bg-white/80 p-1.5 rounded border border-sky-100">
                          <span className="text-[10px] text-slate-500 block">PM2.5 (24h)</span>
                          <span className="font-mono font-bold text-sky-900 text-xs">
                            {forecast24h} µg/m³
                          </span>
                        </div>

                        <div className="bg-white/80 p-1.5 rounded border border-sky-100">
                          <span className="text-[10px] text-slate-500 block">Forecast Uncertainty</span>
                          <span className="font-mono font-bold text-xs text-sky-900">
                            {event.forecast.forecast_uncertainty}
                          </span>
                        </div>
                      </div>

                      <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                        <span>PM2.5 (6h): {forecast6h} µg/m³</span>
                        <span>Confidence: {confidencePct}%</span>
                      </div>
                    </div>
                  )}

                  {/* Footer with Timestamp & Link */}
                  <div className="flex items-center justify-between pt-1 text-[10px] text-slate-400 mb-2">
                    <span className="flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3" />
                      {new Date(event.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                    <span className="capitalize font-mono text-slate-500 bg-slate-100 px-1 rounded">
                      {event.outcome}
                    </span>
                  </div>

                  {/* Link to Event Detail Dossier */}
                  <Link
                    href={`/dashboard/event/${event.event_id}`}
                    className="inline-flex items-center justify-center gap-1.5 w-full py-1.5 px-3 bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-semibold rounded transition-colors"
                  >
                    <span>View Full Evidence Details</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
};

export default LeafletMap;

'use client';

import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import {
  Search,
  X,
  MapPin,
  Flame,
  Radio,
  Layers,
  Wind,
  Compass,
  AlertTriangle,
  Building2,
  Camera,
  Activity,
  ArrowRight,
  ExternalLink,
  Navigation,
} from 'lucide-react';
import { PollutionEvent } from '@/lib/types';
import { EmissionHotspot } from '@/lib/hotspots';
import { FireDetection } from '@/lib/fires';
import { RiskZone } from '@/lib/riskZones';
import { CitizenObservation } from '@/lib/observations';
import { MapLayersState } from './MapLayersPanel';

export type SearchResultType =
  | 'STATION'
  | 'HOTSPOT'
  | 'FIRE'
  | 'RISK_ZONE'
  | 'OBSERVATION'
  | 'CITY'
  | 'COORDINATE';

export interface SearchResultItem {
  id: string;
  type: SearchResultType;
  title: string;
  subtitle: string;
  lat: number;
  lng: number;
  city?: string;
  stationId?: string;
  targetLayer?: keyof MapLayersState;
  entityId?: string;
  badgeLabel: string;
  badgeClass: string;
  icon: React.ComponentType<{ className?: string }>;
  extraInfo?: string;
  // Reference to original entity if needed
  data?: any;
}

export interface CoordinateParseResult {
  isCoordinateQuery: boolean;
  isValid: boolean;
  lat?: number;
  lng?: number;
  errorMessage?: string;
}

/**
 * Robust parser for geographic coordinates.
 * Supports:
 * - "28.6139, 77.2090"
 * - "28.6139 77.2090"
 * - "28.6139,77.2090"
 * - "28.6139°N, 77.2090°E"
 * Validates:
 * - Latitude: -90 to +90
 * - Longitude: -180 to +180
 */
export function parseCoordinates(query: string): CoordinateParseResult {
  const trimmed = query.trim();
  if (!trimmed) {
    return { isCoordinateQuery: false, isValid: false };
  }

  // Regex matching standard decimal coordinates with optional degree/direction indicators
  const coordRegex = /^\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*([NSns])?\s*[, \t/]+\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*([EWew])?\s*$/;
  const match = trimmed.match(coordRegex);

  if (match) {
    let lat = parseFloat(match[1]);
    const latDir = match[2]?.toUpperCase();
    let lng = parseFloat(match[3]);
    const lngDir = match[4]?.toUpperCase();

    if (latDir === 'S') lat = -lat;
    if (lngDir === 'W') lng = -lng;

    if (isNaN(lat) || isNaN(lng)) {
      return {
        isCoordinateQuery: true,
        isValid: false,
        errorMessage: 'Invalid numeric coordinate format.',
      };
    }

    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
      return {
        isCoordinateQuery: true,
        isValid: false,
        errorMessage: 'Invalid coordinates. Latitude must be between -90 and 90 and longitude between -180 and 180.',
      };
    }

    return {
      isCoordinateQuery: true,
      isValid: true,
      lat: Math.round(lat * 100000) / 100000,
      lng: Math.round(lng * 100000) / 100000,
    };
  }

  // Fallback check for numbers with comma or whitespace that exceed valid ranges
  const numericParts = trimmed.split(/[, \t/]+/).filter(Boolean);
  if (numericParts.length === 2 && !isNaN(Number(numericParts[0])) && !isNaN(Number(numericParts[1]))) {
    const lat = parseFloat(numericParts[0]);
    const lng = parseFloat(numericParts[1]);
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
      return {
        isCoordinateQuery: true,
        isValid: false,
        errorMessage: 'Invalid coordinates. Latitude must be between -90 and 90 and longitude between -180 and 180.',
      };
    }
  }

  return { isCoordinateQuery: false, isValid: false };
}

// City centroids representing focal monitoring basins in the current project datasets
export const DELHI_NCR_CENTER: [number, number] = [28.6139, 77.2090];
export const DELHI_NCR_ZOOM = 10;

const CITY_CENTROIDS: Array<{
  cityName: string;
  label: string;
  subtitle: string;
  coords: [number, number];
  zoom: number;
  aliases: string[];
}> = [
  {
    cityName: 'Delhi',
    label: 'Delhi NCR (National Capital Region)',
    subtitle: 'Primary Surveillance Basin • 3 CAAQMS Stations, 7 Hotspots, 5 Fires, 6 Risk Zones',
    coords: DELHI_NCR_CENTER,
    zoom: DELHI_NCR_ZOOM,
    aliases: ['delhi', 'ncr', 'new delhi', 'national capital'],
  },
  {
    cityName: 'Mumbai',
    label: 'Mumbai (Mumbai Metropolitan Region)',
    subtitle: 'Coastal Air Basin • 3 CAAQMS Stations (Bandra, Sion, Malad)',
    coords: [19.0760, 72.8777],
    zoom: 11,
    aliases: ['mumbai', 'bombay', 'mmr', 'bandra', 'sion', 'malad'],
  },
  {
    cityName: 'Bhubaneswar',
    label: 'Bhubaneswar (Eastern Air Basin)',
    subtitle: 'Eastern Regional Air Basin • 2 CAAQMS Stations (OSPCB_01, OSPCB_Patia)',
    coords: [20.2961, 85.8245],
    zoom: 12,
    aliases: ['bhubaneswar', 'bhubaneshwar', 'odisha', 'patia'],
  },
];

export interface MapSearchProps {
  events: PollutionEvent[];
  hotspots: EmissionHotspot[];
  fires: FireDetection[];
  riskZones: RiskZone[];
  observations: CitizenObservation[];
  selectedEventId?: string | null;
  onSelectEntity: (item: SearchResultItem) => void;
  onSelectCoordinates: (lat: number, lng: number) => void;
  onSelectCity: (cityName: string, coords: [number, number], zoom: number) => void;
  onGoToNCR: () => void;
  className?: string;
}

export const MapSearch: React.FC<MapSearchProps> = ({
  events,
  hotspots,
  fires,
  riskZones,
  observations,
  selectedEventId,
  onSelectEntity,
  onSelectCoordinates,
  onSelectCity,
  onGoToNCR,
  className = '',
}) => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Build indexed entity dataset from actual project records
  const allEntities = useMemo<SearchResultItem[]>(() => {
    const items: SearchResultItem[] = [];

    // 1. Base Monitoring Stations from Events
    events.forEach((evt) => {
      const stationId = evt.evidence?.sensor?.station_id || evt.event_id;
      const city = evt.location.city;
      const pm25 = evt.evidence?.sensor?.pm25;
      items.push({
        id: evt.event_id,
        entityId: evt.event_id,
        type: 'STATION',
        title: stationId,
        subtitle: `Monitoring Station • ${city} • PM2.5: ${pm25 !== undefined ? pm25 + ' µg/m³' : 'N/A'} • ${evt.risk} Risk`,
        lat: evt.location.lat,
        lng: evt.location.lng,
        city: evt.location.city,
        stationId: stationId,
        targetLayer: 'events',
        badgeLabel: 'Monitoring Station',
        badgeClass: 'bg-slate-100 text-slate-800 border-slate-300',
        icon: Radio,
        extraInfo: `ID: ${evt.event_id} • Sensor: ${stationId}`,
        data: evt,
      });
    });

    // 2. Emission Hotspots
    hotspots.forEach((hs) => {
      items.push({
        id: hs.id,
        entityId: hs.id,
        type: 'HOTSPOT',
        title: hs.locationName,
        subtitle: `Emission Hotspot • PM2.5: ~${hs.estimatedPm25} µg/m³ • ${hs.possibleSource || 'Industrial plume'}`,
        lat: hs.latitude,
        lng: hs.longitude,
        city: 'Delhi',
        targetLayer: 'hotspots',
        badgeLabel: 'Emission Hotspot',
        badgeClass: 'bg-purple-50 text-purple-800 border-purple-200',
        icon: Activity,
        extraInfo: `ID: ${hs.id} • ${hs.severity}`,
        data: hs,
      });
    });

    // 3. Fire Detections
    fires.forEach((fire) => {
      items.push({
        id: fire.id,
        entityId: fire.id,
        type: 'FIRE',
        title: fire.locationName,
        subtitle: `Fire Detection (${fire.status}) • Intensity: ${fire.intensity} • ${fire.sizeHectares ? fire.sizeHectares + ' ha' : 'Thermal anomaly'}`,
        lat: fire.latitude,
        lng: fire.longitude,
        city: 'Delhi',
        targetLayer: 'fires',
        badgeLabel: 'Fire Detection',
        badgeClass: 'bg-amber-50 text-amber-900 border-amber-200',
        icon: Flame,
        extraInfo: `ID: ${fire.id} • ${fire.status} Fire`,
        data: fire,
      });
    });

    // 4. PM2.5 Risk Zones
    riskZones.forEach((zone) => {
      const centerLat = zone.center ? zone.center[0] : zone.coordinates[0][0];
      const centerLng = zone.center ? zone.center[1] : zone.coordinates[0][1];
      items.push({
        id: zone.id,
        entityId: zone.id,
        type: 'RISK_ZONE',
        title: zone.name,
        subtitle: `PM2.5 Risk Zone • Predicted PM2.5: ~${zone.predicted_pm25} µg/m³ • ${zone.level} Risk`,
        lat: centerLat,
        lng: centerLng,
        city: 'Delhi',
        targetLayer: 'riskZones',
        badgeLabel: 'Risk Zone',
        badgeClass: 'bg-rose-50 text-rose-800 border-rose-200',
        icon: Layers,
        extraInfo: `ID: ${zone.id} • ${zone.forecast_horizon}`,
        data: zone,
      });
    });

    // 5. Citizen Photographic Observations
    observations.forEach((obs) => {
      items.push({
        id: obs.id,
        entityId: obs.id,
        type: 'OBSERVATION',
        title: obs.locationName,
        subtitle: `Citizen Observation • PM2.5: ~${obs.pm25AtLocation} µg/m³ • ${obs.description?.slice(0, 60) || 'Photographic report'}...`,
        lat: obs.latitude,
        lng: obs.longitude,
        city: 'Delhi',
        targetLayer: 'observations',
        badgeLabel: 'Citizen Observation',
        badgeClass: 'bg-sky-50 text-sky-800 border-sky-200',
        icon: Camera,
        extraInfo: `ID: ${obs.id} • Uploaded at ${obs.uploadedAt}`,
        data: obs,
      });
    });

    return items;
  }, [events, hotspots, fires, riskZones, observations]);

  // Coordinate check on raw query
  const coordinateCheck = useMemo(() => {
    return parseCoordinates(query);
  }, [query]);

  // Search Results filtering
  const results = useMemo<SearchResultItem[]>(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];

    const matches: SearchResultItem[] = [];

    // 1. If query is a coordinate input
    if (coordinateCheck.isCoordinateQuery && coordinateCheck.isValid && coordinateCheck.lat !== undefined && coordinateCheck.lng !== undefined) {
      const lat = coordinateCheck.lat;
      const lng = coordinateCheck.lng;

      // Check if coordinates happen to match a known entity closely (~500m)
      const exactMatch = allEntities.find((e) => {
        const dLat = Math.abs(e.lat - lat);
        const dLng = Math.abs(e.lng - lng);
        return dLat < 0.005 && dLng < 0.005;
      });

      matches.push({
        id: `coord_${lat}_${lng}`,
        type: 'COORDINATE',
        title: `Coordinates: ${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E`,
        subtitle: exactMatch
          ? `Direct Coordinates • Co-located near: ${exactMatch.title}`
          : 'Direct Geographic Coordinates • Navigate map camera to target position',
        lat: lat,
        lng: lng,
        badgeLabel: 'Coordinate',
        badgeClass: 'bg-cyan-50 text-cyan-800 border-cyan-200',
        icon: Navigation,
        extraInfo: exactMatch ? `Matches ${exactMatch.badgeLabel} (${exactMatch.title})` : 'Custom Geographic Point',
        data: exactMatch || null,
      });
    }

    // 2. City-level matching
    CITY_CENTROIDS.forEach((city) => {
      const matchedAlias = city.aliases.some((alias) => alias.includes(q) || q.includes(alias));
      const matchedName = city.cityName.toLowerCase().includes(q) || city.label.toLowerCase().includes(q);

      if (matchedAlias || matchedName) {
        matches.push({
          id: `city_${city.cityName.toLowerCase()}`,
          type: 'CITY',
          title: city.label,
          subtitle: city.subtitle,
          lat: city.coords[0],
          lng: city.coords[1],
          city: city.cityName,
          badgeLabel: 'Air Basin',
          badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200',
          icon: Building2,
          extraInfo: `Default focal coordinates: ${city.coords[0]}°N, ${city.coords[1]}°E`,
          data: city,
        });
      }
    });

    // 3. Entity dataset matching across all real fields
    allEntities.forEach((item) => {
      const titleMatch = item.title.toLowerCase().includes(q);
      const subtitleMatch = item.subtitle.toLowerCase().includes(q);
      const idMatch = item.id.toLowerCase().includes(q);
      const stationMatch = item.stationId ? item.stationId.toLowerCase().includes(q) : false;
      const cityMatch = item.city ? item.city.toLowerCase().includes(q) : false;
      const extraMatch = item.extraInfo ? item.extraInfo.toLowerCase().includes(q) : false;

      if (titleMatch || subtitleMatch || idMatch || stationMatch || cityMatch || extraMatch) {
        matches.push(item);
      }
    });

    return matches;
  }, [query, coordinateCheck, allEntities]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      setIsOpen(true);
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results.length > 0) {
        const target = activeIndex >= 0 && activeIndex < results.length ? results[activeIndex] : results[0];
        handleSelectResult(target);
      } else if (coordinateCheck.isCoordinateQuery && coordinateCheck.isValid && coordinateCheck.lat !== undefined && coordinateCheck.lng !== undefined) {
        onSelectCoordinates(coordinateCheck.lat, coordinateCheck.lng);
        setIsOpen(false);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
      setActiveIndex(-1);
      inputRef.current?.blur();
    }
  };

  const handleSelectResult = (item: SearchResultItem) => {
    if (item.type === 'COORDINATE') {
      // If co-located with an actual entity, select that entity
      if (item.data && item.data.type) {
        onSelectEntity(item.data);
      } else {
        onSelectCoordinates(item.lat, item.lng);
      }
    } else if (item.type === 'CITY') {
      onSelectCity(item.city || 'Delhi', [item.lat, item.lng], item.data?.zoom || 11);
    } else {
      onSelectEntity(item);
    }
    setIsOpen(false);
    setActiveIndex(-1);
  };

  const handleClear = () => {
    setQuery('');
    setIsOpen(false);
    setActiveIndex(-1);
    inputRef.current?.focus();
  };

  return (
    <div
      ref={containerRef}
      className={`relative z-[950] pointer-events-auto select-none ${className}`}
    >
      {/* Search Input Bar + Quick "Go to NCR" Action */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Main Search Input Box */}
        <div className="relative flex items-center w-[220px] xs:w-[260px] sm:w-[320px] md:w-[360px] bg-white/95 backdrop-blur-md rounded-lg border border-slate-300 shadow-md transition-all duration-200 focus-within:ring-2 focus-within:ring-[#0a2540] focus-within:border-[#0a2540]">
          <div className="pl-3 pr-2 text-slate-400 shrink-0">
            <Search className="w-4 h-4 text-slate-500" />
          </div>

          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={isOpen}
            aria-controls="map-search-dropdown"
            aria-label="Search locations, cities, monitoring stations, or coordinates"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
              setActiveIndex(-1);
            }}
            onFocus={() => {
              if (query.trim()) setIsOpen(true);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search locations, cities, stations, lat/lng..."
            className="w-full py-1.5 text-xs text-slate-900 bg-transparent placeholder-slate-400 focus:outline-hidden font-medium min-w-0"
          />

          {query && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 mr-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors cursor-pointer"
              aria-label="Clear search input"
              title="Clear search query"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Dedicated "Go to NCR" Button */}
        <button
          type="button"
          onClick={() => {
            onGoToNCR();
            setIsOpen(false);
          }}
          className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 bg-white/95 backdrop-blur-md border border-slate-300 rounded-lg shadow-md hover:bg-slate-50 active:bg-slate-100 text-xs font-semibold text-slate-800 hover:text-[#0a2540] transition-all cursor-pointer shrink-0"
          title="Reset map view to Delhi NCR Air Basin (28.6139°N, 77.2090°E)"
          aria-label="Go to Delhi NCR basin"
        >
          <Compass className="w-3.5 h-3.5 text-sky-600 shrink-0" />
          <span className="font-semibold">Go to NCR</span>
        </button>
      </div>

      {/* Auto-suggest Dropdown Results */}
      {isOpen && (
        <div
          id="map-search-dropdown"
          className="absolute left-0 top-full mt-1.5 w-full sm:w-[420px] max-h-[380px] bg-white/98 backdrop-blur-md border border-slate-300 shadow-2xl rounded-xl overflow-hidden flex flex-col z-[1100] animate-in fade-in slide-in-from-top-1 duration-150"
        >
          {/* Header Summary / Type Context */}
          <div className="px-3 py-1.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
            <span>
              {coordinateCheck.isCoordinateQuery
                ? 'Coordinate Navigation'
                : `Matching Results (${results.length})`}
            </span>
            <span className="font-mono text-[9px] text-slate-400 lowercase">
              esc to close • ↑↓ to navigate
            </span>
          </div>

          {/* Coordinate Validation Warning */}
          {coordinateCheck.isCoordinateQuery && !coordinateCheck.isValid && (
            <div className="p-3 bg-amber-50 border-b border-amber-200 text-xs text-amber-900 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold">Coordinate Input Error</strong>
                <p className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
                  {coordinateCheck.errorMessage ||
                    'Invalid coordinates. Latitude must be between -90 and 90 and longitude between -180 and 180.'}
                </p>
                <p className="text-[10px] text-amber-700 font-mono mt-1">
                  Example: 28.6139, 77.2090 or 28.6139 77.2090
                </p>
              </div>
            </div>
          )}

          {/* Results List */}
          <ul
            ref={listRef}
            role="listbox"
            className="flex-1 overflow-y-auto divide-y divide-slate-100 overscroll-contain"
          >
            {results.length > 0 ? (
              results.map((item, idx) => {
                const IconComponent = item.icon;
                const isSelected = idx === activeIndex || Boolean(item.entityId && item.entityId === selectedEventId);

                return (
                  <li
                    key={item.id}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelectResult(item)}
                    onMouseEnter={() => setActiveIndex(idx)}
                    className={`px-3 py-2.5 transition-colors cursor-pointer flex items-start gap-2.5 ${
                      isSelected
                        ? 'bg-sky-50/90 text-[#0a2540]'
                        : 'hover:bg-slate-50 text-slate-800'
                    }`}
                  >
                    {/* Entity Category Icon */}
                    <div
                      className={`p-1.5 rounded-lg shrink-0 mt-0.5 border ${item.badgeClass}`}
                    >
                      <IconComponent className="w-3.5 h-3.5" />
                    </div>

                    {/* Entity Content Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1.5 mb-0.5">
                        <span className="font-bold text-xs truncate text-slate-900">
                          {item.title}
                        </span>
                        <span
                          className={`text-[9px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.2 rounded border shrink-0 ${item.badgeClass}`}
                        >
                          {item.badgeLabel}
                        </span>
                      </div>

                      <p className="text-[11px] text-slate-500 truncate mb-1">
                        {item.subtitle}
                      </p>

                      {item.extraInfo && (
                        <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                          <span>{item.extraInfo}</span>
                          {item.lat !== undefined && item.lng !== undefined && (
                            <>
                              <span>•</span>
                              <span>
                                {item.lat.toFixed(3)}°N, {item.lng.toFixed(3)}°E
                              </span>
                            </>
                          )}
                        </div>
                      )}
                    </div>

                    <ArrowRight className={`w-3.5 h-3.5 shrink-0 mt-2 transition-transform ${isSelected ? 'translate-x-0.5 text-sky-600' : 'text-slate-300'}`} />
                  </li>
                );
              })
            ) : query.trim() && !coordinateCheck.isCoordinateQuery ? (
              <li className="p-4 text-center text-xs text-slate-500">
                <p className="font-semibold text-slate-700 mb-1">
                  No surveillance locations found matching &ldquo;{query}&rdquo;
                </p>
                <p className="text-[11px] text-slate-500">
                  Try searching for monitoring stations like <span className="font-mono font-bold text-slate-700">DPCC_AnandVihar</span> or <span className="font-mono font-bold text-slate-700">MPCB_Bandra</span>, cities like <span className="font-bold text-slate-700">Delhi</span> or <span className="font-bold text-slate-700">Mumbai</span>, hotspots like <span className="font-bold text-slate-700">Okhla</span>, or coordinates like <span className="font-mono font-bold text-slate-700">28.6139, 77.2090</span>.
                </p>
              </li>
            ) : null}
          </ul>

          {/* Footer Quick Hints */}
          <div className="px-3 py-1.5 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
            <span>Supports: Stations • Hotspots • Fires • Risk Zones • Citizen Reports • Coordinates</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default MapSearch;

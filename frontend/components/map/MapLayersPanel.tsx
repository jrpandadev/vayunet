'use client';

import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Layers,
  Wind,
  Flame,
  Camera,
  Radio,
  CheckSquare,
  Square,
  RotateCcw,
  X,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export interface MapLayersState {
  riskZones: boolean;
  hotspots: boolean;
  fires: boolean;
  observations: boolean;
  events: boolean;
  wind: boolean;
}

export const DEFAULT_MAP_LAYERS: MapLayersState = {
  riskZones: true,
  hotspots: true,
  fires: true,
  observations: true,
  events: true,
  wind: true,
};

export interface MapLayersCounts {
  riskZones?: number;
  hotspots?: number;
  fires?: number;
  observations?: number;
  events?: number;
  wind?: string | number;
}

export interface MapLayersPanelProps {
  layersState: MapLayersState;
  onToggleLayer: (layerKey: keyof MapLayersState, value: boolean) => void;
  onSelectAll: () => void;
  onResetDefault: () => void;
  onDeselectAll?: () => void;
  counts?: MapLayersCounts;
  selectedEventId?: string | null;
  className?: string;
}

interface LayerItemConfig {
  key: keyof MapLayersState;
  title: string;
  subtitle: string;
  tag: string;
  icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
  iconColor: string;
  count: number | string;
}

export const MapLayersPanel: React.FC<MapLayersPanelProps> = ({
  layersState,
  onToggleLayer,
  onSelectAll,
  onResetDefault,
  onDeselectAll,
  counts,
  selectedEventId,
  className = '',
}) => {
  const [desktopOpen, setDesktopOpen] = useState<boolean>(false);
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Automatically collapse / minimize floating panel when an event/marker is selected
  // to prevent obscuring Leaflet popups or map focus
  const [prevEventId, setPrevEventId] = useState(selectedEventId);
  if (selectedEventId && selectedEventId !== prevEventId) {
    setPrevEventId(selectedEventId);
    setDesktopOpen(false);
    setMobileOpen(false);
  } else if (selectedEventId !== prevEventId) {
    setPrevEventId(selectedEventId);
  }

  // Handle outside clicks on desktop to auto-dismiss
  useEffect(() => {
    if (!desktopOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setDesktopOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [desktopOpen]);

  // Lock background scroll on mobile when sheet is active
  useEffect(() => {
    if (mobileOpen) {
      const originalStyle = window.getComputedStyle(document.body).overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalStyle;
      };
    }
  }, [mobileOpen]);

  // Handle escape key on mobile
  useEffect(() => {
    if (!mobileOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMobileOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileOpen]);

  const activeCount = Object.values(layersState).filter(Boolean).length;
  const totalCount = 6;

  const handleClearAll = () => {
    if (onDeselectAll) {
      onDeselectAll();
    } else {
      (Object.keys(layersState) as (keyof MapLayersState)[]).forEach((key) => {
        onToggleLayer(key, false);
      });
    }
  };

  const layersList: LayerItemConfig[] = [
    {
      key: 'riskZones',
      title: 'PM2.5 Risk Zones',
      subtitle: 'Exposure corridors & regional boundary dispersion',
      tag: 'Simulation',
      icon: Layers,
      iconBg: 'bg-emerald-50 border border-emerald-200',
      iconColor: 'text-emerald-600',
      count: counts?.riskZones !== undefined ? `${counts.riskZones} Zones` : '6 Zones',
    },
    {
      key: 'hotspots',
      title: 'Emission Hotspots',
      subtitle: 'Simulated industrial and vehicular plume sources',
      tag: 'Simulation',
      icon: Wind,
      iconBg: 'bg-purple-50 border border-purple-200',
      iconColor: 'text-purple-600',
      count: counts?.hotspots !== undefined ? `${counts.hotspots} Spots` : '7 Spots',
    },
    {
      key: 'fires',
      title: 'Fire Detections',
      subtitle: 'Agricultural thermal anomalies & active burns',
      tag: 'Simulation',
      icon: Flame,
      iconBg: 'bg-amber-50 border border-amber-200',
      iconColor: 'text-amber-600',
      count: counts?.fires !== undefined ? `${counts.fires} Fires` : '5 Fires',
    },
    {
      key: 'observations',
      title: 'Citizen Observations',
      subtitle: 'Photographic evidence & crowd field reports',
      tag: 'Simulation',
      icon: Camera,
      iconBg: 'bg-sky-50 border border-sky-200',
      iconColor: 'text-sky-600',
      count: counts?.observations !== undefined ? `${counts.observations} Photos` : '7 Photos',
    },
    {
      key: 'events',
      title: 'Base Monitoring Stations',
      subtitle: 'CPCB & CAAQMS telemetry stations and events',
      tag: 'Telemetry',
      icon: Radio,
      iconBg: 'bg-slate-100 border border-slate-200',
      iconColor: 'text-[#0a2540]',
      count: counts?.events !== undefined ? `${counts.events} Sites` : 'Telemetry',
    },
    {
      key: 'wind',
      title: 'Wind Flow Overlay',
      subtitle: 'Atmospheric transport vectors & prevailing flow',
      tag: 'Meteorology',
      icon: Wind,
      iconBg: 'bg-cyan-50 border border-cyan-200',
      iconColor: 'text-cyan-600',
      count: counts?.wind !== undefined ? `${counts.wind}` : 'NW 315°',
    },
  ];

  return (
    <div
      ref={panelRef}
      className={`relative inline-block ${className}`}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
      onDoubleClick={(e) => e.stopPropagation()}
    >
      {/* DESKTOP COLLAPSED TRIGGER BUTTON (sm: and up) */}
      <div className="hidden sm:block">
        <button
          type="button"
          onClick={() => setDesktopOpen((prev) => !prev)}
          className={`inline-flex items-center gap-2 bg-white/95 backdrop-blur-md border border-slate-300/90 text-[#0a2540] font-semibold text-xs px-3.5 py-2 rounded-lg shadow-md hover:bg-white hover:border-slate-400 active:scale-95 transition-all cursor-pointer select-none ${
            desktopOpen ? 'ring-2 ring-[#0a2540]/20 bg-white border-[#0a2540]' : ''
          }`}
          aria-label="Toggle map surveillance layers panel"
          aria-expanded={desktopOpen}
        >
          <Layers className="w-3.5 h-3.5 text-[#0a2540]" />
          <span>Layers</span>
          <span className="text-slate-300">•</span>
          <span className="font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[11px] border border-slate-200">
            {activeCount}/{totalCount}
          </span>
          <ChevronDown
            className={`w-3.5 h-3.5 text-slate-500 transition-transform duration-200 ${
              desktopOpen ? 'rotate-180' : ''
            }`}
          />
        </button>
      </div>

      {/* MOBILE TRIGGER BUTTON (<sm: 640px) */}
      <div className="sm:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="inline-flex items-center gap-1.5 bg-white/95 backdrop-blur-md border border-slate-300/90 text-[#0a2540] font-semibold text-xs px-3 py-2 rounded-lg shadow-md hover:bg-white active:scale-95 transition-all cursor-pointer select-none"
          aria-label="Open mobile map layers"
        >
          <Layers className="w-3.5 h-3.5 text-[#0a2540]" />
          <span className="text-xs font-semibold">Layers</span>
          <span className="font-mono text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[10px] border border-slate-200 font-bold">
            {activeCount}
          </span>
        </button>
      </div>

      {/* DESKTOP EXPANDED FLOATING PANEL (DROPDOWN CARD) */}
      {desktopOpen && (
        <div
          className="hidden sm:block absolute right-0 top-full mt-2 w-84 bg-white/95 backdrop-blur-md border border-slate-300/90 rounded-xl p-3.5 shadow-2xl z-[900] text-xs select-none animate-in fade-in slide-in-from-top-1 duration-150"
          role="dialog"
          aria-label="Surveillance Layers Configuration"
        >
          {/* Header */}
          <div className="flex items-center justify-between gap-2 pb-2.5 border-b border-slate-100 mb-2.5">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-[#0a2540]/5 border border-[#0a2540]/15 flex items-center justify-center">
                <Layers className="w-3.5 h-3.5 text-[#0a2540]" />
              </div>
              <span className="font-bold uppercase tracking-wider text-[#0a2540] text-[11px]">
                Map Layers
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                {activeCount} of {totalCount} Active
              </span>
              <button
                type="button"
                onClick={() => setDesktopOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                aria-label="Close layers panel"
                title="Close layers panel"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Quick Action Toolbar: Select All, Clear, Reset to Default */}
          <div className="flex items-center justify-between gap-1.5 px-2.5 py-1.5 bg-slate-50/90 rounded-lg border border-slate-200/80 mb-3 text-[11px]">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={onSelectAll}
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-slate-700 hover:text-[#0a2540] hover:bg-slate-200/70 font-semibold transition-colors cursor-pointer"
                title="Enable all map layers"
              >
                <CheckSquare className="w-3 h-3 text-sky-600" />
                <span>Select All</span>
              </button>
              <span className="text-slate-300">|</span>
              <button
                type="button"
                onClick={handleClearAll}
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-slate-600 hover:text-slate-900 hover:bg-slate-200/70 font-semibold transition-colors cursor-pointer"
                title="Disable all map layers"
              >
                <Square className="w-3 h-3 text-slate-400" />
                <span>Clear</span>
              </button>
            </div>

            <button
              type="button"
              onClick={onResetDefault}
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-slate-700 hover:text-[#0a2540] hover:bg-slate-200/70 font-semibold transition-colors cursor-pointer"
              title="Restore standard surveillance defaults"
            >
              <RotateCcw className="w-3 h-3 text-slate-500" />
              <span>Reset to Default</span>
            </button>
          </div>

          {/* Layer Rows */}
          <div className="space-y-1.5">
            {layersList.map((layer) => {
              const isActive = layersState[layer.key];
              const Icon = layer.icon;

              return (
                <div
                  key={layer.key}
                  onClick={() => onToggleLayer(layer.key, !isActive)}
                  className={`flex items-center justify-between gap-2.5 p-2 rounded-lg border transition-all cursor-pointer ${
                    isActive
                      ? 'bg-slate-50/80 border-slate-200 hover:bg-slate-100/80'
                      : 'bg-white border-transparent opacity-65 hover:opacity-90 hover:bg-slate-50'
                  }`}
                  role="checkbox"
                  aria-checked={isActive}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === ' ' || e.key === 'Enter') {
                      e.preventDefault();
                      onToggleLayer(layer.key, !isActive);
                    }
                  }}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 ${layer.iconBg}`}
                    >
                      <Icon className={`w-3.5 h-3.5 ${layer.iconColor}`} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-slate-900 truncate text-[12px]">
                          {layer.title}
                        </span>
                        <span className="text-[9px] font-mono text-slate-400 uppercase font-semibold">
                          ({layer.count})
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 truncate leading-tight mt-0.5">
                        {layer.subtitle}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {/* Explicit ON / OFF indicator badge */}
                    <span
                      className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase ${
                        isActive
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-slate-100 text-slate-400 border border-slate-200'
                      }`}
                    >
                      {isActive ? 'ON' : 'OFF'}
                    </span>

                    {/* Toggle Switch Component */}
                    <div
                      className={`relative inline-flex h-4.5 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                        isActive ? 'bg-[#0a2540]' : 'bg-slate-300'
                      }`}
                    >
                      <span
                        aria-hidden="true"
                        className={`pointer-events-none inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                          isActive ? 'translate-x-3.5' : 'translate-x-0'
                        }`}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* MOBILE BOTTOM SHEET MODAL DRAWER (<sm: 640px) */}
      {mounted &&
        mobileOpen &&
        createPortal(
          <div
            className="sm:hidden fixed inset-0 z-[1200] flex flex-col justify-end pointer-events-none"
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Backdrop: dim background and dismiss on tap */}
            <div
              className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs pointer-events-auto transition-opacity"
              onClick={() => setMobileOpen(false)}
              aria-label="Close layers backdrop"
            />

            {/* Bottom Sheet Container */}
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="mobile-layers-title"
              className="relative pointer-events-auto w-full max-w-lg mx-auto bg-white rounded-t-2xl shadow-2xl border-t border-slate-200 flex flex-col max-h-[82vh] overflow-hidden select-none"
            >
              {/* Drag Handle */}
              <div className="pt-2.5 pb-1 flex justify-center">
                <div className="w-10 h-1 bg-slate-300 rounded-full" />
              </div>

              {/* Header */}
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-md bg-[#0a2540]/5 border border-[#0a2540]/15 flex items-center justify-center">
                    <Layers className="w-4 h-4 text-[#0a2540]" />
                  </div>
                  <div>
                    <h2
                      id="mobile-layers-title"
                      className="font-bold text-xs uppercase tracking-wider text-[#0a2540]"
                    >
                      Map Layers
                    </h2>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {activeCount} of {totalCount} Active
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  className="p-1.5 -mr-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center"
                  aria-label="Close layers panel"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Quick Actions */}
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={onSelectAll}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-slate-700 font-semibold hover:bg-slate-200 active:bg-slate-300 transition-colors min-h-[36px]"
                  >
                    <CheckSquare className="w-3.5 h-3.5 text-sky-600" />
                    <span>Select All</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleClearAll}
                    className="inline-flex items-center gap-1 px-2 py-1.5 rounded-md text-slate-600 font-semibold hover:bg-slate-200 active:bg-slate-300 transition-colors min-h-[36px]"
                  >
                    <Square className="w-3.5 h-3.5 text-slate-400" />
                    <span>Clear</span>
                  </button>
                </div>
                <button
                  type="button"
                  onClick={onResetDefault}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-slate-700 font-semibold hover:bg-slate-200 active:bg-slate-300 transition-colors min-h-[36px]"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
                  <span>Reset to Default</span>
                </button>
              </div>

              {/* Layers List */}
              <div className="px-4 py-3 space-y-2 overflow-y-auto flex-1 overscroll-contain">
                {layersList.map((layer) => {
                  const isActive = layersState[layer.key];
                  const Icon = layer.icon;

                  return (
                    <div
                      key={layer.key}
                      onClick={() => onToggleLayer(layer.key, !isActive)}
                      className={`flex items-center justify-between gap-3 p-3 rounded-xl border transition-all cursor-pointer min-h-[52px] ${
                        isActive
                          ? 'bg-slate-50 border-slate-200'
                          : 'bg-white border-slate-100 opacity-60'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${layer.iconBg}`}
                        >
                          <Icon className={`w-4 h-4 ${layer.iconColor}`} />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="font-bold text-slate-900 text-xs">
                              {layer.title}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold">
                              ({layer.count})
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 truncate leading-tight mt-0.5">
                            {layer.subtitle}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span
                          className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded uppercase ${
                            isActive
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-slate-100 text-slate-400 border border-slate-200'
                          }`}
                        >
                          {isActive ? 'ON' : 'OFF'}
                        </span>
                        <div
                          className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                            isActive ? 'bg-[#0a2540]' : 'bg-slate-300'
                          }`}
                        >
                          <span
                            aria-hidden="true"
                            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                              isActive ? 'translate-x-4' : 'translate-x-0'
                            }`}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Mobile Footer */}
              <div className="px-4 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  className="w-full bg-[#0a2540] text-white px-5 py-3 rounded-lg text-xs font-semibold hover:bg-[#0f3456] active:scale-95 transition-all shadow-xs cursor-pointer min-h-[44px] flex items-center justify-center"
                >
                  Apply & View Map ({activeCount}/{totalCount} Layers)
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
};

export default MapLayersPanel;

'use client';

import React, { useState } from 'react';
import { Shield, ChevronDown, ChevronUp, Radio, TrendingUp } from 'lucide-react';

interface MapLegendProps {
  totalEvents: number;
  className?: string;
  defaultCollapsed?: boolean;
}

export const MapLegend: React.FC<MapLegendProps> = ({
  totalEvents,
  className = '',
  defaultCollapsed = false,
}) => {
  const [collapsed, setCollapsed] = useState<boolean>(defaultCollapsed);

  const legendItems = [
    { label: 'Low', color: 'bg-[#22c55e]' },
    { label: 'Moderate', color: 'bg-[#eab308]' },
    { label: 'High', color: 'bg-[#f97316]' },
    { label: 'Very High', color: 'bg-[#ef4444]' },
    { label: 'Critical', color: 'bg-[#9333ea]' },
  ];

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={() => setCollapsed(false)}
        className={`inline-flex items-center gap-2 bg-white/95 backdrop-blur-md border border-[#cbd5e1] hover:border-[#0a2540] text-slate-800 rounded-lg px-3 py-2 shadow-md text-xs font-semibold hover:bg-white transition-all cursor-pointer select-none ${className}`}
        aria-label="Expand map legend"
      >
        <Shield className="w-3.5 h-3.5 text-[#0a2540]" />
        <span>Legend ({totalEvents} Sites)</span>
        <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
      </button>
    );
  }

  return (
    <div
      className={`bg-white/95 backdrop-blur-md border border-[#e2e8f0] rounded-lg p-3.5 shadow-lg text-xs select-none ${className}`}
    >
      {/* Header with Minimize Toggle */}
      <div className="flex items-center justify-between gap-3 pb-2 border-b border-slate-100 mb-2.5">
        <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[#0a2540]">
          <Shield className="w-3.5 h-3.5 text-[#0a2540]" />
          <span>Surveillance Legend</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
            {totalEvents} Sites
          </span>
          <button
            type="button"
            onClick={() => setCollapsed(true)}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Collapse legend"
            title="Collapse legend"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 4-tier Civic Risk Scale */}
      <div className="space-y-1.5 mb-3">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1 font-mono">
          Civic Risk Tiers
        </span>
        {legendItems.map((item, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full ${item.color} ring-2 ring-white shadow-2xs shrink-0`}
            />
            <span className="text-slate-700 font-medium">{item.label}</span>
          </div>
        ))}
      </div>

      {/* Observed vs Predicted Symbology & Emission Hotspot */}
      <div className="pt-2 border-t border-slate-100 space-y-1.5 mb-2">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1 font-mono">
          Data Modality & Layers
        </span>
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <span className="h-3 w-3 rounded-full bg-slate-700 border border-white shadow-2xs shrink-0" />
          <span>Solid Core: <strong>Observed Telemetry</strong> (Ground Sensor)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <span className="h-3 w-3 rounded-full border-2 border-dashed border-sky-600 bg-sky-100/50 shrink-0" />
          <span>Dashed Ring: <strong>PM2.5 Forecast (Next 24 Hours)</strong></span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <span className="relative flex items-center justify-center h-3.5 w-3.5 shrink-0">
            <span className="absolute inset-0 rounded-full bg-purple-400/30 border border-purple-500/60" />
            <span className="h-1.5 w-1.5 rounded-full bg-[#9333ea]" />
          </span>
          <span>Smoke Plume: <strong>Emission Hotspot</strong></span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <span className="relative flex items-center justify-center h-3.5 w-3.5 shrink-0">
            <span className="absolute inset-0 rounded-full bg-orange-400/30 border border-orange-500/70" />
            <span className="h-2 w-2 rounded-full bg-gradient-to-tr from-red-600 to-amber-400 shadow-2xs" />
          </span>
          <span>Warm Flame: <strong>Active Fire Detection</strong></span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <span className="relative flex items-center justify-center h-3.5 w-3.5 shrink-0">
            <span className="h-2.5 w-2.5 rounded-full border border-dashed border-amber-800/80 bg-amber-950/20" />
          </span>
          <span>Dashed Circle: <strong>Historical Fire (Muted)</strong></span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <span className="h-3 w-3.5 rounded-xs border border-dashed border-emerald-600 bg-emerald-500/25 shrink-0" />
          <span>Dashed Area: <strong>Predicted PM2.5 Risk Zone</strong></span>
        </div>
        <div className="pl-5 text-[10px] text-slate-500 italic leading-tight">
          Shaded area = Predicted / simulated PM2.5 risk
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <span className="relative flex items-center justify-center h-3.5 w-3.5 shrink-0">
            <span className="absolute inset-0 rounded-full bg-sky-400/25 border border-sky-500/70" />
            <span className="h-2 w-2 rounded-full bg-[#0284c7] shadow-2xs" />
          </span>
          <span>Camera Pin: <strong>Citizen Observation</strong> (User Evidence)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-600">
          <span className="relative flex items-center justify-center h-3.5 w-3.5 shrink-0">
            <span className="w-3.5 h-0.5 bg-cyan-500 rounded-full" />
            <span className="absolute right-0 top-1/2 -translate-y-1/2 border-t-2 border-r-2 border-cyan-600 w-1.5 h-1.5 rotate-45" />
          </span>
          <span>Translucent Vector: <strong>Wind Flow / Pollutant Transport (NW 315°)</strong></span>
        </div>
        <div className="pl-5 text-[10px] text-slate-500 italic leading-tight">
          Directional vectors indicate prevailing atmospheric flow & transport orientation
        </div>
      </div>

      <div className="mt-2.5 pt-2 border-t border-slate-100 text-[10px] text-slate-400 font-mono flex items-center justify-between">
        <span>WGS84 • Leaflet Grid</span>
        <span>Simulation Feed</span>
      </div>
    </div>
  );
};

export default MapLegend;

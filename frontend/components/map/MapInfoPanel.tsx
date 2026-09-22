'use client';

import React, { useState, useMemo, useEffect } from 'react';
import Link from 'next/link';
import { createPortal } from 'react-dom';
import {
  X,
  MapPin,
  Clock,
  ArrowRight,
  ExternalLink,
  Activity,
  Wind,
  Flame,
  Camera,
  Layers,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Radio,
  CheckCircle2,
  ZoomIn,
  Check,
  HelpCircle,
} from 'lucide-react';
import { MapLayersState } from './MapLayersPanel';
import { getIsSimulationMode } from '@/lib/api';
import { PollutionEvent, RiskLevel } from '@/lib/types';
import RiskBadge from '@/components/ui/RiskBadge';
import { MOCK_EMISSION_HOTSPOTS, EmissionHotspot } from '@/lib/hotspots';
import { MOCK_FIRE_DETECTIONS, FireDetection } from '@/lib/fires';
import { MOCK_RISK_ZONES, RiskZone } from '@/lib/riskZones';
import { MOCK_CITIZEN_OBSERVATIONS, CitizenObservation } from '@/lib/observations';
import AIModelPanel from '@/components/ai/AIModelPanel';

export interface MapInfoPanelProps {
  selectedEventId: string | null;
  onClose: () => void;
  events: PollutionEvent[];
  observations?: CitizenObservation[];
  hotspots?: EmissionHotspot[];
  fires?: FireDetection[];
  riskZones?: RiskZone[];
  className?: string;
}

// Map PM2.5 numerical values to civic risk tiers for multi-horizon forecast progression
function getRiskTierForPm25(pm25: number): RiskLevel {
  if (pm25 >= 250) return 'CRITICAL';
  if (pm25 >= 120) return 'HIGH';
  if (pm25 >= 60) return 'MODERATE';
  return 'LOW';
}

// -------------------------------------------------------------------------
// 1. POLLUTION EVENT / BASE MONITORING STATION DETAIL VIEW
// -------------------------------------------------------------------------
const EventDetailView: React.FC<{
  event: PollutionEvent;
  onClose: () => void;
}> = ({ event, onClose }) => {
  const currentPm25 = event.evidence?.sensor?.pm25 ?? 100;
  const f6 = event.forecast?.pm25_6h ?? currentPm25;
  const f24 = event.forecast?.pm25_24h ?? f6;
  const f72 = event.forecast?.pm25_72h;

  // Derive intermediate horizon forecast progressions
  const f12 = Math.round((f6 * 2 + f24) / 3);
  const f18 = Math.round((f6 + f24 * 2) / 3);

  // Calculate 6-hour trend indicator
  const diff = f6 - currentPm25;
  const pct = currentPm25 > 0 ? Math.round((Math.abs(diff) / currentPm25) * 100) : 0;
  const isDeteriorating = diff > 3;
  const isImproving = diff < -3;

  const stationId = event.evidence?.sensor?.station_id || 'CAAQMS Telemetry Station';
  const confidencePct = Math.round((event.detection?.confidence ?? 0.82) * 100);

  const progressionRows = [
    { label: 'Now', hours: 'Observed', val: currentPm25, isNow: true },
    { label: '+6h', hours: 'Forecast', val: f6, isNow: false },
    { label: '+12h', hours: 'Projected', val: f12, isNow: false },
    { label: '+18h', hours: 'Projected', val: f18, isNow: false },
    { label: '+24h', hours: 'Forecast', val: f24, isNow: false },
  ];

  return (
    <div className="space-y-4 text-xs">
      {/* Entity Header Banner */}
      <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-3">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-[#0a2540] text-white">
            <Radio className="w-3 h-3" />
            <span>Base Monitoring Station</span>
          </span>
          <span className="font-mono text-[10px] text-slate-500 bg-white px-1.5 py-0.5 rounded border border-slate-200">
            {event.event_id}
          </span>
        </div>

        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <MapPin className="w-4 h-4 text-[#0a2540] shrink-0" />
          <span>{event.location.city} • {stationId}</span>
        </h3>

        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 font-mono">
          <span>{event.location.lat.toFixed(4)}°N, {event.location.lng.toFixed(4)}°E</span>
          <span>•</span>
          <span className="capitalize">{event.outcome}</span>
        </div>
      </div>

      {/* Observed PM2.5 & Civic Risk Badge */}
      <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-2xs">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-0.5 font-mono">
              Current Observed Particulate
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-black text-slate-900 font-mono tracking-tight">
                {currentPm25}
              </span>
              <span className="text-xs text-slate-500 font-medium font-sans">
                µg/m³ PM2.5
              </span>
            </div>
          </div>
          <RiskBadge level={event.risk} size="md" />
        </div>

        {/* 6-Hour Trend Indicator */}
        <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between">
          <span className="text-[11px] text-slate-600 font-medium">
            Projected 6h Trend:
          </span>
          {isDeteriorating ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
              <TrendingUp className="w-3 h-3 text-rose-600" />
              <span>↑ Deteriorating (+{pct}% in next 6h)</span>
            </span>
          ) : isImproving ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              <TrendingUp className="w-3 h-3 text-emerald-600 rotate-180" />
              <span>↓ Improving (-{pct}% in next 6h)</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              <span>→ Stable (Steady over next 6h)</span>
            </span>
          )}
        </div>
      </div>

      {/* Multi-Horizon Forecast Progression (Table & Visual) */}
      <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-2xs">
        <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-100">
          <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-slate-900 text-[11px]">
            <TrendingUp className="w-3.5 h-3.5 text-sky-600" />
            <span>Multi-Horizon Forecast Progression</span>
          </div>
          <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
            Spike Risk: {event.forecast?.spike_probability || 'LOW'}
          </span>
        </div>

        {/* Forecast Table */}
        <div className="overflow-hidden border border-slate-200 rounded-lg">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                <th className="py-1.5 px-2.5">Horizon</th>
                <th className="py-1.5 px-2.5">PM2.5</th>
                <th className="py-1.5 px-2.5 text-right">Risk Tier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {progressionRows.map((row) => {
                const tier = getRiskTierForPm25(row.val);
                return (
                  <tr
                    key={row.label}
                    className={row.isNow ? 'bg-sky-50/50 font-semibold' : 'hover:bg-slate-50/60'}
                  >
                    <td className="py-1.5 px-2.5">
                      <span className="text-slate-900 font-bold">{row.label}</span>
                      <span className="text-[10px] text-slate-400 block font-normal font-sans leading-none">
                        {row.hours}
                      </span>
                    </td>
                    <td className="py-1.5 px-2.5 font-bold text-slate-800">
                      {row.val} <span className="text-[9px] font-normal text-slate-400">µg/m³</span>
                    </td>
                    <td className="py-1.5 px-2.5 text-right">
                      <RiskBadge level={tier} size="sm" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {f72 !== undefined && (
          <p className="text-[10px] text-slate-500 font-mono mt-2 text-right">
            Extended 72h Outlook: <strong>{f72} µg/m³</strong>
          </p>
        )}
      </div>

      {/* Step 12: Dedicated AI & Predictive Model Dossier Panel */}
      <AIModelPanel entityType="EVENT" event={event} isCompact={true} />

      {/* Quick Action: Link to Full Incident Dossier */}
      {event.event_id && (
        <div className="pt-1">
          <Link
            href={`/dashboard/event?id=${event.event_id}`}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-semibold rounded-xl shadow-md transition-all active:scale-98 cursor-pointer"
          >
            <span>View Full Incident Dossier</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
};

// -------------------------------------------------------------------------
// 2. CITIZEN OBSERVATION DETAIL VIEW
// -------------------------------------------------------------------------
const ObservationDetailView: React.FC<{
  observation: CitizenObservation;
  onClose: () => void;
}> = ({ observation, onClose }) => {
  const [isImageModalOpen, setIsImageModalOpen] = useState<boolean>(false);
  const riskTier = getRiskTierForPm25(observation.pm25AtLocation);

  return (
    <div className="space-y-4 text-xs">
      {/* Header Banner */}
      <div className="bg-sky-50/70 border border-sky-200 rounded-xl p-3">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-sky-700 text-white">
            <Camera className="w-3 h-3" />
            <span>Citizen Observation</span>
          </span>
          <span className="font-mono text-[10px] text-sky-800 bg-white px-1.5 py-0.5 rounded border border-sky-200">
            {observation.id}
          </span>
        </div>

        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <MapPin className="w-4 h-4 text-sky-700 shrink-0" />
          <span>{observation.locationName}</span>
        </h3>

        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 font-mono">
          <span>{observation.latitude.toFixed(4)}°N, {observation.longitude.toFixed(4)}°E</span>
          <span>•</span>
          <span>Uploaded at {observation.uploadedAt}</span>
        </div>
      </div>

      {/* Ground Evidence Attribution Badge */}
      <div className="bg-sky-50 border border-sky-200 rounded-lg p-2.5 flex items-center gap-2 text-sky-900">
        <CheckCircle2 className="w-4 h-4 text-sky-600 shrink-0" />
        <span className="text-[11px] font-semibold">
          User-Submitted Ground Evidence (Simulation)
        </span>
      </div>

      {/* Real Image Preview & Enlarge Trigger */}
      {observation.image && (
        <div className="bg-white border border-slate-200 rounded-xl p-2.5 shadow-2xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5 font-mono">
            Photographic Particulate Evidence
          </span>
          <div
            onClick={() => setIsImageModalOpen(true)}
            className="relative rounded-lg overflow-hidden border border-slate-200 bg-slate-100 group cursor-pointer aspect-video"
            title="Click to view high-resolution photo"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={observation.image}
              alt={`Evidence at ${observation.locationName}`}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
            <div className="absolute inset-0 bg-slate-900/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1.5 text-white text-xs font-semibold backdrop-blur-xs">
              <ZoomIn className="w-4 h-4" />
              <span>Click to Enlarge</span>
            </div>
          </div>
        </div>
      )}

      {/* Citizen Description Note */}
      {observation.description && (
        <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1 font-mono">
            Citizen Field Note
          </span>
          <blockquote className="text-slate-700 italic border-l-2 border-sky-500 pl-2.5 py-0.5 text-[11px] leading-relaxed">
            &ldquo;{observation.description}&rdquo;
          </blockquote>
        </div>
      )}

      {/* Measured / Estimated PM2.5 at Location */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs flex items-center justify-between">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block font-mono">
            Estimated PM2.5 at Location
          </span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-xl font-bold font-mono text-slate-900">
              {observation.pm25AtLocation}
            </span>
            <span className="text-xs text-slate-500">µg/m³</span>
          </div>
        </div>
        <RiskBadge level={riskTier} size="md" />
      </div>

      {/* Correlated Event Relationship Link */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5 font-mono">
          Correlated Incident Telemetry
        </span>
        {observation.relatedEventId ? (
          <Link
            href={`/dashboard/event?id=${observation.relatedEventId}`}
            className="inline-flex items-center justify-between w-full p-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-800 font-semibold transition-colors group"
          >
            <div className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-[#0a2540]" />
              <span>Correlated Incident Dossier ({observation.relatedEventId})</span>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-[#0a2540] group-hover:translate-x-0.5 transition-transform" />
          </Link>
        ) : (
          <div className="text-[11px] text-slate-500 bg-slate-50 p-2.5 rounded-lg border border-slate-200 font-medium">
            Model relationship: <strong>Not established</strong>
          </div>
        )}
      </div>

      {/* Step 12: Citizen Ground Evidence & Cross-Reference */}
      <AIModelPanel entityType="OBSERVATION" observation={observation} isCompact={true} />

      {/* Full-Screen Image Lightbox Modal */}
      {isImageModalOpen &&
        observation.image &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            className="fixed inset-0 z-[1300] bg-slate-950/85 backdrop-blur-sm flex flex-col items-center justify-center p-4"
            onClick={() => setIsImageModalOpen(false)}
          >
            <div
              className="relative max-w-2xl w-full bg-white rounded-2xl overflow-hidden shadow-2xl border border-slate-700/40"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between p-3.5 border-b border-slate-200 bg-slate-50">
                <div>
                  <h4 className="font-bold text-xs uppercase tracking-wide text-slate-900">
                    Citizen Particulate Evidence
                  </h4>
                  <p className="text-[11px] text-slate-500 font-mono">
                    {observation.locationName} • {observation.uploadedAt}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsImageModalOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="bg-black flex items-center justify-center max-h-[70vh]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={observation.image}
                  alt={observation.locationName}
                  className="max-h-[70vh] w-auto object-contain"
                />
              </div>

              {observation.description && (
                <div className="p-3 bg-white border-t border-slate-100 text-xs text-slate-700 italic">
                  &ldquo;{observation.description}&rdquo;
                </div>
              )}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
};

// -------------------------------------------------------------------------
// 3. EMISSION HOTSPOT DETAIL VIEW
// -------------------------------------------------------------------------
const HotspotDetailView: React.FC<{
  hotspot: EmissionHotspot;
  onClose: () => void;
}> = ({ hotspot, onClose }) => {
  const confidencePct = Math.round(hotspot.confidence * 100);

  return (
    <div className="space-y-4 text-xs">
      {/* Header */}
      <div className="bg-purple-50/70 border border-purple-200 rounded-xl p-3">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-purple-700 text-white">
            <Wind className="w-3 h-3" />
            <span>Emission Hotspot</span>
          </span>
          <span className="font-mono text-[10px] text-purple-800 bg-white px-1.5 py-0.5 rounded border border-purple-200">
            {hotspot.id}
          </span>
        </div>

        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <MapPin className="w-4 h-4 text-purple-700 shrink-0" />
          <span>{hotspot.locationName}</span>
        </h3>

        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 font-mono">
          <span>{hotspot.latitude.toFixed(4)}°N, {hotspot.longitude.toFixed(4)}°E</span>
          <span>•</span>
          <span>Detected at {hotspot.detectionTime}</span>
        </div>
      </div>

      {/* Simulation Notice */}
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-2.5 text-[11px] text-purple-900 font-medium">
        Synthetic Plume Demonstration Data (Simulation)
      </div>

      {/* Severity & Estimated PM2.5 Impact */}
      <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-2xs">
        <div className="flex items-start justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-0.5 font-mono">
              Estimated PM2.5 Contribution
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-slate-900 font-mono">
                {hotspot.estimatedPm25}
              </span>
              <span className="text-xs text-slate-500 font-medium">µg/m³</span>
            </div>
          </div>
          <RiskBadge level={hotspot.severity} size="md" />
        </div>

        <div className="mt-3 pt-2.5 border-t border-slate-100 grid grid-cols-2 gap-2 text-[11px]">
          <div>
            <span className="text-[10px] font-mono text-slate-400 block uppercase">Detection Confidence</span>
            <span className="font-bold text-slate-800 font-mono">{confidencePct}%</span>
          </div>
          <div>
            <span className="text-[10px] font-mono text-slate-400 block uppercase">Plume Status</span>
            <span className={`font-bold ${hotspot.isActiveRecent ? 'text-purple-700' : 'text-slate-600'}`}>
              {hotspot.isActiveRecent ? 'Active Plume' : 'Historical'}
            </span>
          </div>
        </div>
      </div>

      {/* Step 12: Dedicated AI & Screening Model Dossier Panel */}
      <AIModelPanel entityType="HOTSPOT" hotspot={hotspot} isCompact={true} />
    </div>
  );
};

// -------------------------------------------------------------------------
// 4. FIRE DETECTION DETAIL VIEW
// -------------------------------------------------------------------------
const FireDetailView: React.FC<{
  fire: FireDetection;
  onClose: () => void;
}> = ({ fire, onClose }) => {
  return (
    <div className="space-y-4 text-xs">
      {/* Header */}
      <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-3">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-amber-700 text-white">
            <Flame className="w-3 h-3" />
            <span>Fire Detection</span>
          </span>
          <span className="font-mono text-[10px] text-amber-900 bg-white px-1.5 py-0.5 rounded border border-amber-200">
            {fire.id}
          </span>
        </div>

        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <MapPin className="w-4 h-4 text-amber-700 shrink-0" />
          <span>{fire.locationName}</span>
        </h3>

        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 font-mono">
          <span>{fire.latitude.toFixed(4)}°N, {fire.longitude.toFixed(4)}°E</span>
          <span>•</span>
          <span>Detected at {fire.detectionTime}</span>
        </div>
      </div>

      {/* Simulation Notice */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-[11px] text-amber-900 font-medium">
        Satellite Thermal Simulation (Demonstration Feed)
      </div>

      {/* Fire Status & Intensity */}
      <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-2xs">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block font-mono">
              Operational Status
            </span>
            <span className={`inline-flex items-center gap-1 font-bold text-xs mt-0.5 ${
              fire.status === 'ACTIVE' ? 'text-amber-700' : 'text-slate-600'
            }`}>
              <span className={`w-2 h-2 rounded-full ${fire.status === 'ACTIVE' ? 'bg-amber-500 animate-ping' : 'bg-slate-400'}`} />
              <span>{fire.status === 'ACTIVE' ? 'Active Thermal Anomaly' : 'Historical Burn'}</span>
            </span>
          </div>

          <span className="font-bold text-[11px] px-2 py-1 rounded bg-amber-100 text-amber-900 border border-amber-300 uppercase font-mono">
            {fire.intensity} Intensity
          </span>
        </div>

        {/* Existing attributes: sizeHectares, pm25Contribution */}
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          {fire.sizeHectares !== undefined && (
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-400 block font-mono uppercase">Burn Area</span>
              <span className="font-bold text-slate-800 font-mono">{fire.sizeHectares} Hectares</span>
            </div>
          )}

          {fire.pm25Contribution && (
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-400 block font-mono uppercase">PM2.5 Impact</span>
              <span className="font-bold text-slate-800 font-mono">{fire.pm25Contribution}</span>
            </div>
          )}
        </div>
      </div>

      {/* Satellite Evidence & Pollution Correlation */}
      {fire.satelliteEvidence && (
        <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1 font-mono">
            Satellite Telemetry Verification
          </span>
          <p className="text-slate-700 text-[11px]">{fire.satelliteEvidence}</p>
        </div>
      )}

      {fire.pollutionRelationship && (
        <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1 font-mono">
            Downwind Regional Exposure
          </span>
          <p className="text-slate-700 text-[11px]">{fire.pollutionRelationship}</p>
        </div>
      )}

      {/* Step 12: Thermal Detection Telemetry Panel */}
      <AIModelPanel entityType="FIRE" fire={fire} isCompact={true} />
    </div>
  );
};

// -------------------------------------------------------------------------
// 5. PM2.5 RISK ZONE DETAIL VIEW
// -------------------------------------------------------------------------
const RiskZoneDetailView: React.FC<{
  zone: RiskZone;
  onClose: () => void;
}> = ({ zone, onClose }) => {
  return (
    <div className="space-y-4 text-xs">
      {/* Header */}
      <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-emerald-800 text-white">
            <Layers className="w-3 h-3" />
            <span>PM2.5 Risk Zone</span>
          </span>
          <span className="font-mono text-[10px] text-emerald-900 bg-white px-1.5 py-0.5 rounded border border-emerald-200">
            {zone.id}
          </span>
        </div>

        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <MapPin className="w-4 h-4 text-emerald-700 shrink-0" />
          <span>{zone.name}</span>
        </h3>

        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 font-mono">
          <span>Centroid: {zone.center[0].toFixed(4)}°N, {zone.center[1].toFixed(4)}°E</span>
          <span>•</span>
          <span>{zone.coordinates.length} Boundary Vertices</span>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2.5 text-[11px] text-emerald-900 font-medium">
        {zone.simulation_disclaimer || 'Prototype simulation data — not live PM2.5 prediction output'}
      </div>

      {/* Predicted PM2.5 & Risk Level */}
      <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-2xs">
        <div className="flex items-start justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-0.5 font-mono">
              Model Predicted PM2.5
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-slate-900 font-mono">
                {zone.predicted_pm25}
              </span>
              <span className="text-xs text-slate-500 font-medium">µg/m³</span>
            </div>
          </div>
          <RiskBadge level={zone.level} size="md" />
        </div>

        <div className="mt-3 pt-2.5 border-t border-slate-100 grid grid-cols-2 gap-2 text-[11px]">
          <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-mono uppercase">Forecast Horizon</span>
            <span className="font-bold text-slate-800 font-mono">{zone.forecast_horizon}</span>
          </div>

          <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-mono uppercase">Confidence</span>
            <span className="font-bold text-slate-800 font-mono">{zone.prediction_confidence}%</span>
          </div>
        </div>

        {zone.forecast_uncertainty && (
          <div className="mt-2 p-2 bg-slate-50 rounded-lg border border-slate-200 text-[11px]">
            <span className="text-[10px] text-slate-400 block font-mono uppercase">Uncertainty Band</span>
            <span className="font-semibold text-slate-800 font-mono">{zone.forecast_uncertainty}</span>
          </div>
        )}
      </div>

      {/* Step 12: Dedicated AI & Dispersion Model Dossier Panel */}
      <AIModelPanel entityType="RISK_ZONE" riskZone={zone} isCompact={true} />
    </div>
  );
};

// -------------------------------------------------------------------------
// MAIN EXPORTED MapInfoPanel COMPONENT
// -------------------------------------------------------------------------
export const MapInfoPanel: React.FC<MapInfoPanelProps> = ({
  selectedEventId,
  onClose,
  events,
  observations,
  hotspots,
  fires,
  riskZones,
  className = '',
}) => {
  // Resolve entity data by matching selectedEventId
  const selectedEvent = useMemo(() => {
    if (!selectedEventId) return null;
    return events.find((e) => e.event_id === selectedEventId) || null;
  }, [selectedEventId, events]);

  const selectedObs = useMemo(() => {
    if (!selectedEventId) return null;
    const isSim = getIsSimulationMode();
    const list = observations || (isSim ? MOCK_CITIZEN_OBSERVATIONS : []);
    return list.find((o) => o.id === selectedEventId) || null;
  }, [selectedEventId, observations]);

  const selectedHotspot = useMemo(() => {
    if (!selectedEventId) return null;
    const isSim = getIsSimulationMode();
    const list = hotspots || (isSim ? MOCK_EMISSION_HOTSPOTS : []);
    return list.find((h) => h.id === selectedEventId) || null;
  }, [selectedEventId, hotspots]);

  const selectedFire = useMemo(() => {
    if (!selectedEventId) return null;
    const isSim = getIsSimulationMode();
    const list = fires || (isSim ? MOCK_FIRE_DETECTIONS : []);
    return list.find((f) => f.id === selectedEventId) || null;
  }, [selectedEventId, fires]);

  const selectedZone = useMemo(() => {
    if (!selectedEventId) return null;
    const isSim = getIsSimulationMode();
    const list = riskZones || (isSim ? MOCK_RISK_ZONES : []);
    return list.find((z) => z.id === selectedEventId) || null;
  }, [selectedEventId, riskZones]);

  // If no entity is selected, render nothing
  if (!selectedEventId) return null;

  const entityTitle =
    selectedEvent?.location.city ||
    selectedObs?.locationName ||
    selectedHotspot?.locationName ||
    selectedFire?.locationName ||
    selectedZone?.name ||
    'Selected Map Entity';

  return (
    <>
      {/* -------------------------------------------------------------
          DESKTOP SLIDE-OUT DRAWER (>=768px: md:flex)
          Floating card on the right-hand side, occupies ~25-30% viewport
          ------------------------------------------------------------- */}
      <div
        className={`hidden md:flex flex-col absolute top-14 sm:top-16 right-3.5 sm:right-4 bottom-4 w-88 lg:w-96 bg-white/95 backdrop-blur-md border border-slate-300/90 rounded-2xl shadow-2xl z-[900] overflow-hidden select-none animate-in fade-in slide-in-from-right-3 duration-200 ${className}`}
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        onDoubleClick={(e) => e.stopPropagation()}
        onTouchStart={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-white/80">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-[#0a2540] text-white flex items-center justify-center shrink-0 shadow-xs">
              <Activity className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h2 className="font-bold text-xs uppercase tracking-wider text-[#0a2540] truncate">
                Location & Evidence Dossier
              </h2>
              <p className="text-[10px] text-slate-500 truncate font-mono">
                {entityTitle}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Close information panel"
            title="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto p-4 overscroll-contain">
          {selectedEvent && <EventDetailView event={selectedEvent} onClose={onClose} />}
          {selectedObs && <ObservationDetailView observation={selectedObs} onClose={onClose} />}
          {selectedHotspot && <HotspotDetailView hotspot={selectedHotspot} onClose={onClose} />}
          {selectedFire && <FireDetailView fire={selectedFire} onClose={onClose} />}
          {selectedZone && <RiskZoneDetailView zone={selectedZone} onClose={onClose} />}
        </div>
      </div>

      {/* -------------------------------------------------------------
          MOBILE BOTTOM-SHEET DRAWER (<768px: md:hidden)
          Swipeable/dismissible sheet with drag handle, max 65vh height
          ------------------------------------------------------------- */}
      <div
        className={`md:hidden fixed inset-x-0 bottom-0 z-[1100] max-h-[65vh] bg-white rounded-t-2xl shadow-2xl border-t border-slate-200 flex flex-col overflow-hidden select-none animate-in fade-in slide-in-from-bottom-4 duration-200 ${className}`}
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        onDoubleClick={(e) => e.stopPropagation()}
        onTouchStart={(e) => e.stopPropagation()}
      >
        {/* Drag Handle */}
        <div className="pt-2.5 pb-1 flex justify-center shrink-0">
          <div className="w-10 h-1 bg-slate-300 rounded-full" />
        </div>

        {/* Mobile Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <Activity className="w-4 h-4 text-[#0a2540]" />
            <h2 className="font-bold text-xs uppercase tracking-wider text-[#0a2540] truncate">
              {entityTitle}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 -mr-1 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 active:bg-slate-200 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer"
            aria-label="Close information panel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto px-4 py-3.5 overscroll-contain">
          {selectedEvent && <EventDetailView event={selectedEvent} onClose={onClose} />}
          {selectedObs && <ObservationDetailView observation={selectedObs} onClose={onClose} />}
          {selectedHotspot && <HotspotDetailView hotspot={selectedHotspot} onClose={onClose} />}
          {selectedFire && <FireDetailView fire={selectedFire} onClose={onClose} />}
          {selectedZone && <RiskZoneDetailView zone={selectedZone} onClose={onClose} />}
        </div>
      </div>
    </>
  );
};

export default MapInfoPanel;

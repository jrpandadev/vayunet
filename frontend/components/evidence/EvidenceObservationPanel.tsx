'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { createPortal } from 'react-dom';
import {
  FileText,
  Radio,
  Orbit,
  Wind,
  Users,
  Camera,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Flame,
  Activity,
  MapPin,
  Clock,
  ZoomIn,
  X,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  Eye,
  Info,
  ChevronRight,
} from 'lucide-react';
import {
  PollutionEvent,
  CitizenEvidence,
  SensorEvidence,
  SatelliteEvidence,
  WeatherEvidence,
} from '@/lib/types';
import { RiskZone } from '@/lib/riskZones';
import { EmissionHotspot } from '@/lib/hotspots';
import { FireDetection } from '@/lib/fires';
import { getIsSimulationMode } from '@/lib/api';
import { CitizenObservation, MOCK_CITIZEN_OBSERVATIONS } from '@/lib/observations';
import ProvenanceBadge from '@/components/ui/ProvenanceBadge';
import { getEvidenceUrl } from '@/lib/api';

export interface EvidenceObservationPanelProps {
  entityType: 'EVENT' | 'RISK_ZONE' | 'HOTSPOT' | 'FIRE' | 'OBSERVATION';
  event?: PollutionEvent | null;
  riskZone?: RiskZone | null;
  hotspot?: EmissionHotspot | null;
  fire?: FireDetection | null;
  observation?: CitizenObservation | null;
  isCompact?: boolean;
  className?: string;
}

export const EvidenceObservationPanel: React.FC<EvidenceObservationPanelProps> = ({
  entityType,
  event,
  riskZone,
  hotspot,
  fire,
  observation,
  isCompact = false,
  className = '',
}) => {
  const [activeLightbox, setActiveLightbox] = useState<{
    url: string;
    caption: string;
    meta: string;
  } | null>(null);

  const citizen = event?.evidence?.citizen;
  const [resolvedPhotoUrl, setResolvedPhotoUrl] = useState<string | null>(citizen?.photo_url || null);

  React.useEffect(() => {
    if (citizen && !citizen.photo_url && citizen.supabase_path) {
      getEvidenceUrl(citizen.supabase_path).then(url => {
        if (url) setResolvedPhotoUrl(url);
      });
    } else if (citizen?.photo_url) {
      setResolvedPhotoUrl(citizen.photo_url);
    }
  }, [citizen]);

  // For events, find any linked citizen observations from MOCK_CITIZEN_OBSERVATIONS if in simulation
  const linkedObservations = useMemo<CitizenObservation[]>(() => {
    if (entityType !== 'EVENT' || !event) return [];
    if (!getIsSimulationMode()) return [];
    return MOCK_CITIZEN_OBSERVATIONS.filter((o) => o.relatedEventId === event.event_id);
  }, [entityType, event]);

  // ---------------------------------------------------------------------------
  // CASE 1: POLLUTION EVENT (evt_*)
  // Full 4-modality evidence streams + Corroboration Matrix + Linked Citizen Reports
  // ---------------------------------------------------------------------------
  if (entityType === 'EVENT' && event) {
    const supporting = event.detection.supporting_evidence || [];
    const contradicting = event.detection.contradicting_evidence || [];

    const isSensorSupporting = supporting.some((s) => s.includes('sensor'));
    const isSensorContradicting = contradicting.some((c) => c.includes('sensor'));

    const isSatelliteSupporting = supporting.some((s) => s.includes('satellite'));
    const isSatelliteContradicting = contradicting.some((c) => c.includes('satellite'));

    const isWeatherSupporting = supporting.some((s) => s.includes('weather'));
    const isWeatherContradicting = contradicting.some((c) => c.includes('weather'));

    const isCitizenSupporting = supporting.some((s) => s.includes('citizen'));
    const isCitizenContradicting = contradicting.some((c) => c.includes('citizen'));

    const sensor = event.evidence?.sensor;
    const satellite = event.evidence?.satellite;
    const weather = event.evidence?.weather;
    const citizen = event.evidence?.citizen;

    return (
      <div
        className={`rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden text-xs ${className}`}
      >
        {/* Panel Header */}
        <div className="bg-slate-900 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-sky-500/20 text-sky-400 shrink-0">
              <FileText className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate flex items-center gap-1.5">
                <span>Multi-Source Evidence Dossier</span>
              </h4>
              <span className="text-[10px] text-slate-300 font-mono block truncate">
                CPCB Ground Sensors • Sentinel-5P • Open-Meteo • Citizen Field Reports
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700 shrink-0">
            {event.event_id}
          </span>
        </div>

        <div className="p-3.5 space-y-3.5">
          {/* Section 1: Corroboration Matrix */}
          <div className="bg-slate-50 border border-slate-200/90 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-200/80">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700 font-mono flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-[#0a2540]" />
                <span>Evidence Cross-Validation Matrix</span>
              </span>
              <span className="text-[10px] font-mono text-slate-600">
                Score: <strong>{supporting.length} Supporting</strong> / <strong>{contradicting.length} Contradicting</strong>
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
              {/* Supporting Modalities */}
              <div className="bg-emerald-50/70 border border-emerald-200/90 rounded-md p-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1 mb-1 font-mono">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  <span>Supporting Corroborators ({supporting.length})</span>
                </span>
                <div className="flex flex-wrap gap-1">
                  {supporting.length > 0 ? (
                    supporting.map((item, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-mono font-semibold px-1.5 py-0.2 rounded bg-white text-emerald-900 border border-emerald-300"
                      >
                        ✓ {item}
                      </span>
                    ))
                  ) : (
                    <span className="text-[10px] text-slate-400 italic">None registered</span>
                  )}
                </div>
              </div>

              {/* Contradicting Modalities */}
              <div className="bg-amber-50/70 border border-amber-200/90 rounded-md p-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1 mb-1 font-mono">
                  <AlertTriangle className="w-3 h-3 text-amber-600" />
                  <span>Contradicting / Inconclusive ({contradicting.length})</span>
                </span>
                <div className="flex flex-wrap gap-1">
                  {contradicting.length > 0 ? (
                    contradicting.map((item, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-mono font-semibold px-1.5 py-0.2 rounded bg-white text-amber-900 border border-amber-300"
                      >
                        ⚠ {item}
                      </span>
                    ))
                  ) : (
                    <span className="text-[10px] text-slate-500 italic">Zero contradicting indicators</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Four Individual Evidence Modalities */}
          <div className="space-y-2.5">
            {/* 1. Ground Sensor Telemetry Card */}
            {sensor && (
              <div className="border border-slate-200 rounded-lg p-3 bg-white shadow-2xs">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1 rounded bg-slate-100 text-slate-800">
                      <Radio className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <h5 className="font-bold text-xs uppercase tracking-wider text-slate-900">
                        1. Ground CAAQMS Sensor
                      </h5>
                      <ProvenanceBadge
                        source={sensor.source || 'CPCB'}
                        qualityOrFreshness={sensor.quality}
                        className="mt-0.5"
                      />
                    </div>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border ${
                      isSensorSupporting
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : isSensorContradicting
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-slate-50 text-slate-600 border-slate-200'
                    }`}
                  >
                    {isSensorSupporting
                      ? '✓ Supporting'
                      : isSensorContradicting
                      ? '⚠ Contradicting'
                      : 'Contextual'}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] mb-2">
                  <div className="p-2 rounded bg-slate-50 border border-slate-200/80">
                    <span className="text-[9px] font-mono uppercase text-slate-500 block">Observed PM2.5</span>
                    <strong className="text-slate-900 font-mono text-xs">{sensor.pm25} µg/m³</strong>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-slate-200/80">
                    <span className="text-[9px] font-mono uppercase text-slate-500 block">Observed PM10</span>
                    <strong className="text-slate-700 font-mono text-xs">{sensor.pm10} µg/m³</strong>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-slate-200/80 col-span-2 sm:col-span-1">
                    <span className="text-[9px] font-mono uppercase text-slate-500 block">Anomaly Score</span>
                    <strong className="text-amber-800 font-mono text-xs">{sensor.anomaly_score != null ? sensor.anomaly_score.toFixed(2) : 'N/A'}</strong>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1.5 border-t border-slate-100">
                  <span>Station: <strong>{sensor.station_id}</strong></span>
                  <span>Ingest Quality: <strong>{sensor.quality || 'Verified'}</strong></span>
                </div>
              </div>
            )}

            {/* 2. Satellite Spectroscopy Card */}
            {satellite && (
              <div className="border border-slate-200 rounded-lg p-3 bg-white shadow-2xs">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1 rounded bg-sky-50 text-sky-700">
                      <Orbit className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <h5 className="font-bold text-xs uppercase tracking-wider text-slate-900">
                        2. Orbital Satellite Ingest
                      </h5>
                      <ProvenanceBadge
                        source={satellite.source || 'Sentinel-5P'}
                        qualityOrFreshness={satellite.freshness}
                        className="mt-0.5"
                      />
                    </div>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border ${
                      isSatelliteSupporting
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : isSatelliteContradicting
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-slate-50 text-slate-600 border-slate-200'
                    }`}
                  >
                    {isSatelliteSupporting
                      ? '✓ Supporting'
                      : isSatelliteContradicting
                      ? '⚠ Contradicting'
                      : 'Contextual'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] mb-2">
                  <div className="p-2 rounded bg-slate-50 border border-slate-200/80">
                    <span className="text-[9px] font-mono uppercase text-slate-500 block">Tropospheric NO₂</span>
                    <strong className="text-slate-900 font-mono text-xs">{satellite.no2_index.toFixed(1)} mol/m²</strong>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-slate-200/80">
                    <span className="text-[9px] font-mono uppercase text-slate-500 block">Aerosol Index (AI)</span>
                    <strong className="text-slate-900 font-mono text-xs">{satellite.aerosol_index.toFixed(2)}</strong>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1.5 border-t border-slate-100">
                  <span>Spectral Instrument: <strong>UV-VIS/TROPOMI</strong></span>
                  <span>Spatial Res: <strong>5.5 km</strong></span>
                </div>
              </div>
            )}

            {/* 3. Synoptic Meteorology Card */}
            {weather && (
              <div className="border border-slate-200 rounded-lg p-3 bg-white shadow-2xs">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1 rounded bg-cyan-50 text-cyan-800">
                      <Wind className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <h5 className="font-bold text-xs uppercase tracking-wider text-slate-900">
                        3. Synoptic Meteorology
                      </h5>
                      <ProvenanceBadge
                        source={weather.source || 'Weather'}
                        className="mt-0.5"
                      />
                    </div>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border ${
                      isWeatherSupporting
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : isWeatherContradicting
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-slate-50 text-slate-600 border-slate-200'
                    }`}
                  >
                    {isWeatherSupporting
                      ? '✓ Supporting'
                      : isWeatherContradicting
                      ? '⚠ Contradicting'
                      : 'Contextual'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] mb-2">
                  <div className="p-2 rounded bg-slate-50 border border-slate-200/80">
                    <span className="text-[9px] font-mono uppercase text-slate-500 block">Surface Wind Velocity</span>
                    <strong className="text-slate-900 font-mono text-xs">{weather.wind_speed_kmh} km/h</strong>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-slate-200/80">
                    <span className="text-[9px] font-mono uppercase text-slate-500 block">Relative Humidity</span>
                    <strong className="text-slate-900 font-mono text-xs">{weather.humidity_percent}%</strong>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1.5 border-t border-slate-100">
                  <span>
                    Atmospheric Dispersion:{' '}
                    <strong className={weather.wind_speed_kmh != null ? (weather.wind_speed_kmh < 5 ? 'text-rose-700' : 'text-emerald-700') : 'text-slate-700'}>
                      {weather.wind_speed_kmh != null ? (weather.wind_speed_kmh < 5 ? 'Stagnant (Dispersion Barrier)' : 'Active Ventilation') : 'Unknown'}
                    </strong>
                  </span>
                  <span>Model: <strong>Open-Meteo</strong></span>
                </div>
              </div>
            )}

            {/* 4. Citizen Crowdsourced Evidence Card with Photo Inspection */}
            {citizen && (
              <div className="border border-slate-200 rounded-lg p-3 bg-white shadow-2xs">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1 rounded bg-slate-100 text-slate-800">
                      <Users className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <h5 className="font-bold text-xs uppercase tracking-wider text-slate-900">
                        4. Citizen Photographic Report
                      </h5>
                      <ProvenanceBadge
                        source={citizen.source || 'Citizen'}
                        qualityOrFreshness={citizen.freshness}
                        className="mt-0.5"
                      />
                    </div>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border ${
                      isCitizenSupporting
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : isCitizenContradicting
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-slate-50 text-slate-600 border-slate-200'
                    }`}
                  >
                    {isCitizenSupporting
                      ? '✓ Supporting'
                      : isCitizenContradicting
                      ? '⚠ Contradicting'
                      : 'Contextual'}
                  </span>
                </div>

                {/* Narrative & Visual Classifier Output */}
                <div className="bg-slate-50 rounded-lg p-2.5 border border-slate-200/80 mb-2.5 text-[11px]">
                  <p className="text-slate-800 italic mb-1.5 leading-relaxed">
                    &ldquo;{citizen.gemini_output.description}&rdquo;
                  </p>
                  <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-500">
                    <span>
                      Visual Class: <strong className="text-slate-900 capitalize">{citizen.gemini_output.event_type}</strong>
                    </span>
                    <span>•</span>
                    <span>
                      Severity: <strong className="text-slate-900 capitalize">{citizen.gemini_output.severity}</strong>
                    </span>
                    <span>•</span>
                    <span>
                      Classifier Confidence: <strong className="text-slate-900">{Math.round(citizen.gemini_output.confidence * 100)}%</strong>
                    </span>
                  </div>
                </div>

                {/* Actual Citizen Photo Thumbnail with Lightbox Trigger */}
                {resolvedPhotoUrl ? (
                  <div className="flex items-center gap-3 p-2 rounded-lg bg-sky-50/50 border border-sky-200/80">
                    <div
                      onClick={() =>
                        setActiveLightbox({
                          url: resolvedPhotoUrl!,
                          caption: citizen.gemini_output.description,
                          meta: `${event.location.city} • Citizen Evidence (${citizen.gemini_output.event_type})`,
                        })
                      }
                      className="relative w-24 h-16 rounded overflow-hidden border border-sky-300 bg-slate-100 group cursor-pointer shrink-0 shadow-2xs"
                      title="Click to inspect citizen photo evidence"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={resolvedPhotoUrl}
                        alt={`Citizen evidence for ${event.event_id}`}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                      <div className="absolute inset-0 bg-slate-900/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white">
                        <ZoomIn className="w-4 h-4" />
                      </div>
                    </div>

                    <div className="min-w-0 flex-1">
                      <span className="font-bold text-slate-900 block text-[11px] mb-0.5">
                        Field Photograph Evidence
                      </span>
                      <p className="text-[10px] text-slate-500 truncate mb-1">
                        Captured in {event.location.city} • Freshness: {citizen.freshness}
                      </p>
                      <button
                        type="button"
                        onClick={() =>
                          setActiveLightbox({
                            url: resolvedPhotoUrl!,
                            caption: citizen.gemini_output.description,
                            meta: `${event.location.city} • Citizen Evidence (${citizen.gemini_output.event_type})`,
                          })
                        }
                        className="inline-flex items-center gap-1 text-[10px] font-bold text-sky-700 hover:text-sky-900 hover:underline cursor-pointer"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Inspect High-Resolution Photo</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-2 rounded bg-slate-50 border border-slate-200 text-[10px] text-slate-400 italic">
                    No photographic file attached to this citizen report.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Section 3: Linked Field Observations from Step 5 Dataset */}
          {linkedObservations.length > 0 && (
            <div className="bg-slate-50 border border-slate-200/90 rounded-lg p-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700 font-mono block mb-2">
                Cross-Referenced Field Observations ({linkedObservations.length})
              </span>

              <div className="space-y-2">
                {linkedObservations.map((obs) => (
                  <div
                    key={obs.id}
                    className="p-2 rounded bg-white border border-slate-200 flex items-center justify-between gap-2"
                  >
                    {obs.image && (
                      <div
                        onClick={() =>
                          setActiveLightbox({
                            url: obs.image!,
                            caption: obs.description || obs.locationName,
                            meta: `${obs.locationName} • Uploaded at ${obs.uploadedAt}`,
                          })
                        }
                        className="w-12 h-10 rounded overflow-hidden border border-slate-300 bg-slate-100 shrink-0 cursor-pointer group relative"
                        title="Click to inspect photo"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={obs.image}
                          alt={obs.locationName}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        />
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <span className="font-bold text-slate-900 block truncate text-[11px]">
                        {obs.locationName}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        {obs.pm25AtLocation} µg/m³ PM2.5 • {obs.uploadedAt}
                      </span>
                    </div>
                    {obs.image && (
                      <button
                        type="button"
                        onClick={() =>
                          setActiveLightbox({
                            url: obs.image!,
                            caption: obs.description || obs.locationName,
                            meta: `${obs.locationName} • Uploaded at ${obs.uploadedAt}`,
                          })
                        }
                        className="text-[10px] text-sky-700 hover:text-sky-900 p-1 rounded hover:bg-sky-50 font-semibold shrink-0 cursor-pointer"
                        title="View photo"
                      >
                        Inspect
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Full-Screen Lightbox Portal */}
        {activeLightbox &&
          typeof document !== 'undefined' &&
          createPortal(
            <div
              className="fixed inset-0 z-[1400] bg-slate-950/85 backdrop-blur-sm flex flex-col items-center justify-center p-4"
              onClick={() => setActiveLightbox(null)}
            >
              <div
                className="relative max-w-2xl w-full bg-white rounded-2xl overflow-hidden shadow-2xl border border-slate-700/40 animate-in fade-in zoom-in-95 duration-150"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between p-3.5 border-b border-slate-200 bg-slate-50">
                  <div>
                    <h4 className="font-bold text-xs uppercase tracking-wide text-slate-900">
                      Citizen Particulate Evidence Inspection
                    </h4>
                    {activeLightbox.meta && (
                      <p className="text-[11px] text-slate-500 font-mono">{activeLightbox.meta}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setActiveLightbox(null)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
                    aria-label="Close photo lightbox"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="bg-black flex items-center justify-center max-h-[70vh]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={activeLightbox.url}
                    alt={activeLightbox.caption}
                    className="max-h-[70vh] w-auto object-contain"
                  />
                </div>

                {activeLightbox.caption && (
                  <div className="p-3 bg-white border-t border-slate-100 text-xs text-slate-700 italic">
                    &ldquo;{activeLightbox.caption}&rdquo;
                  </div>
                )}
              </div>
            </div>,
            document.body
          )}
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // CASE 2: PM2.5 RISK ZONE (zone_*)
  // Spatial boundary vertices, centroid geometry, and dispersion modeling evidence
  // ---------------------------------------------------------------------------
  if (entityType === 'RISK_ZONE' && riskZone) {
    return (
      <div className={`rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden text-xs ${className}`}>
        <div className="bg-emerald-950 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-emerald-500/20 text-emerald-400 shrink-0">
              <Layers className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate">
                Dispersion Corridor Geometry & Modeling Evidence
              </h4>
              <span className="text-[10px] text-emerald-300 font-mono block truncate">
                Spatial Boundary Synthesis • {riskZone.coordinates.length} Vertices
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-emerald-900 text-emerald-200 px-2 py-0.5 rounded border border-emerald-700 shrink-0">
            {riskZone.id}
          </span>
        </div>

        <div className="p-3.5 space-y-3">
          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] space-y-1.5 font-mono">
            <div className="flex items-center justify-between text-slate-700">
              <span className="text-slate-500">Centroid Coordinates:</span>
              <strong>{riskZone.center[0].toFixed(4)}°N, {riskZone.center[1].toFixed(4)}°E</strong>
            </div>
            <div className="flex items-center justify-between text-slate-700">
              <span className="text-slate-500">Polygon Perimeter Vertices:</span>
              <strong>{riskZone.coordinates.length} Coordinate Points</strong>
            </div>
            <div className="flex items-center justify-between text-slate-700">
              <span className="text-slate-500">Modeled Exposure Horizon:</span>
              <strong>{riskZone.forecast_horizon}</strong>
            </div>
          </div>

          <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-[10px] text-emerald-900 flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 text-emerald-700 shrink-0 mt-0.5" />
            <span>
              Regional atmospheric transport corridor. Boundary polygon is synthesized from synoptic wind streamlines and topographical basin boundaries; no solitary sensor station is co-located inside the zone polygon.
            </span>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // CASE 3: EMISSION HOTSPOT (hs_*)
  // Ground plume screening telemetry, detection timestamp, and source attribution
  // ---------------------------------------------------------------------------
  if (entityType === 'HOTSPOT' && hotspot) {
    return (
      <div className={`rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden text-xs ${className}`}>
        <div className="bg-purple-950 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-purple-500/20 text-purple-400 shrink-0">
              <Activity className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate">
                Hotspot Plume Telemetry Evidence
              </h4>
              <span className="text-[10px] text-purple-300 font-mono block truncate">
                Industrial Cluster Screening • Timestamp: {hotspot.detectionTime}
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-purple-900 text-purple-200 px-2 py-0.5 rounded border border-purple-700 shrink-0">
            {hotspot.id}
          </span>
        </div>

        <div className="p-3.5 space-y-2.5">
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="p-2 rounded bg-slate-50 border border-slate-200">
              <span className="text-[9px] font-mono text-slate-500 uppercase block">Estimated Loading</span>
              <strong className="font-mono text-slate-900">{hotspot.estimatedPm25} µg/m³</strong>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-slate-200">
              <span className="text-[9px] font-mono text-slate-500 uppercase block">Plume State</span>
              <strong className={hotspot.isActiveRecent ? 'text-purple-700' : 'text-slate-600'}>
                {hotspot.isActiveRecent ? 'Active Dispersion' : 'Historical Plume'}
              </strong>
            </div>
          </div>

          {hotspot.possibleSource && (
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px]">
              <span className="text-[9px] font-bold font-mono text-slate-500 uppercase block mb-0.5">
                Attribution Telemetry:
              </span>
              <p className="text-slate-800 font-medium">{hotspot.possibleSource}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // CASE 4: FIRE DETECTION (fire_*)
  // Satellite thermal anomaly telemetry, burn area, and downwind relationship
  // ---------------------------------------------------------------------------
  if (entityType === 'FIRE' && fire) {
    return (
      <div className={`rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden text-xs ${className}`}>
        <div className="bg-amber-950 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-amber-500/20 text-amber-400 shrink-0">
              <Flame className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate">
                Satellite Thermal Observation Evidence
              </h4>
              <span className="text-[10px] text-amber-300 font-mono block truncate">
                Orbital Thermal Radiance • Ingest Time: {fire.detectionTime}
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-amber-900 text-amber-200 px-2 py-0.5 rounded border border-amber-700 shrink-0">
            {fire.id}
          </span>
        </div>

        <div className="p-3.5 space-y-2.5">
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="p-2 rounded bg-slate-50 border border-slate-200">
              <span className="text-[9px] font-mono text-slate-500 uppercase block">Thermal Intensity</span>
              <strong className="text-amber-800 font-bold uppercase">{fire.intensity}</strong>
            </div>
            {fire.sizeHectares !== undefined && (
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-[9px] font-mono text-slate-500 uppercase block">Burn Footprint</span>
                <strong className="font-mono text-slate-900">{fire.sizeHectares} Hectares</strong>
              </div>
            )}
          </div>

          {fire.satelliteEvidence && (
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px]">
              <span className="text-[9px] font-bold font-mono text-slate-500 uppercase block mb-0.5">
                Satellite Verification:
              </span>
              <p className="text-slate-800">{fire.satelliteEvidence}</p>
            </div>
          )}

          {fire.pollutionRelationship && (
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px]">
              <span className="text-[9px] font-bold font-mono text-slate-500 uppercase block mb-0.5">
                Downwind Trajectory:
              </span>
              <p className="text-slate-800">{fire.pollutionRelationship}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // CASE 5: CITIZEN OBSERVATION (obs_*)
  // Ground photographic evidence with full-screen inspection & incident correlation
  // ---------------------------------------------------------------------------
  if (entityType === 'OBSERVATION' && observation) {
    return (
      <div className={`rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden text-xs ${className}`}>
        <div className="bg-sky-950 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-sky-500/20 text-sky-400 shrink-0">
              <Camera className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate">
                Citizen Photographic Evidence Dossier
              </h4>
              <span className="text-[10px] text-sky-300 font-mono block truncate">
                Field Submission • Uploaded: {observation.uploadedAt}
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-sky-900 text-sky-200 px-2 py-0.5 rounded border border-sky-700 shrink-0">
            {observation.id}
          </span>
        </div>

        <div className="p-3.5 space-y-3">
          {/* Field Measurement */}
          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-[11px]">
            <div>
              <span className="text-[9px] font-mono uppercase text-slate-500 block">Reported PM2.5 at Site</span>
              <strong className="text-slate-900 font-mono text-xs">{observation.pm25AtLocation} µg/m³</strong>
            </div>
            <div className="text-right">
              <span className="text-[9px] font-mono uppercase text-slate-500 block">Coordinates</span>
              <span className="font-mono text-slate-700 text-[10px]">
                {observation.latitude.toFixed(4)}°N, {observation.longitude.toFixed(4)}°E
              </span>
            </div>
          </div>

          {/* Citizen Description Narrative */}
          {observation.description && (
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px]">
              <span className="text-[9px] font-bold font-mono text-slate-500 uppercase block mb-0.5">
                Citizen Narrative Note:
              </span>
              <p className="text-slate-800 italic leading-relaxed">&ldquo;{observation.description}&rdquo;</p>
            </div>
          )}

          {/* Photo Preview & Lightbox Trigger */}
          {observation.image ? (
            <div className="p-2.5 rounded-lg bg-sky-50/60 border border-sky-200 space-y-2">
              <div
                onClick={() =>
                  setActiveLightbox({
                    url: observation.image!,
                    caption: observation.description || observation.locationName,
                    meta: `${observation.locationName} • Uploaded at ${observation.uploadedAt}`,
                  })
                }
                className="relative rounded-lg overflow-hidden border border-sky-300 bg-slate-100 group cursor-pointer aspect-video"
                title="Click to view full-resolution photo"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={observation.image}
                  alt={observation.locationName}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
                <div className="absolute inset-0 bg-slate-900/35 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1.5 text-white text-xs font-semibold backdrop-blur-xs">
                  <ZoomIn className="w-4 h-4" />
                  <span>Click to Inspect Full Photo</span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-600 pt-1">
                <span>Field Image Asset</span>
                <button
                  type="button"
                  onClick={() =>
                    setActiveLightbox({
                      url: observation.image!,
                      caption: observation.description || observation.locationName,
                      meta: `${observation.locationName} • Uploaded at ${observation.uploadedAt}`,
                    })
                  }
                  className="font-bold text-sky-700 hover:text-sky-900 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <Eye className="w-3 h-3" />
                  <span>Inspect High Resolution</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-[10px] text-slate-400 italic">
              Photographic preview unavailable for this submission.
            </div>
          )}

          {/* Correlated Event Link */}
          {observation.relatedEventId && (
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-[11px]">
              <div>
                <span className="text-[9px] font-mono text-slate-500 uppercase block">Correlated Telemetry</span>
                <span className="font-bold text-slate-900">Incident {observation.relatedEventId}</span>
              </div>
              <Link
                href={`/dashboard/event/${observation.relatedEventId}`}
                className="inline-flex items-center gap-1 text-[10px] font-bold text-sky-700 hover:text-sky-900 bg-sky-50 hover:bg-sky-100 px-2 py-1 rounded border border-sky-200 transition-colors"
              >
                <span>View Incident Dossier</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          )}
        </div>

        {/* Lightbox Modal */}
        {activeLightbox &&
          typeof document !== 'undefined' &&
          createPortal(
            <div
              className="fixed inset-0 z-[1400] bg-slate-950/85 backdrop-blur-sm flex flex-col items-center justify-center p-4"
              onClick={() => setActiveLightbox(null)}
            >
              <div
                className="relative max-w-2xl w-full bg-white rounded-2xl overflow-hidden shadow-2xl border border-slate-700/40 animate-in fade-in zoom-in-95 duration-150"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between p-3.5 border-b border-slate-200 bg-slate-50">
                  <div>
                    <h4 className="font-bold text-xs uppercase tracking-wide text-slate-900">
                      Citizen Particulate Evidence Inspection
                    </h4>
                    {activeLightbox.meta && (
                      <p className="text-[11px] text-slate-500 font-mono">{activeLightbox.meta}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setActiveLightbox(null)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
                    aria-label="Close photo lightbox"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="bg-black flex items-center justify-center max-h-[70vh]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={activeLightbox.url}
                    alt={activeLightbox.caption}
                    className="max-h-[70vh] w-auto object-contain"
                  />
                </div>

                {activeLightbox.caption && (
                  <div className="p-3 bg-white border-t border-slate-100 text-xs text-slate-700 italic">
                    &ldquo;{activeLightbox.caption}&rdquo;
                  </div>
                )}
              </div>
            </div>,
            document.body
          )}
      </div>
    );
  }

  return null;
};

export default EvidenceObservationPanel;

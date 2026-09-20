'use client';

import React from 'react';
import Link from 'next/link';
import {
  Bot,
  BrainCircuit,
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  Radio,
  Orbit,
  Wind,
  Users,
  CheckCircle2,
  HelpCircle,
  Sparkles,
  ArrowRight,
  ExternalLink,
  Layers,
  Flame,
  Camera,
  Activity,
  Info,
} from 'lucide-react';
import { PollutionEvent, RiskLevel, UncertaintyLevel } from '@/lib/types';
import { RiskZone } from '@/lib/riskZones';
import { EmissionHotspot } from '@/lib/hotspots';
import { FireDetection } from '@/lib/fires';
import { CitizenObservation } from '@/lib/observations';
import RiskBadge from '@/components/ui/RiskBadge';
import ProvenanceBadge from '@/components/ui/ProvenanceBadge';

export interface AIModelPanelProps {
  entityType: 'EVENT' | 'RISK_ZONE' | 'HOTSPOT' | 'FIRE' | 'OBSERVATION';
  event?: PollutionEvent | null;
  riskZone?: RiskZone | null;
  hotspot?: EmissionHotspot | null;
  fire?: FireDetection | null;
  observation?: CitizenObservation | null;
  isCompact?: boolean;
  className?: string;
}

const UNCERTAINTY_CONFIG: Record<
  UncertaintyLevel | string,
  { bg: string; text: string; border: string }
> = {
  LOW: { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' },
  MEDIUM: { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200' },
  HIGH: { bg: 'bg-rose-50', text: 'text-rose-800', border: 'border-rose-200' },
};

export const AIModelPanel: React.FC<AIModelPanelProps> = ({
  entityType,
  event,
  riskZone,
  hotspot,
  fire,
  observation,
  isCompact = false,
  className = '',
}) => {
  // ---------------------------------------------------------------------------
  // CASE 1: BASE MONITORING STATION POLLUTION EVENT (evt_*)
  // Has full model fusion, prediction horizons, confidence, signals, and explanation
  // ---------------------------------------------------------------------------
  if (entityType === 'EVENT' && event) {
    const currentObservedPm25 = event.evidence?.sensor?.pm25;
    const currentObservedPm10 = event.evidence?.sensor?.pm10;
    const anomalyScore = event.evidence?.sensor?.anomaly_score;

    const f6 = event.forecast?.pm25_6h;
    const f24 = event.forecast?.pm25_24h;
    const f72 = event.forecast?.pm25_72h;
    const spikeRisk = event.forecast?.spike_probability || 'LOW';
    const uncertainty = event.forecast?.forecast_uncertainty || 'MEDIUM';
    const uncertaintyStyle = UNCERTAINTY_CONFIG[uncertainty] || UNCERTAINTY_CONFIG.MEDIUM;

    const detectionConfidencePct = Math.round(event.detection.confidence * 100);
    const hypothesisConfidencePct = Math.round(event.source_hypothesis.confidence * 100);

    const supporting = event.detection.supporting_evidence || [];
    const contradicting = event.detection.contradicting_evidence || [];

    const isSensorSupporting = supporting.some((s) => s.includes('sensor'));
    const isCitizenSupporting = supporting.some((s) => s.includes('citizen'));
    const isSatelliteSupporting = supporting.some((s) => s.includes('satellite'));
    const isWeatherSupporting = supporting.some((s) => s.includes('weather'));

    const categoryLabel = event.source_hypothesis.category.replace(/_/g, ' ');

    return (
      <div
        className={`rounded-xl border border-sky-200/90 bg-gradient-to-b from-sky-50/40 via-white to-slate-50/50 shadow-sm overflow-hidden text-xs ${className}`}
      >
        {/* Header Ribbon */}
        <div className="bg-[#0a2540] text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-sky-500/20 border border-sky-400/30 text-sky-300 shrink-0">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate flex items-center gap-1.5">
                <span>AI & Predictive Model Dossier</span>
              </h4>
              <span className="text-[10px] text-sky-200/80 font-mono block truncate">
                Algorithm: {event.detection.method || 'weighted_fusion_v1'} • Prototype Model
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-sky-900/60 text-sky-200 px-2 py-0.5 rounded border border-sky-700/50 shrink-0">
            {event.event_id}
          </span>
        </div>

        <div className="p-3.5 space-y-3.5">
          {/* Section 1: Model Assessment & Risk Classification */}
          <div className="bg-white border border-slate-200/90 rounded-lg p-3 shadow-2xs">
            <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-100">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono flex items-center gap-1">
                <BrainCircuit className="w-3.5 h-3.5 text-sky-600" />
                <span>Model Risk Assessment</span>
              </span>
              <RiskBadge level={event.risk} size="sm" />
            </div>

            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-[11px] text-slate-600 font-medium">Inferred Source:</span>
              <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide bg-purple-50 text-purple-800 border border-purple-200 capitalize">
                {categoryLabel}
              </span>
              <span className="text-[10px] font-mono text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
                Fit Confidence: <strong>{hypothesisConfidencePct}%</strong>
              </span>
            </div>

            {/* Verbatim AI Explanation */}
            {event.explanation && (
              <div className="mt-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200/80 text-[11px] text-slate-700 leading-relaxed">
                <span className="font-bold text-slate-900 block mb-0.5 text-[10px] uppercase font-mono tracking-wider">
                  Multimodal Evidence Reasoning:
                </span>
                &ldquo;{event.explanation}&rdquo;
              </div>
            )}
          </div>

          {/* Section 2: Observed Data vs Forward Prediction Horizons */}
          <div className="bg-white border border-slate-200/90 rounded-lg p-3 shadow-2xs">
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-100">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5 text-sky-600" />
                <span>Observed vs Predicted Horizons</span>
              </span>
              <span
                className={`text-[9px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.2 rounded border ${uncertaintyStyle.bg} ${uncertaintyStyle.text} ${uncertaintyStyle.border}`}
              >
                {uncertainty} Uncertainty
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px]">
              {/* Box A: Ground Observed Telemetry */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-[9px] font-bold font-mono uppercase tracking-wider text-slate-600 block mb-1">
                  1. Ground Observed
                </span>
                <div className="space-y-0.5">
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] text-slate-500">Observed PM2.5:</span>
                    <strong className="text-slate-900 font-mono text-xs">
                      {currentObservedPm25 != null ? `${currentObservedPm25} µg/m³` : 'UNAVAILABLE'}
                    </strong>
                  </div>
                  {currentObservedPm10 != null && (
                    <div className="flex items-baseline justify-between">
                      <span className="text-[10px] text-slate-500">Observed PM10:</span>
                      <strong className="text-slate-700 font-mono text-xs">
                        {currentObservedPm10} µg/m³
                      </strong>
                    </div>
                  )}
                  {anomalyScore != null && (
                    <div className="flex items-baseline justify-between pt-1 border-t border-slate-200/60 mt-1">
                      <span className="text-[10px] text-slate-500">Anomaly Score:</span>
                      <span className="font-mono text-[10px] text-amber-800 font-bold bg-amber-50 px-1 rounded">
                        {anomalyScore.toFixed(2)}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Box B: Forward Model Prediction */}
              <div className="p-2.5 rounded-lg bg-sky-50/60 border border-sky-200">
                <span className="text-[9px] font-bold font-mono uppercase tracking-wider text-sky-900 block mb-1">
                  2. Forward Prediction
                </span>
                <div className="space-y-0.5">
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] text-slate-500">Predicted (+6h):</span>
                    <strong className="text-sky-950 font-mono text-xs">
                      {f6 != null ? `${f6} µg/m³` : 'UNAVAILABLE'}
                    </strong>
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-[10px] text-slate-500">Predicted (+24h):</span>
                    <strong className="text-sky-950 font-mono text-xs">
                      {f24 != null ? `${f24} µg/m³` : 'UNAVAILABLE'}
                    </strong>
                  </div>
                  <div className="flex items-baseline justify-between pt-1 border-t border-sky-200/60 mt-1">
                    <span className="text-[10px] text-slate-500">Spike Probability:</span>
                    <span
                      className={`font-mono text-[10px] font-bold px-1 rounded ${
                        spikeRisk === 'HIGH'
                          ? 'bg-rose-100 text-rose-800'
                          : spikeRisk === 'MEDIUM'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {spikeRisk}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {f72 != null && (
              <div className="mt-2 text-[10px] text-slate-500 font-mono flex items-center justify-between px-1">
                <span>Extended Outlook (+72h Projection):</span>
                <strong className="text-slate-800">{f72} µg/m³</strong>
              </div>
            )}
          </div>

          {/* Section 3: Model Confidence & Cross-Validation Gauge */}
          <div className="bg-white border border-slate-200/90 rounded-lg p-3 shadow-2xs">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>Detection Confidence</span>
              </span>
              <span className="font-mono text-xs font-bold text-slate-900 tabular-telemetry">
                {detectionConfidencePct}% ({event.detection.confidence.toFixed(2)})
              </span>
            </div>

            {/* Gauge Progress Bar */}
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden mb-2">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  detectionConfidencePct >= 80
                    ? 'bg-[#0a2540]'
                    : detectionConfidencePct >= 60
                    ? 'bg-sky-600'
                    : 'bg-amber-500'
                }`}
                style={{ width: `${detectionConfidencePct}%` }}
              />
            </div>

            <p className="text-[10px] text-slate-500 leading-tight">
              Derived from multi-source fusion cross-validation across telemetry, satellite spectroscopy, and crowdsourced evidence.
            </p>
          </div>

          {/* Section 4: Multi-Source Signal Breakdown & Provenance */}
          <div className="bg-white border border-slate-200/90 rounded-lg p-3 shadow-2xs">
            <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-100">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">
                Model Signals & Data Provenance
              </span>
              <span className="text-[10px] font-mono text-slate-500">
                Corroboration: <strong>{supporting.length} Supporting</strong> / <strong>{contradicting.length} Contradicting</strong>
              </span>
            </div>

            <div className="space-y-1.5 text-[11px]">
              {/* Sensor Signal */}
              {event.evidence?.sensor && (
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-50 border border-slate-200/70">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <Radio className="w-3.5 h-3.5 text-slate-700 shrink-0" />
                    <span className="font-medium text-slate-800 truncate">
                      Ground CAAQMS Station ({event.evidence.sensor.station_id})
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <ProvenanceBadge source={event.evidence.sensor.source || 'CPCB'} qualityOrFreshness={event.evidence.sensor.quality} />
                    <span
                      className={`text-[9px] font-mono px-1 rounded ${
                        isSensorSupporting ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {isSensorSupporting ? '✓ Corroborated' : 'Neutral'}
                    </span>
                  </div>
                </div>
              )}

              {/* Satellite Signal */}
              {event.evidence?.satellite && (
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-50 border border-slate-200/70">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <Orbit className="w-3.5 h-3.5 text-sky-600 shrink-0" />
                    <span className="font-medium text-slate-800 truncate">
                      Tropospheric NO₂ ({event.evidence.satellite.no2_index}) • Aerosol ({event.evidence.satellite.aerosol_index})
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <ProvenanceBadge source={event.evidence.satellite.source || 'Sentinel-5P'} qualityOrFreshness={event.evidence.satellite.freshness} />
                    <span
                      className={`text-[9px] font-mono px-1 rounded ${
                        isSatelliteSupporting ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {isSatelliteSupporting ? '✓ Corroborated' : 'Contextual'}
                    </span>
                  </div>
                </div>
              )}

              {/* Weather Signal */}
              {event.evidence?.weather && (
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-50 border border-slate-200/70">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <Wind className="w-3.5 h-3.5 text-cyan-600 shrink-0" />
                    <span className="font-medium text-slate-800 truncate">
                      Atmospheric Wind: {event.evidence.weather.wind_speed_kmh} km/h • {event.evidence.weather.humidity_percent}% RH
                    </span>
                  </div>
                  <ProvenanceBadge source={event.evidence.weather.source || 'Weather'} />
                </div>
              )}

              {/* Citizen Signal */}
              {event.evidence?.citizen && (
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-50 border border-slate-200/70">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <Users className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                    <span className="font-medium text-slate-800 truncate">
                      Gemini Visual Classifier: &ldquo;{event.evidence.citizen.gemini_output?.event_type}&rdquo; ({event.evidence.citizen.gemini_output?.confidence ? Math.round(event.evidence.citizen.gemini_output.confidence * 100) + '%' : 'Unknown'})
                    </span>
                  </div>
                  <ProvenanceBadge source="citizen" qualityOrFreshness={event.evidence.citizen.freshness} />
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions (if in compact drawer) */}
          {isCompact && event.event_id && (
            <div className="pt-1">
              <Link
                href={`/dashboard/event/${event.event_id}`}
                className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
              >
                <span>Inspect Full Evidence Dossier</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // CASE 2: PM2.5 RISK ZONE (zone_*)
  // Has predicted PM2.5, horizon, uncertainty band, and prediction confidence
  // ---------------------------------------------------------------------------
  if (entityType === 'RISK_ZONE' && riskZone) {
    return (
      <div
        className={`rounded-xl border border-emerald-200/90 bg-gradient-to-b from-emerald-50/40 via-white to-slate-50/50 shadow-sm overflow-hidden text-xs ${className}`}
      >
        {/* Header Ribbon */}
        <div className="bg-emerald-900 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-emerald-500/20 border border-emerald-400/30 text-emerald-300 shrink-0">
              <Layers className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate">
                AI Dispersion Risk Corridor
              </h4>
              <span className="text-[10px] text-emerald-200 font-mono block truncate">
                Atmospheric Dispersion Simulation • Prototype Model
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-emerald-950/60 text-emerald-200 px-2 py-0.5 rounded border border-emerald-700/50 shrink-0">
            {riskZone.id}
          </span>
        </div>

        <div className="p-3.5 space-y-3">
          {/* Section 1: Model Prediction */}
          <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-2xs">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500 block mb-0.5 font-mono">
                  Model Predicted PM2.5
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-black text-slate-900 font-mono">
                    {riskZone.predicted_pm25}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">µg/m³</span>
                </div>
              </div>
              <RiskBadge level={riskZone.level} size="sm" />
            </div>

            <div className="mt-2.5 pt-2 border-t border-slate-100 grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-1.5 rounded bg-slate-50 border border-slate-200">
                <span className="text-[9px] font-mono text-slate-400 block uppercase">Horizon</span>
                <span className="font-bold text-slate-800 font-mono">{riskZone.forecast_horizon}</span>
              </div>
              <div className="p-1.5 rounded bg-slate-50 border border-slate-200">
                <span className="text-[9px] font-mono text-slate-400 block uppercase">Prediction Confidence</span>
                <span className="font-bold text-slate-800 font-mono">{riskZone.prediction_confidence}%</span>
              </div>
            </div>

            {riskZone.forecast_uncertainty && (
              <div className="mt-1.5 p-1.5 rounded bg-slate-50 border border-slate-200 text-[10px] font-mono text-slate-600 flex items-center justify-between">
                <span>Model Uncertainty Band:</span>
                <strong className="text-slate-800">{riskZone.forecast_uncertainty}</strong>
              </div>
            )}
          </div>

          {/* Notice: Purely modeled corridor without direct sensor */}
          <div className="p-2 bg-emerald-50/70 border border-emerald-200 rounded-lg text-[10px] text-emerald-900 flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 text-emerald-700 shrink-0 mt-0.5" />
            <span>
              {riskZone.simulation_disclaimer || 'Prototype simulation data — regional atmospheric dispersion exposure projection.'}
            </span>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // CASE 3: EMISSION HOTSPOT (hs_*)
  // Has estimated PM2.5, severity, detection confidence, and possible source
  // ---------------------------------------------------------------------------
  if (entityType === 'HOTSPOT' && hotspot) {
    const confidencePct = Math.round(hotspot.confidence * 100);

    return (
      <div
        className={`rounded-xl border border-purple-200/90 bg-gradient-to-b from-purple-50/40 via-white to-slate-50/50 shadow-sm overflow-hidden text-xs ${className}`}
      >
        {/* Header */}
        <div className="bg-purple-950 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-purple-500/20 border border-purple-400/30 text-purple-300 shrink-0">
              <Activity className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate">
                AI Emission Plume Assessment
              </h4>
              <span className="text-[10px] text-purple-200 font-mono block truncate">
                Hotspot Screening Model • Prototype Simulation
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-purple-900 text-purple-200 px-2 py-0.5 rounded border border-purple-700 shrink-0">
            {hotspot.id}
          </span>
        </div>

        <div className="p-3.5 space-y-3">
          <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-2xs">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500 block mb-0.5 font-mono">
                  Estimated PM2.5 Loading
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-black text-slate-900 font-mono">
                    {hotspot.estimatedPm25}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">µg/m³</span>
                </div>
              </div>
              <RiskBadge level={hotspot.severity} size="sm" />
            </div>

            <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Detection Confidence:</span>
              <strong className="font-mono text-slate-900">{confidencePct}%</strong>
            </div>
          </div>

          {hotspot.possibleSource && (
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px]">
              <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500 block mb-1 font-mono">
                Source Inference:
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
  // Satellite thermal detection telemetry — NOT labeled as AI prediction
  // ---------------------------------------------------------------------------
  if (entityType === 'FIRE' && fire) {
    return (
      <div
        className={`rounded-xl border border-amber-200/90 bg-gradient-to-b from-amber-50/40 via-white to-slate-50/50 shadow-sm overflow-hidden text-xs ${className}`}
      >
        {/* Header */}
        <div className="bg-amber-950 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-amber-500/20 border border-amber-400/30 text-amber-300 shrink-0">
              <Flame className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate">
                Thermal Detection Telemetry
              </h4>
              <span className="text-[10px] text-amber-200 font-mono block truncate">
                Satellite Thermal Observation (Demonstration Feed)
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-amber-900 text-amber-200 px-2 py-0.5 rounded border border-amber-700 shrink-0">
            {fire.id}
          </span>
        </div>

        <div className="p-3.5 space-y-2.5">
          <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[10px] text-slate-500 uppercase font-mono">Status:</span>
              <strong className="text-amber-800 font-semibold">{fire.status} Thermal Anomaly</strong>
            </div>

            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[10px] text-slate-500 uppercase font-mono">Thermal Intensity:</span>
              <span className="px-1.5 py-0.5 rounded font-bold uppercase text-[10px] bg-amber-100 text-amber-900 border border-amber-300">
                {fire.intensity} Intensity
              </span>
            </div>

            {fire.sizeHectares !== undefined && (
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-[10px] text-slate-500 uppercase font-mono">Burn Area:</span>
                <strong className="font-mono text-slate-900">{fire.sizeHectares} Hectares</strong>
              </div>
            )}

            {fire.pm25Contribution && (
              <div className="flex items-center justify-between text-[11px] pt-1.5 border-t border-slate-100">
                <span className="text-[10px] text-slate-500 uppercase font-mono">Modeled PM2.5 Impact:</span>
                <strong className="font-mono text-slate-900">{fire.pm25Contribution}</strong>
              </div>
            )}
          </div>

          {fire.pollutionRelationship && (
            <p className="text-[11px] text-slate-700 bg-slate-50 p-2 rounded border border-slate-200 leading-relaxed">
              <strong>Downwind Exposure:</strong> {fire.pollutionRelationship}
            </p>
          )}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // CASE 5: CITIZEN OBSERVATION (obs_*)
  // Ground photographic evidence — graceful indication of model relationship
  // ---------------------------------------------------------------------------
  if (entityType === 'OBSERVATION' && observation) {
    return (
      <div
        className={`rounded-xl border border-sky-200/90 bg-gradient-to-b from-sky-50/30 via-white to-slate-50/50 shadow-sm overflow-hidden text-xs ${className}`}
      >
        <div className="bg-sky-950 text-white px-3.5 py-2.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded bg-sky-500/20 border border-sky-400/30 text-sky-300 shrink-0">
              <Camera className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs uppercase tracking-wider text-white truncate">
                Citizen Ground Evidence
              </h4>
              <span className="text-[10px] text-sky-200 font-mono block truncate">
                Crowdsourced Field Telemetry
              </span>
            </div>
          </div>
          <span className="font-mono text-[10px] bg-sky-900 text-sky-200 px-2 py-0.5 rounded border border-sky-700 shrink-0">
            {observation.id}
          </span>
        </div>

        <div className="p-3.5 space-y-2.5">
          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-700">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Field Measurement:</span>
              <strong className="font-mono text-slate-900">{observation.pm25AtLocation} µg/m³ PM2.5</strong>
            </div>
            <p className="text-slate-600 text-[10px]">
              {observation.description || 'Photographic particulate evidence submitted by citizen.'}
            </p>
          </div>

          {observation.relatedEventId ? (
            <div className="p-2 bg-sky-50 border border-sky-200 rounded-lg text-[10px] text-sky-900 flex items-center justify-between">
              <span>Cross-referenced with Incident: <strong>{observation.relatedEventId}</strong></span>
              <Link
                href={`/dashboard/event/${observation.relatedEventId}`}
                className="font-bold text-sky-700 hover:underline flex items-center gap-0.5"
              >
                <span>View Model Dossier</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          ) : (
            <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg text-[10px] text-slate-500 italic">
              Model assessment unlinked for this standalone observation.
            </div>
          )}
        </div>
      </div>
    );
  }

  // Graceful empty fallback
  return null;
};

export default AIModelPanel;

import React from 'react';
import {
  CitizenEvidence,
  SensorEvidence,
  SatelliteEvidence,
  WeatherEvidence,
} from '@/lib/types';
import ProvenanceBadge from '@/components/ui/ProvenanceBadge';
import {
  CheckCircle2,
  AlertTriangle,
  Users,
  Gauge,
  Orbit,
  Wind,
  Image as ImageIcon,
  Check,
  X,
} from 'lucide-react';

interface CorroborationStatusProps {
  isSupporting: boolean;
  isContradicting: boolean;
}

const CorroborationStatus: React.FC<CorroborationStatusProps> = ({
  isSupporting,
  isContradicting,
}) => {
  if (isSupporting) {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
        Supporting Evidence
      </span>
    );
  }
  if (isContradicting) {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
        <AlertTriangle className="w-3 h-3 text-amber-600" />
        Contradicting Evidence
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
      Neutral / Contextual
    </span>
  );
};

// 1. Citizen Evidence Card
export const CitizenEvidenceCard: React.FC<{
  evidence?: CitizenEvidence | null;
  isSupporting: boolean;
  isContradicting: boolean;
}> = ({ evidence, isSupporting, isContradicting }) => {
  if (!evidence) {
    return (
      <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 text-slate-400 text-xs">
        No citizen report evidence on record for this event.
      </div>
    );
  }

  return (
    <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 flex flex-col justify-between shadow-xs">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-slate-100 text-[#0a2540]">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#0f172a]">
                Citizen Report
              </h4>
              <ProvenanceBadge
                source={evidence.source || 'Citizen'}
                qualityOrFreshness={evidence.freshness}
                className="mt-1"
              />
            </div>
          </div>
          <CorroborationStatus
            isSupporting={isSupporting}
            isContradicting={isContradicting}
          />
        </div>

        <div className="bg-slate-50 rounded p-3 border border-slate-200/80 mb-3">
          <p className="text-xs text-slate-800 italic">
            &ldquo;{evidence.gemini_output.description}&rdquo;
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-[#64748b]">
            <span>
              Type: <strong className="text-slate-900 capitalize">{evidence.gemini_output.event_type}</strong>
            </span>
            <span>•</span>
            <span>
              Severity: <strong className="text-slate-900 capitalize">{evidence.gemini_output.severity}</strong>
            </span>
            <span>•</span>
            <span>
              Gemini Conf: <strong className="text-slate-900 tabular-telemetry">{Math.round(evidence.gemini_output.confidence * 100)}%</strong>
            </span>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-[#64748b]">
        <div className="flex items-center gap-1.5">
          <ImageIcon className="w-3.5 h-3.5 text-slate-400" />
          <span>{(evidence.photo_url || evidence.supabase_path) ? 'Observation photo attached' : 'No photo uploaded'}</span>
        </div>
        {(evidence.photo_url || evidence.supabase_path) && (
          <span className="text-[10px] text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200">
            Image Verified
          </span>
        )}
      </div>
    </div>
  );
};

// 2. Sensor Evidence Card
export const SensorEvidenceCard: React.FC<{
  evidence?: SensorEvidence | null;
  isSupporting: boolean;
  isContradicting: boolean;
}> = ({ evidence, isSupporting, isContradicting }) => {
  if (!evidence) {
    return (
      <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 text-slate-400 text-xs">
        No ground sensor evidence linked to this event.
      </div>
    );
  }

  return (
    <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 flex flex-col justify-between shadow-xs">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-slate-100 text-[#0a2540]">
              <Gauge className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#0f172a]">
                Ground Sensor Grid
              </h4>
              <ProvenanceBadge
                source={evidence.source || 'CPCB'}
                qualityOrFreshness={evidence.quality}
                className="mt-1"
              />
            </div>
          </div>
          <CorroborationStatus
            isSupporting={isSupporting}
            isContradicting={isContradicting}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="bg-slate-50 rounded p-2.5 border border-slate-200/80">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748b] block">
              PM2.5 Observation
            </span>
            <span className="text-xl font-bold text-[#0f172a] tabular-telemetry">
              {evidence.pm25}
            </span>
            <span className="text-[10px] text-slate-500 ml-1">µg/m³</span>
          </div>

          <div className="bg-slate-50 rounded p-2.5 border border-slate-200/80">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748b] block">
              PM10 Observation
            </span>
            <span className="text-xl font-bold text-[#0f172a] tabular-telemetry">
              {evidence.pm10}
            </span>
            <span className="text-[10px] text-slate-500 ml-1">µg/m³</span>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-[#64748b]">
        <span className="font-mono text-[11px] text-slate-600 truncate">
          Station: {evidence.station_id}
        </span>
        <span className="text-[11px] font-mono tabular-telemetry text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
          Anomaly: {evidence.anomaly_score != null ? evidence.anomaly_score.toFixed(2) : 'N/A'}
        </span>
      </div>
    </div>
  );
};

// 3. Satellite Evidence Card
export const SatelliteEvidenceCard: React.FC<{
  evidence?: SatelliteEvidence | null;
  isSupporting: boolean;
  isContradicting: boolean;
}> = ({ evidence, isSupporting, isContradicting }) => {
  if (!evidence) {
    return (
      <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 text-slate-400 text-xs">
        No satellite pass ingest on record for this event.
      </div>
    );
  }

  return (
    <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 flex flex-col justify-between shadow-xs">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-sky-50 text-[#0284c7]">
              <Orbit className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#0f172a]">
                Orbital Satellite
              </h4>
              <ProvenanceBadge
                source={evidence.source || 'Sentinel-5P'}
                qualityOrFreshness={evidence.freshness}
                className="mt-1"
              />
            </div>
          </div>
          <CorroborationStatus
            isSupporting={isSupporting}
            isContradicting={isContradicting}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="bg-slate-50 rounded p-2.5 border border-slate-200/80">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748b] block">
              NO₂ Column Index
            </span>
            <span className="text-xl font-bold text-[#0f172a] tabular-telemetry">
              {evidence.no2_index.toFixed(1)}
            </span>
            <span className="text-[10px] text-slate-500 ml-1">mol/m²</span>
          </div>

          <div className="bg-slate-50 rounded p-2.5 border border-slate-200/80">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748b] block">
              Aerosol Index (AI)
            </span>
            <span className="text-xl font-bold text-[#0f172a] tabular-telemetry">
              {evidence.aerosol_index.toFixed(2)}
            </span>
            <span className="text-[10px] text-slate-500 ml-1">index</span>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-[#64748b]">
        <span>Spectral Band: UV-VIS/TROPOMI</span>
        <span className="text-[10px] font-mono uppercase text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-100">
          Spatial Resolution 5.5km
        </span>
      </div>
    </div>
  );
};

// 4. Weather Evidence Card
export const WeatherEvidenceCard: React.FC<{
  evidence?: WeatherEvidence | null;
  isSupporting: boolean;
  isContradicting: boolean;
}> = ({ evidence, isSupporting, isContradicting }) => {
  if (!evidence) {
    return (
      <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 text-slate-400 text-xs">
        No meteorological readings available.
      </div>
    );
  }

  return (
    <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 flex flex-col justify-between shadow-xs">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-cyan-50 text-cyan-800">
              <Wind className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#0f172a]">
                Meteorology & Atmospheric Conditions
              </h4>
              <ProvenanceBadge
                source={evidence.source || 'Weather'}
                className="mt-1"
              />
            </div>
          </div>
          <CorroborationStatus
            isSupporting={isSupporting}
            isContradicting={isContradicting}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="bg-slate-50 rounded p-2.5 border border-slate-200/80">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748b] block">
              Surface Wind Speed
            </span>
            <span className="text-xl font-bold text-[#0f172a] tabular-telemetry">
              {evidence.wind_speed_kmh}
            </span>
            <span className="text-[10px] text-slate-500 ml-1">km/h</span>
          </div>

          <div className="bg-slate-50 rounded p-2.5 border border-slate-200/80">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748b] block">
              Relative Humidity
            </span>
            <span className="text-xl font-bold text-[#0f172a] tabular-telemetry">
              {evidence.humidity_percent}
            </span>
            <span className="text-[10px] text-slate-500 ml-1">%</span>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-[#64748b]">
        <span>
          Ventilation Condition:{' '}
          <strong className="text-slate-800 font-semibold">
            {evidence.wind_speed_kmh != null ? (evidence.wind_speed_kmh < 5 ? 'Stagnant (Trap)' : 'Active Venting') : 'Unknown'}
          </strong>
        </span>
        <span className="text-[10px] font-mono text-slate-500 uppercase">
          Open-Meteo Synoptic
        </span>
      </div>
    </div>
  );
};

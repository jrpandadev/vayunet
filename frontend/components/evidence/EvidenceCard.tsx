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
      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#27E0C3] bg-[rgba(39,224,195,0.1)] px-2 py-0.5 rounded border border-[rgba(39,224,195,0.25)]">
        <CheckCircle2 className="w-3 h-3 text-[#27E0C3]" />
        Supporting Evidence
      </span>
    );
  }
  if (isContradicting) {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#FFB52E] bg-[rgba(255,181,46,0.1)] px-2 py-0.5 rounded border border-[rgba(255,181,46,0.25)]">
        <AlertTriangle className="w-3 h-3 text-[#FFB52E]" />
        Contradicting Evidence
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#7BA4BC] bg-[rgba(255,255,255,0.05)] px-2 py-0.5 rounded border border-[rgba(255,255,255,0.1)]">
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
      <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 text-[#7BA4BC] text-xs">
        No citizen report evidence on record for this event.
      </div>
    );
  }

  return (
    <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 flex flex-col justify-between shadow-lg shadow-black/20">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[rgba(0,213,255,0.08)] text-[#00E5FF]">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
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

        <div className="bg-[rgba(255,255,255,0.02)] rounded p-3 border border-[rgba(0,213,255,0.1)] mb-3">
          <p className="text-xs text-[#E8F4FD] italic">
            &ldquo;{evidence.gemini_output.description}&rdquo;
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-[#7BA4BC]">
            <span>
              Type: <strong className="text-[#E8F4FD] capitalize">{evidence.gemini_output.event_type}</strong>
            </span>
            <span>•</span>
            <span>
              Severity: <strong className="text-[#E8F4FD] capitalize">{evidence.gemini_output.severity}</strong>
            </span>
            <span>•</span>
            <span>
              Gemini Conf: <strong className="text-[#00E5FF] tabular-telemetry">{Math.round(evidence.gemini_output.confidence * 100)}%</strong>
            </span>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-[rgba(0,213,255,0.1)] flex items-center justify-between text-xs text-[#7BA4BC]">
        <div className="flex items-center gap-1.5">
          <ImageIcon className="w-3.5 h-3.5 text-[#2E5470]" />
          <span>{(evidence.photo_url || evidence.supabase_path) ? 'Observation photo attached' : 'No photo uploaded'}</span>
        </div>
        {(evidence.photo_url || evidence.supabase_path) && (
          <span className="text-[10px] text-[#00E5FF] bg-[rgba(0,213,255,0.08)] px-1.5 py-0.5 rounded border border-[rgba(0,213,255,0.2)]">
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
      <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 text-[#7BA4BC] text-xs">
        No ground sensor evidence linked to this event.
      </div>
    );
  }

  return (
    <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 flex flex-col justify-between shadow-lg shadow-black/20">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[rgba(0,213,255,0.08)] text-[#00E5FF]">
              <Gauge className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
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
          <div className="bg-[rgba(255,255,255,0.02)] rounded p-2.5 border border-[rgba(0,213,255,0.1)]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#7BA4BC] block">
              PM2.5 Observation
            </span>
            <span className="text-xl font-bold text-[#E8F4FD] tabular-telemetry">
              {evidence.pm25}
            </span>
            <span className="text-[10px] text-[#2E5470] ml-1">µg/m³</span>
          </div>

          <div className="bg-[rgba(255,255,255,0.02)] rounded p-2.5 border border-[rgba(0,213,255,0.1)]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#7BA4BC] block">
              PM10 Observation
            </span>
            <span className="text-xl font-bold text-[#E8F4FD] tabular-telemetry">
              {evidence.pm10}
            </span>
            <span className="text-[10px] text-[#2E5470] ml-1">µg/m³</span>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-[rgba(0,213,255,0.1)] flex items-center justify-between text-xs text-[#7BA4BC]">
        <span className="font-mono text-[11px] text-[#2E5470] truncate">
          Station: {evidence.station_id}
        </span>
        <span className="text-[11px] font-mono tabular-telemetry text-[#00E5FF] bg-[rgba(0,213,255,0.05)] border border-[rgba(0,213,255,0.1)] px-1.5 py-0.5 rounded">
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
      <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 text-[#7BA4BC] text-xs">
        No satellite pass ingest on record for this event.
      </div>
    );
  }

  return (
    <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 flex flex-col justify-between shadow-lg shadow-black/20">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[rgba(0,213,255,0.08)] text-[#00E5FF]">
              <Orbit className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
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
          <div className="bg-[rgba(255,255,255,0.02)] rounded p-2.5 border border-[rgba(0,213,255,0.1)]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#7BA4BC] block">
              NO₂ Column Index
            </span>
            <span className="text-xl font-bold text-[#E8F4FD] tabular-telemetry">
              {evidence.no2_index.toFixed(1)}
            </span>
            <span className="text-[10px] text-[#2E5470] ml-1">mol/m²</span>
          </div>

          <div className="bg-[rgba(255,255,255,0.02)] rounded p-2.5 border border-[rgba(0,213,255,0.1)]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#7BA4BC] block">
              Aerosol Index (AI)
            </span>
            <span className="text-xl font-bold text-[#E8F4FD] tabular-telemetry">
              {evidence.aerosol_index.toFixed(2)}
            </span>
            <span className="text-[10px] text-[#2E5470] ml-1">index</span>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-[rgba(0,213,255,0.1)] flex items-center justify-between text-xs text-[#7BA4BC]">
        <span>Spectral Band: UV-VIS/TROPOMI</span>
        <span className="text-[10px] font-mono uppercase text-[#00E5FF] bg-[rgba(0,213,255,0.05)] border border-[rgba(0,213,255,0.1)] px-1.5 py-0.5 rounded">
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
      <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 text-[#7BA4BC] text-xs">
        No meteorological readings available.
      </div>
    );
  }

  return (
    <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 flex flex-col justify-between shadow-lg shadow-black/20">
      <div>
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[rgba(0,213,255,0.08)] text-[#00E5FF]">
              <Wind className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
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
          <div className="bg-[rgba(255,255,255,0.02)] rounded p-2.5 border border-[rgba(0,213,255,0.1)]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#7BA4BC] block">
              Surface Wind Speed
            </span>
            <span className="text-xl font-bold text-[#E8F4FD] tabular-telemetry">
              {evidence.wind_speed_kmh}
            </span>
            <span className="text-[10px] text-[#2E5470] ml-1">km/h</span>
          </div>

          <div className="bg-[rgba(255,255,255,0.02)] rounded p-2.5 border border-[rgba(0,213,255,0.1)]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#7BA4BC] block">
              Relative Humidity
            </span>
            <span className="text-xl font-bold text-[#E8F4FD] tabular-telemetry">
              {evidence.humidity_percent}
            </span>
            <span className="text-[10px] text-[#2E5470] ml-1">%</span>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-[rgba(0,213,255,0.1)] flex items-center justify-between text-xs text-[#7BA4BC]">
        <span>
          Ventilation Condition:{' '}
          <strong className="text-[#00E5FF] font-semibold">
            {evidence.wind_speed_kmh != null ? (evidence.wind_speed_kmh < 5 ? 'Stagnant (Trap)' : 'Active Venting') : 'Unknown'}
          </strong>
        </span>
        <span className="text-[10px] font-mono text-[#2E5470] uppercase">
          Open-Meteo Synoptic
        </span>
      </div>
    </div>
  );
};
